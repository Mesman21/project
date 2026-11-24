import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import joblib
from sklearn.pipeline import Pipeline

from .schemas import (
    CATEGORIES,
    CategoryCode,
    ClassificationResult,
    EvaluationSummary,
)

logger = logging.getLogger(__name__)
ACTIVE_MODEL_FILE = "active_model.txt"


class ArtifactUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class ActiveArtifacts:
    directory: Path | None
    pipeline: Pipeline | None

    def classify(self, text: str) -> ClassificationResult:
        if self.pipeline is None:
            raise ArtifactUnavailable("Модель недоступна. Навчіть її локально.")
        code = str(self.pipeline.predict([text])[0])
        if code not in CATEGORIES:
            raise ArtifactUnavailable("Модель повернула невідому категорію.")
        category_code = cast(CategoryCode, code)
        return ClassificationResult(
            category_code=category_code, category_name=CATEGORIES[category_code]
        )

    def summary(self) -> EvaluationSummary:
        if self.directory is None:
            return EvaluationSummary(total=0, categories=[])
        try:
            content = (self.directory / "statistics.json").read_text(
                encoding="utf-8"
            )
        except FileNotFoundError:
            return EvaluationSummary(total=0, categories=[])
        except OSError as error:
            raise ArtifactUnavailable("Зведення недоступне.") from error
        try:
            return EvaluationSummary.model_validate_json(content)
        except ValueError as error:
            raise ArtifactUnavailable("Файл зведення пошкоджений.") from error


def load_artifacts(root: Path) -> ActiveArtifacts:
    try:
        version = (root / ACTIVE_MODEL_FILE).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ActiveArtifacts(None, None)
    except (OSError, ValueError):
        logger.warning("Не вдалося прочитати версію активної моделі.")
        return ActiveArtifacts(None, None)
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", version):
        return ActiveArtifacts(None, None)

    folder = root / version
    try:
        pipeline = joblib.load(folder / "model.joblib")
    except Exception:
        logger.warning("Не вдалося завантажити локальну модель.")
        pipeline = None
    return ActiveArtifacts(folder, pipeline if isinstance(pipeline, Pipeline) else None)
