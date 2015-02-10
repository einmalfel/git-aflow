"""Tag-related functionality wrapper

About ref search:
Here we cannot use 'git show-ref --tags tag_name' to search for tag (and for
branches so), cause it will show tag_name exists if there is x/tag_name.
Git rev-parse isn't suitable too, cause 'git rev-parse --tags=tag_name' will
search for refs/tags/tag_name/*
"""

import sys

from thingitwrapper.aux import get_output, check_01, call

if 'thingitwrapper.cached' in sys.modules:
    from thingitwrapper.grouped_cache import cache, invalidate
else:
    from thingitwrapper.stub_cache import cache, invalidate


def get_list(pattern=''):
    return get_output(['git', 'tag', '--list'] +
                      ([] if pattern == '' else [pattern])).splitlines()


@cache('tags')
def get_sha(name):
    return get_output(['git', 'show-ref', '--verify', '--hash',
                       'refs/tags/' + name])


@cache('tags')
def exists(name):
    return check_01(['git', 'show-ref', '--verify', '-q', 'refs/tags/' + name])


def create(name, target=None):
    """ Puts tag on HEAD or on target if specified.
    Returns True if success, False otherwise
    """
    call(['git', 'tag', name] + ([target] if target else []))
    invalidate('tags')


def delete(name):
    call(['git', 'tag', '-d', name])
    invalidate('tags')


def find_by_target(treeish):
    return get_output(['git', 'tag', '--points-at', treeish]).splitlines()
