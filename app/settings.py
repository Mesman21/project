import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE_FILES = ROOT / "database"


@dataclass(frozen=True)
class Settings:
    home: Path
    frontend: Path = ROOT / "frontend" / "dist"

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(Path(os.environ.get("CLASSIFIER_HOME", ROOT / "runtime")))

    @property
    def database(self) -> Path:
        return self.home / "classifier.sqlite3"

    @property
    def artifacts(self) -> Path:
        return self.home / "artifacts"
