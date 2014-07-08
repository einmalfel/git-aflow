"""Topic management functionality"""

import logging
from os import linesep
import re

from gitwrapper import misc, branch, commit
from . import iteration
from .constants import DEVELOP_NAME, MASTER_NAME, STAGING_NAME, \
    FIX_NAME, DEV_NAME, EUF_NAME


class Topic:
    """ This class represents topic. Topic is a sequence of commits merged
    one or multiple times somewhere in history into develop, staging or master.
    Topic may exists in multiple iterations and topic commits may differ from
    iteration to iteration.
    Topic also may have a topic branch associated with it
    """

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_all_merges(self):
        """ Searches for merges of this branch into all develops, stagings and
        master branches
        """
        iters = iteration.get_iteration_list()
        heads = ['master']
        heads.extend(iteration.get_develop(i) for i in iters)
        heads.extend(iteration.get_staging(i) for i in iters)
        logging.info('Searching ' + self.name + ' in branches ' + str(heads))
        shas = commit.find(heads, True, ["^Merge branch '[^/]+/" +
                                         self.name + "'.*$"])
        logging.debug('Found: ' + ', '.join(shas))
        result = []
        for sha in shas:
            m = TopicMerge.from_treeish(sha)
            if (self.is_branch_name_valid(m.rev.get_branch_name()) and
                    m and (iteration.is_master(m.merge_target) or
                           iteration.is_develop(m.merge_target) or
                           iteration.is_staging(m.merge_target))):
                result.append(m)
        logging.debug('After checks: ' + str(result))
        return result

    def is_branch_name_valid(self, branch_name):
        if not misc.is_valid_ref_name(branch_name):
            return False
        if (iteration.is_develop(branch_name) or
                iteration.is_master(branch_name) or
                iteration.is_release(branch_name) or
                iteration.is_staging(branch_name)):
            return False
        result = TopicRevision.from_branch_name(branch_name)
        if not result:
            return False
        if not iteration.is_iteration(result.iteration):
            return False
        if not result.topic.name == self.name:
            return False
        return True

    def get_branches(self):
        relevant_branches = branch.get_list(['*' + self.name + '*'])
        return [b for b in relevant_branches if self.is_branch_name_valid(b)]

    def get_latest_merge(self, list_of_merges):
        last = None
        for m in list_of_merges:
            if (m.rev.topic.name == self.name and
                    (not last or last.rev.version < m.rev.version)):
                last = m
        return last


