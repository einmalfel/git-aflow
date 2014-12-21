"""Iteration management functionality"""

import logging
import re

from gitaflow.common import die, say
from gitaflow.constants import DEVELOP_NAME, MASTER_NAME, STAGING_NAME, \
    RELEASE_NAME
from gitwrapper.cached import tag, branch, misc, commit
from gitwrapper.grouped_cache import cache


def parse_branch_name(branch_name):
    """Returns (iteration, name) tuple or (None, None) if cannot parse.
    E.g.: parse_branch_name("master") produces (None, "master")
    parse_branch_name("iter1/topic_v2") produces ("iter1", "topic_v2")
    """
    if branch_name == MASTER_NAME:
        return None, MASTER_NAME
    if parse_branch_name.regexp is None:
        parse_branch_name.regexp = re.compile('^([^/]*)/(.*)$')
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
            die('There is already an iteration ' + tag_ +
                ' started from the top of master branch')
    if not is_valid_iteration_name(iteration_name):
        die('Please, correct your iteration name. "..", "~", "^", ":", "?",' +
            ' "*", "[", "@", "\", spaces and ASCII control characters' +
            ' are not allowed. Input something like "iter_1" or "start"')
    develop_name = get_develop(iteration_name)
    staging_name = get_staging(iteration_name)
    if tag.exists(iteration_name):
        die('Cannot start iteration, tag ' + iteration_name + ' exists')
    if branch.exists(develop_name):
        die('Cannot start iteration, branch + ' + develop_name + ' exists')
    if branch.exists(staging_name):
        die('Cannot start iteration, branch + ' + staging_name + ' exists')
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


@cache('tags', 'branches')
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


@cache('tags', 'branches')
def get_iteration_list(sort=False):
    iteration_generator = (t for t in tag.get_list() if is_iteration(t))
    if sort:
        return misc.sort(iteration_generator)
    else:
        return tuple(iteration_generator)


def get_first_iteration():
    return get_iteration_list(sort=True)[-1]


@cache('branches', 'tags')
def get_iteration_by_sha(sha):
    iterations = {tag.get_sha(t): t for t in get_iteration_list()}
    position = commit.get_parent(sha, 1)
    while position:
        if position in iterations:
            logging.debug('found latest iteration ' + iterations[position] +
                          ' for SHA ' + sha + ' BP: ' + position)
            return iterations[position]
        position = commit.get_parent(position, 1)
    logging.info('Cannot get iteration for ' + sha)
    return None


@cache('branches', 'tags')
def get_iteration_by_branch(branch_name):
    assert branch.exists(branch_name)
    # try to extract iteration from name
    iteration = parse_branch_name(branch_name)[0]
    if is_iteration(iteration):
        logging.debug('found iteration ' + iteration + ' for branch ' +
                      branch_name)
        return iteration
    else:
        # check whether branch was started from BP
        branching_point = misc.get_merge_base(['master', branch_name])
        for t in tag.find_by_target(branching_point):
            if is_iteration(t):
                return t
        # look for BP nearest to point where branch was created
        return get_iteration_by_sha(branching_point)


@cache('branches', 'tags')
def get_iteration_by_treeish(treeish):
    if branch.exists(treeish):
        return get_iteration_by_branch(treeish)
    else:
        return get_iteration_by_sha(treeish)


@cache('branches', 'tags')
def get_current_iteration():
    for t in tag.find_by_target('HEAD'):
        if is_iteration(t):
            return t
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
