"""Iteration management functionality"""


import logging

from gitaflow.constants import DEVELOP_NAME, MASTER_NAME, STAGING_NAME
import gitwrapper.wrapper


def is_valid_iteration_name(name):
    return (gitwrapper.wrapper.is_valid_ref_name(name) and
            gitwrapper.wrapper.is_valid_ref_name(name + '/' + DEVELOP_NAME) and
            gitwrapper.wrapper.is_valid_ref_name(name + '/' + STAGING_NAME))


def start_iteration(iteration_name):
    if not is_valid_iteration_name(iteration_name):
        print('Please, correct your iteration name. ".."'
', "~", "^", ":", "?", "*", "[", "@", "\", spaces and ASCII control characters'
' are not allowed. Input something like "iter_1" or "start":\n')
        return False
    develop_name = get_develop(iteration_name)
    staging_name = get_staging(iteration_name)
    if gitwrapper.wrapper.tag_exists(iteration_name):
        print('Cannot start iteration, tag ' + iteration_name + ' exists')
        return False
    if gitwrapper.wrapper.branch_exists(develop_name):
        print('Cannot start iteration, branch + ' + develop_name + ' exists')
        return False
    if gitwrapper.wrapper.branch_exists(staging_name):
        print('Cannot start iteration, branch + ' + staging_name + ' exists')
        return False
    if not (gitwrapper.wrapper.create_tag(iteration_name, MASTER_NAME) and
            gitwrapper.wrapper.create_branch(develop_name, MASTER_NAME) and
            gitwrapper.wrapper.create_branch(staging_name, MASTER_NAME)):
        gitwrapper.wrapper.delete_tag(iteration_name)
        gitwrapper.wrapper.delete_branch(staging_name)
        gitwrapper.wrapper.delete_branch(develop_name)
        logging.critical('Failed to create iteration ' + iteration_name)
        return False
    print('Iteration ' + iteration_name + ' created successfully')
    return True


def is_iteration(name):
    """Checks whether there is a base point with given name"""
    result = (gitwrapper.wrapper.tag_exists(name) and
            gitwrapper.wrapper.branch_exists(get_develop(name)) and
            gitwrapper.wrapper.branch_exists(get_staging(name)))
    logging.debug('Check: iteration ' + name +
          (' exists' if result else " doesn't exists"))
    return result


def get_iteration_list():
    return [t for t in gitwrapper.wrapper.get_tag_list() if is_iteration(t)]


def get_current_iteration():
    """Calculates current iteration.
    We cannot store iteration in something like "current_iteration" tag, cause
    user may switch branches without git-aflow.
    TODO: Assuming user will not run git commands while git-af running, this
    func probably needs cache.
    """
    branch = gitwrapper.wrapper.get_current_branch()
    if branch:
        if '/' in branch:
            iteration = branch.lsplit('/')
            if is_iteration(iteration):
                logging.info('found iteration ' + iteration + ' for branch ' +
                              branch)
                return iteration
    iterations = {gitwrapper.wrapper.get_tag_SHA(tag): tag
             for tag in get_iteration_list()}
    commit = gitwrapper.wrapper.get_current_commit_SHA()
    while commit:
        if commit in iterations:
            logging.info('found latest iteration ' + iterations[commit] +
                         ' for branch ' + branch)
            return iterations[commit]
        commit = gitwrapper.wrapper.get_main_ancestor(commit)
    logging.critical('cannot get iteration for ' +
                     (branch if branch else 'detached HEAD'))


def get_develop(iteration=None):
    return ((iteration if iteration else get_current_iteration()) +
            '/' + DEVELOP_NAME)


def get_staging(iteration=None):
    return ((iteration if iteration else get_current_iteration()) +
            '/' + STAGING_NAME)
