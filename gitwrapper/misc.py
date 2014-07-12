"""This module wraps various pieces of git functionality not suitable for
tag, branch and commit modules.
"""

from gitwrapper.aux import get_stdout, call, \
    get_stdout_and_exit_code, GitUnexpectedError, check_01


def is_working_tree_clean(untracked=False):
    """Returns True if working tree is clean. If untracked == True, counts also
    untracked files
    """
    return get_stdout(['git', 'status', '--porcelain'] +
                      ([] if untracked else ['-uno'])) == ''


def checkout(treeish):
    call(['git', 'checkout'] + [treeish])


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
    output, code = get_stdout_and_exit_code(['git', 'rev-parse', '--git-dir'])
    if code == 0:
        return True
    elif output.startswith('fatal: Not a git repository (or any of the ' +
                           'parent directories):'):
        return False
    else:
        raise GitUnexpectedError('Strange git rev-parse --git-dir output :' +
                                 output + ' Exit-code: ' + str(code))


def get_git_dir():
    return get_stdout(['git', 'rev-parse', '--git-dir'])


def rev_parse(treeish):
    return get_stdout(['git', 'rev-parse', treeish])


def is_valid_ref_name(name):
    return check_01(['git', 'check-ref-format', 'refs/heads/' + name])


def set_merge_msg(string):
    with open(get_git_dir() + '/MERGE_MSG', 'w') as merge_msg_file:
        merge_msg_file.write(string)
