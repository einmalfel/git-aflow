"""Git-aflow repo initialization functionality"""

import sys
from gitaflow.common import say

from gitaflow.iteration import start_iteration, get_iteration_list


def init_aflow(iteration_name):
    """Check if isn't initialized already. Create new develop and staging
    TODO: make interactive?
    """
    if in_aflow_repo():
        say('There is a git-aflow repo already, aborting')
        sys.exit(1)
    if start_iteration(iteration_name):
        say('Git-aflow initialized successfully')
    else:
        say('Git-aflow initialization failed')


def in_aflow_repo():
    return [] != get_iteration_list()
