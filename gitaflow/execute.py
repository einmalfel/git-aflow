"""execute.py
Process args for git af
"""

import sys
import logging


def setup_logging(verbosity, file_name):
    """setup_logging(verbosity, file_name)
    sets up log level, file name and string format
    """
    if verbosity < 0:
        loglevel = logging.CRITICAL
    elif verbosity == 0:
        loglevel = logging.WARNING
    elif verbosity == 1:
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG

    logging.basicConfig(
        filename=file_name,
        format='%(levelname)s %(module)s:%(lineno)d %(asctime)s %(message)s',
        level=loglevel
        )


def execute(args_namespace):
    setup_logging(args_namespace.verbosity, args_namespace.log_file)
    logging.info('Git aflow ' + str(sys.modules['gitaflow'].VERSION) +
                 '. Processing namespace ' + str(args_namespace))
