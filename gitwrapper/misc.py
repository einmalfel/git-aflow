"""This module wraps various pieces of git functionality not suitable for
tag, branch and commit modules.
"""

import logging
import os.path

from gitwrapper.aux import get_exit_code, get_stdout


def is_working_tree_clean(untracked=False):
    """Returns True if working tree is clean. If untracked == True, counts also
    untracked files
    """
    return get_stdout(['git', 'status', '--porcelain'] +
                      ([] if untracked else ['-uno'])) == ''


def checkout(treeish):
    result = get_exit_code(['git', 'checkout'] + [treeish]) == 0
    if not result:
        logging.warning("failed to checkout " + treeish)
    return result


def get_untracked_files():
    status = get_stdout(['git', 'status', '--porcelain', '-uall']).splitlines()
    result = []
    for line in status:
        if line.startswith('?? '):
            result.append(line.split(' ', 1)[1])
    return result


def list_files_differ(treeish1, treeish2):
    """Returns list of files which is different between treeish1 and treeish2
    """
    diff = get_stdout(['git', 'diff', '--numstat', treeish1,
                       treeish2]).splitlines()
    return [line.rsplit('\t', 1)[1] for line in diff if line]


def in_git_repo():
    return 0 == get_exit_code(['git', 'rev-parse', '--git-dir'])


def get_git_dir():
    return get_stdout(['git', 'rev-parse', '--git-dir'])


def rev_parse(treeish):
    return get_stdout(['git', 'rev-parse', treeish])


def is_valid_ref_name(name):
    return 0 == get_exit_code(['git', 'check-ref-format',
                               'refs/heads/' + name])


def set_merge_msg(string):
    merge_msg_path = get_git_dir() + '/MERGE_MSG'
    if not os.path.exists(merge_msg_path):
        return False
    with open(merge_msg_path, 'w') as merge_msg_file:
        merge_msg_file.write(string)
    return True
