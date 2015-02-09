from gitaflow.common import die, start_iteration


def rebase(name, port):
    if port:
        die('NIY')
    else:
        start_iteration(name)
