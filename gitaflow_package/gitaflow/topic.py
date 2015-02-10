"""Topic management functionality"""

import logging
from os import linesep
import re
import collections

from thingitwrapper.grouped_cache import cache
from thingitwrapper.cached import misc, branch, commit
from gitaflow import iteration
from gitaflow.constants import FIX_NAME, DEV_NAME, EUF_NAME


class MergeNonConflictError(Exception):
    """ Merge failed unexpectedly."""


class IncompleteMergeObjectError(Exception):
    """ Merge object is not complete enough to execute called method."""


def get_merges_and_reverts(treeish1, treeish2, reduce=False):
    """ Returns a list of merges and reverts parse starts from treeish1 and
    ends on treeish2"""
    result = []
    commits = commit.get_commits_between(treeish1, treeish2, True,
                                         ['^Revert "Merge branch .*"$',
                                          "^Merge branch .*$"])
    for sha in commits:
        revert = TopicRevert.from_treeish(sha)
        if revert:
            if reduce:
                for obj in reversed(result):
                    if isinstance(obj, TopicMerge) and obj.rev == revert.rev:
                        result.remove(obj)
                        logging.debug('Searching for topics in ' + treeish1 +
                                      '..' + treeish2 + ' Removing ' + str(obj))
                        break
                else:
                    result.append(revert)
            else:
                result.append(revert)
        else:
            merge = TopicMerge.from_treeish(sha)
            if merge:
                result.append(merge)
                logging.debug('Searching for topics in ' + treeish1 +
                              '..' + treeish2 + ' Adding ' + str(merge))

    return tuple(result)


class Topic(collections.namedtuple('TopicT', ('name',))):
    """ This class represents topic. Topic is a sequence of commits merged
    one or multiple times somewhere in history into develop, staging or master.
    Topic may exists in multiple iterations and topic commits may differ from
    iteration to iteration.
    Topic also may have a topic branch associated with it
    """

    def __new__(cls, name):
        return super().__new__(cls, name)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.name)

    def get_all_merges_in(self, treeish):
        """ Searches for merges of this topic between RP and specified treeish
        """
        iter_name = iteration.get_iteration_by_treeish(treeish)
        logging.debug('Searching ' + self.name + ' in ' + str(treeish))
        shas = commit.get_commits_between(
            iter_name, treeish, True,
            ["^Merge branch '([^/]+/)?" + self.name + "(_v[0-9]+)?'.*$"])
        result = []
        for sha in shas:
            m = TopicMerge.from_treeish(sha)
            if m and (m.rev.topic == self):
                result.append(m)
        return result

    def get_all_merges(self):
        """ Searches for merges of this topic into all develops, stagings and
        master branches
        """
        iters = iteration.get_iterations()
        heads = ['master']
        heads.extend(iteration.get_develop(i) for i in iters)
        heads.extend(iteration.get_staging(i) for i in iters)
        logging.info('Searching ' + self.name + ' in branches ' + str(heads))
        shas = commit.find(heads, True, ["^Merge branch '([^/]+/)?" +
                                         self.name + "(_v[0-9]+)?'.*$"])
        logging.debug('Found: ' + ', '.join(shas))
        result = []
        for sha in shas:
            m = TopicMerge.from_treeish(sha)
            if (m and (m.rev.topic == self) and (
                    iteration.is_master(m.merge_target) or
                    iteration.is_develop(m.merge_target) or
                    iteration.is_staging(m.merge_target))):
                result.append(m)
        logging.debug('After checks: ' + str(result))
        return result

    branch_name_regexp = None

    @classmethod
    def is_valid_tb_name(cls, branch_name):
        if cls.branch_name_regexp is None:
            cls.branch_name_regexp = re.compile(
                '^(?:[^/]+/)?.+?(?:_v(\d+))?$')
        result = cls.branch_name_regexp.search(branch_name)
        if result:
            groups = result.groups()[0]
            if groups:
                try:
                    version = int(groups[0])
                except ValueError:
                    return False
                else:
                    if version < 1:
                        return False
        else:
            return False
        if (not misc.is_valid_ref_name(branch_name) or
                iteration.is_develop(branch_name) or
                iteration.is_master(branch_name) or
                iteration.is_release(branch_name) or
                iteration.is_staging(branch_name)):
            return False
        return True

    def is_in_merges(self, merges):
        for merge in merges:
            if merge.rev.topic == self:
                return True
        return False

    def get_branches(self):
        relevant_branches = branch.get_list(['*' + self.name + '*'])
        return [b for b in relevant_branches
                if TopicRevision.from_branch_name(b).topic == self]

    def get_latest_merge(self, list_of_merges, no_fake=False):
        last = None
        for m in list_of_merges:
            if (m.rev.topic.name == self.name and (not no_fake or m.rev.SHA) and
                    (not last or last.rev.version < m.rev.version)):
                last = m
        return last


