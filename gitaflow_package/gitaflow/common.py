"""Some common code for other modules of package"""

import logging


def say(message):
    logging.info('Say to user: ' + message)
    print(message)


def die(message, exit_code=1):
    logging.info('Before exit say: ' + message)
    print(message)
    exit(exit_code)
