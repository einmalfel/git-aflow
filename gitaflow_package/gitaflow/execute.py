"""Process args for git af"""

import logging
import sys
import traceback

from gitaflow import init, merge, start, rebase, continue_, checkout, finish,\
    args, list_, revert
from gitaflow.common import die
from gitaflow.constants import VERSION
from gitwrapper.cached import misc


def log_unhandled_exception(type_, value, traceback_):
    description = ''.join(traceback.format_exception(type_, value, traceback_))
    logging.critical(description)
    print(description)


def setup_logging(verbosity, file_name):
    """setup_logging(verbosity, file_name)
    sets up log level, file name and string format
    If log file specified replace exception hook to print exception info to log
    """
    if verbosity < 0:
        loglevel = logging.CRITICAL
    elif verbosity == 0:
        loglevel = logging.WARNING
    elif verbosity == 1:
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG

    # this is the only way to specify time format and print milliseconds:
    logging.Formatter.default_time_format = '%y%m%d %T'
    logging.basicConfig(
        filename=file_name,
        format='{levelname:<7}{asctime:<20}{module}:{lineno} {message}',
        style='{',
        level=loglevel)

    if file_name:
        sys.excepthook = log_unhandled_exception


def execute(cli_args=sys.argv[1:]):
    args_namespace = args.parse_args(cli_args)
    if args_namespace:
        setup_logging(args_namespace.verbosity, args_namespace.log_file)
        logging.info(
            'Git aflow ' + VERSION + '. Processing args ' + str(args_namespace))

        # here is first git call, so do coupla checks:
        # - we are inside git repo
        # - git present
        # TODO ? suggest commands to install git
        try:
            if not misc.in_git_repo():
                die('No git repo found. Please, chdir to repo')
        except FileNotFoundError:
            die('Git not found. You need to install it to use git-aflow')

        if args_namespace.subcommand == 'init':
            init.init_aflow(args_namespace.name)
        elif args_namespace.subcommand == 'start':
            start.start(args_namespace.name)
        elif args_namespace.subcommand == 'continue':
            continue_.continue_(args_namespace.name, args_namespace.unfinish)
        elif args_namespace.subcommand == 'finish':
            finish.finish(args_namespace.description,
                          args_namespace.topic_finish_type,
                          args_namespace.name)
        elif args_namespace.subcommand == 'merge':
            merge.merge(args_namespace.source,
                        args_namespace.merge_type,
                        args_namespace.dependencies,
                        args_namespace.merge_object,
                        args_namespace.topic,
                        args_namespace.edit_description)
        elif args_namespace.subcommand == 'rebase':
            rebase.rebase(args_namespace.name, args_namespace.port)
        elif args_namespace.subcommand == 'checkout':
            checkout.checkout(args_namespace.name)
        elif args_namespace.subcommand == 'list':
            list_.list_(args_namespace.source,
                        args_namespace.all,
                        args_namespace.filters)
        elif args_namespace.subcommand == 'revert':
            revert.revert(args_namespace.name, args_namespace.dependencies)

    exit(0)
