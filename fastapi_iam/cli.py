from argparse import ArgumentParser
from fastapi_iam.models import UserCreate
from fastapi_iam.models import UserRepository
from fastapi_iam.auth import PasswordHasher
from getpass import getpass

import asyncio
import asyncpg
import os
import sys
import textwrap

parser = ArgumentParser()
parser.add_argument("--dsn", help="postgres-dsn")
parser.add_argument("--schema", help="postgres schema")


async def create_user():
    args = parser.parse_args()
    env_dsn = os.getenv("DB_DSN", None)
    env_schema = os.getenv("DB_SCHEMA", None) or args.schema or ""
    dbdsn = env_dsn or args.dsn
    if dbdsn is None:
        print(
            textwrap.dedent(
                """
        >>>> ERROR!
        Provide a -dsn argument or a DB_DSN env variable with
        your postgresql configuration.
        This script will create users, hashing passwords with
            default PasswordHasher

        """
            )
        )
        sys.exit(1)

    org_id = int(input("Org_id: "))
    email = input("Email: ").strip()
    password = getpass("Password: ").strip()
    repassword = getpass("Password Again: ").strip()

    if password != repassword:
        print("Not matching passwords")
        sys.exit(1)

    is_admin = parse_bool(input("Admin? [Y/n] "))
    is_staff = parse_bool(input("Is Staff? [Y/n] "))
    is_active = parse_bool(input("Is Active? [Y/n] "))

    db = await asyncpg.connect(dsn=dbdsn)
    repo = UserRepository(db, schema=env_schema)
    hasher = PasswordHasher()

    user = UserCreate(
        org_id=org_id,
        email=email,
        password=await hasher.hash_password(password),
        is_staff=is_staff,
        is_active=is_active,
        is_admin=is_admin,
    )
    user = await repo.create(user)
    print(f"User {user.email} with user_id={user.user_id} CREATED!")
    await db.close()


def parse_bool(val):
    return val.strip() in ("Y", "y", "1", "yes", "t", "True", "")


def main():
    asyncio.run(create_user())


if __name__ == "__main__":
    main()
