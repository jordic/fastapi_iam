from setuptools import find_packages
from setuptools import setup


with open("README.md", "r") as f:
    readme = f.read()


setup(
    name="fastapi_iam",
    version="1.0.0",
    url="https://github.com/jordic/fastapi_iam",
    license="MIT",
    author="Jordi collell",
    author_email="jordic@gmail.com",
    description="FastAPI Identity Access Management",
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=("tests",)),
    install_requires=[
        "fastapi",
        "fastapi_asyncpg",
        "argon2-cffi",
        "python-jose[cryptography]",
    ],
    package_data={"fastapi_iam": ["py.typed"]},
    extras_require={
        "dev": [
            "black",
            "isort",
            "flake8",
            "tox",
        ],
        "docs": ["sphinx", "recommonmark"],
        "test": [
            "pytest",
            "async_asgi_testclient",
            "pytest-asyncio",
            "pytest-docker-fixtures[pg]",
        ],
        "publish": ["twine"],
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
