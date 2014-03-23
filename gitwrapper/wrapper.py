import gitwrapper.aux


def in_git_repo():
    return True if gitwrapper.aux.launch_and_get_exit_code(
        'git rev-parse --git-dir'.split()) == 0 else False
