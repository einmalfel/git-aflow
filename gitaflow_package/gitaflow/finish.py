import logging

import conflicts
from gitaflow import iteration
from gitaflow.common import die, say, consistency_check_ok, check_iteration, \
    check_working_tree_clean, check_untracked_not_differ, check_topic_name_valid
from gitaflow.constants import RELEASE_NAME, DEVELOP_NAME, MASTER_NAME, \
    STAGING_NAME
from gitaflow.topic import TopicRevision, TopicMerge, \
    MergeNonConflictError
from gitwrapper.cached import misc, branch, commit


def finish(description, type_, name):
    ci = check_iteration()
    cd = iteration.get_develop(ci)
    cb = branch.get_current()

    if cb and (iteration.is_develop(cb) or
               iteration.is_master(cb) or
               iteration.is_release(cb) or
               iteration.is_staging(cb)):
        die('Finish failed for branch ' + cb + '. Cannot finish ' +
            DEVELOP_NAME + ', ' + MASTER_NAME + ', ' + STAGING_NAME +
            ' or ' + RELEASE_NAME + '/* branches.')

    # Set up TopicRevision describing topic being finished.
    # It is possible to do topic finish for arbitrary SHA using detached
    # head, so look for branch name only if no name was specified as argument.
    # If we are detached from any branch and no name specified in CLI,
    # search this revision in cd merges. This is necessary to allow user to
    # refinish reverted topic with "git af checkout X && git af topic finish"
    tb_head = commit.get_current_sha()
    all_m_cd = TopicMerge.get_all_merges_in(cd)
    if not name:
        if cb:
            name = cb
        else:
            for m in reversed(all_m_cd):
                if m.rev.SHA == tb_head:
                    name = m.rev.get_branch_name()
                    say('Assuming topic you are finishing is ' + name + '.')
                    break
            else:
                die('You are in detached head state now. Please check ' +
                    'out topic you want to finish, e.g. '
                    '"git af checkout topicA" or specify name '
                    '(like git af topic finish -n TopicName if you '
                    'are going to merge a commit, not branch')
    cr = TopicRevision.from_branch_name(name, sha=tb_head, default_iteration=ci)
    if cr.iteration:
        if not cr.iteration == ci:
            die('It is not possible to finish in current iteration topic from '
                'other one. Finish failed.')
    last_m = cr.topic.get_latest_merge(cr.topic.get_all_merges())
    if last_m:
        if last_m.rev.version < cr.version - 1:
            die('Wrong topic version specified. Latest revision has version ' +
                '== ' + str(last_m.rev.version) + '. Increment version by 1')
    # If no version specified and this topic was ever merged in ci, try to
    # select appropriate version.
    if cr.default_version:
        if all_m_cd:
            for m in all_m_cd:
                if m.rev.topic == cr.topic and m.rev.SHA == cr.SHA:
                    cr = TopicRevision(cr.topic, cr.SHA,
                                       m.rev.version, cr.iteration)
                    say('Using version ' + str(cr.version) +
                        ' of already merged revision with same head SHA.')
                    break
            else:
                last_m_cd = cr.topic.get_latest_merge(all_m_cd)
                if last_m_cd and commit.is_based_on(last_m_cd.rev.SHA, cr.SHA):
                    cr = TopicRevision(cr.topic, cr.SHA,
                                       last_m_cd.rev.version + 1, cr.iteration)
                    say('Using topic version ' + str(cr.version) +
                        ' as default.')
    elif cr.version > 1:
        if all_m_cd:
            last_v = cr.topic.get_latest_merge(all_m_cd)
        else:
            eff_m_master = TopicMerge.get_effective_merges_in(
                ci, treeish1=iteration.get_first_iteration())
            last_v = cr.topic.get_latest_merge(eff_m_master)
        if not last_v or cr.version > last_v.rev.version + 1:
            die('You should finish version ' + str(cr.version - 1) +
                ' before finishing ' + cr.get_branch_name())
    check_topic_name_valid(cr.get_branch_name())

    logging.info('Consider topic name ' + cr.get_branch_name() + ' as valid, ' +
                 'now checking working tree state..')

    # we will checkout develop to make a merge, so prevent lost of modified
    # and untracked files
    check_working_tree_clean()
    check_untracked_not_differ(cd)

    logging.info('Working tree is OK, checking if revision was already '
                 'in develop...')

    eff_m_cd = TopicMerge.get_effective_merges_in(cd)
    last_eff_m_cd = cr.topic.get_latest_merge(eff_m_cd)
    if (last_eff_m_cd and (cr.SHA == last_eff_m_cd.rev.SHA or
                           commit.is_based_on(cr.SHA, last_eff_m_cd.rev.SHA))):
        die(cd + ' already contains this revision of ' + cr.topic.name)

    logging.info('Checking topic base...')

    # Topic should not be empty
    if cr.SHA == misc.rev_parse(ci):
        die('Finish failed. Topic must contain at least one commit.')
    # Topic should be based on ci
    # And should not be based on any later iteration
    if not commit.is_based_on(ci, cr.SHA):
        die('Finish failed. Current topic branch is not based on iteration '
            'start which is not allowed in git-aflow')
    for iter_ in iteration.get_iterations(sort=True):
        if ci == iter_:
            break
        else:
            if (misc.rev_parse(iter_) == cr.SHA or
                    commit.is_based_on(iter_, cr.SHA)):
                die('Current topic branch is based on ' + iter_ +
                    '. Use "git af topic port" to bring it to current '
                    'iteration and then call "git af topic finish"')

    # If there are revisions of this topic in ci, later revisions are based
    # on elder.
    # If this revision was ever merged into cd, its sha is same as cr.SHA
    # We are not based on other topics
    for merge in all_m_cd:
        if not merge.is_fake():
            if merge.rev.topic == cr.topic:
                if (merge.rev.version < cr.version and
                        not commit.is_based_on(merge.rev.SHA, cr.SHA)):
                    die('Cannot finish. There is elder revision of this '
                        'topic in ' + cd + ' and SHA you are '
                        'trying to finish is not based on it. Please rebase '
                        'your work on ' + merge.rev.get_branch_name())
                elif (merge.rev.version > cr.version and
                        not commit.is_based_on(cr.SHA, merge.rev.SHA)):
                    die('Cannot finish. Newer revision ' +
                        merge.rev.get_branch_name() +
                        ' was merged into ' + cd + ' and it is '
                        'not based on revision you are trying to finish.')
                elif merge.rev == cr and not merge.rev.SHA == cr.SHA:
                    die(cr.get_branch_name() + ' was already merged in ' +
                        cd + ' with different head SHA. Finish failed.')
            elif commit.is_based_on(merge.rev.SHA, cr.SHA):
                die('TB of current topic is based on another topic, which is '
                    'illegal. You should either merge other topic instead of '
                    'basing on it or name topic you are finishing '
                    'appropriately.')
            elif commit.is_based_on(cr.SHA, merge.rev.SHA):
                die('Finish failed. There is another topic (' +
                    merge.rev.get_branch_name() + ') in ' + cd +
                    ' which is based on one you are trying to finish.')

    logging.info('Topic branch was started from correct place. About to '
                 'finish revision ' + cr.get_branch_name() +
                 '. Checking dependencies...')

    revs_cd = tuple(m.rev for m in eff_m_cd)
    for dep in cr.get_own_effective_merges(recursive=True):
        if not dep.rev.topic == cr.topic and dep.rev.is_newest_in(revs_cd):
            die('Finish failed. Your topic depends on ' +
                dep.rev.get_branch_name() + ' which is absent in ' + cd)

    logging.info('Dependencies are OK. Checking develop and cb consistency...')

    if not consistency_check_ok([cd, cb if cb else cr.SHA]):
        die('Please, fix aforementioned problems and rerun topic finish.')

    logging.info('Consistency OK. Checking if topic conflicts with '
                 'others...')

    cfl = conflicts.get_first_conflict([cr.SHA] + [r.SHA for r in revs_cd])
    if cfl:
        # getting names of conflicted branches: might be two branches from
        # develop or branch from develop and current one
        conflict_revisions = [
            r.get_branch_name() for s in cfl[:2] for r in revs_cd if r.SHA == s]
        if len(conflict_revisions) == 1:
            conflict_revisions.append(cr.get_branch_name())
        die('Finish failed because of conflicts in develop and current topic. '
            'First found conflict is between ' + conflict_revisions[0] +
            ' and ' + conflict_revisions[1] + ' in file ' + cfl[2])

    logging.info('No conflicts found, checking out develop and merging...')

    misc.checkout(cd)
    fallback_sha = commit.get_current_sha()
    try:
        if not cr.merge(description, type_):
            branch.reset(fallback_sha)
            die('Merge of ' + cr.get_branch_name() + ' conflicted '
                'unexpectedly. Conflict detector gave false negative result. ' +
                cd + ' reset.')
    except MergeNonConflictError:
        logging.critical('Unexpected merge fail. Resetting ' + cd + ' to ' +
                         fallback_sha)
        branch.reset(fallback_sha)
        raise

    say(cr.get_branch_name() + ' merged into ' + cd + ' successfully.')

    if cb:
        logging.info('Deleting TB...')
        branch.delete(cb)
        say('Branch ' + cb + ' deleted.')
