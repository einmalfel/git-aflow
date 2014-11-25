""" This module is a superstructure on top of the functools.lru_cache. It adds
an ability to group function caches and clear them by group or all at once.
The caching is safe for immutable objects only.
"""


import functools
import collections


lru_funcs_by_group = collections.defaultdict(list)
# groups:
# - branches (includes HEAD)
# - tags
# - commits
# - index (includes working tree state)


def grouped_cache(*groups, maxsize=128, typed=False):
    def decorator(func):
        lru = functools.lru_cache(maxsize, typed)(func)
        if groups:
            for group in groups:
                lru_funcs_by_group[group].append(lru)
        else:
            # use lru_funcs_by_group[None] as a default group
            lru_funcs_by_group[None].append(lru)
        return lru

    return decorator


def invalidate(*groups):
    for group in groups if groups else lru_funcs_by_group.keys():
        for lru_func in lru_funcs_by_group.get(group, []):
            lru_func.cache_clear()
