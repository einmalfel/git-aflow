import logging
from os import linesep

from gitaflow import iteration
from gitaflow.topic import Topic
from gitwrapper import misc, branch


def start(name):
    ci = iteration.get_current_iteration()
    if ci is None:
        print('Could not get current iteration, we are probably not in ' +
              'git-aflow repo')
        logging.info('No CI, stopping')
        return False

    topic = Topic(name)
    branch_name = ci + '/' + name

    logging.info('Checking name ' + branch_name)
    if not topic.is_branch_name_valid(branch_name):
        print('Please correct topic name. "..", "~", "^", ":", "?", "*", ' +
              '"[", "@", "\", spaces and ASCII control characters' +
              ' are not allowed. Input something like "fix_issue18" or ' +
              '"do_api_refactoring"')
        logging.info('Wrong topic name. Stopping')
        return False

    logging.info('Check working tree')
    if not misc.is_working_tree_clean():
        print('Your working tree is dirty. Please, stash or reset your ' +
              'changes before starting topic')
        logging.info('Working tree is dirty stopping, stopping')
        return False

    intersection = (frozenset(misc.get_untracked_files()) &
                    frozenset(misc.list_files_differ('HEAD', ci)))
    if intersection:
        print('You have some untracked files which you may loose when ' +
              'switching to new topic branch. Please, delete or commit them. ' +
              'Here they are: ' + ', '.join(intersection) + '.' + linesep +
              'Use "git clean" to remove all untracked files')
        logging.info('User may lose untracked file, stopping')
        return False

    logging.info('Check if there is branch for this topic already')
    branches = topic.get_branches()
    if branches:
        print('Cannot start topic, there are already branches: ' +
              ', '.join(branches))
        logging.info('Topic branches with given name exists, stopping')
        return False

    logging.info('Ok, now check if there was such topic somewhere in history')
    shas = topic.get_all_merges()
    if shas:
        print('Cannot start topic, it already exists in history, see SHA: ' +
              ', '.join(shas))
        logging.info('Topics with given name exist in history, stopping')
        return False

    logging.info('All good, creating branch ' + branch_name)
    if not branch.create(branch_name, ci):
        logging.critical('Something went wrong, cannot create topic branch')
        return False
    if misc.checkout(branch_name):
        print('Topic ' + name + ' created. You are in ' + branch_name +
              ' branch')
        return True
    else:
        logging.critical('Something went wrong, cannot checkout ' +
                         'topic branch. Deleting branch and stopping')
        branch.delete(branch_name)
        return False
