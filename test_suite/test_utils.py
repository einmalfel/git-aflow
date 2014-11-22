from gitaflow import execute, iteration
from gitaflow.debug import TestDebugState
from gitwrapper import aux


TestDebugState.notify_test_mode(True)


def clear_caches():
    iteration.get_iteration_by_sha.cache_clear()
    TestDebugState.reset()


class AflowUnexpectedResult(Exception):
    pass


def check_aflow(*args):
    output, exit_code = call_aflow(*args)
    if not exit_code == 0:
        raise AflowUnexpectedResult('Output: ' + str(exit_code) + '. ' + output)


def call_aflow(*args):
    if TestDebugState.get_test_debug_mode():
        clear_caches()
        try:
            execute.execute(args)
            raise TestDebugState.AflowStopped(129, '')
        except TestDebugState.AflowStopped as stop:
            return stop.output, stop.exit_code
    else:
        return aux.get_output_and_exit_code(['git', 'af'] + list(args))
