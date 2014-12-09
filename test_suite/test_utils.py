from copy import deepcopy
import os
import profile
from tempfile import TemporaryDirectory
import unittest
import atexit
import logging

from gitaflow import execute
from gitaflow.debug import TestDebugState
from gitwrapper import aux, grouped_cache

TestDebugState.notify_test_mode(True)

average_cache_info = None
cache_samples = 0

log_file = os.environ.get('AFLOW_TEST_LOGGING')
if log_file and TestDebugState.get_test_debug_mode():
    # in debug mode logging.py uses stderr as a handler for root logger.
    # logging.basicConfig doesn't work when there is a handler set up already
    logging.root.handlers = []


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
    if log_file:
        args = ('-vv', '-l', log_file) + args
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
        result = aux.get_output_and_exit_code(['git', 'af'] + list(args))
        grouped_cache.invalidate()
        return result


class FunctionalTest(unittest.TestCase):
    def add_error_replacement(self, _, err):
        value, traceback = err[1:]
        raise value.with_traceback(traceback)

    def run(self, result=None):
        if result and TestDebugState.get_test_debug_mode():
            result.addError = self.add_error_replacement
        super().run(result)

    def assert_aflow_returns_0(self, message, *cmd_and_args):
        output, code = call_aflow(*cmd_and_args)
        if code:
            print('Aflow said:', output)
        if message:
            self.assertEqual((output, code), (message, 0))
        else:
            self.assertEqual(code, 0)

    def assert_aflow_dies_with(self, message, *cmd_and_args):
        if message:
            self.assertEqual(call_aflow(*cmd_and_args), (message, 1))
        else:
            self.assertEqual(call_aflow(*cmd_and_args)[1], 1)


class LocalTest(FunctionalTest):
    def setUp(self):
        self.temp_dir = TemporaryDirectory(prefix=self.id() + '_')
        os.chdir(self.temp_dir.name)

    def tearDown(self):
        os.chdir(os.pardir)
        self.temp_dir.cleanup()


def run_tests():
    if TestDebugState.get_test_profile_mode():
        profile.run('unittest.main()', sort='cumtime')
    else:
        unittest.main()
