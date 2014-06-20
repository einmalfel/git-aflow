"""Topic management functionality"""

import logging
from os import linesep
import re

from gitwrapper import misc, branch, commit
from . import iteration
from .constants import DEVELOP_NAME, MASTER_NAME, STAGING_NAME, \
    FIX_NAME, DEV_NAME, EUF_NAME


def parse_merge_message(message):
    """Parses merge commit message into tuple (headline, type, description).
    If unable to parse, returns (None, None, None)
    Merge commit format is:
    "Merge branch....
    FIX|DEV|EUF
    Description
    Description
    ...."
    If type is omitted sets it to EUF
    """
    headline = None
    description = ''
    topic_type = None
    for line in message.splitlines():
        if not headline:
            headline = line
        elif not type:
            topic_type = line
        else:
            description = description + linesep + line if description else line
    if topic_type not in (FIX_NAME, DEV_NAME, EUF_NAME):
        if topic_type:
            description = topic_type + linesep + description
        topic_type = EUF_NAME
    return (headline, topic_type, description)


def parse_merge_headline(headline):
    """Returns (merged_branch, merged_into) tuple
    E.g.: "Merge branch 'a/b_v2' into a/develop" produces
    ('a/b_v2', 'a/develop')
    If cannot parse, returns (None, None)
    """
    if parse_merge_headline.regexp == None:
        parse_merge_headline.regexp =\
            re.compile("^Merge branch '([^/]*/.*)'(?: into ([^/]*/.*))?$")
    # when branch is merged into master headline does not contain "into.." part
    re_result = parse_merge_headline.regexp.search(headline)
    if not re_result:
        re_result = re.search("^Merge branch '([^/]*/.*)' into (.*)?$",
                              headline)
        if not re_result:
            logging.warning('Failed to parse merge headline: ' + headline)
            return (None, None)
        else:
            logging.warning('Warning: incorrect branch name: ' +
                            re_result.groups()[1] + '. Which iteration does ' +
                            'this branch belong to?')
    result = re_result.groups()
    return result if result[1] is not None else (result[0], 'master')
parse_merge_headline.regexp = None


def parse_revert_headline(headline):
    """Returns (merged_branch, merged_into) tuple
    E.g.: "Revert "Merge branch 'a/b_v2' into a/develop"" produces
    ('a/b_v2', 'a/develop')
    If cannot parse, return (None, None)
    """
    if parse_revert_headline.regexp == None:
        parse_revert_headline.regexp = re.compile(
            "^Revert \"Merge branch '([^/]*/.*)'(?: into ([^/]*/.*))?\"$")
    re_result = parse_revert_headline.regexp.search(headline)
    if not re_result:
        re_result = re.search(
            "^Revert \"Merge branch '([^/]*/.*)' into (.*)\"$",
            headline)
        if not re_result:
            logging.warning('Failed to parse revert headline: ' + headline)
            return (None, None)
        else:
            logging.warning('Warning: incorrect branch name: ' +
                            re_result.groups()[1] + '. Which iteration does ' +
                            'this branch belong to?')
    if not re_result:
        logging.warning('Failed to parse revert headline: ' + headline)
        return (None, None)
    result = re_result.groups()
    return result if result[1] is not None else (result[0], 'master')
parse_revert_headline.regexp = None


def get_merged_topics(treeish, iteration_name=None, recursive=False):
    """List all topics which were merged in treeish and weren't reverted.
    If you don't know branch iteration it will calculate it.
    Returns list of tuple in order topics were merged.
    Tuple format: (topic name, version, last commit SHA, type, description).
    If several versions of topic founded returns all of them.
    """
    if not iteration_name:
        iteration_name = iteration.parse_branch_name(treeish)[0]
        if not iteration_name:
            iteration_name = iteration.get_iteration_by_SHA(
                                                    misc.rev_parse(treeish))
    result = []
    commits = commit.get_commits_between(iteration_name, treeish, True,
                                         ['^Revert "Merge branch .*"$',
                                          "^Merge branch .*$"])
    for SHA in commits:
        message = commit.get_full_message(SHA)
        headline, topic_type, description = parse_merge_message(message)
        if headline.startswith('Merge branch'):
            merged_branch = parse_merge_headline(headline)[0]
            if merged_branch:
                tname, tversion = parse_topic_branch_name(merged_branch)[1:3]
                # TODO handle revert revert case
                tSHA = commit.get_parent(SHA, 2)
                result += [(tname, tversion, tSHA, topic_type, description)]
                logging.debug('Searching for topics in ' + treeish + ' Add ' +
                              tname + ' version: ' + str(tversion) + ' SHA: ' +
                              tSHA + ' description: ' + description +
                              ' type: ' + topic_type)
        elif headline.startswith('Revert "Merge branch '):
            reverted_branch = parse_revert_headline(headline)[0]
            if reverted_branch:
                rname, rversion = parse_topic_branch_name(reverted_branch)[1:3]
                for merged in result:
                    if merged[0] == rname and merged[1] == rversion:
                        result.remove(merged)
                        logging.debug('Searching for topics in ' + treeish +
                                      ' Remove ' + rname + ' version ' +
                                      str(rversion))
    if recursive:
        recursive_result = []
        for topic in result:
            for merged_in_topic in get_merged_topics(topic[2], iteration_name,
                                                     True) + [topic]:
                for already_added in recursive_result:
                    if (already_added[0] == merged_in_topic[0] and
                            already_added[1] >= merged_in_topic[1]):
                        break
                else:
                    recursive_result.append(merged_in_topic)
        return recursive_result
    else:
        return result


