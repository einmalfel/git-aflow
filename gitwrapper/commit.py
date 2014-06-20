"""Commit-related functionality wrapper"""


import logging

from gitwrapper.aux import get_exit_code, get_stdout, get_stdout_and_exit_code


def get_headline(treeish):
    return get_stdout(['git', 'log', '--format=%s', '-n1', treeish])


def find(start_commits=[], first_parent=False,
                              regexps=[], match_all=False):
    """Searches for commits starting from start_commits and going to the
    beginning of history.
    Reduces results with regexps (in commit message) if any. Matches any of
    given regexps, unless match_all is set to True.
    If first_parent is set to True, exclude merged branches from search.
    Returns list of SHA"""
    return get_stdout(['git', 'rev-list'] +
                (['--first-parent'] if first_parent else []) +
                (['--all-match'] if match_all else []) +
                [('--grep=' + regexp) for regexp in regexps] +
                (start_commits if start_commits else ['--all'])).splitlines()


def get_current_SHA():
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


def merge(treeish, description):
    return 0 == get_exit_code(['git', 'merge', '--no-ff', '--no-edit', '-m',
                            description, treeish])


def abort_merge():
    get_stdout(['git', 'merge', '--abort'])
