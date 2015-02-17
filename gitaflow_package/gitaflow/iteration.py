"""Iteration management functionality"""

import logging
import collections

from gitaflow.constants import DEVELOP_NAME, STAGING_NAME
from thingitwrapper.cached import tag, branch, misc, commit
from thingitwrapper.grouped_cache import cache


class Iteration(collections.namedtuple('IterationT', ('name',))):
    @cache()
    def __new__(cls, name):
        return super().__new__(cls, name)

    @classmethod
    @cache('branches', 'rags')
    def get_all(cls, sort=False):
        """ Returns tuple of all iterations. If sort==True descendants are
        put after ancestors.
        """
        iters = (t for t in tag.get_list() if cls(t).valid_and_exists())
        if sort:
            iters = misc.sort(iters, reverse=True)
        return tuple(Iteration(i) for i in iters)

    @classmethod
    @cache('branches', 'rags')
    def from_branch_name(cls, branch_name):
        if '/' not in branch_name:
            return None
        new = cls(branch_name.split('/', maxsplit=1)[0])
        return new if new.valid_and_exists() else None

    def name_valid(self):
        return ('/' not in self.name and misc.is_valid_ref_name(self.name) and
                misc.is_valid_ref_name(self.get_develop()) and
                misc.is_valid_ref_name(self.get_staging()))

    def get_develop(self):
        return self.name + '/' + DEVELOP_NAME

    def get_staging(self):
        return self.name + '/' + STAGING_NAME

    def valid_and_exists(self):
        return (self.name_valid() and tag.exists(self.name) and
                branch.exists(self.get_develop()) and
                branch.exists(self.get_staging()))

    def next(self):
        all_iterations = Iteration.get_all(True)
        ind = all_iterations.index(self) + 1
        return all_iterations[ind] if ind < len(all_iterations) else None

    def prev(self):
        all_iterations = Iteration.get_all(True)
        ind = all_iterations.index(self) - 1
        return all_iterations[ind] if ind >= 0 else None

    def get_master_head(self):
        """ Returns last master commit SHA if self is not last iteration,
        otherwise returns 'master'.
        """
        next_ = self.next()
        return misc.rev_parse(next_.name) if next_ else 'master'

    @classmethod
    def get_first(cls):
        return cls.get_all(sort=True)[0]

    @classmethod
    def get_last(cls):
        return cls.get_all(sort=True)[-1]

    @classmethod
    @cache('branches', 'tags')
    def get_by_sha(cls, sha):
        iters_by_sha = {tag.get_sha(i.name): i for i in Iteration.get_all()}
        pos = commit.get_parent(sha, 1)
        while pos:
            if pos in iters_by_sha:
                logging.debug('found last iteration ' + iters_by_sha[pos].name +
                              ' for SHA ' + sha + ' BP: ' + pos)
                return iters_by_sha[pos]
            pos = commit.get_parent(pos, 1)
        logging.info('Cannot get iteration for ' + sha)
        return None

    @classmethod
    @cache('branches', 'tags')
    def get_by_branch(cls, branch_name):
        assert branch.exists(branch_name)
        iteration = cls.from_branch_name(branch_name)
        if iteration:
            return iteration

        # check whether branch points to some iteration
        for t in tag.find_by_target(branch_name):
            i = Iteration(t)
            if i.valid_and_exists():
                return i

        return Iteration.get_by_sha(branch_name)

    @classmethod
    @cache('branches', 'tags')
    def get_by_treeish(cls, treeish):
        if branch.exists(treeish):
            return cls.get_by_branch(treeish)
        else:
            return cls.get_by_sha(treeish)

    @classmethod
    @cache('branches', 'tags')
    def get_current(cls):
        cb = branch.get_current()
        return cls.get_by_branch(cb) if cb else cls.get_by_sha('HEAD')

    @staticmethod
    def is_staging(branch_name):
        if '/' not in branch_name:
            return None
        i_name, staging = branch_name.split('/', maxsplit=1)
        return Iteration(i_name).valid_and_exists() and staging == STAGING_NAME

    @staticmethod
    def is_develop(branch_name):
        if '/' not in branch_name:
            return None
        i_name, staging = branch_name.split('/', maxsplit=1)
        return Iteration(i_name).valid_and_exists() and staging == DEVELOP_NAME
