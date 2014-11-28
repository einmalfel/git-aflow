""" This module is a superstructure on top of the functools.lru_cache. It adds
an ability to group function caches and clear them by group or all at once.
The caching is safe for immutable objects only.
"""


import functools
import collections
import os
import atexit
import itertools


__lru_funcs_by_group = collections.defaultdict(list)
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
                __lru_funcs_by_group[group].append(lru)
        else:
            # use lru_funcs_by_group[None] as a default group
            __lru_funcs_by_group[None].append(lru)
        return lru
    return decorator


def invalidate(*groups):
    """Calling invalidate() will clear all caches"""
    for group in groups if groups else __lru_funcs_by_group.keys():
        for lru_func in __lru_funcs_by_group.get(group, []):
            lru_func.cache_clear()


def get_cache_info():
    """Returns dict of cache info dicts.
    get_cache_info is the only piece of code that knows about
    functools._CacheInfo structure
    """
    result = dict()
    for func in set(itertools.chain(*__lru_funcs_by_group.values())):
        info = func.cache_info()
        result[func] = {'used': info.currsize,
                        'size': info.maxsize,
                        'hits': info.hits,
                        'misses': info.misses}
    return result


def print_cache_info(info=None):
    groups_by_func = collections.defaultdict(list)
    for group in __lru_funcs_by_group:
        for func in __lru_funcs_by_group.get(group, []):
            groups_by_func[func].append(group)
    if info is None:
        info = get_cache_info()
    for f in groups_by_func:
        if not(info[f]['used'] or info[f]['misses'] or info[f]['hits']):
            continue
        s = []
        # We have to maintain consistent print order and handle float values
        for k in sorted(info[f]):
            s.append(k + '{:.1f}'.format(info[f][k]).replace('.0', '').rjust(5))
        print(f.__name__.ljust(16),
              ','.join(map(str, groups_by_func[f])).ljust(21),
              ','.join(s))


output_info = os.environ.get('GIT_WRAPPER_CACHE_INFO') == '1'
if output_info:
    atexit.register(print_cache_info)
