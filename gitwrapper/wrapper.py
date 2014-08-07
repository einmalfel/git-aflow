"""This module wraps some of git functionality into simple python functions.

About ref search:
Here we cannot use 'git show-ref --tags tag_name' to search for tag (and for
branches so), cause it will show tag_name exists if there is x/tag_name.
Git rev-parse isn't suitable too, cause 'git rev-parse --tags=tag_name' will
search for refs/tags/tag_name/*
"""


import logging
import re

from gitwrapper.aux import get_exit_code, get_stdout, get_stdout_and_exit_code


def is_working_tree_clean(untracked=False):
    """Returns True if working tree is clean. If untracked == True, counts also
    untracked files
    """
    return get_stdout(['git', 'status', '--porcelain'] +
                      ([] if untracked else ['-uno'])) == ''


def checkout(treeish, create_branch=False):
    return get_exit_code(['git', 'checkout'] +
                         (['-b'] if create_branch else []) + [treeish]) == 0


def get_untracked_files():
    status = get_stdout(['git', 'status', '--porcelain', '-uall']).splitlines()
    result = []
    for line in status:
        if line.startswith('?? '):
            result += [line.split(' ', 1)[1]]
    return result


def list_files_differ(treeish1, treeish2):
    """Returns list of files which is different between treeish1 and treeish2
    """
    diff = get_stdout(['git', 'diff', '--numstat', treeish1,
                       treeish2]).splitlines()
    return [line.rsplit('\t', 1)[1] for line in diff if line]


def get_commit_headline(treeish):
    return get_stdout(['git', 'log', '--format=%s', '-n1', treeish])


def find_commits(start_commits=[], first_parent=False,
                              regexps=[], match_all=False):
    """Searches for commits starting from start_commits and going to the
    beginning of history.
    Reduces results with regexps if any. Matches any of given regexps, unless
    match_all is set to True.
    If first_parent is set to True, exclude merged branches from search.
    Returns list of SHA"""
    return get_stdout(['git', 'rev-list'] +
                (['--first-parent'] if first_parent else []) +
                (['--all-match'] if match_all else []) +
                [('--grep=' + regexp) for regexp in regexps] +
                (start_commits if start_commits else ['--all'])).splitlines()


def in_git_repo():
    return 0 == get_exit_code(['git', 'rev-parse', '--git-dir'])


def rev_parse(treeish):
    return get_stdout(['git', 'rev-parse', treeish])


def get_branch_list(patterns=[]):
    """ List all branches if pattern is empty list, branches matching any
    pattern otherwise
    """
    return re.sub('[ *]', '', get_stdout(['git', 'branch', '--list'] +
                                         patterns)).splitlines()


def get_current_branch():
    """Returns current branch name or None if in detached HEAD state"""
    output, code = get_stdout_and_exit_code(['git', 'symbolic-ref',
                                             '--short', '--q', 'HEAD'])
    return output if code == 0 else None


def get_tag_list(pattern=''):
    return get_stdout(['git', 'tag', '--list'] +
                             ([] if pattern == '' else [pattern])).splitlines()


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
        logging.critical("Error in ancestor check " + result)
    return result == 0


def get_main_ancestor(treeish):
    """For merge commits it returns parent commit belonging to branch into
    which another branch was merged. If threeish has no parents, return None
    """
    code, output = get_stdout_and_exit_code(['git', 'rev-parse',
                                             treeish + '^1'])
    return output if code == 0 else None


def get_branches_containing(treeish):
    return re.sub('[ *]', '',
                  get_stdout(['git', 'branch', '--contains', treeish
                              ])).splitlines()


def create_branch(name, start_point=None):
    """ Starts branch from start_point or from HEAD if no start_point
    specified. Returns True if success, False otherwise
    """
    result = (0 == get_exit_code(['git', 'branch', name] +
                           ([start_point] if start_point else [])))
    if not result:
        logging.warning('Failed to create branch ' + name)
    return result


def create_tag(name, target=None):
    """ Puts tag on HEAD or on target if specified.
    Returns True if success, False otherwise
    """
    result = (0 == get_exit_code(['git', 'tag', name] +
                                 ([target] if target else [])))
    if not result:
        logging.warning('Failed to create tag ' + name)
    return result


def delete_tag(name):
    result = (0 == get_exit_code(['git', 'tag', '-d', name]))
    if not result:
        logging.warning('Failed to delete tag ' + name)
    return result


def delete_branch(name):
    result = (0 == get_exit_code(['git', 'branch', '-d', name]))
    if not result:
        logging.warning('Failed to delete branch ' + name)
    return result


def get_tags_by_target(treeish):
    return get_stdout(['git', 'tag', '--points-at', treeish]).splitlines()


def is_valid_ref_name(name):
    return 0 == get_exit_code(['git', 'check-ref-format',
                               'refs/heads/' + name])