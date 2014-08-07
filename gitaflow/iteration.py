"""Iteration management functionality"""

import atexit
from functools import lru_cache
import logging
import re

from gitwrapper import misc, branch, tag, commit
from .constants import DEVELOP_NAME, MASTER_NAME, STAGING_NAME, RELEASE_NAME


def parse_branch_name(branch_name):
    """Returns (iteration, name) tuple or (None, None) if cannot parse.
    E.g.: parse_branch_name("master") produces (None, "master")
    parse_branch_name("iter1/topic_v2") produces ("iter1", "topic_v2")
    """
    if branch_name == MASTER_NAME:
        return None, MASTER_NAME
    if parse_branch_name.regexp is None:
        parse_branch_name.regexp =\
            re.compile('^([^/]*)/(.*)$')
    result = parse_branch_name.regexp.search(branch_name)
    if not result:
        return None, None
    return result.groups()
parse_branch_name.regexp = None


def is_valid_iteration_name(name):
    return (misc.is_valid_ref_name(name) and
            misc.is_valid_ref_name(name + '/' + DEVELOP_NAME) and
            misc.is_valid_ref_name(name + '/' + STAGING_NAME))


def start_iteration(iteration_name):
    for tag_ in tag.find_by_target(MASTER_NAME):
        if is_iteration(tag_):
            print('There is already an iteration ' + tag_ +
                  ' started from the top of master branch')
            return False
    if not is_valid_iteration_name(iteration_name):
        print('Please, correct your iteration name. "..", "~", "^", ":", "?",' +
              ' "*", "[", "@", "\", spaces and ASCII control characters' +
              ' are not allowed. Input something like "iter_1" or "start"')
        return False
    develop_name = get_develop(iteration_name)
    staging_name = get_staging(iteration_name)
    if tag.exists(iteration_name):
        print('Cannot start iteration, tag ' + iteration_name + ' exists')
        return False
    if branch.exists(develop_name):
        print('Cannot start iteration, branch + ' + develop_name + ' exists')
        return False
    if branch.exists(staging_name):
        print('Cannot start iteration, branch + ' + staging_name + ' exists')
        return False
    if not (tag.create(iteration_name, MASTER_NAME) and
            branch.create(develop_name, MASTER_NAME) and
            branch.create(staging_name, MASTER_NAME)):
        tag.delete(iteration_name)
        branch.delete(staging_name)
        branch.delete(develop_name)
        logging.critical('Failed to create iteration ' + iteration_name)
        return False
    print('Iteration ' + iteration_name + ' created successfully')
    get_iteration_by_sha.cache_clear()
    return True


def is_iteration(name):
    """Checks whether there is a base point with given name"""
    if name is None:
        return False
    result = (tag.exists(name) and
              branch.exists(get_develop(name)) and
              branch.exists(get_staging(name)))
    logging.debug('Check: iteration ' + name +
                  (' exists' if result else " doesn't exists"))
    return result


def get_iteration_list():
    return [t for t in tag.get_list() if is_iteration(t)]


@lru_cache()
def get_iteration_by_sha(sha):
    iterations = {tag.get_sha(t): t for t in get_iteration_list()}
    position = sha
    while position:
        if position in iterations:
            logging.info('found latest iteration ' + iterations[position] +
                         ' for SHA ' + sha + ' BP: ' + position)
            return iterations[position]
        position = commit.get_parent(position, 1)
    logging.warning('Cannot get iteration for ' + sha)
    return None
atexit.register(lambda: logging.debug('get_iteration_by_SHA cache info:' +
                                      str(get_iteration_by_sha.cache_info())))


def get_iteration_by_branch(branch_name):
    iteration = parse_branch_name(branch_name)[0]
    if is_iteration(iteration):
        logging.info('found iteration ' + iteration + ' for branch ' +
                     branch_name)
        return iteration
    if branch.exists(branch_name):
        return get_iteration_by_sha(branch.get_head_sha(branch_name))
    logging.warning('Failed to get iteration for branch ' + branch_name)
    return None


def get_iteration_by_treeish(treeish):
    if branch.exists(treeish):
        iter_ = parse_branch_name(treeish)[0]
    else:
        iter_ = None
    return iter_ if iter_ else get_iteration_by_sha(misc.rev_parse(treeish))


def get_current_iteration():
    """Calculates current iteration.
    We cannot store iteration in something like "current_iteration" tag, cause
    user may switch branches without git-aflow.
    """
    current_branch = branch.get_current()
    if current_branch:
        return get_iteration_by_branch(current_branch)
    return get_iteration_by_sha(commit.get_current_sha())


def get_develop(iteration=None):
    return ((iteration if iteration else get_current_iteration()) +
            '/' + DEVELOP_NAME)


def get_staging(iteration=None):
    return ((iteration if iteration else get_current_iteration()) +
            '/' + STAGING_NAME)


def is_staging(branch_name):
    iteration, name = parse_branch_name(branch_name)
    return is_iteration(iteration) and name == STAGING_NAME


def is_develop(branch_name):
    iteration, name = parse_branch_name(branch_name)
    return is_iteration(iteration) and name == DEVELOP_NAME


def is_master(branch_name):
    iteration, name = parse_branch_name(branch_name)
    return branch_name == MASTER_NAME and iteration is None


def is_release(branch_name):
    iteration, name = parse_branch_name(branch_name)
    return is_iteration(iteration) and name.startswith(RELEASE_NAME + '/')