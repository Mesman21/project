import argparse
import sqlite3
from getpass import getpass
from typing import get_args

from .auth import create_account
from .database import initialize_database
from .schemas import Role
from .settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Створення облікового запису")
    parser.add_argument("username", help="Логін")
    parser.add_argument("role", choices=get_args(Role), help="Роль")
    args = parser.parse_args()

    password = getpass("Пароль: ")
    if password != getpass("Повторіть пароль: "):
        parser.exit(1, "Паролі не збігаються.\n")
    path = Settings.from_environment().database
    initialize_database(path)
    try:
        create_account(path, args.username, password, args.role)
    except sqlite3.IntegrityError:
        parser.exit(1, "Такий логін уже існує.\n")
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    print("Обліковий запис створено.")


if __name__ == "__main__":
    main()
