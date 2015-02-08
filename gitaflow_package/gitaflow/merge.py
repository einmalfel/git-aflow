import logging
import itertools

from gitaflow import iteration
from gitaflow.topic import TopicRevision, TopicMerge, \
    MergeNonConflictError
from gitaflow.common import say, die, consistency_check, check_iteration, \
    check_working_tree_clean, default_sources, complete_branch_name, \
    check_current_branch
from gitwrapper.cached import branch, misc, commit


def merge(sources=None, merge_type=None, dependencies=False, merge_object=None,
          topics=None, description=None):
    cb = check_current_branch()

    if (merge_type or description) and (not topics or len(topics) != 1):
        die('If you are going to specify topic description and/or type, ' +
            'you should merge one single topic')

    check_working_tree_clean()

    ci = check_iteration()

    if iteration.is_develop(cb):
        die('You cannot merge into develop, use git af topic finish instead')

    if not sources:
        sources = default_sources()
    sources = tuple(complete_branch_name(s, ci) for s in sources)
    for source in sources:
        if not iteration.get_iteration_by_branch(source) == ci:
            die('Merge sources should belong to current iteration. ' + source +
                " doesn't.")

    consistency_check(sources + (cb, ))

    # Topics in own_merges will be excluded from merge
    own_merges = list(TopicMerge.get_effective_merges_in(
        cb, treeish1=iteration.get_first_iteration()))
    if (not iteration.is_master(cb) and not iteration.is_staging(cb) and
            not iteration.is_release(cb) and
            not commit.get_current_sha() == misc.rev_parse(ci)):
        for m in TopicMerge.get_all_merges_in(iteration.get_develop()):
            if m.rev.SHA and (commit.is_based_on(m.rev.SHA, cb) or
                              m.rev.SHA == misc.rev_parse(cb)):
                own_merges.append(m)
                logging.info('Excluding from merge: ' + str(m.rev))

    merges_to_commit = []
    source_merges = list(itertools.chain.from_iterable(
        [TopicMerge.get_effective_merges_in(s) for s in sources]))
    if merge_object == 'all':
        for m in source_merges:
            if m.is_newest_in(own_merges + merges_to_commit):
                merges_to_commit.append(m)
                logging.info('Adding to merge ' + str(m))
            else:
                logging.info('Already have this version of ' + str(m))
    elif merge_object == 'update':
        for m in source_merges:
            add = False
            for already_have in own_merges + merges_to_commit:
                if m.rev.topic == already_have.rev.topic:
                    if m.rev.version > already_have.rev.version:
                        add = True
                    else:
                        logging.info('Already have this version of ' +
                                     already_have.rev.topic.name +
                                     '. Ours: ' + str(already_have) +
                                     ' theirs: ' + str(m))
                        break
            else:
                if add:  # if no break and this one (m) is newer then ours
                    merges_to_commit.append(m)
                    logging.info('Adding to merge ' + str(m))
    elif merge_object is None:
        logging.info('Source merges: ' +
                     ', '.join(str(m) for m in source_merges))
        for topic in topics:
            revision = TopicRevision.from_branch_name(topic,
                                                      default_iteration=ci)
            if revision.default_version:
                last_merge = revision.topic.get_latest_merge(source_merges)
                if last_merge:
                    if last_merge.is_newest_in(own_merges + merges_to_commit):
                        merges_to_commit.append(last_merge)
                    else:
                        say('Latest revision of ' + topic + ' in sources is ' +
                            last_merge.rev.get_branch_name() + '. We '
                            'already have it merged in ' + cb + '. Skipping..')
                else:
                    die('Merge failed. No topic ' + topic + ' in sources ' +
                        ', '.join(sources))
            else:
                for m in source_merges:
                    if m.rev == revision:
                        if m.is_newest_in(own_merges + merges_to_commit):
                            merges_to_commit.append(m)
                        else:
                            say('We already have this version of ' +
                                topic + ' in ' + cb + '. Skipping..')
                        break
                else:
                    die('Merge failed. No topic ' + topic + ' in sources ' +
                        ', '.join(sources))
    else:
        logging.critical('Unknown merge object ' + str(merge_object))

    if not merges_to_commit:
        die('There is nothing to merge.')
    logging.info(
        'Topics to merge: ' +
        ', '.join([m.rev.get_branch_name() for m in merges_to_commit]) +
        '. Checking dependencies now...')

    merges_with_deps = []
    for m in merges_to_commit:
        logging.info('Dependency search for ' + m.rev.get_branch_name())
        for dependency in m.rev.get_own_effective_merges(True):
            logging.info('Processing dependency ' +
                         dependency.rev.get_branch_name())
            if dependency.is_newest_in(own_merges + merges_with_deps):
                if dependencies:
                    merges_with_deps.append(dependency)
                elif m.rev.topic != dependency.rev.topic:
                    # merging some version of topic we don't depend on its elder
                    # versions
                    die('Merge failed. Topic ' + m.rev.get_branch_name() +
                        ' depends on ' + dependency.rev.get_branch_name() +
                        '. Try merge it first or use "git af merge -d" to ' +
                        'merge dependencies automatically')
        merges_with_deps.append(m)

    # add elder versions of topics being merged
    merges_with_versions = []
    own_revisions = tuple(m.rev for m in own_merges)
    for m in merges_with_deps:
        for v in range(1, m.rev.version):
            rev = TopicRevision(m.rev.topic, None, v, ci)
            if not rev.is_in_merges(merges_with_versions + own_merges):
                for sm in source_merges:
                    if sm.rev == rev:
                        merges_with_versions.append(sm)
                        break
                else:
                    if rev.is_newest_in(own_revisions):
                        die('Merge failed. We should merge ' +
                            m.rev.get_branch_name() + ' along with ' +
                            rev.get_branch_name() + ', but ' +
                            rev.get_branch_name() + ' is absent in sources.')
        merges_with_versions.append(m)

    logging.info(
        'Revisions to merge with dependencies and elder versions: ' +
        ', '.join([m.rev.get_branch_name() for m in merges_with_versions]) +
        '. Merging now...')

    fallback_sha = commit.get_current_sha()
    for idx, m in enumerate(merges_with_versions):
        logging.info('Merging ' + m.rev.get_branch_name())
        try:
            merge_result = m.merge(description, merge_type)
        except MergeNonConflictError:
            logging.critical('Unexpected merge error, falling back to ' +
                             fallback_sha)
            branch.reset(fallback_sha)
            raise
        if not merge_result:
            if (iteration.is_master(cb) or iteration.is_staging(cb) or
                    iteration.is_release(cb)):
                commit.abort_merge()
                die('Merge of ' + m.rev.get_branch_name() + ' failed. ' +
                    'Something went wrong, did not expect conflict there (' +
                    cb + '). Please check carefully what you are doing. ' +
                    'Merge aborted.')
            say('Merge of ' + m.rev.get_branch_name() + ' failed. ' +
                'See conflicted files via "git status", resolve conflicts, ' +
                'add files to index ("git add") and do ' +
                '"git commit --no-edit" to finish the merge.')
            if idx + 1 < len(merges_with_versions):
                remain = merges_with_versions[idx + 1:]
                say('Then call "git af merge [topics]" again to merge ' +
                    'remaining topics. Topics remaining to merge: ' +
                    ', '.join([r.rev.get_branch_name() for r in remain]))
            die('Alternatively, you may abort failed merge via ' +
                '"git merge --abort"')
        else:
            say(m.rev.get_branch_name() + ' merged successfully')

    return True
