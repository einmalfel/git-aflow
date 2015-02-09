"""Iteration management functionality"""

import logging
import re

from gitaflow.constants import DEVELOP_NAME, MASTER_NAME, STAGING_NAME, \
    RELEASE_NAME
from gitwrapper.cached import tag, branch, misc, commit
from gitwrapper.grouped_cache import cache


class WrongIterationNameError(Exception):
    """ Raised when wrong iteration name is given"""


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
def get_iterations(sort=False):
    iteration_generator = (t for t in tag.get_list() if is_iteration(t))
    if sort:
        return misc.sort(iteration_generator)
    else:
        return tuple(iteration_generator)


def get_first_iteration():
    return get_iterations(sort=True)[-1]


@cache('branches', 'tags')
def get_iteration_by_sha(sha):
    iterations = {tag.get_sha(t): t for t in get_iterations()}
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


def get_master_head(iteration):
    """ Returns last master commit for given iteration. For last iteration,
    returns 'master'.
    """
    next_ = None
    for i in get_iterations(sort=True):
        if i == iteration:
            break
        next_ = i
    return misc.rev_parse(next_) if next_ else 'master'


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


def __get_next_in(iteration, i_list):
    next_ = None
    for i in i_list:
        if i == iteration:
            return next_
        next_ = i
    else:
        raise WrongIterationNameError(str(iteration) + ' not in ' + str(i_list))


def get_next(iteration):
    return __get_next_in(iteration, get_iterations(True))


def get_previous(iteration):
    return __get_next_in(iteration, reversed(get_iterations(True)))
