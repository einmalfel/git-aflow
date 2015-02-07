"""args.py
This module is about args parsing and checking for 'git af'

TODO:
 - show values for defaults e.g. 'Name of topic to fix.
Defaults to current topic (feature/some_feature_'). Also pass default value to
ArgumentParser
"""

import argparse

from gitaflow.common import say
from gitaflow.constants import VERSION


def parse_args(args_list):
    """parse_args(args_list)
    Parse git af command line arguments, check errors and return namespace
    object with arguments as fields
    """

    main_parser = argparse.ArgumentParser(
        prog='git-aflow',
        description='Git-aflow helper tool. Use "git af SUBCOMMAND -h" to \
learn more about using subcommands listed below')
    main_parser.add_argument(
        '--version', action='version', version='%(prog)s ' + VERSION)
    main_parser.add_argument('--log-file', '-l')
    output_mode = main_parser.add_mutually_exclusive_group()
    output_mode.add_argument(
        '-v', '--verbosity', action='count', default=0,
        help='Increase output verbosity. Every instance of -v increments the \
verbosity level by one')
    output_mode.add_argument(
        '-q', '--quiet', action='store_const', const=-1, dest='verbosity',
        help='Suppress warning and error messages')
    main_subparsers = main_parser.add_subparsers(
        title='Subcommands',
        dest='subcommand')

    # Not described in python docs:
    # help is what user sees in subcommands list (git af)
    # description is what (s)he sees in git af topic -h
    #
    # TODO more detailed description
    topic_start_parser = main_subparsers.add_parser(
        'start',
        help='Start new topic branch and switch to it',
        description='Start new topic branch and switch to it')
    topic_start_parser.add_argument('name', help='Name for new topic branch')
    topic_finish_parser = main_subparsers.add_parser(
        'finish',
        help='Finish topic and merge it into develop',
        description='Finish topic: checks if it conflicts with other topics, ' +
                    'merges it into develop branch and deletes topic branch')
    topic_finish_parser.add_argument(
        '-n', '--name',
        help='Set name of topic. Defaults to topic branch name. Use it if you '
             'want to change topic name given on topic start')
    topic_finish_parser.add_argument(
        'description',
        nargs='?',
        help='Some text describing purpose of this topic branch and what was '
             'done in it.')
    topic_finish_type = topic_finish_parser.add_mutually_exclusive_group()
    topic_finish_type.add_argument(
        '-D', '--DEV', dest='topic_finish_type',
        action='store_const', const='DEV',
        help='Set topic type to DEV (e.g. refactoring)')
    topic_finish_type.add_argument(
        '-E', '--EUF', dest='topic_finish_type',
        action='store_const', const='EUF',
        help='Set topic type to EUF (end user feature)')
    topic_finish_type.add_argument(
        '-F', '--FIX', dest='topic_finish_type',
        action='store_const', const='FIX',
        help='Set topic type to FIX (bug fix)')
    topic_stage_parser = main_subparsers.add_parser(
        'stage',
        help='Finish topic and put it into develop',
        description='Finish topic and put it into develop')
    topic_stage_parser.add_argument(
        'name',
        nargs='?',
        help='Topic will be checked for conflicts against and merged into \
stage. Defaults to current branch')
    topic_continue_parser = main_subparsers.add_parser(
        'continue',
        help='Create a branch for new version of topic',
        description='Use this to update topic by making a new version of it. '
                    'Commit changes to branch created by this command, '
                    'then call "git af topic finish" to merge new '
                    'version of topic into develop')
    topic_continue_parser.add_argument(
        'name',
        nargs='?',
        help='Name of topic to be continued. If none given, aflow will check '
             'if your HEAD points to last commit of some topic. Aflow will '
             'use iteration prefix to switch iteration before proceeding and '
             'will ignore version suffix.')

    release_parser = main_subparsers.add_parser(
        'release',
        help='Release branches management',
        description='Release branches management')
    release_subparsers = release_parser.add_subparsers(
        title='Release subcommands',
        dest='subsubcommand')
    release_minor_parser = release_subparsers.add_parser(
        'minor',
        help='Branch new minor release',
        description='Branch new minor release')
    release_minor_parser.add_argument(
        'prev-release',
        nargs='?',
        help='Specify release on which this one will base. Defaults to \
release checked out now')
    release_minor_parser.add_argument(
        '-n', '--name',
        help='Name of new release. If not specified will ask interactively')
    release_major_parser = release_subparsers.add_parser(
        'major',
        help='Branch out new major release from master',
        description='Branch out new major release from master')
    release_major_parser.add_argument(
        '-n', '--name',
        help='Name of new release. If not specified will ask interactively')
    release_finish_parser = release_subparsers.add_parser(
        'finish',
        help='Branch out new major release from master',
        description='Branch out new major release from master')
    release_finish_parser.add_argument(
        'name',
        nargs='?',
        help='Which release to finish. Defaults to currently checked out')

    list_parser = main_subparsers.add_parser(
        'list',
        help='Listing branches',
        description='Listing branches')
    list_mode = list_parser.add_mutually_exclusive_group()
    list_mode.add_argument(
        '-s', '--staged', dest='listmode',
        action='store_const', const='staged',
        help='List staged branches. These branches may not conflict \
with each other and may be merged in release or master')
    list_mode.add_argument(
        '-d', '--developing', dest='listmode',
        action='store_const', const='developing',
        help='List topics not yet reviewed and staged. These branches \
may conflict with each other')
    list_mode.add_argument(
        '-a', '--all', dest='listmode',
        action='store_const', const=None,
        help='List all finished topics in repo')

    rebase_parser = main_subparsers.add_parser(
        'rebase',
        help='Start new iteration.',
        description='This command starts new iteration by creating BP, '
                    'develop and staging on the top of master branch. By '
                    'default, it also tries to rebase some of '
                    'not-merged-in-master topics into created iteration.')
    rebase_parser.add_argument(
        'name',
        help='Name of new iteration. Name should describe what your are going '
             'to do after BP rather then what you have done before it')
    rebase_parser.add_argument(
        '-n', '--no-porting',
        action='store_false',
        dest='port',
        help='Do not rebase any topics, just start new iteration.')

    merge_parser = main_subparsers.add_parser(
        'merge',
        help='Merge topics into current branch',
        description='Merge topics into current branch')
    merge_parser.add_argument(
        '-d', '--dependencies',
        action='store_true',
        help="If topics specified to merge depend on other topics you don't \
have in current branch those topics would be merged prior to specified ones")
    merge_type = merge_parser.add_mutually_exclusive_group()
    merge_type.add_argument(
        '-D', '--DEV', dest='merge_type',
        action='store_const', const='DEV',
        help='Set DEV type to topic while merging')
    merge_type.add_argument(
        '-E', '--EUF', dest='merge_type',
        action='store_const', const='EUF',
        help='Set EUF type to topic while merging')
    merge_type.add_argument(
        '-F', '--FIX', dest='merge_type',
        action='store_const', const='FIX',
        help='Set FIX type to topic while merging')
    merge_object = merge_parser.add_mutually_exclusive_group()
    merge_object.add_argument(
        '-a', '--all', dest='merge_object',
        action='store_const', const='all',
        help='Merge all topics from source(s)')
    merge_object.add_argument(
        '-u', '--update', dest='merge_object',
        action='store_const', const='update',
        help='Merge only topics which version in source(s) is greater then \
version in current branch')
    merge_object.add_argument(
        '-c', '--choose', dest='merge_object',
        action='store_const', const=None,
        help='Merge topics specified as positional arguments. This is default.')
    merge_parser.add_argument(
        'topic', nargs='*',
        help='List of topics to merge into current. It will merge topics of \
given versions if they are present in sources or merge newest versions if no \
versions specified. E.g. "git af merge topicA topicB_v2" merges latest version \
of topicA and second version of topicB')
    merge_parser.add_argument(
        '-s', '--source', action='append',
        help='Sources to search for topics. This could be master and any \
branches from current iteration. By default it is master+staging if you are \
in release branch, staging if you are in master and develop in other cases. \
You may specify more then one source (e.g. -s source1 -ssource2)')
    merge_parser.add_argument(
        '-e', '--edit-description',
        help='You may replace topic description with yours. This only works if \
if single topic is specified to merge (with or without dependencies)')

    checkout_parser = main_subparsers.add_parser(
        'checkout',
        help='Checkout given topic branch or revision head',
        description='If there is a branch for given revision, checks it out. '
                    'Otherwise, checks out head commit of specified revision'
                    '(detached HEAD mode). '
                    'This command will assume that you are switching '
                    'between topics and branches inside current iteration, '
                    'unless topic is specified along with "iteration/" prefix. '
                    'Master branch always belongs to last iteration.')
    checkout_parser.add_argument(
        'name',
        help='Name of branch/topic/revision to checkout.')

    init_parser = main_subparsers.add_parser(
        'init',
        help='Initialize git-aflow for existing git repo',
        description='Initialize git-aflow for existing git repo. Call this \
from the top of master branch')
    init_parser.add_argument(
        'name',
        help='Name of first iteration.')

    args = main_parser.parse_args(args_list)

    if args.subcommand is None:
        say(main_parser.format_help())
        return None
    elif args.subcommand == 'release':
        if args.subsubcommand is None:
            say(release_parser.format_help())
            return None
    elif args.subcommand == 'merge':
        if args.merge_object is None and not args.topic:
            merge_parser.error('Please, specify topics you wish to merge, or \
one of [-u|-a] options.')
        if args.merge_object is not None and args.topic:
            merge_parser.error('Cannot process --all or --update with topic \
list. You may choose to merge all topics from sources OR update your topics \
OR specify a list of topics to merge.')
    return args
