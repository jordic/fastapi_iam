from collections.abc import MutableMapping
from functools import partial
from concurrent.futures import ThreadPoolExecutor

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