class TopicRevision:
    """ This class represents a version on topic which was merged in one or
    more branches of single iteration
    """

    def __init__(self, topic, sha, version, iteration_):
        if version:
            version = int(version)
            if version <= 0:
                topic.name = topic.name + '_v' + str(version)
                version = 1
                self.default_version = True
            else:
                self.default_version = False
        else:
            version = 1
            self.default_version = True

        self.SHA = sha
        self.version = version
        self.topic = topic
        self.iteration = iteration_

    def __str__(self):
        s = str(self.topic)
        if self.iteration:
            s = self.iteration + '/' + s
        if self.version:
            if self.default_version:
                s += '(_v' + str(self.version) + ')'
            else:
                s += '_v' + str(self.version)
        if self.SHA:
            s += '[' + self.SHA + ']'
        return s

    def __eq__(self, other):
        # TopicRevision may be created w/o SHA, so do not compare SHA if not set
        return (isinstance(other, self.__class__) and
                self.iteration == other.iteration and
                self.topic == other.topic and
                self.version == other.version and
                (self.SHA == other.SHA if self.SHA and other.SHA else True))

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_effective_merges(self, recursive=False):
        if self.SHA:
            return TopicMerge.get_effective_merges_in(self.SHA, recursive)
        else:
            logging.critical('Searching for merges it topic w/o Topic.SHA')
            return None

    def merge(self, description=None, type_=None):
        """ Checks whether this revision was already merged and reverted in
        this branch. Makes "revert revert" for this case
        Does not check if this revision is already merged
        Returns None if conflict happened, TopicMerge otherwise
        """
        iter_ = iteration.get_current_iteration()
        commits = commit.get_commits_between(iter_, commit.get_current_sha(),
                                             True,
                                             ['^Revert "Merge branch .*"$',
                                              "^Merge branch .*$"])
        revert_search = None
        last_merge = None
        last_revert = None
        for sha in commits:
            if not commit.get_headline(sha).startswith('Revert "Merge'):
                merge = TopicMerge.from_treeish(sha)
                if merge:
                    if merge.rev == self:
                        revert_search = True
                        last_merge = merge
            elif revert_search:
                revert = TopicRevert.from_treeish(sha)
                if revert and revert.rev == self:
                    last_revert = revert

        if last_merge:
            if last_revert:
                logging.debug('Reverting ' + str(last_revert))
                result = commit.revert(last_revert.SHA, None, True)
                last_merge.merge_target = branch.get_current()
                if description:
                    last_merge.description = description
                if type_:
                    last_merge.type = type_
                if not misc.set_merge_msg(last_merge.get_message()):
                    logging.critical('Failed to set MERGE_MSG')
                    commit.abort_revert()
                    return None
                if not result:
                    return None
                else:
                    if commit.commit(None, True):
                        last_merge.SHA = commit.get_current_sha()
                        return last_merge
                    else:
                        logging.critical('Failed to commit pseudomerge' +
                                         str(last_merge))
                        return None
            else:
                logging.critical('Trying to merge already merged ' + str(self))
        else:
            if not self.SHA:
                logging.critical('Cannot merge w/o revision SHA')
                return None
            new_merge = TopicMerge(self, None, description, type_,
                                   branch.get_current())
            message = new_merge.get_message()
            if commit.merge(self.SHA, message):
                new_merge.SHA = commit.get_current_sha()
                return new_merge
            else:
                # don't let git to add "Conflicts:" section
                misc.set_merge_msg(message)
                return None

    def is_newest_in(self, array_of_revisions):
        for rev in array_of_revisions:
            if rev.topic == self.topic and rev.version >= self.version:
                return False
        return True

    branch_name_regexp = None

    @classmethod
    def from_branch_name(cls, branch_name):
        if cls.branch_name_regexp is None:
            cls.branch_name_regexp = re.compile(
                '^(?:([^/]+)/)?(.+?)(?:_v(\d+))?$')
        result = cls.branch_name_regexp.search(branch_name)
        logging.debug('Parsing branch name ' + branch_name + ' result: ' +
                      (str(result.groups()) if result else ' failed'))
        if not result:
            return None
        iteration_, name, version = result.groups()
        if not name:
            return None
        return TopicRevision(Topic(name), None, version, iteration_)

    def get_branch_name(self):
        return self.iteration + '/' + self.topic.name + '_v' + str(self.version)

    @staticmethod
    def get_all_revisions_in(treeish):
        return [m.rev for m in TopicMerge.get_effective_merges_in(treeish)]


