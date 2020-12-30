from .groups import *  # noqa
from .session import *  # noqa
from .users import *  # noqa


def pg_service_factory(iam, service):
    return service(iam.pool, iam.settings["db_schema"])
