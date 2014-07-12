import logging
from os import linesep

from gitaflow import iteration
from gitaflow.common import die, say
from gitaflow.topic import Topic
from gitwrapper import misc, branch


def start(name):
    ci = iteration.get_current_iteration()
    if ci is None:
        die('Could not get current iteration, we are probably not in ' +
            'git-aflow repo')

    topic = Topic(name)
    branch_name = ci + '/' + name

    logging.info('Checking name ' + branch_name)
    if not topic.is_branch_name_valid(branch_name):
        die('Please correct topic name. "..", "~", "^", ":", "?", "*", ' +
            '"[", "@", "\", spaces and ASCII control characters' +
            ' are not allowed. Input something like "fix_issue18" or ' +
            '"do_api_refactoring"')

    logging.info('Check working tree')
    if not misc.is_working_tree_clean():
        die('Your working tree is dirty. Please, stash or reset your ' +
            'changes before starting topic')

    intersection = (frozenset(misc.get_untracked_files()) &
                    frozenset(misc.list_files_differ('HEAD', ci)))
    if intersection:
        die('You have some untracked files which you may loose when ' +
            'switching to new topic branch. Please, delete or commit them. ' +
            'Here they are: ' + ', '.join(intersection) + '.' + linesep +
            'Use "git clean" to remove all untracked files')

    logging.info('Check if there is branch for this topic already')
    branches = topic.get_branches()
    if branches:
        die('Cannot start topic, there are already branches: ' +
            ', '.join(branches))

    logging.info('Ok, now check if there was such topic somewhere in history')
    shas = topic.get_all_merges()
    if shas:
        die('Cannot start topic, it already exists in history, see SHA: ' +
            ', '.join(shas))

    logging.info('All good, creating branch ' + branch_name)
    try:
        branch.create(branch_name, ci)
    except:
        logging.critical('Something went wrong, cannot create topic branch')
        raise
    try:
        misc.checkout(branch_name)
    except:
        logging.critical('Something went wrong, cannot checkout ' +
                         'topic branch. Deleting branch and stopping')
        branch.delete(branch_name)
        raise
    say('Topic ' + name + ' created. You are in ' + branch_name + ' branch')
    return True
