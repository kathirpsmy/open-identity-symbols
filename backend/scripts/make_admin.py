"""
CLI script to promote or demote a user's admin status.

Usage:
    python -m backend.scripts.make_admin --email user@example.com
    python -m backend.scripts.make_admin --email user@example.com --revoke
    python -m backend.scripts.make_admin --list
"""

import argparse
import sys

from backend.core.database import SessionLocal
from backend.models.user import User

# Ensure all models are registered before any DB operation
import backend.models  # noqa: F401


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def promote(email: str, revoke: bool) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Error: no user found with email '{email}'")
            sys.exit(1)

        if not user.totp_confirmed:
            print(f"Warning: '{email}' has not completed TOTP setup — they won't be able to log in yet.")

        action = "revoke" if revoke else "grant"
        if user.is_admin == (not revoke):
            status = "already an admin" if not revoke else "already not an admin"
            print(f"No change: '{email}' is {status}.")
            return

        user.is_admin = not revoke
        db.commit()
        print(f"Done: admin access {'revoked from' if revoke else 'granted to'} '{email}'.")
    finally:
        db.close()


def list_admins() -> None:
    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.is_admin == True).all()  # noqa: E712
        if not admins:
            print("No admin users found.")
            return
        print(f"{'ID':<6} {'Email':<40} {'Active':<8} {'TOTP OK'}")
        print("-" * 65)
        for u in admins:
            print(f"{u.id:<6} {u.email:<40} {'yes' if u.is_active else 'no':<8} {'yes' if u.totp_confirmed else 'no'}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage admin users for Open Identity Symbols."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--email", metavar="EMAIL", help="Email of the user to promote (or revoke)")
    group.add_argument("--list", action="store_true", help="List all current admin users")
    parser.add_argument("--revoke", action="store_true", help="Revoke admin access instead of granting it")

    args = parser.parse_args()

    if args.list:
        list_admins()
    else:
        promote(args.email, args.revoke)


if __name__ == "__main__":
    main()
