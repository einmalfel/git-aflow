import logging
import itertools

from gitaflow import iteration
from gitaflow.constants import STAGING_NAME, MASTER_NAME, DEVELOP_NAME
from gitaflow.topic import TopicRevision, TopicMerge
from gitaflow.common import say, die
from gitwrapper import branch, misc, commit


def merge(sources=None, merge_type=None, dependencies=False, merge_object=None,
          topics=None, description=None):
    cb = branch.get_current()
    if not cb:
        die('Cannot merge while in detached head state. Please check out a ' +
            'branch into which you are going to merge, e.g. "git af ' +
            'checkout staging"')

    if (merge_type or description) and (not topics or len(topics) != 1):
        die('If you are going to specify topic description and/or type, ' +
            'you should merge one single topic')

    if not misc.is_working_tree_clean():
        die('Your working tree is dirty. Please, stash or reset your ' +
            'changes before merge')

    ci = iteration.get_current_iteration()
    if ci is None:
        die('Cannot get current iteration, we are probably not in ' +
            'git-aflow repo')

    if iteration.is_develop(cb):
        die('You cannot merge into develop, use git af topic finish instead')

    if not sources:
        if iteration.is_master(cb):
            sources = [STAGING_NAME]
        elif iteration.is_release(cb):
            sources = [MASTER_NAME, STAGING_NAME]
        else:
            sources = [DEVELOP_NAME]
        logging.info('Auto-sources: ' + ', '.join(sources))

    for idx, source in enumerate(sources):
        if (not source == MASTER_NAME and not source.startswith(ci + '/') and
                not branch.exists(source)):
            sources[idx] = ci + '/' + source
            logging.info('Correcting ' + source + ' to ' + sources[idx])
        if (not branch.exists(sources[idx]) or
                not ci == iteration.get_iteration_by_branch(sources[idx])):
            die('Cannot find branch ' + sources[idx] + '. Note: sources may ' +
                'contain only master and branches from current iteration')

    own_merges = TopicMerge.get_effective_merges_in(cb)
    current_revision = TopicRevision.from_branch_name(cb)
    if ((not current_revision or not current_revision.iteration) and
            not iteration.is_master(cb) and not iteration.is_staging(cb) and
            not iteration.is_release(cb)):
        if commit.get_current_sha() == misc.rev_parse(ci):
            logging.info('Current branch is unknown, but it is empty so it is' +
                         ' safe to merge')
        else:
            logging.info('We are in unknown branch now: ' + cb +
                         '. Checking if it is based on some topic')
            d_merges = TopicMerge.get_all_merges_in(iteration.get_develop())
            for sha in commit.get_commits_between(ci, cb):
                for m in d_merges:
                    if m.rev.SHA == sha:
                        current_revision = m.rev
                        logging.warning('Current branch is based on ' +
                                        current_revision.get_branch_name() +
                                        '. Will exclude it from merge')
                        break
            else:
                logging.info('This branch is not based on any known topic, ' +
                             'so proceed as is')
    else:
        if not current_revision.iteration:
            current_revision.iteration = ci
    if current_revision:
        # Make virtual merge of current topic
        current_revision_merge = TopicMerge(current_revision, None, None, None,
                                            None)
        own_merges.append(current_revision_merge)

    merges_to_commit = []

    if merge_object == 'all':
        for source in sources:
            for m in TopicMerge.get_effective_merges_in(source):
                if m.is_newest_in(own_merges + merges_to_commit):
                    merges_to_commit.append(m)
                    logging.info('Adding to merge ' + str(m))
                else:
                    logging.info('Already have this version of ' + str(m))
    elif merge_object == 'update':
        for source in sources:
            for m in TopicMerge.get_effective_merges_in(source):
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
        source_merges = list(itertools.chain.from_iterable(
            [TopicMerge.get_effective_merges_in(s) for s in sources]))
        logging.info('Source merges: ' +
                     ', '.join(str(m) for m in source_merges))
        for topic in topics:
            revision = TopicRevision.from_branch_name(topic)
            if not revision.iteration:
                revision.iteration = ci
            if revision.default_version:
                last_merge = revision.topic.get_latest_merge(source_merges)
                if last_merge:
                    if last_merge.is_newest_in(own_merges + merges_to_commit):
                        merges_to_commit.append(last_merge)
                    else:
                        say('We already have same or newer version ' +
                            'of ' + topic + ' in ' + cb)
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
        if description:
            merges_to_commit[0].description = description
        if merge_type:
            merges_to_commit[0].type = merge_type
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
        for dependency in m.rev.get_effective_merges(True):
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

    logging.info('Topics with dependencies: ' +
                 ', '.join([m.rev.get_branch_name() for m in merges_with_deps])
                 + '. Merging now...')

    for idx, m in enumerate(merges_with_deps):
        logging.info('Merging ' + m.rev.get_branch_name())
        if not m.merge():
            if (iteration.is_master(cb) or iteration.is_staging(cb) or
                    iteration.is_release(cb)):
                commit.abort_merge()
                die('Merge of ' + m.rev.get_branch_name() + ' failed. ' +
                    'Something went wrong, did not expect conflict there(' +
                    cb + '). Please check carefully what you are doing. ' +
                    'Merge aborted.')
            say('Merge of ' + m.rev.get_branch_name() + ' failed. ' +
                'See conflicted files via "git status", resolve conflicts, ' +
                'add files to index ("git add") and do ' +
                '"git commit --no-edit" to finish the merge.')
            if idx + 1 < len(merges_with_deps):
                remain = merges_with_deps[idx + 1:]
                say('Then call "git af merge [topics]" again to merge ' +
                    'remaining topics. Topics remaining to merge: ' +
                    ', '.join([r.rev.get_branch_name() for r in remain]))
            die('Alternatively, you may abort failed merge via ' +
                '"git merge --abort"')
        else:
            say(m.rev.get_branch_name() + ' merged successfully')

    return True
