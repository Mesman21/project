import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from .database import connect, initialize_database
from .schemas import CATEGORIES, normalize_text
from .settings import DATABASE_FILES, Settings


def seed_examples(database: Path, source: Path) -> int:
    with connect(database, immediate=True) as db:
        if db.execute("SELECT 1 FROM labeled_messages LIMIT 1").fetchone():
            return 0
        data = pd.read_csv(source, dtype=str, keep_default_na=False)
        if set(data.columns) != {"text", "category_code"}:
            raise ValueError("CSV має містити text та category_code.")
        data["text"] = data["text"].map(normalize_text)
        if data["text"].duplicated().any():
            raise ValueError("CSV містить повтори текстів.")
        if set(data["category_code"]) != set(CATEGORIES):
            raise ValueError("CSV має містити приклади всіх трьох категорій.")
        train, test = train_test_split(
            data,
            test_size=0.25,
            random_state=42,
            stratify=data["category_code"],
        )
        rows = [
            (item.text, item.category_code, split)
            for part, split in ((train, "train"), (test, "test"))
            for item in part.itertuples(index=False)
        ]
        db.executemany(
            "INSERT INTO labeled_messages (text, category_code, dataset_split) "
            "VALUES (?, ?, ?)",
            rows,
        )
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Підготувати локальну базу")
    parser.add_argument(
        "--seed", action="store_true", help="Додати приклади до порожньої бази"
    )
    args = parser.parse_args()
    settings = Settings.from_environment()
    initialize_database(settings.database)
    if args.seed:
        inserted = seed_examples(
            settings.database, DATABASE_FILES / "training_examples.csv"
        )
        print(f"Додано прикладів: {inserted}")
    print(f"База готова: {settings.database}")


if __name__ == "__main__":
    main()
