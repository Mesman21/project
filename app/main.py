import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import auth, database
from .classifier import ArtifactUnavailable, load_artifacts
from .schemas import (
    Account,
    ClassificationRequest,
    ClassificationResult,
    EvaluationSummary,
    ExampleInput,
    ExampleRecord,
    LoginRequest,
)
from .settings import Settings

MessageId = Annotated[int, Path(ge=1)]
operator = auth.require_role("operator", "maintainer")
coordinator = auth.require_role("coordinator", "maintainer")
maintainer = auth.require_role("maintainer")


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.from_environment()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database.initialize_database(config.database)
        application.state.artifacts = load_artifacts(config.artifacts)
        yield

    application = FastAPI(
        title="Класифікатор повідомлень", lifespan=lifespan
    )
    application.state.settings = config
    application.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"]
    )

    @application.middleware("http")
    async def protect_local_api(request: Request, call_next):
        is_api = request.url.path.startswith("/api/")
        origin = request.headers.get("origin")
        if (
            is_api and request.method in {"POST", "PUT", "DELETE"}
            and origin and origin != str(request.base_url).rstrip("/")
        ):
            return JSONResponse(
                status_code=403, content={"detail": "Запит має інше джерело."}
            )
        response = await call_next(request)
        if is_api:
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        for item in error.errors():
            if item["loc"] == ("body", "text"):
                cause = item.get("ctx", {}).get("error")
                detail = str(cause) if cause else "Введіть текст повідомлення."
                return JSONResponse(status_code=422, content={"detail": detail})
        return JSONResponse(
            status_code=422, content={"detail": "Перевірте дані запиту."}
        )

    @application.exception_handler(database.DatasetConflict)
    async def data_conflict(request: Request, error: database.DatasetConflict):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @application.exception_handler(sqlite3.IntegrityError)
    async def invalid_write(request: Request, error: sqlite3.IntegrityError):
        detail = "Запис суперечить обмеженням бази даних."
        if error.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE":
            detail = "Такий текст уже є у списку."
        return JSONResponse(status_code=409, content={"detail": detail})

    @application.exception_handler(sqlite3.OperationalError)
    async def unavailable_database(request: Request, error: sqlite3.OperationalError):
        return JSONResponse(
            status_code=503, content={"detail": "База даних тимчасово недоступна."}
        )

    @application.exception_handler(ArtifactUnavailable)
    async def unavailable_artifact(request: Request, error: ArtifactUnavailable):
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @application.post("/api/auth/login")
    def sign_in(payload: LoginRequest, request: Request, response: Response) -> Account:
        authenticated = auth.login(
            config.database, payload.username, payload.password,
            request.cookies.get(auth.SESSION_COOKIE),
        )
        if authenticated is None:
            raise HTTPException(status_code=401, detail="Неправильний логін або пароль.")
        account, token = authenticated
        response.set_cookie(
            auth.SESSION_COOKIE, token, max_age=auth.SESSION_SECONDS,
            httponly=True, samesite="strict",
        )
        return account

    @application.get("/api/auth/me")
    def who_am_i(account: Annotated[Account, Depends(auth.current_account)]) -> Account:
        return account

    @application.post("/api/auth/logout", status_code=204)
    def sign_out(request: Request) -> Response:
        auth.logout(config.database, request.cookies.get(auth.SESSION_COOKIE))
        response = Response(status_code=204)
        response.delete_cookie(auth.SESSION_COOKIE, httponly=True, samesite="strict")
        return response

    @application.post("/api/classify", dependencies=[Depends(operator)])
    def classify(payload: ClassificationRequest, request: Request) -> ClassificationResult:
        return request.app.state.artifacts.classify(payload.text)

    @application.get("/api/statistics", dependencies=[Depends(coordinator)])
    def statistics(request: Request) -> EvaluationSummary:
        return request.app.state.artifacts.summary()

    @application.get("/api/examples", dependencies=[Depends(maintainer)])
    def examples() -> list[ExampleRecord]:
        return database.list_examples(config.database)

    @application.post("/api/examples", status_code=201, dependencies=[Depends(maintainer)])
    def create_example(payload: ExampleInput) -> ExampleRecord:
        return database.add_example(config.database, payload)

    @application.get("/api/examples/{message_id}", dependencies=[Depends(maintainer)])
    def read_example(message_id: MessageId) -> ExampleRecord:
        record = database.get_example(config.database, message_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Приклад не знайдено.")
        return record

    @application.put("/api/examples/{message_id}", dependencies=[Depends(maintainer)])
    def edit_example(message_id: MessageId, payload: ExampleInput) -> ExampleRecord:
        record = database.update_example(config.database, message_id, payload)
        if record is None:
            raise HTTPException(status_code=404, detail="Приклад не знайдено.")
        return record

    @application.delete(
        "/api/examples/{message_id}", status_code=204, dependencies=[Depends(maintainer)]
    )
    def remove_example(message_id: MessageId) -> Response:
        if not database.delete_example(config.database, message_id):
            raise HTTPException(status_code=404, detail="Приклад не знайдено.")
        return Response(status_code=204)

    if (config.frontend / "assets").is_dir():
        application.mount(
            "/assets", StaticFiles(directory=config.frontend / "assets"), name="assets"
        )

    @application.get("/", include_in_schema=False)
    def index() -> FileResponse:
        path = config.frontend / "index.html"
        if not path.is_file():
            raise HTTPException(status_code=503, detail="Спочатку зберіть фронтенд Vite.")
        return FileResponse(path)

    return application


app = create_app()