class TopicMerge:
    """ This class represents merge of revision of topic into some branch
    """

    def __init__(self, revision, merge_sha, description, type_, merge_target):
        self.rev = revision
        self.SHA = merge_sha
        self.description = description
        self.type = type_
        self.merge_target = merge_target

    def __str__(self):
        s = '{Merge'
        if self.SHA:
            s += '[' + self.SHA + ']'
        s += ' of ' + str(self.rev)
        if self.merge_target:
            s += ' into ' + self.merge_target
        if self.type:
            s += ' ' + self.type
        if self.description:
            s += ' ' + self.description
        s += '}'
        return s

    def is_newest_in(self, array_of_merges):
        for merge in array_of_merges:
            if (merge.rev.topic == self.rev.topic and
                    merge.rev.version >= self.rev.version):
                return False
        return True

    headline_regexp = None

    @classmethod
    def from_headline(cls, headline):
        if cls.headline_regexp is None:
            cls.headline_regexp = re.compile(
                "^Merge branch '([^/]*/.*)'(?: into ([^/]*/.*))?$")
        # if branch is merged into master headline doesn't contain "into.." part
        re_result = cls.headline_regexp.search(headline)
        if not re_result:
            re_result = re.search("^Merge branch '([^/]*/.*)' into (.*)?$",
                                  headline)
            if not re_result:
                logging.warning('Failed to parse merge headline: ' + headline)
                return None
            else:
                logging.warning('Warning: incorrect branch name: ' +
                                re_result.groups()[1] +
                                '. Which iteration does this branch belong to?')
        branch_name, target = re_result.groups()
        revision = TopicRevision.from_branch_name(branch_name)
        if not target:
            target = 'master'
        if not revision.iteration:
            revision.iteration = iteration.parse_branch_name(target)[0]
        return TopicMerge(revision, None, None, None, target)

    @classmethod
    def from_message(cls, message):
        new = None
        for line in message.splitlines():
            if not new:
                new = cls.from_headline(line)
                if not new:
                    return None
            elif not new.type:
                new.type = line
            else:
                new.description = (new.description + linesep +
                                   line if new.description else line)
        if new.type not in (FIX_NAME, DEV_NAME, EUF_NAME):
            if new.type:
                new.description = new.type + linesep + new.description
            new.type = None
        return new

    @classmethod
    def from_treeish(cls, treeish):
        new = cls.from_message(commit.get_full_message(treeish))
        if new:
            new.SHA = misc.rev_parse(treeish)
            if not new.rev.iteration:
                new.rev.iteration = iteration.get_iteration_by_treeish(treeish)
            new.rev.SHA = commit.get_parent(new.SHA, 2)
        return new

    @classmethod
    def get_all_merges_in(cls, treeish):
        """ Returns all not-reverted merges in BP..treeish"""
        iter_name = iteration.get_iteration_by_treeish(treeish)
        result = []
        for sha in commit.get_commits_between(iter_name, treeish, True,
                                              ['^Revert "Merge branch .*"$',
                                               "^Merge branch .*$"]):
            merge = TopicMerge.from_treeish(sha)
            if merge:
                result.append(merge)
        return result

    @classmethod
    def get_effective_merges_in(cls, treeish, recursive=False):
        """ Returns all not-reverted merges in BP..treeish
        If some topic was reverted and remerged, returns original merge of this
        topic with revision extracted from original merge
        We cannot return here just not reverted original merges, cause latest
        merges contain actual type/descriptions
        """
        iter_name = iteration.get_iteration_by_treeish(treeish)
        result = []
        commits = commit.get_commits_between(iter_name, treeish, True,
                                             ['^Revert "Merge branch .*"$',
                                              "^Merge branch .*$"])
        for sha in commits:
            if commit.get_headline(sha).startswith('Revert "Merge'):
                revert = TopicRevert.from_treeish(sha)
                if revert:
                    for merge in reversed(result):
                        if merge.rev == revert.rev:
                            result.remove(merge)
                            logging.debug('Searching for topics in ' + treeish +
                                          ' Removing ' + str(merge))
                            break
            else:
                merge = TopicMerge.from_treeish(sha)
                if merge:
                    result.append(merge)
                    logging.debug('Searching for topics in ' + treeish +
                                  ' Adding ' + str(merge))

        for merge in result:
            if merge.is_fake():
                merge.rev = merge.get_original().rev

        if recursive:
            recursive_result = []
            for merge in result:
                merges2 = merge.rev.get_effective_merges(True)
                merges2.append(merge)
                for merge2 in merges2:
                    if merge2.is_newest_in(recursive_result):
                        recursive_result.append(merge2)
            return recursive_result
        else:
            return result

    def merge(self):
        return self.rev.merge(self.description, self.type)

    def get_message(self):
        result = "Merge branch '" + self.rev.get_branch_name() + "'"
        if not iteration.is_master(self.merge_target):
            result += ' into ' + self.merge_target
        result = result + linesep + (self.type if self.type else EUF_NAME)
        if self.description:
            result = result + linesep + self.description
        return result

    def is_fake(self):
        if not self.SHA:
            logging.critical('Checking for fake merge in TopicMerge that has ' +
                             'no SHA')
        return self.rev.SHA is None

    def get_original(self):
        if not self.SHA:
            logging.critical('Trying to found original merge of merge w\o SHA')
            return None
        ci = None
        if self.rev.iteration:
            ci = self.rev.iteration
        else:
            if self.merge_target:
                ci = iteration.get_iteration_by_branch(self.merge_target)
                if not ci:
                    ci = iteration.get_iteration_by_sha(self.SHA)
        if not ci:
            logging.critical('Unable to find iteration of merge ' + str(self))


