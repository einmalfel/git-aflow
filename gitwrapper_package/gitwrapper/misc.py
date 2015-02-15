"""This module wraps various pieces of git functionality not suitable for
tag, branch and commit modules.
"""

import collections
import sys

from gitwrapper.aux import get_output, call, \
    get_output_and_exit_code, GitUnexpectedError, check_01


if 'gitwrapper.cached' in sys.modules:
    from gitwrapper.grouped_cache import cache, invalidate
else:
    from gitwrapper.stub_cache import cache, invalidate


def is_working_tree_clean(untracked=False):
    """Returns True if working tree is clean. If untracked == True, counts also
    untracked files
    """
    return get_output(['git', 'status', '--porcelain'] +
                      ([] if untracked else ['-uno'])) == ''


def checkout(treeish):
    call(['git', 'checkout'] + [treeish])
    invalidate('branches', 'index')


def get_untracked_files():
    status = get_output(['git', 'status', '--porcelain', '-uall']).splitlines()
    result = []
    for line in status:
        if line.startswith('?? '):
            result.append(line.split(' ', 1)[1])
    return result


def list_files_differ(treeish1, treeish2):
    """Returns list of files which is different between treeish1 and treeish2
    """
    diff = get_output(['git', 'diff', '--numstat', treeish1,
                       treeish2, '--']).splitlines()
    return [line.rsplit('\t', 1)[1] for line in diff if line]


@cache()
def in_git_repo():
    output, code = get_output_and_exit_code(['git', 'rev-parse', '--git-dir'])
    if code == 0:
        return True
    elif output.startswith('fatal: Not a git repository (or any of the ' +
                           'parent directories):'):
        return False
    else:
        raise GitUnexpectedError('Strange git rev-parse --git-dir output :' +
                                 output + ' Exit-code: ' + str(code))


@cache()
def get_git_dir():
    return get_output(['git', 'rev-parse', '--git-dir'])


def get_root_dir():
    return get_output(['git', 'rev-parse', '--show-toplevel'])


@cache('branches', 'commits', 'tags')
def rev_parse(treeish):
    return get_output(['git', 'rev-parse', treeish])


def sort(list_of_treeish, by_date=False, reverse=False):
    """ Sort list of treeish in topological order (descendants first).
    If by_date - sorts by date, newer first.
    """
    list_of_treeish = list(list_of_treeish)
    if not list_of_treeish:
        return tuple()
    shas = get_output(['git', 'rev-list'] +
                      ['--date-order' if by_date else '--topo-order'] +
                      (['--reverse'] if reverse else []) +
                      list_of_treeish + ['--']).splitlines()
    sha_treeish = collections.defaultdict(list)
    for treeish in list_of_treeish:
        sha_treeish[rev_parse(treeish)].append(treeish)
    return tuple(t for sha in shas for t in sha_treeish.get(sha, tuple()))


def is_valid_ref_name(name):
    return check_01(['git', 'check-ref-format', 'refs/heads/' + name])


class MergeMsgError(Exception):
    """ Failed to set merge msg for some reason."""


def set_merge_msg(string):
    try:
        with open(get_git_dir() + '/MERGE_MSG', 'w') as merge_msg_file:
            written = merge_msg_file.write(string)
    except OSError as error:
        raise MergeMsgError from error
    else:
        if not written == len(string):
            raise MergeMsgError('Failed to write merge msg. ' +
                                str(written) + ' characters written of ' +
                                str(len(string)) + ' (' + string + ').')


def get_merge_base(shas):
    return get_output(["git", "merge-base", "--octopus"] + shas)


def get_diff(from_treeish, to_treeish, files=None, working_dir=None):
    """Returns changes of files between from_treeish and to_treeish. If files is
    None, return changes for all files.
    """
    # need '--' at the end because to_treeish may be interpreted as filename
    return get_output(["git", "diff", from_treeish, to_treeish, '--'] +
                      (files if files else []), cwd=working_dir)


def add(path):
    call(['git', 'add', path])
    invalidate('index')


def rm(path, recursively=False):
    call(['git', 'rm', '-f'] + (['-r'] if recursively else []) + [path])
    invalidate('index')


def init(bare=False):
    call(['git', 'init'] + (['--bare'] if bare else []))
    invalidate()
