from fastapi import FastAPI
from fastapi_asyncpg import configure_asyncpg
from fastapi_iam import configure_iam
from starlette.config import Config
from starlette.datastructures import URL


config = Config(".env")
DB_DSN = config(
    "DB_DSN", cast=URL, default="postgresql://postgres:postgres@localhost/db"
)

iam_settings = {"db_schema": "auth"}

app = FastAPI()

iam = configure_iam(iam_settings)


async def initialize_db(conn):
    await iam.initialize_iam_db(conn)


db = configure_asyncpg(app, str(DB_DSN), init_db=initialize_db)
iam.set_asyncpg(db)


app.include_router(iam.router, prefix="/auth", tags=["auth"])
