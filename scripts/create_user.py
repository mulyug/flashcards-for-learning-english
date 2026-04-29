"""CLI: create the single owner account.

Usage (inside the running container or with deps installed locally):
    docker compose run --rm app python -m scripts.create_user
"""
import getpass
import sys

from app.db import SessionLocal
from app.models import User
from app.security import hash_password

MIN_PASSWORD_LENGTH = 12


def main() -> int:
    db = SessionLocal()
    try:
        existing = db.query(User).first()
        if existing is not None:
            print(f"A user already exists: {existing.username!r}.")
            print(
                "This app is intentionally single-user. "
                "Delete the row from the users table if you really want to recreate it."
            )
            return 1

        username = input("Username: ").strip()
        if not username:
            print("Username cannot be empty.")
            return 1

        password = getpass.getpass("Password: ")
        if len(password) < MIN_PASSWORD_LENGTH:
            print(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
            return 1

        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.")
            return 1

        db.add(User(username=username, password_hash=hash_password(password)))
        db.commit()
        print(f"Created user: {username}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
