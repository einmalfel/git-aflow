"""Iteration management functionality"""


import logging

from gitwrapper import misc, branch, tag, commit

from .constants import DEVELOP_NAME, MASTER_NAME, STAGING_NAME


def is_valid_iteration_name(name):
    return (misc.is_valid_ref_name(name) and
            misc.is_valid_ref_name(name + '/' + DEVELOP_NAME) and
            misc.is_valid_ref_name(name + '/' + STAGING_NAME))


def start_iteration(iteration_name):
    for tag in tag.get_tags_by_target(MASTER_NAME):
        if is_iteration(tag):
            print('There is already an iteration ' + tag +
                  ' started from the top of master branch')
            return False
    if not is_valid_iteration_name(iteration_name):
        print('Please, correct your iteration name. ".."'
', "~", "^", ":", "?", "*", "[", "@", "\", spaces and ASCII control characters'
' are not allowed. Input something like "iter_1" or "start"')
        return False
    develop_name = get_develop(iteration_name)
    staging_name = get_staging(iteration_name)
    if tag.tag_exists(iteration_name):
        print('Cannot start iteration, tag ' + iteration_name + ' exists')
        return False
    if branch.branch_exists(develop_name):
        print('Cannot start iteration, branch + ' + develop_name + ' exists')
        return False
    if branch.branch_exists(staging_name):
        print('Cannot start iteration, branch + ' + staging_name + ' exists')
        return False
    if not (tag.create_tag(iteration_name, MASTER_NAME) and
            branch.create_branch(develop_name, MASTER_NAME) and
            branch.create_branch(staging_name, MASTER_NAME)):
        tag.delete_tag(iteration_name)
        branch.delete_branch(staging_name)
        branch.delete_branch(develop_name)
        logging.critical('Failed to create iteration ' + iteration_name)
        return False
    print('Iteration ' + iteration_name + ' created successfully')
    return True


def is_iteration(name):
    """Checks whether there is a base point with given name"""
    result = (tag.tag_exists(name) and
            branch.branch_exists(get_develop(name)) and
            branch.branch_exists(get_staging(name)))
    logging.debug('Check: iteration ' + name +
          (' exists' if result else " doesn't exists"))
    return result


def get_iteration_list():
    return [t for t in tag.get_tag_list() if is_iteration(t)]


def get_current_iteration():
    """Calculates current iteration.
    We cannot store iteration in something like "current_iteration" tag, cause
    user may switch branches without git-aflow.
    TODO: Assuming user will not run git commands while git-af running, this
    func probably needs cache.
    """
    branch = branch.get_current_branch()
    if branch:
        if '/' in branch:
            iteration = branch.split('/', 1)[0]
            if is_iteration(iteration):
                logging.info('found iteration ' + iteration + ' for branch ' +
                              branch)
                return iteration
    iterations = {tag.get_tag_SHA(tag): tag
             for tag in get_iteration_list()}
    position = commit.get_current_commit_SHA()
    while position:
        if position in iterations:
            logging.info('found latest iteration ' + iterations[position] +
                         ' for branch ' + branch)
            return iterations[position]
        position = commit.get_main_ancestor(position)
    logging.critical('cannot get iteration for ' +
                     (branch if branch else 'detached HEAD'))


def get_develop(iteration=None):
    return ((iteration if iteration else get_current_iteration()) +
            '/' + DEVELOP_NAME)


def get_staging(iteration=None):
    return ((iteration if iteration else get_current_iteration()) +
            '/' + STAGING_NAME)