def parse_topic_branch_name(name, raw_version=False, no_iteration=False):
    """Returns (iteration, name, version) tuple or None if cannot parse
    E.g.: iter/name_v produces ("iter", "name_v", 1), cause first version
    of topic doesn't have any suffix and suffix ends with number
    """
    if parse_topic_branch_name.regexp == None:
        parse_topic_branch_name.regexp =\
            re.compile('^(?:([^/]+)/)?(.+?)(?:_v(\d+))?$')
    result = parse_topic_branch_name.regexp.search(name)
    logging.debug('Parsing branch name ' + name + ' result: ' +
                  (str(result.groups()) if result else ' failed'))
    if not result:
        return None
    groups = result.groups()
    if not no_iteration and not groups[0]:
        return None
    return (groups[0],
        groups[1],
        groups[2] if raw_version else (1 if not groups[2] else int(groups[2])))
parse_topic_branch_name.regexp = None


def is_valid_topic_branch(branch_name, topic_name=None):
    """If no topic name passed, checks if topic branch name is valid (iteration
    exists and branch name has correct format)
    Otherwise, also checks if it is valid branch name for given topic
    TODO: check if there are releases with same name
    """
    if not misc.is_valid_ref_name(branch_name):
        return False
    if iteration.is_develop(branch_name) or\
            iteration.is_master(branch_name) or\
            iteration.is_release(branch_name) or\
            iteration.is_staging(branch_name):
        return False
    result = parse_topic_branch_name(branch_name)
    logging.debug('Branch name parsed ' + str(result))
    if not result:
        return False
    else:
        if not iteration.is_iteration(result[0]):
            return False
        if not topic_name:
            return True
        else:
            return result[1] == topic_name


def topic_branches(name):
    """Returns topic branch names list for all versions of given topic.
    Name should be given without iteration prefix and version suffix
    """
    topics = branch.get_list(['*' + name + '*'])
    return [topic for topic in topics if is_valid_topic_branch(topic, name)]


def topic_merges_in_history(name):
    """Returns list of merge commits SHA, in which any version of topic was
    merged into master, develop and staging
    Name should be given without iteration prefix and version suffix
    """
    iters = iteration.get_iteration_list()
    heads = ['master']
    heads += [iteration.get_develop(i) for i in iters]
    heads += [iteration.get_staging(i) for i in iters]
    logging.info('Searching ' + name + ' in branches ' + str(heads))
    SHAs = commit.find(heads, True,
                ["^Merge branch '[^/]+/" + name + "'.*$"])
    logging.debug('Found: ' + str(SHAs))
    result = []
    for SHA in SHAs:
        branch, merged_to = parse_merge_headline(
                                commit.get_headline(SHA))
        if is_valid_topic_branch(branch, name):
            if merged_to == MASTER_NAME:
                result += [SHA]
            else:
                mt_iteration, mt_branch =\
                        iteration.parse_branch_name(merged_to)
                if iteration.is_iteration(mt_iteration) and\
                    (mt_branch == DEVELOP_NAME or mt_branch == STAGING_NAME):
                    result += [SHA]
    logging.debug('After checks: ' + str(result))
    return result


