from copy import deepcopy
import profile
import unittest
import atexit

from gitaflow import execute
from gitaflow.debug import TestDebugState
from gitwrapper import aux, grouped_cache

TestDebugState.notify_test_mode(True)

average_cache_info = None
cache_samples = 0


def output_average_cache_info():
    if average_cache_info:
        to_print = deepcopy(average_cache_info)
        for func in to_print:
            for field in to_print[func]:
                to_print[func][field] /= cache_samples
        print('Average cache usage among all aflow invocations:'.ljust(80, '-'))
        grouped_cache.print_cache_info(to_print)


if grouped_cache.output_info and TestDebugState.get_test_debug_mode():
    atexit.unregister(grouped_cache.print_cache_info)
    atexit.register(output_average_cache_info)


class AflowUnexpectedResult(Exception):
    pass


def check_aflow(*args):
    output, exit_code = call_aflow(*args)
    if not exit_code == 0:
        raise AflowUnexpectedResult('Output: ' + str(exit_code) + '. ' + output)


def call_aflow(*args):
    if TestDebugState.get_test_debug_mode():
        grouped_cache.invalidate()
        TestDebugState.reset()
        try:
            execute.execute(args)
            raise TestDebugState.AflowStopped(129, '')
        except TestDebugState.AflowStopped as stop:
            if grouped_cache.output_info:
                global average_cache_info, cache_samples
                info = grouped_cache.get_cache_info()
                cache_samples += 1
                if average_cache_info is None:
                    average_cache_info = info
                else:
                    for func in info:
                        for field in info[func]:
                            average_cache_info[func][field] += info[func][field]
                print(('Cache info for ' + str(args) + ':').ljust(80, '-'))
                grouped_cache.print_cache_info()
            return stop.output, stop.exit_code
    else:
        return aux.get_output_and_exit_code(['git', 'af'] + list(args))


def run_tests():
    if TestDebugState.get_test_profile_mode():
        profile.run('unittest.main()', sort='cumtime')
    else:
        unittest.main()
