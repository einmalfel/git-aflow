"""Commit-related functionality wrapper"""

import logging
import re

from gitwrapper.aux import get_output, get_output_and_exit_code,\
    GitUnexpectedError, call, check_01, get_output_01
from gitwrapper import misc


class AlreadyMergedError(Exception):
    """Merge target already contains merge object. Git returned "Already
    up-to-date
    """


def get_headline(treeish):
    return get_output(['git', 'log', '--format=%s', '-n1', treeish, '--'])


def get_full_message(treeish):
    return get_output(['git', 'show', '--format=%B', '-s', treeish])


def find(start_commits=None, first_parent=False,
         regexps=None, match_all=False):
    """Searches for commits starting from start_commits and going to the
    beginning of history.
    Reduces results with regexps (in commit message) if any. Matches any of
    given regexps, unless match_all is set to True.
    If first_parent is set to True, exclude merged branches from search.
    Returns list of SHA"""
    return get_output(
        ['git', 'rev-list'] +
        (['--first-parent'] if first_parent else []) +
        (['--all-match'] if match_all else []) +
        (['-E'] + [('--grep=' + r) for r in regexps] if regexps else []) +
        (start_commits if start_commits else ['--all']) + ['--']).splitlines()


def get_current_sha():
    return get_output(['git', 'rev-parse', 'HEAD'])


def is_ancestor(ancestor, descendant):
    return check_01(['git', 'merge-base', '--is-ancestor', ancestor, descendant])


def is_based_on(ancestor, descendant):
    """This checks whether ancestor is reachable from descendant via
    first-parent tree traversal.
    """
    rev_list = get_output(['git', 'rev-list', '--first-parent',
                           ancestor + '..' + descendant, '--']).splitlines()
    if not rev_list:
        return False
    else:
        # git rev-list --first-parent will print some commits even if ancestor
        # is not reachable via traverse by first parent, so check if ancestor
        # is indeed first parent of last commit rev-list returned
        return misc.rev_parse(ancestor) == get_parent(rev_list[-1])


def get_parent(treeish, number=1):
    """Get parent commit SHA. If commit is merge commit, use number to select
    which parent to return. Parent #1 belongs to merge target. If specified
    parent doesn't exist, returns None
    """
    return get_output_01(['git', 'rev-parse', '-q', '--verify',
                          treeish + '^' + str(number)])


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
    return get_output(
        ['git', 'rev-list', '--ancestry-path', '--topo-order'] +
        ['--first-parent'] + (['--reverse'] if reverse else []) +
        (['-E'] + ['--grep=' + r for r in regexps] if regexps else []) +
        (['--all-match'] if match_all else []) +
        [treeish1 + '..' + treeish2] + ['--']).splitlines()


def merge(treeish, description):
    """Returns True if merged successfull, False if conflicted.
    Throws AlreadyMergedError if git says "Already up-to-date."
    """
    output, code = get_output_and_exit_code(['git', 'merge', '--no-ff',
                                             '--no-edit', '-m',
                                             description, treeish])
    if code == 0:
        if output == 'Already up-to-date.':
            raise AlreadyMergedError('Merge object: ' + str(treeish))
        else:
            return True
    else:
        if code == 1:
            if not merge.conflict_re:
                merge.conflict_re = re.compile(
                    '^CONFLICT .*: Merge conflict in .*$', re.MULTILINE)
            if merge.conflict_re.search(output):
                return False
            raise GitUnexpectedError('Git merge returned ' + str(code) +
                                     '. Output: ' + output)
merge.conflict_re = None


def abort_merge():
    return get_output(['git', 'merge', '--abort'])


def revert(treeish, parent=None, no_commit=False):
    return check_01(['git', 'revert', treeish] +
                   (['-m' + str(parent)] if parent else []) +
                   (['-n'] if no_commit else []))


def abort_revert():
    call(['git', 'revert', '--abort'])


def commit(message=None, allow_empty=False):
    """Returns True if committed successfully. Returns False if commit failed
    because of merge conflicts
    """
    output, code = get_output_and_exit_code(['git', 'commit', '--no-edit'] +
                           (['-m' + message] if message else []) +
                           (['--allow-empty'] if allow_empty else []))
    if code == 0:
        return True
    else:
        if "error: 'commit' is not possible because you have unmerged files." \
                in output:
            logging.info('Commit failed due to unresolved conflicts')
            return False
        else:
            raise GitUnexpectedError('Git commit returns ' + code +
                                     '. Output: ' + output)
