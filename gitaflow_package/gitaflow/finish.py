import logging
from os import linesep

import conflicts
from gitaflow import iteration
from gitaflow.common import die, say
from gitaflow.constants import RELEASE_NAME, DEVELOP_NAME, MASTER_NAME, \
    STAGING_NAME
from gitaflow.topic import Topic, TopicRevision, TopicMerge, \
    consistency_check_ok, MergeNonConflictError
from gitwrapper import misc, branch, commit


def finish(description, type_, name):
    ci = iteration.get_current_iteration()
    if ci is None:
        die('Could not get current iteration, we are probably not in ' +
            'git-aflow repo')
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
    cr = TopicRevision.from_branch_name(name)
    cr.SHA = tb_head
    if cr.iteration:
        if not cr.iteration == ci:
            die('It is not possible to finish in current iteration topic from '
                'other one. Finish failed.')
    else:
        cr.iteration = ci
    last_m = cr.topic.get_latest_merge(cr.topic.get_all_merges())
    if last_m:
        if last_m.rev.version < cr.version - 1:
            die('Wrong topic version specified. Latest revision has version ' +
                '== ' + str(last_m.version) + '. Increment version by 1')
    elif not cr.version == 1:
        say('Correcting topic version from ' + str(cr.version) + ' to 1')
        cr.version = 1
        cr.default_version = False
    # If no version specified and this topic was ever merged in ci, try to
    # select appropriate version.
    if cr.default_version:
        if all_m_cd:
            for m in all_m_cd:
                if m.rev.topic == cr.topic and m.rev.SHA == cr.SHA:
                    cr.version = m.rev.version
                    cr.default_version = False
                    say('Using version ' + str(cr.version) +
                        ' of already merged revision with same head SHA.')
                    break
            else:
                last_m_cd = cr.topic.get_latest_merge(all_m_cd)
                if last_m_cd and commit.is_based_on(last_m_cd.rev.SHA, cr.SHA):
                    cr.version = last_m_cd.rev.version + 1
                    cr.default_version = False
                    say('Using topic version ' + str(cr.version) +
                        ' as default.')
    if not Topic.is_valid_tb_name(cr.get_branch_name()):
        die('Please correct topic name. "..", "~", "^", ":", "?", "*", ' +
            '"[", "@", "\", spaces and ASCII control characters' +
            ' are not allowed. */' + RELEASE_NAME + '/*, ' +
            '*/' + DEVELOP_NAME + ', */' + STAGING_NAME + ' and ' +
            MASTER_NAME + ' are not ' + 'allowed too. Input something '
            'like "fix_issue18" or "do_api_refactoring"')

    logging.info('Consider topic name ' + cr.get_branch_name() + ' as valid, ' +
                 'now checking working tree state..')

    # we will checkout develop to make a merge, so prevent lost of modified
    # and untracked files
    if not misc.is_working_tree_clean():
        die('Your working tree is dirty. Please, stash or reset your ' +
            'changes before finishing topic.')
    intersection = (frozenset(misc.get_untracked_files()) &
                    frozenset(misc.list_files_differ(cd, ci)))
    if intersection:
        die('You have some untracked files which you may loose while ' +
            'finishing topic branch. Please, delete or commit them. ' +
            'Here they are: ' + ', '.join(intersection) + '.' + linesep +
            'Use "git clean" to remove all untracked files')

    logging.info('Working tree is OK, checking if revision was already '
                 'in develop...')

    eff_m_cd = TopicMerge.get_effective_merges_in(cd)
    last_eff_m_cd = cr.topic.get_latest_merge(eff_m_cd)
    if (last_eff_m_cd and (cr.SHA == last_eff_m_cd.rev.SHA or
                           commit.is_based_on(cr.SHA, last_eff_m_cd.rev.SHA))):
        die(cd + ' already contains this revision of ' + cr.topic.name)

    logging.info('Checking topic base...')

    # Topic should be based on ci
    # And should not be based on any later iteration
    if not commit.is_based_on(ci, cr.SHA):
        die('Finish failed. Current topic branch is not based on iteration '
            'start which is not allowed in git-aflow')
    for iter_ in misc.sort(iteration.get_iteration_list()):
        if ci == iter_:
            break
        else:
            if commit.is_based_on(iter_, cr.SHA):
                die('Current topic branch is based on ' + iter_ +
                    'Use "git af topic port" to bring it to current iteration' +
                    '. And then call "git af topic finish"')

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
                        'your work on ' + str(merge.rev))
                elif (merge.rev.version > cr.version and
                        not commit.is_based_on(cr.SHA, merge.rev.SHA)):
                    die('Cannot finish. Newer revision (' + str(merge.rev) +
                        ') of this topic was merged into ' + cd + ' and it is '
                        'not based on revision you are trying to finish.')
                elif merge.rev == cr and not merge.rev.SHA == cr.SHA:
                    die('This revision was already merged(' + str(merge) +
                        ') in ' + cd + ' with different head SHA. Finish '
                        'failed.')
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
                 'finish revision ' + str(cr) + '. Checking dependencies...')

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
            die('Merge of ' + str(cr) + ' conflicted unexpectedly. '
                'Conflict detector gave false negative result. ' +
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
