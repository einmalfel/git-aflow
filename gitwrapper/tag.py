"""Tag-related functionality wrapper

About ref search:
Here we cannot use 'git show-ref --tags tag_name' to search for tag (and for
branches so), cause it will show tag_name exists if there is x/tag_name.
Git rev-parse isn't suitable too, cause 'git rev-parse --tags=tag_name' will
search for refs/tags/tag_name/*
"""


import logging

from gitwrapper.aux import get_exit_code, get_stdout


def get_list(pattern=''):
    return get_stdout(['git', 'tag', '--list'] +
                             ([] if pattern == '' else [pattern])).splitlines()


def get_SHA(name):
    return get_stdout(['git', 'show-ref', '--verify', '--hash',
                       'refs/tags/' + name])


def exists(name):
    return 0 == get_exit_code(['git', 'show-ref', '--verify', '-q',
                       'refs/tags/' + name])


def create(name, target=None):
    """ Puts tag on HEAD or on target if specified.
    Returns True if success, False otherwise
    """
    result = (0 == get_exit_code(['git', 'tag', name] +
                                 ([target] if target else [])))
    if not result:
        logging.warning('Failed to create tag ' + name)
    return result


def delete(name):
    result = (0 == get_exit_code(['git', 'tag', '-d', name]))
    if not result:
        logging.warning('Failed to delete tag ' + name)
    return result


def find_by_target(treeish):
    return get_stdout(['git', 'tag', '--points-at', treeish]).splitlines()
