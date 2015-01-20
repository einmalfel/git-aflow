"""Some common code for other modules of package"""

import logging
import itertools

from gitaflow import iteration
from gitaflow.constants import STAGING_NAME, MASTER_NAME, DEVELOP_NAME, \
    RELEASE_NAME
from gitaflow.debug import TestDebugState
from gitwrapper.cached import misc, branch, commit, tag
from gitaflow.topic import TopicMerge, Topic


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


def consistency_check(list_of_treeish):
    """Checks revisions merged in all given treeish:
    - same revisions have same head SHAs
    - newer revisions based on elder ones
    """
    # sort non-fake merges by topic
    merges = {}
    for treeish in list_of_treeish:
        for m in TopicMerge.get_all_merges_in(treeish):
            if not m.is_fake():
                m.origin = treeish
                if m.rev.topic not in merges.keys():
                    merges[m.rev.topic] = [m]
                else:
                    merges[m.rev.topic].append(m)

    # do checks
    result = True
    for topic in merges.keys():
        for m1, m2 in itertools.combinations(merges[topic], 2):
            if m1.rev.version == m2.rev.version:
                if not m1.rev.SHA == m2.rev.SHA:
                    say(m1.rev.get_branch_name() + ' was merged into ' +
                        m1.origin + '(merge SHA: ' + m1.SHA + ') and into ' +
                        m2.origin + '(merge SHA: ' + m2.SHA + ') with '
                        'different head SHA (' + m1.rev.SHA + ' and ' +
                        m2.rev.SHA + ').')
                    result = False
            else:
                if m1.rev.version > m2.rev.version:
                    m1, m2 = m2, m1
                # assuming m2 is the newer revision as we got here
                if not commit.is_based_on(m1.rev.SHA, m2.rev.SHA):
                    say(m2.rev.get_branch_name() + ' merged into ' + m2.origin +
                        '(merge SHA: ' + m2.SHA + ') is newer version of ' +
                        m1.rev.get_branch_name() + ' merged into ' + m1.origin +
                        '(merge SHA: ' + m1.SHA + '), but newer one is not ' +
                        'based on elder.')
                    result = False

    if not result:
        die('Please, fix aforementioned problems and rerun git-aflow again.')


def check_iteration():
    ci = iteration.get_current_iteration()
    if ci is None:
        die('Error: could not get current iteration, we are probably not in ' +
            'git-aflow repo.')
    return ci


def check_working_tree_clean():
    if not misc.is_working_tree_clean():
        die('Error: your working tree is dirty. Please, stash or reset your ' +
            'changes before proceeding.')


def check_untracked_not_differ(treeish):
    intersection = (frozenset(misc.get_untracked_files()) &
                    frozenset(misc.list_files_differ('HEAD', treeish)))
    if intersection:
        die('Error: you have some untracked files which you may loose when ' +
            'switching to ' + treeish + '. Please, delete or commit them. ' +
            'Here they are: ' + ', '.join(intersection) + '.')


def default_sources():
    cb = branch.get_current()
    assert cb
    if iteration.is_master(cb):
        sources = [STAGING_NAME]
    elif iteration.is_release(cb):
        sources = [MASTER_NAME, STAGING_NAME]
    else:
        sources = [DEVELOP_NAME]
    say('Using default topic source(s): ' + ', '.join(sources))
    return sources


def check_topic_name_valid(name):
    if not Topic.is_valid_tb_name(name):
        die('Error: invalid topic name ' + name +
            '. "..", "~", "^", ":", "?", "*", ' +
            '"[", "@", "\", spaces and ASCII control characters' +
            ' are not allowed. */' + RELEASE_NAME + '/*, ' +
            '*/' + DEVELOP_NAME + ', */' + STAGING_NAME + ' and ' +
            MASTER_NAME + ' are not ' + 'allowed too. Input something '
            'like "fix_issue18" or "do_api_refactoring"')


def complete_sources(sources, iteration_):
    result = []
    for s in sources:
        iter_s = iteration_ + '/' + s
        if branch.exists(iter_s):
            result.append(iter_s)
        elif branch.exists(s):
            result.append(s)
        else:
            die('Cannot find branch ' + iter_s + ' or ' + s + '.')
    return result
