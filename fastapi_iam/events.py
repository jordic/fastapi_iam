from typing import Protocol

import typing


class IEvent(Protocol):
    pass


events: typing.Dict[IEvent, typing.List[typing.Callable]] = {}


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


class UserLogin:
    def __init__(self, user, token):
        self.user = user
        self.token = token


class UserLogout:
    def __init__(self, user):
        self.user = user
