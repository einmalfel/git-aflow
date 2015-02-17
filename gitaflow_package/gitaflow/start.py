import logging

from gitaflow import iteration
from gitaflow.common import die, say, check_iteration, \
    check_working_tree_clean, check_untracked_not_differ, check_topic_name_valid
from gitaflow.topic import Topic
from thingitwrapper.cached import misc, branch


def start(name):
    ci = check_iteration()
    topic = Topic(name)
    branch_name = ci + '/' + name

    check_topic_name_valid(branch_name)
    check_working_tree_clean()
    check_untracked_not_differ(ci)

    logging.info('Check if there is branch for this topic already')
    branches = topic.get_branches()
    for b in branches:
        if iteration.get_iteration_by_treeish(b) == ci:
            die('Cannot start topic, it already has a branch(' + b +
                ') in current iteration(' + ci + ').')

    logging.info('Ok, now check if there was such topic somewhere in history')
    shas = tuple(str(m.SHA) for m in topic.get_all_merges())
    if shas:
        die('Cannot start topic, it already exists in history, see SHA: ' +
            ', '.join(shas))

    logging.info('All good, creating branch ' + branch_name)
    try:
        branch.create(branch_name, ci)
    except:
        logging.critical('Something went wrong, cannot create topic branch')
        raise
    try:
        misc.checkout(branch_name)
    except:
        branch.delete(branch_name)
        raise
    say('Topic ' + name + ' created. You are in ' + branch_name + ' branch')
    return True
