"""Branch-related functionality wrapper"""

import logging
import re

from gitwrapper.aux import get_exit_code, get_stdout, get_stdout_and_exit_code


def get_list(patterns=None):
    """ List all branches if pattern is empty list, branches matching any
    pattern (shell wildcard) otherwise
    """
    output = get_stdout(['git', 'branch', '--list'] +
                        (patterns if patterns else []))
    return re.sub('[ *]', '', output).splitlines()


def get_current():
    """Returns current branch name or None if in detached HEAD state"""
    output, code = get_stdout_and_exit_code(['git', 'symbolic-ref',
                                             '--short', '--q', 'HEAD'])
    return output if code == 0 else None


def get_head_sha(name):
    return get_stdout(['git', 'show-ref', '--verify', '--hash',
                       'refs/heads/' + name])


def exists(name):
    return 0 == get_exit_code(['git', 'show-ref', '--verify', '-q',
                              'refs/heads/' + name])


def get_branches_containing(treeish):
    return re.sub('[ *]', '',
                  get_stdout(['git', 'branch', '--contains', treeish
                              ])).splitlines()


def create(name, start_point=None):
    """ Starts branch from start_point or from HEAD if no start_point
    specified. Returns True if success, False otherwise
    """
    result = (0 == get_exit_code(['git', 'branch', name] +
                                 ([start_point] if start_point else [])))
    if not result:
        logging.warning('Failed to create branch ' + name)
    return result


def delete(name):
    result = (0 == get_exit_code(['git', 'branch', '-d', name]))
    if not result:
        logging.warning('Failed to delete branch ' + name)
    return result
