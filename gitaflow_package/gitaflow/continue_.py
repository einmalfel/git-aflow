import logging
from os import linesep

from gitaflow import iteration
from gitaflow.common import die, say
from gitaflow.topic import TopicRevision, TopicMerge
from gitwrapper.cached import commit, branch, misc


def continue_(name=None):
    head = commit.get_current_sha()

    logging.info('Looking for revision to continue..')
    last_r_cd = None
    if name:
        nr = TopicRevision.from_branch_name(name)  # revision for name parsing
        ci = nr.iteration if nr.iteration else iteration.get_current_iteration()
        if not ci:
            die('Could not continue topic outside of iteration.')
        if not nr.default_version:
            say('Version suffix ignored.')
        cd_all_merges = TopicMerge.get_all_merges_in(iteration.get_develop(ci))
        last_m = nr.topic.get_latest_merge(cd_all_merges, True)
        if last_m:
            last_r_cd = last_m.rev
        else:
            iters = iteration.get_iteration_list()
            p_iters = misc.sort([i for i in iters if commit.is_ancestor(i, ci)])
            if not p_iters:
                die('No topic ' + str(nr.topic) + ' in the only iteration ' +
                    ci + '.')
            # there is nothing before first iteration
            for i in p_iters[:-1]:
                last_m = nr.topic.get_latest_merge(
                    TopicMerge.get_effective_merges_in(i + '^'))
                if last_m:
                    logging.info('Found effective merge in master before ' + i +
                                 ': ' + str(last_m))
                    last_r_cd = TopicRevision(nr.topic, ci,
                                              last_m.rev.version + 1, ci)
                    break
            else:
                die('Failed to find merges of ' + str(nr.topic) +
                    ' in iterations: ' + ', '.join([ci] + p_iters) + '.')

    else:
        ci = iteration.get_current_iteration()
        if not ci:
            die('Could not continue topic outside of iteration.')
        for m in TopicMerge.get_all_merges_in(iteration.get_develop(ci)):
            if m.rev.SHA == head:
                last_r_cd = m.rev
                break
        else:
            die('No topic name was specified, neither HEAD is pointing to '
                'last commit of some topic. Nothing to continue.')

    logging.info('Last revision: ' + str(last_r_cd) + '. Checking branch '
                 'not exists and working tree is clean')

    new_r = TopicRevision(last_r_cd.topic, None, last_r_cd.version + 1, ci)
    tb_name = new_r.get_branch_name()
    if branch.exists(tb_name):
        die(tb_name + ' already exists. Use "git af checkout ' + tb_name +
            '" to continue your work on topic')
    if not head == last_r_cd.SHA:
        logging.info('Check working tree')
        if not misc.is_working_tree_clean():
            die('You are going to create and checkout ' + tb_name + ' but your '
                'working tree is dirty. Please, stash or reset your changes.')
        intersection = (frozenset(misc.get_untracked_files()) &
                        frozenset(misc.list_files_differ(head, last_r_cd.SHA)))
        if intersection:
            die('You have some untracked files which you may loose when '
                'switching to new topic branch. Please, delete or commit them. '
                'Here they are: ' + ', '.join(intersection) + '.' + linesep +
                'Use "git clean" to remove all untracked files')
    last_v_ever = last_r_cd.topic.get_latest_merge(
        last_r_cd.topic.get_all_merges()).rev.version
    if last_v_ever >= new_r.version:
        say('Please, note that ' + tb_name +
            ' is already present in other iteration(s), so changes you will '
            'make for this revision in current iteration should correspond to '
            'changes made for same revision in other iterations. You may '
            'also use "git af port" to bring commits of some revision from '
            'one iteration to another.')

    logging.info('All good, creating and checking out branch')

    branch.create(tb_name, last_r_cd.SHA)
    try:
        misc.checkout(tb_name)
    except:
        logging.error('Failed to checkout newly created branch, deleting..')
        branch.delete(tb_name)
        raise

    say(tb_name + ' created and checked out. Use "git af topic finish" to '
        'merge new revision of topic into develop')
