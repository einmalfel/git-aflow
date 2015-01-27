#!/usr/bin/python3

from copy import deepcopy
import os
import profile
import pstats
from tempfile import TemporaryDirectory
import unittest
import atexit
import logging
import inspect
import time

from gitaflow import execute
from gitaflow.debug import TestDebugState
from gitwrapper import aux, grouped_cache


class AflowUnexpectedResult(Exception):
    pass


def check_aflow(*args):
    if measure_t == 'ALL_CALLS' or profiling == 'ALL_CALLS':
        frame = inspect.currentframe()
    else:
        frame = None
    output, exit_code = call_aflow(*args,
                                   caller_frame=frame.f_back if frame else None)
    if not exit_code == 0:
        raise AflowUnexpectedResult('Output: ' + str(exit_code) + '. ' + output)


def call_and_measure_aflow(args, call, caller):
    if profiling == 'ALL_CALLS' or (profiling == 'ASSERT_CALLS' and caller):
        print('Profiling ' + call.__name__ + '(["' + '", "'.join(args) + '"])' +
              (' called from ' + os.path.basename(caller.f_code.co_filename) +
               ':' + str(caller.f_lineno)) if caller else ':')
        profiler = profile.Profile()
        try:
            result = profiler.runcall(call, list(args))
        finally:
            profiler.create_stats()
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumtime')
            stats.print_stats(30)
        return result
    elif measure_t == 'ALL_CALLS' or (measure_t == 'ASSERT_CALLS' and caller):
        t1 = time.perf_counter()
        try:
            result = call(list(args))
        finally:
            t2 = time.perf_counter()
            spent = t2 - t1
            if caller:
                file = os.path.basename(caller.f_code.co_filename)
                timings.append((args, spent, file + ':' + str(caller.f_lineno)))
            else:
                timings.append((args, spent, None))
        return result
    else:
        return call(list(args))


def call_aflow(*args, caller_frame=None):
    if caller_frame is None and (measure_t == 'ALL_CALLS' or
                                 profiling == 'ALL_CALLS'):
        frame = inspect.currentframe()
        caller_frame = frame.f_back if frame else None
    if log_file:
        args = ('-vv', '-l', log_file) + args
    if TestDebugState.get_test_debug_mode():
        grouped_cache.invalidate(dont_print_info=True)
        TestDebugState.reset()
        try:
            call_and_measure_aflow(args, execute.execute, caller_frame)
            if grouped_cache.output_info:
                print(('Collecting cache info for ' + str(args)).ljust(80, '-'))
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
                print(('Cache info after ' + str(args) + ':').ljust(80, '-'))
                grouped_cache.print_cache_info()
            return stop.output, stop.exit_code
    else:
        result = call_and_measure_aflow(['git', 'af'] + list(args),
                                        aux.get_output_and_exit_code,
                                        caller_frame)
        grouped_cache.invalidate(dont_print_info=True)
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
        frame = inspect.currentframe()
        output, code = call_aflow(*cmd_and_args,
                                  caller_frame=frame.f_back if frame else None)
        if code:
            print('Aflow said:', output)
        if message:
            self.assertEqual((output, code), (message, 0))
        else:
            self.assertEqual(code, 0)

    def assert_aflow_dies_with(self, message, *cmd_and_args):
        frame = inspect.currentframe()
        output, code = call_aflow(*cmd_and_args,
                                  caller_frame=frame.f_back if frame else None)
        if message:
            self.assertEqual((output, code), (message, 1))
        else:
            self.assertEqual(code, 1)


class LocalTest(FunctionalTest):
    def setUp(self):
        self.temp_dir = TemporaryDirectory(prefix=self.id() + '_')
        os.chdir(self.temp_dir.name)
        if log_file:
            # Re-config logging. Reasons to do this:
            # 1. Logging may be used first time before aflow set it up
            # 2. Log should be stored in temp directory when relative path is
            # specified
            logging.basicConfig(
                filename=log_file,
                format='{levelname:<7}{asctime:<20}{module}:{lineno} {message}',
                style='{',
                level=logging.DEBUG)

    def tearDown(self):
        if log_file:
            for h in logging.root.handlers:
                h.close()
                logging.root.removeHandler(h)
        os.chdir(os.pardir)
        self.temp_dir.cleanup()


if __name__ == '__main__':
    unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('.'))
else:
    TestDebugState.notify_test_mode(True)
    profiling = os.environ.get('AFLOW_TEST_PROFILE')
    # AFLOW_TEST_PROFILE=ASSERT_CALLS profiles calls like assert_aflow_*().
    # ASSERT_CALLS may not work with some interpreters
    # AFLOW_TEST_PROFILE=ALL_CALLS profiles all calls
    # ASSERT_CALLS and ALL_CALLS print 20 slowest(by cumtime) functions
    if profiling and not (profiling == 'ALL_CALLS' or
                          profiling == 'ASSERT_CALLS'):
        print('Wrong AFLOW_TEST_PROFILE value', profiling,
              'choose one of ALL_CALLS, ASSERT_CALLS')
        exit(2)
    if profiling and not TestDebugState.get_test_debug_mode():
        print('WARNING: profiling with debug mode disabled. There is no sense '
              'in running profiler when child processes do all the work')

    log_file = os.environ.get('AFLOW_TEST_LOG')
    if log_file:
        # logging.basicConfig doesn't work when it has a handler set up
        # already. When debugging in PyCharm, it initially has stderr as
        # default handler
        for handler in logging.root.handlers:
            handler.close()
            logging.root.removeHandler(handler)
        logging.Formatter.default_time_format = '%y%m%d %T'

    measure_t = os.environ.get('AFLOW_TEST_TIME')
    # AFLOW_TEST_TIME=ASSERT_CALLS measures calls like self.assert_aflow_*()
    # ASSERT_CALLS may not work with some python interpreters (need
    # inspect.currentframe() support)
    # AFLOW_TEST_TIME=ALL_CALLS measures all calls
    if measure_t and not (measure_t == 'ALL_CALLS' or
                          measure_t == 'ASSERT_CALLS'):
        print('Wrong AFLOW_TEST_TIME value', measure_t,
              'possible values are ALL_CALLS and ASSERT_CALLS')
        exit(2)
    timings = []
    if profiling and measure_t:
        print('Profiling is incompatible with call time measurement')
        exit(2)
    if measure_t:
        def print_timings():
            to_print = sorted(timings, key=lambda x: -x[1])
            if len(to_print) > 10:
                to_print = to_print[:10]
            print(('Top ' + str(len(to_print)) +
                   ' slowest aflow calls').ljust(80, '-'))
            for arg_list, spent, caller_info in to_print:
                print('{:5.3f} {:<20} {}'.format(
                    spent, caller_info if caller_info else '', arg_list))
        atexit.register(print_timings)

    average_cache_info = None
    cache_samples = 0
    if grouped_cache.output_info and TestDebugState.get_test_debug_mode():
        def output_average_cache_info():
            if average_cache_info:
                to_print = deepcopy(average_cache_info)
                for func in to_print:
                    for field in to_print[func]:
                        to_print[func][field] /= cache_samples
                print('Average cache usage of all aflow calls:'.ljust(80, '-'))
                grouped_cache.print_cache_info(to_print)

        atexit.unregister(grouped_cache.print_cache_info)
        atexit.register(output_average_cache_info)
