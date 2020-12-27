.PHONY: isort black flake8 mypy

lint: isort black flake8 mypy

isort:
	isort fastapi_iam

black:
	black fastapi_iam/  -l 80

flake8:
	flake8 fastapi_iam

mypy:
	mypy fastapi_iam