def start(name):
    ci = iteration.get_current_iteration()
    branch_name = ci + '/' + name
    logging.info('Checking name ' + branch_name)
    if not is_valid_topic_branch(branch_name):
        print('Please correct topic name. ".."'
', "~", "^", ":", "?", "*", "[", "@", "\", spaces and ASCII control characters'
' are not allowed. Input something like "fix_issue18" or "do_api_refactoring"')
        logging.info('Wrong topic name. Stopping')
        return False
    logging.info('Check working tree')
    if not misc.is_working_tree_clean():
        print('Your working tree is dirty. Please, stash or reset your \
changes before starting topic')
        logging.info('Working tree is dirty stopping, stopping')
        return False
    intersection = frozenset(misc.get_untracked_files()) &\
        frozenset(misc.list_files_differ('HEAD', ci))
    if intersection:
        print('You have some untracked files which you may loose when \
switching to new topic branch. Please, delete or commit them. \
Here they are: ' + ', '.join(intersection))
        logging.info('User may lose untracked file, stopping')
        return False

    logging.info('Check if there is branch for this topic already')
    branches = topic_branches(name)
    if branches:
        print('Cannot start topic, there are already branches: ' +
              str(branches))
        logging.info('Topic branches with given name exists, stopping')
        return False

    logging.info('Ok, now check if there was such topic somewhere in history')
    SHAs = topic_merges_in_history(name)
    if SHAs:
        print('Cannot start topic, it already exists in history, see SHA: ' +
              ', '.join(SHAs))
        logging.info('Topics with given name exist in history, stopping')
        return False

    logging.info('All good, creating branch ' + branch_name)
    if not branch.create(branch_name, ci):
        logging.critical("Something went wrong, cannot create \
topic branch")
        return False
    if misc.checkout(branch_name):
        print('Topic ' + name + ' created. You are in ' + branch_name +
              ' branch')
        return True
    else:
        logging.critical("Something went wrong, cannot checkout \
topic branch. Deleting branch and stopping")
        branch.delete(branch_name)
        return False


def is_topic_newer(topic, array):
    """Returns True if there are no topics in array with same name and same or
    greater version, otherwise return False
    """
    for another in array:
        if topic[0] == another[0] and topic[1] <= another[1]:
            return False
    return True


