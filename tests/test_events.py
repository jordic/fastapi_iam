from fastapi_iam import events
import pytest

pytestmark = pytest.mark.asyncio


class AEvent:
    def __init__(self, val):
        self.val = val


class AEvent2:
    pass


async def test_events():
    counter = 0

    async def check(event):
        nonlocal counter
        counter = counter + 1

    events.add_subscriber(AEvent, check)

    await events.notify(AEvent(1))
    await events.notify(AEvent2())

    assert counter == 1
    await events.notify(AEvent(1))
    assert counter == 2
