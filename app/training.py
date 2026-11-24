import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.pipeline import Pipeline

from .classifier import ACTIVE_MODEL_FILE
from .database import connect
from .schemas import CATEGORIES
from .settings import Settings
from .strategies import DEFAULT_STRATEGY, STRATEGIES, TrainingStrategy

SELECT_CORPUS = (
    "SELECT message_id, text, category_code, dataset_split "
    "FROM labeled_messages ORDER BY message_id"
)


def build_pipeline(strategy: TrainingStrategy = DEFAULT_STRATEGY) -> Pipeline:
    return Pipeline(
        [
            (
                "vectorizer",
                TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True),
            ),
            ("classifier", strategy.build_estimator()),
        ]
    )


def train_and_publish(
    settings: Settings, strategy: TrainingStrategy = DEFAULT_STRATEGY
) -> dict[str, object]:
    with connect(settings.database) as db:
        data = pd.read_sql_query(SELECT_CORPUS, db)
    train = data[data["dataset_split"] == "train"]
    test = data[data["dataset_split"] == "test"]
    if any(set(part["category_code"]) != set(CATEGORIES) for part in (train, test)):
        raise ValueError("Кожна вибірка має містити приклади всіх категорій.")

    pipeline = build_pipeline(strategy)
    pipeline.fit(train["text"], train["category_code"])
    predictions = pipeline.predict(test["text"])
    majority = str(train["category_code"].mode().iloc[0])
    report = classification_report(
        test["category_code"], predictions, labels=list(CATEGORIES),
        output_dict=True, zero_division=0,
    )
    baseline_f1 = f1_score(
        test["category_code"], [majority] * len(test),
        labels=list(CATEGORIES), average="macro", zero_division=0,
    )
    version = datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
    folder = settings.artifacts / version
    folder.mkdir(parents=True)
    joblib.dump(pipeline, folder / "model.joblib")

    with connect(settings.database, immediate=True) as db:
        current_data = pd.read_sql_query(SELECT_CORPUS, db)
        if not current_data.equals(data):
            raise ValueError("Приклади змінилися. Запустіть навчання повторно.")
        cursor = db.execute(
            "INSERT INTO evaluation_runs (model_version) VALUES (?)", (version,)
        )
        evaluation_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO predictions "
            "(evaluation_id, message_id, predicted_category_code) VALUES (?, ?, ?)",
            [
                (evaluation_id, int(message_id), str(code))
                for message_id, code in zip(test["message_id"], predictions)
            ],
        )
        counts = db.execute(
            "SELECT category_code, category_name, count, share "
            "FROM evaluation_distribution WHERE evaluation_id = ? "
            "ORDER BY category_code",
            (evaluation_id,),
        )
        summary = {
            "model_version": version,
            "strategy": strategy.name,
            "evaluation_id": evaluation_id,
            "training_count": len(train),
            "total": len(test),
            "categories": [dict(row) for row in counts],
            "accuracy": float(accuracy_score(test["category_code"], predictions)),
            "macro_f1": float(report["macro avg"]["f1-score"]),
            "baseline_macro_f1": float(baseline_f1),
            "classification_report": report,
        }
        (folder / "statistics.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=settings.artifacts, delete=False
    ) as pointer:
        pointer.write(version + "\n")
    temporary = Path(pointer.name)
    try:
        temporary.replace(settings.artifacts / ACTIVE_MODEL_FILE)
    finally:
        temporary.unlink(missing_ok=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Навчання локального класифікатора"
    )
    parser.add_argument(
        "--strategy", choices=STRATEGIES, default=DEFAULT_STRATEGY.name,
        help="Алгоритм класифікації",
    )
    args = parser.parse_args()
    try:
        summary = train_and_publish(
            Settings.from_environment(), STRATEGIES[args.strategy]
        )
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
