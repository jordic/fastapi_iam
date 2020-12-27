from collections.abc import MutableMapping
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

import asyncio


def merge_dicts(d1: dict, d2: dict) -> dict:
    """
    Update two dicts of dicts recursively,
    if either mapping has leaves that are non-dicts,
    the second's leaf overwrites the first's.
    """
    for k, v in d1.items():
        if k in d2:
            # this next check is the only difference!
            if all(isinstance(e, MutableMapping) for e in (v, d2[k])):
                d2[k] = merge_dicts(v, d2[k])
            if isinstance(v, list):
                d2[k].extend(v)
            # we could further check types and merge as appropriate here.
    d3 = d1.copy()
    d3.update(d2)
    return d3


async def run_in_threadpool(func, *args, **kwargs):
    curr = partial(func, *args, **kwargs)
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, curr)


def resolve_dotted_name(name: str) -> Any:
    """
    import the provided dotted name

    >>> resolve_dotted_name('guillotina.interfaces.IRequest')
    <InterfaceClass guillotina.interfaces.IRequest>

    :param name: dotted name
    """
    if not isinstance(name, str):
        return name  # already an object
    names = name.split(".")
    used = names.pop(0)
    found = __import__(used)
    for n in names:
        used += "." + n
        try:
            found = getattr(found, n)
        except AttributeError:
            __import__(used)
            found = getattr(found, n)

    return found


def maybe_resolve(item: Any):
    if isinstance(item, str):
        return resolve_dotted_name(item)
    return item
