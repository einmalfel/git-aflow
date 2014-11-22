"""Some common code for other modules of package"""

import logging

from gitaflow.debug import TestDebugState


def say(message):
    logging.info('Say to user: ' + message)
    TestDebugState.output(message)


def die(message, exit_code=1):
    if message:
        logging.info('Before exit say: ' + message)
        TestDebugState.output(message)
    TestDebugState.exit(exit_code)

