"""This module wraps some of git functionality into simple python functions.

About ref search:
Here we cannot use 'git show-ref --tags tag_name' to search for tag (and for
branches so), cause it will show tag_name exists if there is x/tag_name.
Git rev-parse isn't suitable too, cause 'git rev-parse --tags=tag_name' will
search for refs/tags/tag_name/*
"""


import re
import logging
from gitwrapper.aux import get_exit_code, get_stdout, get_stdout_and_exit_code


def in_git_repo():
    return 0 == get_exit_code(['git', 'rev-parse', '--git-dir'])


def rev_parse(treeish):
    return get_stdout(['git', 'rev-parse', treeish])


def get_branch_list(pattern=''):
    return re.sub('[ *]', '',
                  get_stdout(['git', 'branch', '--list'] +
                             ([] if pattern == '' else [pattern]))).split('\n')


def get_current_branch():
    """Returns current branch name or None if in detached HEAD state"""
    output, code = get_stdout_and_exit_code(['git', 'symbolic-ref',
                                             '--short', '--q', 'HEAD'])
    return output if code == 0 else None


def get_tag_list(pattern=''):
    return get_stdout(['git', 'tag', '--list'] +
                             ([] if pattern == '' else [pattern])).split('\n')


def get_tag_SHA(name):
    return get_stdout(['git', 'show-ref', '--verify', '--hash',
                       'refs/tags/' + name])


def tag_exists(name):
    return 0 == get_exit_code(['git', 'show-ref', '--verify', '-q',
                       'refs/tags/' + name])


def get_branch_SHA(name):
    return get_stdout(['git', 'show-ref', '--verify', '--hash',
                       'refs/heads/' + name])


def branch_exists(name):
    return 0 == get_exit_code(['git', 'show-ref', '--verify', '-q',
                       'refs/heads/' + name])


def get_current_commit_SHA():
    return get_stdout(['git', 'rev-parse', 'HEAD'])


def is_ancestor(ancestor, descendant):
    result = get_exit_code(['git', 'merge-base', '--is-ancestor',
                            ancestor, descendant])
    if (result != 0 and result != 1):
        logging.critical("error in ancestor check " + result)
    return result == 0


def get_main_ancestor(treeish):
    """For merge commits it returns parent commit belonging to branch into
    which another branch was merged. If threeish has no parents, return None
    """
    code, output = get_stdout_and_exit_code(['git', 'rev-parse',
                                             treeish + '^1'])
    return output if code == 0 else None


def get_branches_containing(treeish):
    return get_stdout([
        'git', 'branch', '--contains', treeish
         ]).split()


def create_branch(name, start_point=None):
    """ Starts branch from start_point or from HEAD if no start_point
    specified. Returns True if success, False otherwise
    """
    result = (0 == get_exit_code(['git', 'branch', name] +
                           ([start_point] if start_point else [])))
    if not result:
        logging.warning('failed to create branch ' + name)
    return result


def create_tag(name, target=None):
    """ Puts tag on HEAD or on target if specified.
    Returns True if success, False otherwise
    """
    result = (0 == get_exit_code(['git', 'tag', name] +
                                 ([target] if target else [])))
    if not result:
        logging.warning('failed to create tag ' + name)
    return result


def delete_tag(name):
    result = (0 == get_exit_code(['git', 'tag', '-d', name]))
    if not result:
        logging.warning('failed to delete tag ' + name)
    return result


def delete_branch(name):
    result = (0 == get_exit_code(['git', 'branch', '-d', name]))
    if not result:
        logging.warning('failed to delete branch ' + name)
    return result


def is_valid_ref_name(name):
    return 0 == get_exit_code(['git', 'check-ref-format',
                               'refs/heads/' + name])