class TopicRevert:
    """ Represents revert of topic revision merge
    """

    def __init__(self, revision, sha, merge_target, reverted_sha):
        self.rev = revision
        self.SHA = sha
        self.merge_target = merge_target
        self.reverted_SHA = reverted_sha

    def __str__(self):
        s = '{Revert of merge of ' + str(self.rev)
        if self.merge_target:
            s += ' into ' + self.merge_target
        if self.reverted_SHA:
            s += '. Reverted SHA: ' + self.reverted_SHA
        if self.SHA:
            s += '[' + self.SHA + ']'
        s += '}'
        return s

    @classmethod
    def from_treeish(cls, treeish):
        new = cls.from_message(commit.get_full_message(treeish))
        if new:
            new.SHA = misc.rev_parse(treeish)
            if not new.rev.iteration:
                new.rev.iteration = iteration.get_iteration_by_treeish(treeish)
        return new

    message_regexp = None

    @classmethod
    def from_message(cls, message):
        """ Parses revert commit message, extracting reverted SHA and headline
        info
        TODO: it's also possible to found commit revert was made relative to
        """
        if cls.message_regexp is None:
            cls.message_regexp = re.compile(
                '^This reverts commit (.*)[,\.].*$')
        new = None
        for line in message.splitlines():
            if not new:
                new = cls.from_headline(line)
                if not new:
                    return None
            else:
                result = cls.message_regexp.search(line)
                if result:
                    new.reverted_SHA = result.groups()[0]
                    break
        return new

    def get_reverted_merge(self):
        if self.reverted_SHA:
            return TopicMerge.from_treeish(self.reverted_SHA)
        else:
            logging.critical('Trying to get reverted merge w/o reverted SHA')
            return None

    headline_regexp = None

    @classmethod
    def from_headline(cls, headline):
        if cls.headline_regexp is None:
            cls.headline_regexp = re.compile(
                "^Revert \"Merge branch '(.*)'(?: into ([^/]*/.*))?\"$")
        re_result = cls.headline_regexp.search(headline)
        if not re_result:
            re_result = re.search(
                "^Revert \"Merge branch '(.*)' into (.*)\"$", headline)
            if not re_result:
                logging.warning('Failed to parse revert headline: ' + headline)
                return None
            else:
                logging.warning('Warning: incorrect branch name: ' +
                                re_result.groups()[1] +
                                '. Which iteration does this branch belong to?')
        branch_name, target = re_result.groups()
        if not target:
            target = 'master'
        revision = TopicRevision.from_branch_name(branch_name)
        if not revision.iteration:
            revision.iteration = iteration.parse_branch_name(target)[0]
        return TopicRevert(revision, None, target, None)


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
    return headline, topic_type, description


def parse_merge_headline(headline):
    """Returns (merged_branch, merged_into) tuple
    E.g.: "Merge branch 'a/b_v2' into a/develop" produces
    ('a/b_v2', 'a/develop')
    If cannot parse, returns (None, None)
    """
    if parse_merge_headline.regexp is None:
        parse_merge_headline.regexp =\
            re.compile("^Merge branch '([^/]*/.*)'(?: into ([^/]*/.*))?$")
    # when branch is merged into master headline does not contain "into.." part
    re_result = parse_merge_headline.regexp.search(headline)
    if not re_result:
        re_result = re.search("^Merge branch '([^/]*/.*)' into (.*)?$",
                              headline)
        if not re_result:
            logging.warning('Failed to parse merge headline: ' + headline)
            return None, None
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
    if parse_revert_headline.regexp is None:
        parse_revert_headline.regexp = re.compile(
            "^Revert \"Merge branch '([^/]*/.*)'(?: into ([^/]*/.*))?\"$")
    re_result = parse_revert_headline.regexp.search(headline)
    if not re_result:
        re_result = re.search(
            "^Revert \"Merge branch '([^/]*/.*)' into (.*)\"$",
            headline)
        if not re_result:
            logging.warning('Failed to parse revert headline: ' + headline)
            return None, None
        else:
            logging.warning('Warning: incorrect branch name: ' +
                            re_result.groups()[1] + '. Which iteration does ' +
                            'this branch belong to?')
    if not re_result:
        logging.warning('Failed to parse revert headline: ' + headline)
        return None, None
    result = re_result.groups()
    return result if result[1] is not None else (result[0], 'master')
parse_revert_headline.regexp = None


