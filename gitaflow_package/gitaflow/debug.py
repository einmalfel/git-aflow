import os
import sys


class TestDebugState():
    """In test debug mode functional tests are run in same interpreter
    context as test framework itself, thus allowing usage of debugger for
    code being tested. Also, in test debug mode test framework should not
    intercept unhandled exceptions
    """

    class AflowStopped(Exception):
        """This exception is to let test suite know git-af command attempted to
        exit
        """
        def __init__(self, exit_code, output):
            self.exit_code = exit_code
            self.output = output

    __ENV_DEBUG = 'AFLOW_TEST_DEBUG'
    __output_buffer = ''
    __test_debug_mode = None
    __test_mode = None

    @classmethod
    def notify_test_mode(cls, value):
        cls.__test_mode = value
        cls.__test_debug_mode = None

    @classmethod
    def get_test_debug_mode(cls):
        if cls.__test_debug_mode is None:
            if cls.__ENV_DEBUG in os.environ:
                cls.__test_debug_mode = os.environ[cls.__ENV_DEBUG] == '1'
            else:
                cls.__test_debug_mode = (cls.__test_mode and sys.gettrace())
            if cls.__test_debug_mode:
                print('Test debug mode ON')
        return cls.__test_debug_mode

    @classmethod
    def reset(cls):
        cls.__output_buffer = ''

    @classmethod
    def output(cls, message):
        if cls.get_test_debug_mode():
            if cls.__output_buffer:
                cls.__output_buffer += os.linesep + message
            else:
                cls.__output_buffer = message
        else:
            print(message)

    @classmethod
    def exit(cls, exit_code):
        if cls.get_test_debug_mode():
            raise cls.AflowStopped(exit_code, cls.__output_buffer)
        else:
            exit(exit_code)
