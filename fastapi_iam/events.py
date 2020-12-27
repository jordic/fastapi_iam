from typing import Protocol


class IEvent(Protocol):
    pass


events = {}


async def notify(event: IEvent):
    if event.__class__ in events:
        for func in events[event.__class__]:
            await func(event)


class subscriber:
    def __init__(self, event: IEvent):
        self.event = event

    def __call__(self, func):
        add_subscriber(self.event, func)


def add_subscriber(event, func):
    global events
    if event not in events:
        events[event] = []
    events[event].append(func)
