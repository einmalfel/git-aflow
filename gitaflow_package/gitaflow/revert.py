import logging

from gitaflow.common import say, die, check_iteration, check_current_branch, \
    consistency_check
from gitaflow.constants import MASTER_NAME
from gitaflow.iteration import Iteration
from gitaflow.topic import TopicMerge, TopicRevision
from thingitwrapper import commit


def find_dependent_topic_merges(merge, cb_merges):
    """ Return merges of topics that depend on merge.rev"""
    result = []
    merge_rev_sha = merge.get_original().rev.SHA
    for m in cb_merges:
        if commit.is_ancestor(merge_rev_sha, m.get_original().rev.SHA):
            result.extend(find_dependent_topic_merges(m, cb_merges))
            result.append(m)
    logging.debug('Found dependents of ' + str(merge) + ':' +
                  ', '.join(map(str, result)))
    return result


def revert(names, dependencies):
    ci = check_iteration()
    cb = check_current_branch()
    consistency_check((cb,))

    # setup topic_name:version dict and check for duplicates
    ver_by_t = {}
    for n in names:
        rev = TopicRevision.from_branch_name(n)
        if rev.topic in ver_by_t:
            die('Error: topic', str(rev.topic), 'specified more than once')
        else:
            ver_by_t[rev.topic] = 0 if rev.default_version else rev.version
    logging.info('Revisions to revert:' +
                 ', '.join(t.name + ':' + str(v) for t, v in ver_by_t.items()) +
                 '. Scanning for merges..')

    # find merges to be reverted and put them in topic_name:merge_list dict
    own_merges = TopicMerge.get_effective_merges_in(cb)
    m_by_t = {t: list() for t in ver_by_t}
    for m in own_merges:
        # if no version specified, revert all versions, otherwise revert
        # given version and newer ones
        if m.rev.topic in ver_by_t and (not ver_by_t[m.rev.topic] or
                                        ver_by_t[m.rev.topic] <= m.rev.version):
            m_by_t[m.rev.topic].append(m)
    logging.info(
        'Merges to revert by topic:' +
        '; '.join(t.name + ','.join(map(str, ms)) for t, ms in m_by_t.items()) +
        '. Checking if all given topics found..')

    # TODO: If all items of merges_to_revert_by_topic are empty lists, this is a
    # TODO: special case: revert of topic merged in master in previous iteration

    # check cb contains merges of given topics and make flat merges_to_revert
    merges_to_revert = []
    for t, m_list in m_by_t.items():
        if ver_by_t[t]:
            for m in m_list:
                if m.rev.version == ver_by_t[t]:
                    break
            else:
                die("Didn't found non-reverted merges of",
                    t.name + '_v' + str(ver_by_t[t]), 'in', cb)
        elif not m_list:
            die("Didn't found non-reverted merges of", t.name, 'in', cb)
        merges_to_revert.extend(m_list)
    logging.info('Merges to revert:' +
                 ', '.join(str(m) for m in merges_to_revert) +
                 '. Searching for dependent topics')

    # check dependencies and make merges_to_revert_with_deps
    merges_to_revert_with_deps = []
    for m in merges_to_revert:
        for d in find_dependent_topic_merges(m, own_merges) + [m]:
            if not d.rev.is_in_merges(merges_to_revert_with_deps):
                if d.rev.is_in_merges(merges_to_revert) or dependencies:
                    merges_to_revert_with_deps.append(d)
                else:
                    die('Unable to revert', m.rev.get_branch_name(),
                        'since', d.rev.get_branch_name(),
                        'depends on it. Revert it first or use '
                        '"git af revert -d" revert dependent topics '
                        'automatically.')
    logging.info('Merges to revert with deps:' +
                 ', '.join(str(m) for m in merges_to_revert_with_deps) +
                 '. Checking upstream..')

    # check topics to revert aren't effectively merged in upstream branches
    if Iteration.is_develop(cb):
        upstream = ci.get_staging()
        upstream_merges = TopicMerge.get_effective_merges_in(upstream)
    elif Iteration.is_staging(cb):
        upstream = MASTER_NAME
        # pick merges from BP of next iteration if present,
        # from master otherwise
        next_iteration = ci.next()
        upstream_merges = TopicMerge.get_effective_merges_in(
            next_iteration.name if next_iteration else upstream)
    else:
        upstream = upstream_merges = None
    if upstream:
        for m in merges_to_revert_with_deps:
            if m.rev.is_in_merges(upstream_merges):
                die('Error:', m.rev.get_branch_name(), 'is merged in',
                    upstream + '. In git-aflow you cannot revert a topic until '
                    'it is reverted from the upstream branch.')

    # do reverts
    for m in merges_to_revert_with_deps:
        logging.info('Reverting ' + m.rev.get_branch_name())
        if commit.get_parent(m.SHA, 2):
            revert_result = commit.revert(m.SHA, 1)
        else:
            revert_result = commit.revert(m.SHA)
        if revert_result:
            say(m.rev.get_branch_name(), 'reverted successfully.')
        else:
            say('Revert failed unexpectedly, aborting..')
            commit.abort_revert()
            die()
