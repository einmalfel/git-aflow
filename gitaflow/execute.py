"""execute.py
Process args for git af
"""

import sys
import logging


def setup_logging(verbosity):
    if verbosity < 0:
        loglevel = logging.CRITICAL
    if verbosity == 0:
        loglevel = logging.WARNING
    elif verbosity == 1:
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG

    logging.basicConfig(
        format='%(levelname)s %(module)s:%(lineno)d %(asctime)s %(message)s',
        level=loglevel
        )


def execute(args_namespace):
    setup_logging(args_namespace.verbosity)
    logging.info('Git aflow ' + str(sys.modules['gitaflow'].VERSION)
                 + '. Processing namespace ' + str(args_namespace))