def merge(sources=None, merge_type=None, dependencies=False, merge_object=None,
          topics=None, description=None):
    cb = branch.get_current()
    if not cb:
        print('Cannot merge while in detached head state. Please check out a\
 branch into which you are going to merge, e.g. "git af merge staging"')
        logging.info('No CB, stopping')
        return False
    if not misc.is_working_tree_clean():
        print('Your working tree is dirty. Please, stash or reset your \
changes before merge')
    ci = iteration.get_current_iteration()
    if ci is None:
        print('Cannot get current iteration, we are probably not in \
git-aflow repo')
        logging.info('No CI, stopping')
        return False
    if iteration.is_develop(cb):
        print('You cannot merge into develop, use git af topic finish instead')
        logging.info('Merge to develop, stopping')
        return False
    if not sources:
        if iteration.is_master(cb):
            sources = [STAGING_NAME]
        elif iteration.is_release(cb):
            sources = [MASTER_NAME, STAGING_NAME]
        else:
            sources = [DEVELOP_NAME]

    # expand and check sources
    # TODO: sources may also contain topics w/o TB and raw SHA to merge from
    for idx, source in enumerate(sources):
        if (not source == MASTER_NAME and not source.startswith(ci + '/') and
                not branch.exists(source)):
            sources[idx] = ci + '/' + source
        if (not branch.exists(sources[idx]) or
                not ci == iteration.get_iteration_by_branch(sources[idx])):
            print('Cannot find branch ' + sources[idx] + '. Note: sources may \
contain only master and branches from current iteration')
            logging.info('Source ' + sources[idx] + " doesn't exist, stopping")
            return False

    own_topics = get_merged_topics(cb, ci)
    current_topic = parse_topic_branch_name(cb)
    if current_topic:
        own_topics += [(current_topic[1], current_topic[2], None, None, None)]
    topics_to_merge = []

    if merge_object == 'all':
        for source in sources:
            for topic in get_merged_topics(source, ci):
                if is_topic_newer(topic, own_topics + topics_to_merge):
                    topics_to_merge += [topic]
                    logging.debug('Adding to merge ' + topic[0] + '_v' +
                                  str(topic[1]))
                else:
                    logging.debug('Already have this version of ' +
                                  topic[0] + '_v' + str(topic[1]))
    elif merge_object == 'update':
        for source in sources:
            for topic in get_merged_topics(source, ci):
                add = False
                for already_have in own_topics + topics_to_merge:
                    if topic[0] == already_have[0]:
                        if topic[1] > already_have[1]:
                            add = True
                        else:
                            logging.debug('Already have this version of ' +
                                          topic[0] + '. Ours: ' +
                                          str(already_have[1]) + ' theirs: ' +
                                          str(topic[1]))
                            break
                    else:
                        if add:  # if no break and it's newer then ours
                            topics_to_merge += [topic]
                            logging.debug('Adding to merge ' + topic[0] +
                                          '_v' + str(topic[1]))
    elif merge_object is None:
        source_topics = [t for s in sources for t in get_merged_topics(s, ci)]
        logging.debug('Source topics: ' + str(source_topics))
        for topic in topics:
            tname, tversion = parse_topic_branch_name(topic, True, True)[1:]
            if not tversion:
                newest = (None, -1, None, None, None)
                for source_topic in source_topics:
                    if (tname == source_topic[0] and
                            newest[1] < source_topic[1]):
                        newest = source_topic
                if newest[0]:
                    if is_topic_newer(newest, own_topics + topics_to_merge):
                        topics_to_merge += [newest]
                    else:
                        logging.info('We already have same or newer version ' +
                                     'of ' + topic + ' in ' + cb)
                        print('We already have same or newer version ' +
                              'of ' + topic + ' in ' + cb)
                else:
                    logging.info('No topic ' + topic + ' in sources ' +
                                 ', '.join(sources) + '. Stopping')
                    print('Merge failed. No topic ' + topic + ' in sources ' +
                          ', '.join(sources))
                    return False
            else:
                if not is_topic_newer([tname, int(tversion), None, None, None],
                                      own_topics):
                    logging.info('We already have same or newer version of ' +
                             topic + ' in ' + cb)
                    print('We already have same or newer version of ' +
                          topic + ' in ' + cb + '. Skipping..')
                    continue
                for source_topic in source_topics:
                    if ((tname, int(tversion)) == source_topic[:2] and
                            is_topic_newer(source_topic,
                                           topics_to_merge + own_topics)):
                        topics_to_merge += [source_topic]
                        break
                else:
                    logging.info('No topic ' + topic + ' in sources ' +
                                 ', '.join(sources) + '. Stopping')
                    print('Merge failed. No topic ' + topic + ' in sources ' +
                          ', '.join(sources))
                    return False
    else:
        logging.critical('Unknown merge object ' + str(merge_object))

    logging.info('Topics to merge: ' +
                 ', '.join([t[0] + '_v' + str(t[1]) for t in topics_to_merge]) +
                 '. Checking dependencies now...')
    if not topics_to_merge:
        logging.info('Zero topics specified for merge!')
        print('There is nothing to merge.')
        return False

    topics_with_deps = []
    for topic in topics_to_merge:
        logging.debug('Processing topic ' + topic[0] + '_v' + str(topic[1]))
        for dependency in get_merged_topics(topic[2], ci, True):
            logging.debug('Processing dep ' + dependency[0] + '_v' +
                          str(dependency[1]))
            for topic_d in topics_with_deps + own_topics:
                if (topic_d[0] == dependency[0] and
                        topic_d[1] >= dependency[1]):
                    break
            else:
                if dependencies:
                    topics_with_deps.append(dependency)
                else:
                    print('Merge failed. Topic ' + topic[0] + '_v' +
                          str(topic[1]) + ' depends on ' + dependency[0] +
                          '_v' + str(dependency[1]) + '. Try merge it first ' +
                          'or use "git af merge -d" to merge dependencies ' +
                          'automatically')
                    logging.info('Merge failed. Topic ' + topic[0] + '_v' +
                                 str(topic[1]) + ' depends on ' +
                                 dependency[0] + '_v' + str(dependency[1]))
                    return False
        topics_with_deps.append(topic)

    logging.info('Topics with dependencies: ' +
                 ', '.join([t[0] + '_v' + str(t[1]) for t in topics_with_deps])
                 + '. Merging now...')

    for idx, topic in enumerate(topics_with_deps):
        # TODO: handle reverted merges
        logging.debug('Merging ' + topic[0] + '_v' + str(topic[1]))
        if not commit.merge(topic[2], "Merge branch '" + ci + '/' + topic[0] +
                            '_v' + str(topic[1]) + "' into " + cb +
                            linesep + topic[3] + linesep + topic[4]):
            if (iteration.is_develop(cb) or iteration.is_master(cb) or
                    iteration.is_staging(cb) or iteration.is_release(cb)):
                logging.critical('Merge of ' + topic[0] + '_v' + str(topic[1]) +
                                 ' failed. Something went wrong, did not ' +
                                 'expect conflict there(' + cb + '). Please ' +
                                 'check carefully what you are doing. ' +
                                 'Aborting merge.')
                commit.abort_merge()
            logging.info('Merge of ' + topic[0] + '_v' + str(topic[1]) +
                         ' failed.')
            print('Merge of ' + topic[0] + '_v' + str(topic[1]) + ' failed. ' +
                  'See conflicted files via "git status", resolve conflicts, ' +
                  'add files to index ("git add") and do ' +
                  '"git commit --no-edit" to finish the merge.')
            if idx + 1 < len(topics_with_deps):
                print('Then call "git af merge [topics]" again to merge ' +
                      'remaining topics. Topics remaining to merge: ' +
                      ', '.join([t[0] + '_v' + str(t[1]) for t in
                                topics_with_deps[idx + 1:]]))
            print('Alternatively, you may abort current merge via' +
                  '"git merge --abort"')
            return False
        else:
            print(topic[0] + '_v' + str(topic[1]) + ' merged successfully')

    return True