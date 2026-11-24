from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

CategoryCode = Literal["information_request", "incident_report", "suggestion"]
DatasetSplit = Literal["train", "test"]
Role = Literal["operator", "coordinator", "maintainer"]

CATEGORIES: dict[CategoryCode, str] = {
    "information_request": "Інформаційний запит",
    "incident_report": "Повідомлення про збій",
    "suggestion": "Пропозиція",
}
MAX_TEXT_LENGTH = 2000


def normalize_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Введіть текст повідомлення.")
    text = value.strip()
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError("Введіть до 2000 символів.")
    if "\0" in text:
        raise ValueError("Текст містить недопустимий символ.")
    return text


class ClassificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: Annotated[str, BeforeValidator(normalize_text)]


class ExampleInput(ClassificationRequest):
    category_code: CategoryCode
    dataset_split: DatasetSplit


class ExampleRecord(ExampleInput):
    message_id: int
    locked: bool


class ClassificationResult(BaseModel):
    category_code: CategoryCode
    category_name: str


class CategoryStatistics(ClassificationResult):
    count: Annotated[int, Field(ge=0)]
    share: Annotated[float, Field(ge=0, le=1)]


class EvaluationSummary(BaseModel):
    total: Annotated[int, Field(ge=0)]
    categories: list[CategoryStatistics]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Annotated[str, Field(min_length=1, max_length=32)]
    password: Annotated[str, Field(min_length=1, max_length=128)]


class Account(BaseModel):
    username: str
    role: Role
