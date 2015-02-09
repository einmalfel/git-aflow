""" git af checkout implementation"""
import logging

from gitaflow import iteration
from gitaflow.common import say, die, check_iteration, \
    check_working_tree_clean, check_untracked_not_differ
from gitaflow.constants import STAGING_NAME, DEVELOP_NAME
from gitaflow.topic import TopicRevision, TopicMerge
from gitwrapper.cached import branch, misc


def _checkout(ci, treeish):
    check_untracked_not_differ(treeish)
    misc.checkout(treeish)
    new_ci = check_iteration()
    if not new_ci == ci:
        say('Iteration switched from ' + ci + ' to ' + new_ci)
    cb = branch.get_current()
    if cb:
        say(cb + ' checked out.')
    else:
        say(treeish + ' checked out. You are in "detached HEAD" state now.')


def checkout(name):
    check_working_tree_clean()

    # 1 named branch exists (includes master, iter/develop, etc)
    ci = check_iteration()
    if branch.exists(name):
        logging.info('Found branch ' + name)
        return _checkout(ci, name)

    # 2 "develop" or "staging" given
    ci_name = ci + '/' + name
    if name in (STAGING_NAME, DEVELOP_NAME) and branch.exists(ci_name):
        logging.info('Found branch ' + ci_name)
        return _checkout(ci, ci_name)

    # 3 if version specified look for branch of this rev in ci
    # 4 if not, look for latest branch of this topic in ci
    rev = TopicRevision.from_branch_name(name, default_iteration=ci)
    logging.info('Searching for branch of revision ' + str(rev))
    branches = rev.topic.get_branches()
    last_v, last_name = 0, None
    for b in branches:
        b_rev = TopicRevision.from_branch_name(b)
        if rev.default_version:
            if b_rev.iteration == rev.iteration and b_rev.version > last_v:
                logging.info('Latest branch so far: ' + b)
                last_v = b_rev.version
                last_name = b
        else:
            if not b_rev.default_version and b_rev == rev:
                logging.info('Found branch for this revision: ' + b)
                last_name = b
    if last_name:
        return _checkout(ci, last_name)

    logging.info('No branch found for ' + name +
                 ', looking for merged topics in ' +
                 iteration.get_develop(rev.iteration))

    # 5 finally, search merges of given topic
    last_m = None
    for m in TopicMerge.get_all_merges_in(iteration.get_develop(rev.iteration)):
        if m.rev.SHA and m.rev.topic == rev.topic:
            if rev.default_version:
                # not using Topic.get_latest_merge() cause need to filter by SHA
                if not last_m or last_m.rev.version < m.rev.version:
                    last_m = m
                    logging.info('Last merge found: ' + str(m))
            else:
                if m.rev == rev:
                    logging.info('Found merge of this revision: ' + str(m))
                    last_m = m
                    break
    if last_m:
        _checkout(ci, last_m.rev.SHA)
    else:
        die('Failed to found ' + name + ' in iteration ' + ci + '.')
