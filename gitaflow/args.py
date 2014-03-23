"""args.py
this module is about args parsing and checking for 'git af'

TODO:
 - show values for defaults e.g. 'Name of topic to fix.
Defaults to current topic (feature/some_feature_'). Also pass default value to
ArgumentParser
"""


import argparse
import sys


def parse_args(args_list):
    """parse_args(args_list)
    Parse git af command line arguments, check errors and return namespace
    object with arguments as fields
    """

    main_parser = argparse.ArgumentParser(
        prog='git-aflow',
        description='Git-aflow helper scripts'
        )
    main_parser.add_argument(
        '--version', action='version', version='%(prog)s '
        + str(sys.modules['gitaflow'].VERSION)
        )
    output_mode = main_parser.add_mutually_exclusive_group()
    output_mode.add_argument(
        '-v', '--verbosity', action='count', default=0,
        help='Increase output verbosity. Every instance of -v increments the \
        verbosity level by one'
        )
    output_mode.add_argument(
        '-q', '--quiet', action='store_const', const=-1, dest='verbosity',
        help='Suppress warning and error messages'
        )
    main_subparsers = main_parser.add_subparsers(
        title='Subcommands',
        dest='subcommand'
        )

    # Not described in python docs:
    # help is what user sees in subcommands list (git af)
    # description is what (s)he sees in git af topic -h
    #
    # TODO more detailed description
    topic_parser = main_subparsers.add_parser(
        'topic',
        help='Topic branches management',
        description='Topic branches management'
        )
    topic_subparsers = topic_parser.add_subparsers(
        title='Topic subcommands',
        dest='subsubcommand'
        )
    topic_start_parser = topic_subparsers.add_parser(
        'start',
        help='Start new topic branch and switch to it',
        description='Start new topic branch and switch to it'
        )
    topic_start_parser.add_argument('name', help='Name for new topic branch')
    topic_finish_parser = topic_subparsers.add_parser(
        'finish',
        help='Finish topic and put it into devel',
        description='Finish topic and put it into devel'
        )
    topic_finish_parser.add_argument(
        'name',
        nargs='?',
        help='Topic name to finish. Defaults to current branch'
        )
    topic_stage_parser = topic_subparsers.add_parser(
        'stage',
        help='Finish topic and put it into devel',
        description='Finish topic and put it into devel'
        )
    topic_stage_parser.add_argument(
        'name',
        nargs='?',
        help='Topic will be checked for conflicts against and merged into \
        stage. Defaults to current branch'
        )

    release_parser = main_subparsers.add_parser(
        'release',
        help='Release branches management',
        description='Release branches management'
        )
    release_subparsers = release_parser.add_subparsers(
        title='Release subcommands',
        dest='subsubcommand'
        )
    release_minor_parser = release_subparsers.add_parser(
        'minor',
        help='Branch new minor release',
        description='Branch new minor release'
        )
    release_minor_parser.add_argument(
        'prev-release',
        nargs='?',
        help='Specify release on which this one will base. Defaults to \
        release checked out now'
        )
    release_minor_parser.add_argument(
        '-n', '--name',
        help='Name of new release. If not specified will ask interactively'
        )
    release_major_parser = release_subparsers.add_parser(
        'major',
        help='Branch out new major release from master',
        description='Branch out new major release from master'
        )
    release_major_parser.add_argument(
        '-n', '--name',
        help='Name of new release. If not specified will ask interactively'
        )
    release_finish_parser = release_subparsers.add_parser(
        'finish',
        help='Branch out new major release from master',
        description='Branch out new major release from master'
        )
    release_finish_parser.add_argument(
        'name',
        nargs='?',
        help='Which release to finish. Defaults to currently checkouted'
        )

    list_parser = main_subparsers.add_parser(
        'list',
        help='Listing branches',
        description='Listing branches'
        )
    list_mode = list_parser.add_mutually_exclusive_group()
    list_mode.add_argument(
        '-s', '--staged', dest='listmode',
        action='store_const', const='staged',
        help='List staged branches. These branches may not conflict \
        with each other and may be merged in release or master'
        )
    list_mode.add_argument(
        '-d', '--developing', dest='listmode',
        action='store_const', const='developing',
        help='List topics not yet reviewed and staged. These branches \
        may conflict with each other'
        )
    list_mode.add_argument(
        '-a', '--all', dest='listmode',
        action='store_const', const=None,
        help='List all finished topics in repo'
        )

    args = main_parser.parse_args(args_list)

    if args.subcommand is None:
        main_parser.print_help()
        return None
    elif args.subcommand == 'release':
        if args.subsubcommand is None:
            release_parser.print_help()
            return None
    elif args.subcommand == 'topic':
        if args.subsubcommand is None:
            topic_parser.print_help()
            return None
    return args
