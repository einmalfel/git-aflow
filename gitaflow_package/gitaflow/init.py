"""Git-aflow repo initialization functionality"""

from gitaflow.common import say, die, start_iteration
from gitaflow.iteration import get_iterations


def init_aflow(iteration_name):
    """Check if isn't initialized already. Create new develop and staging
    TODO: make interactive?
    """
    if in_aflow_repo():
        die('There is a git-aflow repo already, aborting')
    if start_iteration(iteration_name):
        say('Git-aflow initialized successfully')


def in_aflow_repo():
    return bool(get_iterations())