class TopicRevision(collections.namedtuple('TopicRevisionT', (
        'topic', 'SHA', 'version', 'iteration', 'default_version'))):
    """ This class represents a version on topic which was merged in one or
    more branches of single iteration
    """

    def __new__(cls, topic, sha, version, iteration_):
        if version:
            version = int(version)
            if version <= 0:
                topic.name = topic.name + '_v' + str(version)
                version = 1
                default_v = True
            else:
                default_v = False
        else:
            version = 1
            default_v = True
        return super().__new__(cls, topic, sha, version, iteration_, default_v)

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
            s += '[' + self.SHA[0:7] + ']'
        return s

    def __eq__(self, other):
        # TopicRevision may be created w/o SHA, so do not compare SHAs
        return (isinstance(other, self.__class__) and
                self.iteration == other.iteration and
                self.topic == other.topic and
                self.version == other.version)

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_own_effective_merges(self, recursive=False):
        if self.SHA:
            return TopicMerge.get_effective_merges_in(self.SHA, recursive)
        else:
            logging.critical('Searching for merges it topic w/o Topic.SHA')
            return None

    def is_in_merges(self, sequence_of_merges):
        for merge in sequence_of_merges:
            if merge.rev == self:
                return True
        return False

    def is_in_reverts(self, sequence_of_reverts):
        for revert in sequence_of_reverts:
            if revert.rev == self:
                return True
        return False

    def merge(self, description=None, type_=None):
        """ Checks whether this revision was already merged and reverted in
        this branch. Makes "revert revert" for this case
        Does not check if this revision is already merged
        Returns None if conflict happened, TopicMerge otherwise.
        Raises MergeNonConflictError for other errors
        """
        iter_ = iteration.get_current_iteration()
        commits = commit.get_commits_between(iter_, commit.get_current_sha(),
                                             False,
                                             ['^Revert "Merge branch .*"$',
                                              "^Merge branch .*$"])

        # Before merging new revision we should merge revisions that:
        #  - are revisions of self.topic
        #  - where reverted from cb
        #  - are newer then last effectively merged revision
        #  - are not newer then revision that is being merged now
        reverts = []  # one revert object for each revision of self.topic that
                      # was ever reverted
        last_effect_m = None
        for sha in commits:
            if commit.get_headline(sha).startswith('Revert'):
                revert = TopicRevert.from_treeish(sha)
                if (revert and revert.rev.topic == self.topic and
                        not revert.rev.is_in_reverts(reverts)):
                    reverts.append(revert)
            else:
                m = TopicMerge.from_treeish(sha)
                if (m and not last_effect_m and m.rev.topic == self.topic and
                        not m.rev.is_in_reverts(reverts)):
                    last_effect_m = m

        effect_version = last_effect_m.rev.version if last_effect_m else 0
        reverts_filtered = [revert for revert in reverts if
                            effect_version < revert.rev.version <= self.version]
        reverts_filtered.sort(key=lambda x: x.rev.version)

        reverted_merge = None
        for revert in reverts_filtered:
            reverted_merge = revert.get_reverted_merge()
            logging.info('Re-reverting ' + str(reverted_merge))
            if not commit.revert(revert.SHA, None, True):
                return None
            if reverted_merge.rev == self:
                message = TopicMerge.get_merge_message(
                    reverted_merge.rev,
                    branch.get_current(),
                    description if description else reverted_merge.description,
                    type_ if type_ else reverted_merge.type)
            else:
                message = TopicMerge.get_merge_message(
                    reverted_merge.rev,
                    branch.get_current(),
                    reverted_merge.description,
                    reverted_merge.type)
            try:
                misc.set_merge_msg(message)
            except misc.MergeMsgError as msg_error:
                commit.abort_revert()
                raise MergeNonConflictError from msg_error
            if not commit.commit(None, True):
                commit.abort_revert()
                raise MergeNonConflictError('Failed to commit while ' +
                                            'reverting ' + str(revert))

        # If revision we are going to merge was not re-reverted on previous
        # stage we should make true merge:
        if reverted_merge and reverted_merge.rev == self:
            return TopicMerge.from_treeish('HEAD')
        else:
            if not self.SHA:
                raise MergeNonConflictError('Cannot merge w/o revision SHA')
            message = TopicMerge.get_merge_message(self, branch.get_current(),
                                                   type_, description)
            logging.info('Merging ' + str(self))
            if commit.merge(self.SHA, message):
                return TopicMerge(self, commit.get_current_sha(), description,
                                  type_, branch.get_current())
            else:
                # don't let git to add "Conflicts:" section
                try:
                    misc.set_merge_msg(message)
                except misc.MergeMsgError as msg_error:
                    commit.abort_merge()
                    raise MergeNonConflictError from msg_error
                return None

    def is_newest_in(self, array_of_revisions):
        for rev in array_of_revisions:
            if rev.topic == self.topic and rev.version >= self.version:
                return False
        return True

    branch_name_regexp = None

    @classmethod
    def from_branch_name(cls, branch_name, sha=None, default_iteration=None):
        n, v, i = cls.parse_branch_name(branch_name)
        return TopicRevision(Topic(n), sha, v, i if i else default_iteration)

    @classmethod
    def parse_branch_name(cls, branch_name):
        """Returns (name, version, iteration)"""
        if cls.branch_name_regexp is None:
            cls.branch_name_regexp = re.compile(
                '^(?:([^/]+)/)?(.+?)(?:_v(\d+))?$')
        result = cls.branch_name_regexp.search(branch_name)
        logging.debug('Parsing branch name ' + branch_name + ' result: ' +
                      (str(result.groups()) if result else ' failed'))
        if not result:
            return None, None, None
        iteration_, name, version = result.groups()

        # TB names may contain slash
        if iteration_ and not iteration.is_iteration(iteration_):
            name = iteration_ + '/' + name
            iteration_ = None

        return name, version, iteration_

    def get_branch_name(self):
        return self.iteration + '/' + self.topic.name + '_v' + str(self.version)


