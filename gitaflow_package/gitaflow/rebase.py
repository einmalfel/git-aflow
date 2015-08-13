from gitaflow.common import die, start_iteration
from gitaflow.iteration import Iteration


def rebase(name, port, use_staging):
    if port:
        die('NIY')
    else:
        if use_staging is None:
            use_staging = Iteration.get_last().has_staging()
        start_iteration(name, use_staging)