def get_merged_topics(treeish, iter_name=None, recursive=False):
    """List all topics which were merged in treeish and weren't reverted.
    If you don't know branch iteration it will calculate it.
    Returns list of tuple in order topics were merged.
    Tuple format: (topic name, version, last commit SHA, type, description).
    If several versions of topic founded returns all of them.
    """
    if not iter_name:
        iter_name = iteration.parse_branch_name(treeish)[0]
        if not iter_name:
            iter_name = iteration.get_iteration_by_sha(misc.rev_parse(treeish))
    result = []
    commits = commit.get_commits_between(iter_name, treeish, True,
                                         ['^Revert "Merge branch .*"$',
                                          "^Merge branch .*$"])
    for sha in commits:
        message = commit.get_full_message(sha)
        headline, topic_type, description = parse_merge_message(message)
        if headline.startswith('Merge branch'):
            merged_branch = parse_merge_headline(headline)[0]
            if merged_branch:
                tname, tversion = parse_topic_branch_name(merged_branch)[1:3]
                # TODO handle revert revert case
                tsha = commit.get_parent(sha, 2)
                result.append((tname, tversion, tsha, topic_type, description))
                logging.debug('Searching for topics in ' + treeish + ' Add ' +
                              tname + ' version: ' + str(tversion) + ' SHA: ' +
                              tsha + ' description: ' + description +
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
            for merged_in_topic in get_merged_topics(topic[2], iter_name,
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
    if parse_topic_branch_name.regexp is None:
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
    if not raw_version:
        return groups[0], groups[1], 1 if not groups[2] else int(groups[2])
    else:
        return groups
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
    heads.extend(iteration.get_develop(i) for i in iters)
    heads.extend(iteration.get_staging(i) for i in iters)
    logging.info('Searching ' + name + ' in branches ' + str(heads))
    shas = commit.find(heads, True, ["^Merge branch '[^/]+/" + name + "'.*$"])
    logging.debug('Found: ' + str(shas))
    result = []
    for sha in shas:
        ms_branch, merged_to = parse_merge_headline(commit.get_headline(sha))
        if is_valid_topic_branch(ms_branch, name):
            if merged_to == MASTER_NAME:
                result.append(sha)
            else:
                mt_iteration, mt_branch = iteration.parse_branch_name(merged_to)
                if ((mt_branch == DEVELOP_NAME or mt_branch == STAGING_NAME) and
                        iteration.is_iteration(mt_iteration)):
                    result.append(sha)
    logging.debug('After checks: ' + str(result))
    return result


def start(name):
    ci = iteration.get_current_iteration()
    if ci is None:
        print('Could not get current iteration, we are probably not in \
git-aflow repo')
        logging.info('No CI, stopping')
        return False
    branch_name = ci + '/' + name
    logging.info('Checking name ' + branch_name)
    if not is_valid_topic_branch(branch_name):
        print('Please correct topic name. "..", "~", "^", ":", "?", "*", ' +
              '"[", "@", "\", spaces and ASCII control characters' +
              ' are not allowed. Input something like "fix_issue18" or ' +
              '"do_api_refactoring"')
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
        print('You have some untracked files which you may loose when ' +
              'switching to new topic branch. Please, delete or commit them. ' +
              'Here they are: ' + ', '.join(intersection) + '.' + linesep +
              'Use "git clean" to remove all untracked files')
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
    shas = topic_merges_in_history(name)
    if shas:
        print('Cannot start topic, it already exists in history, see SHA: ' +
              ', '.join(shas))
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
 branch into which you are going to merge, e.g. "git af checkout staging"')
        logging.info('No CB, stopping')
        return False
    if (merge_type or description) and (not topics or len(topics) != 1):
        print('If you are going to specify topic description and/or type, ' +
              'you should merge one single topic')
        logging.info('If you are going to specify topic description and/or ' +
                     'type, you should merge one single topic')
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
        own_topics.append((current_topic[1], current_topic[2], None, None,
                           None))
    topics_to_merge = []

    if merge_object == 'all':
        for source in sources:
            for topic in get_merged_topics(source, ci):
                if is_topic_newer(topic, own_topics + topics_to_merge):
                    topics_to_merge.append(topic)
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
                            topics_to_merge.append(topic)
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
                        add = [newest[0], newest[1], newest[2],
                               merge_type if merge_type else newest[3],
                               description if description else newest[4]]
                        topics_to_merge.append(add)
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
                        add = [source_topic[0],
                               source_topic[1],
                               source_topic[2],
                               merge_type if merge_type else source_topic[3],
                               description if description else source_topic[4]]
                        topics_to_merge.append(add)
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