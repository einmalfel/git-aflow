#!/usr/bin/python3

import os
import unittest

from fixture import Fixture
import utils
from thingitwrapper.cached import commit, misc, branch


class MergeTests(utils.LocalTest):
    def test_dependencies(self):
        Fixture.from_scheme('''1:
                               d:----a1-b1-a2-c1
                               a:-1a----b1-2c
                               b:-1b---------
                               c:----b1-a1-a2-1-''').actualize()

        misc.checkout('1/staging')
        self.assert_aflow_returns_0(None, 'merge', '-a')
        misc.checkout('master')
        self.assert_aflow_returns_0(None, 'merge', '-d', 'c')
        self.assertEqual(Fixture.from_repo(), Fixture.from_scheme(
            '''1:----b1-a1-a2-c1
               s:----a1-b1-a2-c1
               d:----a1-b1-a2-c1
               a:-1a----b1-2c
               b:-1b---------
               c:----b1-a1-a2-1-'''))

    def test_update(self):
        Fixture.from_scheme('''1:
                               s:----a1-b1
                               d:----a1-b1-c1-a2-b2-c2-a3
                               a:-1a----2a-------b2-c2-3a
                               b:-1b----------a2-2b
                               c:-1c----------a2-b2-2c''').actualize()

        misc.checkout('1/staging')
        self.assert_aflow_dies_with(
            'Using default topic source(s): develop' + os.linesep +
            'Merge failed. Topic 1/a_v3 depends on 1/c_v1. Try merge it first '
            'or use "git af merge -d" to merge dependencies automatically',
            'merge', '-u')
        self.assert_aflow_returns_0(None, 'merge', '-d', '-u')
        self.assertEqual(
            Fixture.from_repo(),
            Fixture.from_scheme("""1:-
                                   s:-a1-b1-a2-b2-c1-c2-a3
                                   d:-a1-b1-c1-a2-b2-c2-a3
                                   b:-1b-a1-a2-2b
                                   c:-1c-a1-a2-b1-b2-2c
                                   a:-1a-2a-b1-b2-c1-c2-3a"""))

    def test_exclude_current(self):
        Fixture.from_scheme('''1:
                               d:-a1-------b1
                               b:----a1-1-
                               a:-1a''').actualize()

        # branch c is based on a, so a_v1 should be excluded from merge
        misc.checkout('1/a')
        branch.create('c')
        misc.checkout('c')
        self.assert_aflow_returns_0(
            'Using default topic source(s): develop' + os.linesep +
            '1/b_v1 merged successfully',
            'merge', '-d', 'b')

    def test_description_type(self):
        Fixture.from_scheme('''1:
                               d:-a1
                               a:-1a''').actualize()
        # edit description/type
        misc.checkout('1/staging')
        self.assert_aflow_returns_0(
            None, 'merge', '-e', 'No matter.', '-D', 'a')
        self.assertEqual(commit.get_full_message('HEAD'),
                         """Merge branch '1/a_v1' into 1/staging

DEV
No matter.""")

        # use description/type from sources
        misc.checkout('master')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        self.assertEqual(commit.get_full_message('HEAD'),
                         """Merge branch '1/a_v1'

DEV
No matter.""")

    def test_already_merged(self):
        Fixture.from_scheme('''1:
                               d:-a1-a2
                               a:-1a-2a
                               b:-a1-a2''').actualize()

        misc.checkout('1/b')
        self.assert_aflow_dies_with(
            'Using default topic source(s): develop' + os.linesep +
            'Latest revision of a in sources is 1/a_v2. We already have it '
            'merged in 1/b. Skipping..' + os.linesep +
            'There is nothing to merge.',
            'merge', 'a')
        self.assert_aflow_dies_with(
            'Using default topic source(s): develop' + os.linesep +
            'We already have this version of a_v2 in 1/b. Skipping..' +
            os.linesep + 'There is nothing to merge.',
            'merge', 'a_v2')
        self.assert_aflow_dies_with(
            'Using default topic source(s): develop' + os.linesep +
            'There is nothing to merge.',
            'merge', '-a')

    def test_conflict(self):
        Fixture.from_scheme('''1:
                               d:----b1-c1
                               b:-1b
                               a:-b-
                               c:-1c''').actualize()

        misc.checkout('1/a')
        self.assert_aflow_dies_with(
            'Using default topic source(s): develop' + os.linesep +
            'Merge of 1/b_v1 failed. See conflicted files via "git status", '
            'resolve conflicts, add files to index ("git add") and do '
            '"git commit --no-edit" to finish the merge.' + os.linesep +
            'Alternatively, you may abort failed merge via "git merge --abort"',
            'merge', 'b')
        commit.abort_merge()

        self.assert_aflow_dies_with(
            'Using default topic source(s): develop' + os.linesep +
            'Merge of 1/b_v1 failed. See conflicted files via "git status", '
            'resolve conflicts, add files to index ("git add") and do '
            '"git commit --no-edit" to finish the merge.' + os.linesep +
            'Then call "git af merge [topics]" again to merge remaining '
            'topics. Topics remaining to merge: 1/c_v1' + os.linesep +
            'Alternatively, you may abort failed merge via "git merge --abort"',
            'merge', 'b', 'c')
        commit.abort_merge()

        misc.checkout('1/develop')
        commit.merge('1/a')
        misc.add('b')
        commit.commit()
        misc.checkout('1/staging')
        self.assert_aflow_returns_0(None, 'merge', 'b')
        self.assert_aflow_dies_with(
            'Using default topic source(s): develop' + os.linesep +
            'Merge of 1/a_v1 failed. Something went wrong, did not '
            'expect conflict there (1/staging). Please check carefully what '
            'you are doing. Merge aborted.',
            'merge', 'a')

    def test_checks(self):
        Fixture.from_scheme('''1:
                               a:-a--a-
                               b:-b-''').actualize()

        # detached head
        misc.checkout('1/a^')
        self.assert_aflow_dies_with(
            'Error: detached head state. Please checkout some branch before '
            'proceed', 'merge', 'no_matter')

        # topic description applicable
        misc.checkout('1/a')
        self.assert_aflow_returns_0(None, 'finish')
        misc.checkout('1/b')
        self.assert_aflow_returns_0(None, 'finish')
        misc.checkout('1/staging')
        expected = 'If you are going to specify topic description and/or ' \
                   'type, you should merge one single topic'
        self.assert_aflow_dies_with(expected, 'merge', '-a', '-e', 'no matter')
        self.assert_aflow_dies_with(expected, 'merge', 'a', 'b', '-D')

        # working tree
        self.assert_aflow_returns_0(None, 'continue', 'a')
        os.remove('a')
        self.assert_aflow_dies_with(
            'Error: your working tree is dirty. Please, stash or reset your '
            'changes before proceeding.',
            'merge', 'no_matter')
        branch.reset('HEAD')

        # topic present in sources
        misc.checkout('master')
        self.assert_aflow_dies_with(
            'Using default topic source(s): staging' + os.linesep +
            'Merge failed. No topic a in sources 1/staging',
            'merge', 'a')
        self.assert_aflow_dies_with(
            'Merge failed. No topic a_v2 in sources 1/develop',
            'merge', '-s', 'develop', 'a_v2')

        # is there anything to merge
        self.assert_aflow_dies_with(
            'Using default topic source(s): staging' + os.linesep +
            'There is nothing to merge.',
            'merge', '-a')

        # dependency check
        self.assert_aflow_returns_0(None, 'start', 'c')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        self.assert_aflow_returns_0(None, 'finish')
        misc.checkout('1/staging')
        self.assert_aflow_dies_with(
            'Using default topic source(s): develop' + os.linesep +
            'Merge failed. Topic 1/c_v1 depends on 1/a_v1. Try merge it first '
            'or use "git af merge -d" to merge dependencies automatically',
            'merge', 'c')
        commit.merge('1/a_v2', "Merge branch '1/a_v2' into 1/staging")
        misc.checkout('master')
        self.assert_aflow_dies_with(
            'Using default topic source(s): staging' + os.linesep +
            'Merge failed. We should merge 1/a_v2 along with 1/a_v1, but '
            '1/a_v1 is absent in sources.',
            'merge', 'a')
        misc.checkout('1/staging')
        branch.reset('HEAD^')

        # source exists and belongs to ci
        self.assert_aflow_dies_with(
            'Cannot find branch 1/wrong_source or wrong_source.',
            'merge', '-a', '-s', 'wrong_source')
        misc.checkout('1/staging')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        misc.checkout('master')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        self.assert_aflow_returns_0(None, 'rebase', '-n', '2')
        self.assert_aflow_returns_0(None, 'start', 'wrong_source')
        misc.checkout('1/staging')
        self.assert_aflow_dies_with(
            "Merge sources should belong to current iteration. 2/wrong_source"
            " doesn't.",
            'merge', '-a', '-s', '2/wrong_source')

        # consistency check
        branch.create('1/b_v2')
        misc.checkout('1/b_v2')
        commit.commit('no matter', allow_empty=True)
        misc.checkout('1/develop')
        commit.merge('1/b_v2')
        misc.checkout('1/staging')
        self.assert_aflow_dies_with(None, 'merge', 'no_matter')

        # merge into develop
        misc.checkout('1/develop')
        self.assert_aflow_dies_with(
            'You cannot merge into develop, use git af topic finish instead',
            'merge', 'a')

        # not valid aflow repo
        branch.delete('1/staging')
        self.assert_aflow_dies_with(
            'Error: could not get current iteration, we are probably not in '
            'git-aflow repo.',
            'merge', 'no_matter')


if __name__ == '__main__':
    unittest.main(module='test_merge')