class TopicMerge(collections.namedtuple(
        'TopicMergeT', ('rev', 'SHA', 'description', 'type', 'merge_target'))):
    """ This class represents merge of revision of topic into some branch
    """
    def __new__(cls, revision, merge_sha, description, type_, merge_target):
        return super().__new__(cls, revision, merge_sha, description, type_,
                               merge_target)

    def __str__(self):
        s = '{Merge'
        if self.SHA:
            s += '[' + self.SHA[0:7] + ']'
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
    def parse_headline(cls, headline):
        if cls.headline_regexp is None:
            cls.headline_regexp = re.compile(
                "^Merge branch '((?:[^/]*/)?.*)'(?: into ([^/]*/.*))?$")
        # if branch is merged into master headline doesn't contain "into.." part
        re_result = cls.headline_regexp.search(headline)
        if not re_result:
            re_result = re.search("^Merge branch '((?:[^/]*/)?.*)' into (.*)?$",
                                  headline)
            if not re_result:
                logging.warning('Failed to parse merge headline: ' + headline)
                return None, None, None, None
            else:
                logging.warning('Warning: incorrect branch name: ' +
                                re_result.groups()[1] +
                                '. Which iteration does this branch belong to?')
        branch_name, target = re_result.groups()
        return branch_name, target if target else 'master'

    message_regexp = None

    @classmethod
    def parse_message(cls, message):
        """Returns (headline, type, description)"""
        if not cls.message_regexp:
            cls.message_regexp = re.compile(
                '\A(^.+?$)(?:[\r\n]+^({}|{}|{})$)?(?:[\r\n]+(^.*?))?\Z'.format(
                    DEV_NAME, FIX_NAME, EUF_NAME),
                re.MULTILINE | re.DOTALL)
        result = cls.message_regexp.search(message)
        if result:
            headline, type_, d = result.groups()
            if not type_:
                type_ = EUF_NAME
            return headline, type_, d
        else:
            return None, None, None

    @classmethod
    @cache('branches', 'tags')
    def from_treeish(cls, treeish):
        headline, type_, d = cls.parse_message(commit.get_full_message(treeish))
        if not headline:
            return None
        branch_name, target = cls.parse_headline(headline)
        default_i = iteration.parse_branch_name(target)[0] if target else None
        if not default_i:
            default_i = iteration.get_iteration_by_treeish(treeish)
        revision = TopicRevision.from_branch_name(branch_name,
                                                  commit.get_parent(treeish, 2),
                                                  default_i)
        return TopicMerge(revision, treeish, d, type_, target)

    @classmethod
    @cache('tags', 'branches')
    def get_all_merges_in(cls, treeish):
        """ Returns all (including reverted) in BP..treeish"""
        iter_name = iteration.get_iteration_by_treeish(treeish)
        shas = commit.get_commits_between(iter_name, treeish, True,
                                          ["^Merge branch .*$"])
        return tuple(m for m in (cls.from_treeish(sha) for sha in shas) if m)

    @staticmethod
    def get_reverted_merges_in(treeish, original_only=False):
        iter_name = iteration.get_iteration_by_treeish(treeish)
        result = []
        commits = commit.get_commits_between(iter_name, treeish, False,
                                             ['^Revert "Merge branch .*"$'])
        for sha in commits:
            revert = TopicRevert.from_treeish(sha)
            if revert:
                merge = revert.get_reverted_merge()
                if not (merge.is_fake() and original_only):
                    result.append(merge)
        return result

    @classmethod
    @cache('branches', 'tags')
    def get_effective_merges_in(cls, treeish2, recursive=False, treeish1=None):
        """ Returns all not-reverted merges in treeish1..treeish2
        Treeish1 defaults to BP of iteration treeish2 belongs to
        If some topic was reverted and remerged, returns original merge of this
        topic with revision extracted from original merge
        We cannot return here just not reverted original merges, cause latest
        merges contain actual type/descriptions
        """
        if not treeish1:
            treeish1 = iteration.get_iteration_by_treeish(treeish2)
        assert treeish1
        result = []
        commits = commit.get_commits_between(treeish1, treeish2, True,
                                             ['^Revert "Merge branch .*"$',
                                              "^Merge branch .*$"])
        for sha in commits:
            if commit.get_headline(sha).startswith('Revert "Merge'):
                revert = TopicRevert.from_treeish(sha)
                if revert:
                    for merge in reversed(result):
                        if merge.rev == revert.rev:
                            result.remove(merge)
                            logging.debug('Searching for topics in ' +
                                          treeish1 + '..' + treeish2 +
                                          ' Removing ' + str(merge))
                            break
            else:
                merge = TopicMerge.from_treeish(sha)
                if merge:
                    result.append(merge)
                    logging.debug('Searching for topics in ' +
                                  treeish1 + '..' + treeish2 +
                                  ' Adding ' + str(merge))

        if recursive:
            recursive_result = []
            for m in result:
                for merge2 in m.rev.get_own_effective_merges(True) + (m,):
                    if merge2.is_newest_in(recursive_result):
                        recursive_result.append(merge2)
            return tuple(recursive_result)
        else:
            return tuple(result)

    def merge(self, set_description=None, set_type=None):
        return self.rev.merge(
            set_description if set_description else self.description,
            set_type if set_type else self.type)

    @staticmethod
    def get_merge_message(revision, target, type_=None, description=None):
        result = "Merge branch '" + revision.get_branch_name() + "'"
        if not iteration.is_master(target):
            result += ' into ' + target
        result = result + linesep * 2 + (type_ if type_ else EUF_NAME)
        if description:
            result = result + linesep + description
        return result

    def get_message(self):
        return TopicMerge.get_merge_message(self.rev, self.merge_target,
                                            self.type, self.description)

    def is_fake(self):
        if not self.SHA:
            raise IncompleteMergeObjectError('Checking for fake merge in '
                                             'TopicMerge that has no SHA')
        return self.rev.SHA is None

    def get_original(self):
        if not self.SHA:
            raise IncompleteMergeObjectError(
                'Trying to found original merge of merge w\o SHA')
        if self.rev.SHA:
            return self

        ci = None
        if self.rev.iteration:
            ci = self.rev.iteration
        else:
            if self.merge_target and not iteration.is_master(self.merge_target):
                ci = iteration.get_iteration_by_branch(self.merge_target)
            if not ci:
                ci = iteration.get_iteration_by_sha(self.SHA)
        if not ci:
            raise IncompleteMergeObjectError(
                'Unable to find iteration of merge ' + str(self))

        for sha in commit.get_commits_between(
                ci, self.SHA, True, ["^Merge branch '([^/]+/)?" +
                                     self.rev.topic.name + "(_v[0-9]+)?'.*$"]):
            merge = self.__class__.from_treeish(sha)
            if merge and merge.rev == self.rev and merge.rev.SHA:
                return merge

        return None


