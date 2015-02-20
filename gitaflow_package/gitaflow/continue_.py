import logging

from gitaflow.common import die, say, check_iteration, \
    check_working_tree_clean, check_untracked_not_differ
from gitaflow.constants import MASTER_NAME
from gitaflow.topic import TopicRevision, TopicMerge, get_merges_and_reverts
from thingitwrapper.cached import commit, branch, misc


def continue_(name=None, unfinish=False):
    head = commit.get_current_sha()

    logging.info('Looking for revision to continue..')
    last_m = None
    if name:
        nr = TopicRevision.from_branch_name(name)  # revision for name parsing
        ci = nr.iteration if nr.iteration else check_iteration()
        if not nr.default_version:
            say('Version suffix ignored.')
        cd = ci.get_develop()
        cd_all_merges = TopicMerge.get_all_merges_in(cd)
        last_m = nr.topic.get_latest_merge(cd_all_merges, True)
        if not last_m:
            prev = ci.prev()
            while prev:
                last_m = nr.topic.get_latest_merge(
                    TopicMerge.get_effective_merges_in(prev.get_master_head()))
                if last_m:
                    logging.info('Found effective merge in master before ' +
                                 prev.name + ': ' + str(last_m))
                    break
                prev = prev.prev()
            if not last_m:
                die('Failed to find merges of', str(nr.topic),
                    'in', ci.name, 'and previous iterations.')
    else:
        ci = check_iteration()
        cd = ci.get_develop()
        for m in TopicMerge.get_all_merges_in(cd):
            if m.rev.SHA == head:
                last_m = m
                break
        else:
            die('No topic name was specified, neither HEAD is pointing to '
                'last commit of some topic. Nothing to continue.')

    logging.info('Last revision: ' + str(last_m.rev) + '. Checking branch '
                 'not exists and working tree is clean')

    last_m = last_m.get_original()
    if unfinish:
        new_r = last_m.rev
    else:
        # Let new_r.SHA contain SHA to start TB from. It's either RB or head of
        # previous revision
        if commit.is_ancestor(last_m.rev.SHA, ci.name):
            sha = misc.rev_parse(ci.name)
        else:
            sha = last_m.rev.SHA
        new_r = TopicRevision(last_m.rev.topic, sha, last_m.rev.version + 1, ci)
    tb_name = new_r.get_branch_name()
    if branch.exists(tb_name):
        die(tb_name + ' already exists. Use "git af checkout',
            tb_name + '" to continue your work on topic')
    if not head == new_r.SHA:
        logging.info('Check working tree')
        check_working_tree_clean()
        check_untracked_not_differ(new_r.SHA)
    last_v_ever = new_r.topic.get_latest_merge(
        new_r.topic.get_all_merges()).rev.version
    if last_v_ever > new_r.version or (last_v_ever == new_r.version and
                                       not unfinish):
        say('Please, note that', new_r.topic.name + '_v' + str(new_r.version),
            'is already present in other iteration(s), so changes you will '
            'make for this revision in current iteration should correspond to '
            'changes made for same revision in other iterations. You may '
            'also use "git af port" to bring commits of some revision from '
            'one iteration to another.')

    if unfinish:
        logging.info('Checking if ' + new_r.get_branch_name() +
                     ' is merged somewhere and rebuilding develop.')
        for b in MASTER_NAME, ci.get_staging():
            if commit.is_ancestor(new_r.SHA, b):
                die(new_r.get_branch_name(), 'was previously merged in',
                    b + ", so it's impossible to unfinish it.")
        fallback = misc.rev_parse(cd)
        check_working_tree_clean()
        check_untracked_not_differ(cd)
        misc.checkout(cd)
        # last_r_cd was never merged in master, so it isn't continuation of
        # revision from previous iteration
        try:
            branch.reset(commit.get_parent(last_m.SHA, 1))
            for o in get_merges_and_reverts(last_m.SHA, fallback, reduce=True):
                if o.rev == new_r:
                    continue
                logging.info('Applying ' + str(o))
                if isinstance(o, TopicMerge):
                    if commit.is_ancestor(new_r.SHA, o.get_original().rev.SHA):
                        branch.reset(fallback)
                        die('Failed to continue',
                            new_r.get_branch_name() + '. It is merged in',
                            o.rev.get_branch_name(),
                            'which was later merged in', cd + '.', cd,
                            'reset back to', fallback + '.')
                    # original merge could be reduced, we need it's rev.SHA
                    # take description/type from the last non reverted merge
                    if not o.get_original().merge(o.description, o.type):
                        branch.reset(fallback)
                        die('Failed to merge (unexpected conflict)',
                            o.rev.get_branch_name() + '.', cd, 'reset back to',
                            fallback + '.')
                else:
                    if not o.revert():
                        branch.reset(fallback)
                        die('Failed to revert (unexpected conflict)',
                            o.rev.get_branch_name() + '.', cd, 'reset back to',
                            fallback + '.')
        except Exception:
            logging.error('Something went wrong while rebuilding develop, '
                          'restoring its state')
            branch.reset(fallback)
            raise

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
