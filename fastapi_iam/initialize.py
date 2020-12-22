from pathlib import Path

import asyncpg
import glob
import logging
import typing

logger = logging.getLogger("fastapi_iam")

_current = Path(__file__).parent


def get_migrations_path() -> Path:
    return _current / "schema"


def load_migration(name: str):
    file = get_migrations_path() / name
    with file.open() as f:
        return f.read()


def get_available():
    files: typing.Dict[int, str] = {}
    path = str(get_migrations_path())
    for item in glob.glob(f"{path}/*.up.sql"):
        file = item.replace(path + "/", "")
        version = int(file.split("_")[0])
        files[version] = file
    return files


async def initialize_db(settings, db):
    migrations = get_available()
    schema = f"{settings['db_schema']}." if settings["db_schema"] else ""
    try:
        current = await db.fetchval(
            f"""
            SELECT value FROM {schema}users_version
        """
        )
    except asyncpg.exceptions.UndefinedTableError:
        current = 0
    logger.info("current migration %s", current)
    applied = current
    async with db.transaction():
        if settings["db_schema"]:
            await db.execute(f"set schema '{settings['db_schema']}'")
        for avail in sorted(list(migrations.keys())):
            if avail > current:
                data = load_migration(migrations[avail])
                await db.execute(data)
                applied = avail
                logger.info("applied migration %s", applied)

        logger.info("update migration history")
        await db.execute(f"update {schema}users_version set value=$1", applied)

    if applied == current:
        logger.info("No migrations applied")