class TopicRevert(collections.namedtuple('TopicRevertT', (
        'rev', 'SHA', 'merge_target', 'reverted_SHA'))):
    """ Represents revert of topic revision merge
    """

    def __new__(cls, revision, sha, merge_target, reverted_sha):
        return super().__new__(cls, revision, sha, merge_target, reverted_sha)

    def __str__(self):
        s = '{Revert of merge of ' + str(self.rev)
        if self.merge_target:
            s += ' into ' + self.merge_target
        if self.reverted_SHA:
            s += '. Reverted SHA: ' + self.reverted_SHA
        if self.SHA:
            s += '[' + self.SHA[0:7] + ']'
        s += '}'
        return s

    def revert(self):
        assert self.reverted_SHA
        if commit.get_parent(self.reverted_SHA, 2):
            return commit.revert(self.reverted_SHA, 1)
        else:
            return commit.revert(self.reverted_SHA)

    @classmethod
    @cache('branches', 'tags')
    def from_treeish(cls, treeish):
        headline, sha = cls.parse_message(commit.get_full_message(treeish))
        if not headline:
            return None
        branch_name, target = TopicMerge.parse_headline(headline)
        return TopicRevert(
            TopicRevision.from_branch_name(
                branch_name,
                default_iteration=iteration.get_iteration_by_treeish(treeish)),
            misc.rev_parse(treeish),
            target,
            sha)

    message_regexp = None

    @classmethod
    def parse_message(cls, message):
        """ Parses revert commit message, extracting reverted SHA and headline
        info
        TODO: it's also possible to found commit revert was made relative to
        """
        if cls.message_regexp is None:
            cls.message_regexp = re.compile(
                '\ARevert "(.*?)"[\n\r]+This reverts commit (.*?)[.,].*',
                re.DOTALL)
        result = cls.message_regexp.search(message)
        if result:
            return result.groups()
        else:
            return None, None

    def get_reverted_merge(self):
        if self.reverted_SHA:
            return TopicMerge.from_treeish(self.reverted_SHA)
        else:
            if not self.SHA:
                logging.critical('Trying to get reverted merge w/o SHA')
                return None

        # Suboptimal solution.
        # TODO: implement and use here TopicRevision.get_all_merges_in()
        for m in reversed(self.rev.topic.get_all_merges_in(self.SHA)):
            if m.rev == self.rev:
                return m
