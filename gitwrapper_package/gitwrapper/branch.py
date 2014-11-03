"""Branch-related functionality wrapper"""

import re

from gitwrapper.aux import get_output, call, check_01, get_output_01


def get_list(patterns=None):
    """ List all branches if pattern is empty list, branches matching any
    pattern (shell wildcard) otherwise
    """
    output = get_output(['git', 'branch', '--list'] +
                        (patterns if patterns else []))
    return re.sub('[ *]', '', output).splitlines()


def get_current():
    """Returns current branch name or None if in detached HEAD state"""
    return get_output_01(['git', 'symbolic-ref', '--short', '--q', 'HEAD'])


def get_head_sha(name):
    return get_output(['git', 'show-ref', '--verify', '--hash',
                       'refs/heads/' + name])


def exists(name):
    return check_01(['git', 'show-ref', '--verify', '-q', 'refs/heads/' + name])


def get_branches_containing(treeish):
    return re.sub('[ *]', '',
                  get_output(['git', 'branch', '--contains', treeish
                              ])).splitlines()


def create(name, start_point=None):
    """ Starts branch from start_point or from HEAD if no start_point specified.
    """
    call(['git', 'branch', name] + ([start_point] if start_point else []))


def delete(name):
    call(['git', 'branch', '-D', name])


def reset(treeish, mode='hard'):
    call(['git', 'reset', '--' + mode, treeish])
