import pytest
from pydantic import ValidationError

from app.schemas import ExampleInput, MAX_TEXT_LENGTH, normalize_text


def test_trims_unicode_whitespace() -> None:
    assert normalize_text("\t\u00a0Привіт!\r\n") == "Привіт!"


def test_accepts_one_character() -> None:
    assert normalize_text("1") == "1"


def test_accepts_maximum_length_after_trim() -> None:
    text = "а" * MAX_TEXT_LENGTH
    assert normalize_text(" " + text + "\n") == text


def test_rejects_whitespace_only() -> None:
    with pytest.raises(ValueError, match="Введіть текст"):
        normalize_text(" \r\n\u2003")


def test_rejects_non_string() -> None:
    with pytest.raises(ValueError, match="Введіть текст"):
        normalize_text(123)


def test_rejects_too_long_text() -> None:
    with pytest.raises(ValueError, match="до 2000"):
        normalize_text("б" * (MAX_TEXT_LENGTH + 1))


def test_rejects_embedded_null_character() -> None:
    with pytest.raises(ValueError, match="недопустимий символ"):
        normalize_text("текст\x00прикладу")


def test_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError, match="category_code"):
        ExampleInput.model_validate(
            {"text": "Що нового?", "category_code": "unknown", "dataset_split": "train"}
        )
