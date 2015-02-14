""" This module is a superstructure on top of the functools.lru_cache. It adds
an ability to group function caches and clear them by group or all at once.
The caching is safe for immutable objects only.
"""


import functools
import collections
import inspect
import os
import atexit
import itertools


__lru_funcs_by_group = collections.defaultdict(list)
# groups:
# - branches (includes HEAD)
# - tags
# - commits
# - index (includes working tree state)


def cache(*groups, maxsize=128):
    def decorator(func):
        lru = functools.lru_cache(maxsize)(func)
        if groups:
            for group in groups:
                __lru_funcs_by_group[group].append(lru)
        else:
            # use lru_funcs_by_group[None] as a default group
            __lru_funcs_by_group[None].append(lru)
        return lru
    return decorator


def invalidate(*groups, dont_print_info=False):
    """Calling invalidate() will clear all caches"""
    if output_info and not dont_print_info:
        fs_to_print = set()
        for group in groups if groups else __lru_funcs_by_group.keys():
            fs_to_print.update(set(__lru_funcs_by_group[group]))
        if fs_to_print:
            fr = inspect.currentframe()
            from_ = (' from ' + os.path.basename(fr.f_back.f_code.co_filename) +
                     ':' + str(fr.f_back.f_lineno)) if fr else ''
            print(('Cache being invalidated' + from_).ljust(80, '-'))
            print_cache_info(
                {f: i for f, i in get_cache_info().items() if f in fs_to_print})
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
        result[func] = {'use': info.currsize,
                        'siz': info.maxsize,
                        'hit': info.hits,
                        'mis': info.misses}
    return result


def print_cache_info(info=None):
    groups_by_func = collections.defaultdict(list)
    for group in __lru_funcs_by_group:
        for func in __lru_funcs_by_group.get(group, []):
            groups_by_func[func].append(group)
    if info is None:
        info = get_cache_info()
    for f in groups_by_func:
        if f not in info or not (info[f]['use'] or info[f]['mis'] or
                                 info[f]['hit']):
            continue
        s = []
        # We have to maintain consistent print order and handle float values
        for k in sorted(info[f]):
            s.append(k + '{:.1f}'.format(info[f][k]).replace('.0', '').rjust(4))
        print(f.__name__.ljust(26),
              ','.join(map(str, groups_by_func[f])).ljust(21),
              ','.join(s))


output_info = os.environ.get('GIT_WRAPPER_CACHE_INFO') == '1'
if output_info:
    atexit.register(print_cache_info)
