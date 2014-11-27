""" This module is a superstructure on top of the functools.lru_cache. It adds
an ability to group function caches and clear them by group or all at once.
The caching is safe for immutable objects only.
"""


import functools
import collections
import os
import atexit


lru_funcs_by_group = collections.defaultdict(list)
# groups:
# - branches (includes HEAD)
# - tags
# - commits
# - index (includes working tree state)


def cache(*groups, maxsize=128, typed=False):
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
    """Calling invalidate() will clear all caches"""
    for group in groups if groups else lru_funcs_by_group.keys():
        for lru_func in lru_funcs_by_group.get(group, []):
            lru_func.cache_clear()


def print_cache_info():
    groups_by_func = collections.defaultdict(list)
    for group in lru_funcs_by_group:
        for func in lru_funcs_by_group.get(group, []):
            groups_by_func[func].append(group)
    for f in groups_by_func:
        info = f.cache_info()
        if info.currsize or info.hits or info.misses:
            print(
                f.__name__, '(' + ', '.join(map(str, groups_by_func[f])) + ')',
                'size:', info.maxsize,
                'used:', info.currsize,
                'hits:', info.hits,
                'misses:', info.misses)


output_info = os.environ.get('GIT_WRAPPER_CACHE_INFO') == '1'
if output_info:
    atexit.register(print_cache_info)
