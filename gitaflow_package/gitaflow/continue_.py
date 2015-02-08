import logging

from gitaflow import iteration
from gitaflow.common import die, say, check_iteration, \
    check_working_tree_clean, check_untracked_not_differ
from gitaflow.topic import TopicRevision, TopicMerge
from gitwrapper.cached import commit, branch, misc


def continue_(name=None):
    head = commit.get_current_sha()

    logging.info('Looking for revision to continue..')
    last_m = None
    if name:
        nr = TopicRevision.from_branch_name(name)  # revision for name parsing
        ci = nr.iteration if nr.iteration else check_iteration()
        if not nr.default_version:
            say('Version suffix ignored.')
        cd_all_merges = TopicMerge.get_all_merges_in(iteration.get_develop(ci))
        last_m = nr.topic.get_latest_merge(cd_all_merges, True)
        if not last_m:
            p_iters = tuple(i for i in iteration.get_iterations(sort=True)
                            if commit.is_ancestor(i, ci))
            # there is nothing before first iteration
            if p_iters:
                for i in (ci,) + p_iters[:-1]:
                    last_m = nr.topic.get_latest_merge(
                        TopicMerge.get_effective_merges_in(i))
                    if last_m:
                        logging.info('Found effective merge in master before ' +
                                     i + ': ' + str(last_m))
                        break
            if not last_m:
                die('Failed to find merges of ' + str(nr.topic) +
                    ' in iterations: ' + ', '.join((ci,) + p_iters) + '.')
    else:
        ci = check_iteration()
        for m in TopicMerge.get_all_merges_in(iteration.get_develop(ci)):
            if m.rev.SHA == head:
                last_m = m
                break
        else:
            die('No topic name was specified, neither HEAD is pointing to '
                'last commit of some topic. Nothing to continue.')

    logging.info('Last revision: ' + str(last_m.rev) + '. Checking branch '
                 'not exists and working tree is clean')

    # Let new_r.SHA contain SHA to start TB from. It's either RB or head of
    # previous revision
    new_r = TopicRevision(
        last_m.rev.topic,
        ci if commit.is_ancestor(last_m.rev.SHA, ci) else last_m.rev.SHA,
        last_m.rev.version + 1, ci)
    tb_name = new_r.get_branch_name()
    if branch.exists(tb_name):
        die(tb_name + ' already exists. Use "git af checkout ' + tb_name +
            '" to continue your work on topic')
    if not head == new_r.SHA:
        logging.info('Check working tree')
        check_working_tree_clean()
        check_untracked_not_differ(new_r.SHA)
    last_v_ever = new_r.topic.get_latest_merge(
        new_r.topic.get_all_merges()).rev.version
    if last_v_ever >= new_r.version:
        say('Please, note that ' +
            new_r.topic.name + '_v' + str(new_r.version) +
            ' is already present in other iteration(s), so changes you will '
            'make for this revision in current iteration should correspond to '
            'changes made for same revision in other iterations. You may '
            'also use "git af port" to bring commits of some revision from '
            'one iteration to another.')

    logging.info('All good, creating and checking out branch')

    branch.create(tb_name, new_r.SHA)
    try:
        misc.checkout(tb_name)
    except:
        logging.error('Failed to checkout newly created branch, deleting..')
        branch.delete(tb_name)
        raise

    say(tb_name + ' created and checked out. Use "git af topic finish" to '
        'merge new revision of topic into develop')
