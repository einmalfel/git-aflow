"""Commit-related functionality wrapper"""

import logging

from gitwrapper.aux import get_exit_code, get_stdout, get_stdout_and_exit_code


def get_headline(treeish):
    return get_stdout(['git', 'log', '--format=%s', '-n1', treeish])


def get_full_message(treeish):
    return get_stdout(['git', 'show', '--format=%B', '-s', treeish])


def find(start_commits=None, first_parent=False,
         regexps=None, match_all=False):
    """Searches for commits starting from start_commits and going to the
    beginning of history.
    Reduces results with regexps (in commit message) if any. Matches any of
    given regexps, unless match_all is set to True.
    If first_parent is set to True, exclude merged branches from search.
    Returns list of SHA"""
    return get_stdout(['git', 'rev-list'] +
                      (['--first-parent'] if first_parent else []) +
                      (['--all-match'] if match_all else []) +
                      ([('--grep=' + r) for r in regexps] if regexps else []) +
                      (start_commits if start_commits else ['--all'])
                      ).splitlines()


def get_current_sha():
    return get_stdout(['git', 'rev-parse', 'HEAD'])


def is_ancestor(ancestor, descendant):
    result = get_exit_code(['git', 'merge-base', '--is-ancestor',
                            ancestor, descendant])
    if result != 0 and result != 1:
        logging.critical("Error in ancestor check " + result)
    return result == 0


def get_parent(treeish, number=1):
    """Get parent commit SHA. If commit is merge commit, use number to select
    which parent to return
    """
    output, code = get_stdout_and_exit_code(['git', 'rev-parse',
                                             treeish + '^' + str(number)])
    return output if code == 0 else None


def get_commits_between(treeish1, treeish2, reverse=False, regexps=None,
                        match_all=False):
    """Get list of commits between treeish1 and treeish2 in form of list of
    SHA including treeish2 and excluding treeish1.
    For merge commits walks only by first parent path.
    Commits are returned in order as they appear in history, from newer to
    elder. If reverse==True, order is reversed.
    Optionally you may reduce result by applying regexps on commit headline.
    Results matching any of regexps will be produced if match_all==False,
    matching all regexps otherwise.
    """
    return get_stdout(['git', 'rev-list', '--ancestry-path', '--topo-order',
                      '--first-parent', treeish1 + '..' + treeish2] +
                      (['--reverse'] if reverse else []) +
                      (['--all-match'] if match_all else []) +
                      (['--grep=' + r for r in regexps] if regexps else [])
                      ).splitlines()


def merge(treeish, description):
    return 0 == get_exit_code(['git', 'merge', '--no-ff', '--no-edit', '-m',
                              description, treeish])


def abort_merge():
    get_stdout(['git', 'merge', '--abort'])
