from fastapi.applications import FastAPI
from .initialize import initialize_db
from fastapi_asyncpg import configure_asyncpg
from fastapi_asyncpg import create_pool_test
from fastapi_iam import configure_iam
from pathlib import Path
from pytest_docker_fixtures import images

import asyncpg
import pytest

dir = Path(__file__).parent

images.configure(
    "postgresql", "postgres", "11.1", env={"POSTGRES_DB": "test_db"}
)


async def noop(db):
    pass


@pytest.fixture
async def pool(pg):
    host, port = pg
    url = f"postgresql://postgres@{host}:{port}/test_db"

    settings = {"db_schema": None}

    # apply migrations
    conn = await asyncpg.connect(dsn=url)
    await initialize_db(settings, conn)

    pool = await create_pool_test(url, initialize=noop)

    yield pool
    if pool._conn.is_closed():
        return
    await pool.release()


@pytest.fixture
async def conn(pool):
    async with pool.acquire() as db:
        yield db


@pytest.fixture
async def iam(pool):
    app = FastAPI()
    db = configure_asyncpg(app, "", pool=pool)
    settings = {}
    iam = configure_iam(settings, fastapi_asyncpg=db)
    yield iam
