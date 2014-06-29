"""Process args for git af"""

import logging
import os
import sys

from gitwrapper import misc
from . import init, topic


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
        level=loglevel)


def execute(args_namespace):
    setup_logging(args_namespace.verbosity, args_namespace.log_file)
    logging.info('Git aflow ' + str(sys.modules['gitaflow'].VERSION) +
                 '. Processing namespace ' + str(args_namespace))

    # here is first git call, so do coupla checks:
    # - we are inside git repo
    # - git present
    # TODO ? suggest commands to install git
    try:
        if not misc.in_git_repo():
            logging.info('trying to launch aflow outside of git repo: ' +
                         os.getcwd())
            print('No git repo found. Please, chdir to repo')
            sys.exit(1)
    except FileNotFoundError:
        logging.info('trying to launch git-aflow without git installed')
        print("Git not found. You need to install it to use git-aflow")
        sys.exit(1)

    if args_namespace.subcommand == 'init':
        init.init_aflow(args_namespace.name)
    elif args_namespace.subcommand == 'topic':
        if args_namespace.subsubcommand == 'start':
            topic.start(args_namespace.name)
    elif args_namespace.subcommand == 'merge':
        topic.merge(args_namespace.source,
                    args_namespace.merge_type,
                    args_namespace.dependencies,
                    args_namespace.merge_object,
                    args_namespace.topic,
                    args_namespace.edit_description)
