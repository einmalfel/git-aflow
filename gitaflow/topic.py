"""Topic management functionality"""


import logging
import re

from gitwrapper import misc, branch, commit

from . import iteration
from .constants import DEVELOP_NAME, MASTER_NAME, STAGING_NAME


def parse_merge_commit_headline(headline):
    """Returns (merged_branch, merged_into) tuple
    E.g.: "Merge branch 'a/b_v2' into a/develop" produces
    ('a/b_v2', 'a/develop')
    If cannot parse, return None
    """
    if parse_merge_commit_headline.regexp == None:
        parse_merge_commit_headline.regexp =\
            re.compile("^Merge branch '([^/]*/.*)' into ([^/]*/.*)$")
    result = parse_merge_commit_headline.regexp.search(headline)
    return None if not result else result.groups()
parse_merge_commit_headline.regexp = None


def parse_topic_branch_name(name):
    """Returns (iteration, name, version) tuple or None if cannot parse
    E.g.: iter/name_v produces ("iter", "name_v", 1), cause first version
    of topic doesn't have any suffix and suffix ends with number
    """
    if parse_topic_branch_name.regexp == None:
        parse_topic_branch_name.regexp =\
            re.compile('^([^/]*)/(.*?)(?:_v(\d+))?$')
    result = parse_topic_branch_name.regexp.search(name)
    if not result:
        return None
    groups = result.groups()
    return (groups[0], groups[1], 1 if groups[2] == None else int(groups[2]))
parse_topic_branch_name.regexp = None


def is_valid_topic_branch(branch_name, topic_name=None):
    """If no topic name passed, checks if topic branch name is valid (iteration
    exists and branch name has correct format)
    Otherwise, also checks if it is valid branch name for given topic
    """
    if not misc.is_valid_ref_name(branch_name):
        return False
    result = parse_topic_branch_name(branch_name)
    logging.debug('Branch name parsed ' + str(result))
    if not result:
        return False
    else:
        if not iteration.is_iteration(result[0]):
            return False
        if not topic_name:
            return True
        else:
            return result[1] == topic_name


def topic_branches(name):
    """Returns topic branch names list for all versions of given topic.
    Name should be given without iteration prefix and version suffix
    """
    topics = branch.get_branch_list(['*' + name + '*'])
    return [topic for topic in topics if is_valid_topic_branch(topic, name)]


def topic_merges_in_history(name):
    """Returns list of merge commits SHA, in which any version of topic was
    merged into master, develop and staging
    Name should be given without iteration prefix and version suffix
    """
    iters = iteration.get_iteration_list()
    heads = ['master']
    heads += [iteration.get_develop(i) for i in iters]
    heads += [iteration.get_staging(i) for i in iters]
    logging.info('Searching ' + name + ' in branches ' + str(heads))
    SHAs = commit.find_commits(heads, True,
                ["^Merge branch '[^/]*/" + name + ".*' into .*$"])
    logging.debug('Found: ' + str(SHAs))
    result = []
    for SHA in SHAs:
        branch, merged_to = parse_merge_commit_headline(
                                commit.get_commit_headline(SHA))
        if is_valid_topic_branch(branch, name):
            if merged_to == MASTER_NAME:
                result += [SHA]
            else:
                mt_iteration, mt_branch = merged_to.split('/', 1)
                if iteration.is_iteration(mt_iteration) and\
                    (mt_branch == DEVELOP_NAME or mt_branch == STAGING_NAME):
                    result += [SHA]
    logging.debug('After checks: ' + str(result))
    return result


def start(name):
    ci = iteration.get_current_iteration()
    branch_name = ci + '/' + name
    logging.info('Checking name ' + branch_name)
    if not is_valid_topic_branch(branch_name):
        print('Please correct topic name. ".."'
', "~", "^", ":", "?", "*", "[", "@", "\", spaces and ASCII control characters'
' are not allowed. Input something like "fix_issue18" or "do_api_refactoring"')
        logging.info('Wrong topic name. Stopping')
        return False
    logging.info('Check working tree')
    if not misc.is_working_tree_clean():
        print('Your working tree is dirty. Please, stash or reset your \
changes before starting topic')
        logging.info('Working tree is dirty stopping, stopping')
        return False
    intersection = frozenset(misc.get_untracked_files()) &\
        frozenset(misc.list_files_differ('HEAD', ci))
    if intersection:
        print('You have some untracked files which you may loose when \
switching to new topic branch. Please, delete or commit them. \
Here they are: ' + ', '.join(intersection))
        logging.info('User may lose untracked file, stopping')
        return False

    logging.info('Check if there is branch for this topic already')
    branches = topic_branches(name)
    if branches:
        print('Cannot start topic, there are already branches: ' +
              str(branches))
        logging.info('Topic branches with given name exists, stopping')
        return False

    logging.info('Ok, now check if there was such topic somewhere in history')
    SHAs = topic_merges_in_history(name)
    if SHAs:
        print('Cannot start topic, it already exists in history, see SHA: ' +
              ', '.join(SHAs))
        logging.info('Topics with given name exist in history, stopping')
        return False

    logging.info('All good, creating branch ' + branch_name)
    if misc.checkout(branch_name, True):
        print('Topic ' + name + ' created. You are in ' + branch_name +
              ' branch')
        return True
    else:
        logging.critical("Something went wrong, cannot create & checkout \
topic branch")
        return False
