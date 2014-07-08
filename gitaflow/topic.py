"""Topic management functionality"""

import logging
from os import linesep
import re

from gitwrapper import misc, branch, commit
from gitaflow import iteration
from gitaflow.constants import FIX_NAME, DEV_NAME, EUF_NAME


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
