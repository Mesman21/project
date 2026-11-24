import re
import secrets
from collections.abc import Callable
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from time import time
from typing import get_args

from fastapi import HTTPException, Request
from pwdlib import PasswordHash

from .database import connect
from .schemas import Account, Role

SESSION_COOKIE = "classifier_session"
SESSION_SECONDS = 8 * 60 * 60
password_hash = PasswordHash.recommended()


def _token_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return password_hash.hash(secrets.token_urlsafe(32))


def create_account(
    path: Path, username: str, password: str, role: Role
) -> None:
    username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]{3,32}", username):
        raise ValueError("Логін має містити від 3 до 32 латинських символів.")
    if not 15 <= len(password) <= 128:
        raise ValueError("Пароль має містити від 15 до 128 символів.")
    if role not in get_args(Role):
        raise ValueError("Невідома роль.")
    hashed = password_hash.hash(password)
    with connect(path) as db:
        db.execute(
            "INSERT INTO accounts (username, password_hash, role) "
            "VALUES (?, ?, ?)",
            (username, hashed, role),
        )


def login(
    path: Path, username: str, password: str, previous_token: str | None
) -> tuple[Account, str] | None:
    with connect(path) as db:
        account = db.execute(
            "SELECT account_id, username, password_hash, role FROM accounts "
            "WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
    valid = password_hash.verify(
        password, account["password_hash"] if account else _dummy_hash()
    )
    if not valid or account is None:
        return None

    token = secrets.token_urlsafe(32)
    now = int(time())
    with connect(path, immediate=True) as db:
        db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        if previous_token:
            db.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (_token_hash(previous_token),),
            )
        db.execute(
            "INSERT INTO sessions (token_hash, account_id, expires_at) "
            "VALUES (?, ?, ?)",
            (_token_hash(token), account["account_id"], now + SESSION_SECONDS),
        )
    return Account(username=account["username"], role=account["role"]), token


def logout(path: Path, token: str | None) -> None:
    if token:
        with connect(path) as db:
            db.execute(
                "DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),)
            )


def current_account(request: Request) -> Account:
    token = request.cookies.get(SESSION_COOKIE)
    if token and len(token) == 43:
        with connect(request.app.state.settings.database) as db:
            row = db.execute(
                "SELECT a.username, a.role FROM sessions AS s "
                "JOIN accounts AS a USING (account_id) "
                "WHERE s.token_hash = ? AND s.expires_at > ?",
                (_token_hash(token), int(time())),
            ).fetchone()
        if row is not None:
            return Account.model_validate(dict(row))
    raise HTTPException(status_code=401, detail="Увійдіть до системи.")


def require_role(*roles: Role) -> Callable[[Request], Account]:
    def check(request: Request) -> Account:
        account = current_account(request)
        if account.role not in roles:
            raise HTTPException(
                status_code=403, detail="Для цієї дії потрібна інша роль."
            )
        return account

    return check
