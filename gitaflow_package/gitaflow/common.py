"""Some common code for other modules of package"""

import logging

from gitaflow import iteration
from gitaflow.constants import STAGING_NAME, MASTER_NAME, DEVELOP_NAME, \
    RELEASE_NAME
from gitaflow.debug import TestDebugState
from gitwrapper.cached import misc, branch, commit, tag


def say(message):
    logging.info('Say to user: ' + message)
    TestDebugState.output(message)


def die(message, exit_code=1):
    if message:
        logging.info('Before exit say: ' + message)
        TestDebugState.output(message)
    TestDebugState.exit(exit_code)



def start_iteration(iteration_name):
    for tag_ in tag.find_by_target(MASTER_NAME):
        if iteration.is_iteration(tag_):
            die('There is already an iteration ' + tag_ +
                ' started from the top of master branch')
    if not iteration.is_valid_iteration_name(iteration_name):
        die('Please, correct your iteration name. "..", "~", "^", ":", "?",' +
            ' "*", "[", "@", "\", spaces and ASCII control characters' +
            ' are not allowed. Input something like "iter_1" or "start"')
    develop_name = iteration.get_develop(iteration_name)
    staging_name = iteration.get_staging(iteration_name)
    if tag.exists(iteration_name):
        die('Cannot start iteration, tag ' + iteration_name + ' exists')
    if branch.exists(develop_name):
        die('Cannot start iteration, branch ' + develop_name + ' exists')
    if branch.exists(staging_name):
        die('Cannot start iteration, branch ' + staging_name + ' exists')
    try:
        tag.create(iteration_name, MASTER_NAME)
        branch.create(develop_name, MASTER_NAME)
        branch.create(staging_name, MASTER_NAME)
    except:
        tag.delete(iteration_name)
        branch.delete(staging_name)
        branch.delete(develop_name)
        logging.critical('Failed to create iteration ' + iteration_name)
        raise
    say('Iteration ' + iteration_name + ' created successfully')
    return True
