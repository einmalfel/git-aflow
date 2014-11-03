from gitaflow.common import die
from gitaflow import iteration


def rebase(name, port):
    if port:
        die('NIY')
    else:
        iteration.start_iteration(name)
