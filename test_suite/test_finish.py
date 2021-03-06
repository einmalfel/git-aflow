#!/usr/bin/python3

import os
import unittest

from fixture import Fixture
import utils
from thingitwrapper.cached import commit, misc, branch


class FinishTests(utils.LocalTest):
    def test_conflict_with_deps_first(self):
        Fixture.from_scheme("""1:
                               d:-a1-b1-c1-e1
                               a:-1a
                               b:-a1-1b
                               c:-a1----1c
                               e:-a1-------1e
                               """).actualize()
        self.assert_aflow_returns_0(None, 'start', 'f')
        with open('a', 'w') as a:
            a.write('Does not matter')
        misc.add('a')
        commit.commit('No matter')
        # bug isn't reproduced stably, but probably it fails on the first try
        for i in range(0, 5):
            self.assert_aflow_dies_with(
                'Finish failed because of conflicts between current '
                'topic and 1/a_v1 in file a',
                'finish')

    def test_refinish(self):
        Fixture.from_scheme("""1:
                               d:-a1
                               a:-1a""").actualize()

        misc.checkout('1/develop')
        commit.revert('HEAD', parent=1)
        branch.delete('1/a')
        self.assert_aflow_returns_0(None, 'checkout', 'a')
        self.assert_aflow_returns_0(
            'Assuming topic you are finishing is 1/a_v1.' + os.linesep +
            'Taking topic type from previous merge of 1/a_v1.' + os.linesep +
            '1/a_v1 merged into 1/develop successfully.',
            'finish')
        self.assertEqual(Fixture.from_repo(), Fixture.from_scheme("""
            1:
            d:-a1-A1-a1
            a:-1a"""))

    def test_reverts(self):
        Fixture.from_scheme("""1:
                               d:-a1
                               a:-1a
                               b:-a1""").actualize()
        misc.checkout('1/b')
        self.assert_aflow_returns_0(None, 'revert', 'a')
        self.assert_aflow_dies_with(
            "Current topic contains reverts of topics from current iteration "
            "which is forbidden. Please rebase your topic excluding merges you "
            "don't like and try to finish it again.", 'finish')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        self.assert_aflow_returns_0(None, 'revert', 'a')
        self.assert_aflow_dies_with(
            "Current topic contains reverts of topics from current iteration "
            "which is forbidden. Please rebase your topic excluding merges you "
            "don't like and try to finish it again.", 'finish')

    def test_update_for_prev_iter_topic(self):
        Fixture.from_scheme("""1:-a1
                               s:-a1
                               d:-a1
                               a:-1a
                               2:
                               d:-b1
                               b:-1b""").actualize()
        branch.create('2/a_v2', '2')
        misc.checkout('2/a_v2')
        commit.commit('No matter', allow_empty=True)
        self.assert_aflow_returns_0(
            """Taking topic type from previous merge of 1/a_v1.
2/a_v2 merged into 2/develop successfully.
Branch 2/a_v2 deleted.""", 'finish')

    def test_unexpected_conflict(self):
        Fixture.from_scheme("""1:
                               a:-1a""").actualize()
        misc.checkout('1/develop')
        with open('a', 'w') as b:
            b.write('Does not matter')
        misc.add('a')
        commit.commit('No matter')
        misc.checkout('1/a_v1')
        self.assert_aflow_dies_with(
            'Using "End User Feature" as default topic type.' + os.linesep +
            'Merge of 1/a_v1 conflicted unexpectedly. Conflict detector gave '
            'false negative result. 1/develop reset.',
            'finish')

    def test_subdirectory_conflict(self):
        Fixture.from_scheme("""1:
                               a:
                               b:""").actualize()
        misc.checkout('1/a')
        os.mkdir('subdir')
        with open('subdir/a', 'w') as a:
            a.write('A content')
        misc.add('subdir/a')
        commit.commit('No matter a')
        self.assert_aflow_returns_0(None, 'finish')
        misc.checkout('1/b')
        os.mkdir('subdir')
        with open('subdir/a', 'w') as a:
            a.write('B content')
        misc.add('subdir/a')
        commit.commit('No matter b')
        os.chdir('subdir')
        self.assert_aflow_dies_with(
            'Finish failed because of conflicts between current '
            'topic and 1/a_v1 in file subdir/a',
            'finish')
        os.chdir(misc.get_root_dir())
        misc.checkout('1/staging')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        misc.checkout('master')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        self.assert_aflow_returns_0(None, 'rebase', '-n', '2')
        self.assert_aflow_returns_0(None, 'continue', 'a')
        with open('subdir/a', 'w') as a:
            a.write('A new content')
        misc.add('subdir/a')
        commit.commit('No matter a2')
        self.assert_aflow_returns_0(None, 'finish')
        self.assert_aflow_returns_0(None, 'start', 'b')
        misc.rm('subdir', recursively=True)
        commit.commit('delete a')
        self.assert_aflow_dies_with(
            'Finish failed because of conflicts between current '
            'topic and 2/a_v2 in file subdir/a',
            'finish')

    def test_complex(self):
        Fixture.from_scheme("""1:
                               d:-a1-b1-a2-b2-c1
                               a:-1a-a--2A
                               b:-1b-a1-a2-2--c1
                               c:-a1-a2-b1-b2-1c""").actualize()
        self.assert_aflow_returns_0(None, 'checkout', 'b')
        commit.commit('No matter', allow_empty=True)
        self.assert_aflow_returns_0(None, 'finish')
        self.assertEqual(Fixture.from_repo(), Fixture.from_scheme("""
            1:-
            s:-
            d:-a1-b1-a2-b2-c1-b3
            a:-1a-a--2A
            b:-1b-a1-a2-2--c1-3-
            c:-a1-a2-b1-b2-1c"""))

    def test_preserve_description(self):
        Fixture.from_scheme("""1:-a1
                               s:-a1
                               d:-a1
                               a:-1a
                               2:""").actualize()
        branch.create('2/a_v2', '2')
        misc.checkout('2/a_v2')
        commit.commit('No matter', allow_empty=True)
        self.assert_aflow_returns_0(
            """Taking topic type from previous merge of 1/a_v1.
2/a_v2 merged into 2/develop successfully.
Branch 2/a_v2 deleted.""",
            'finish', 'Some description')
        misc.checkout('2/staging')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        misc.checkout('master')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        self.assert_aflow_returns_0(None, 'continue', 'a')
        commit.commit('No matter', allow_empty=True)
        self.assert_aflow_returns_0(None, 'finish', '-D', 'Other description')
        self.assert_aflow_returns_0(None, 'rebase', '-n', '3')
        self.assert_aflow_returns_0(None, 'continue', '3/a')
        commit.commit('No matter', allow_empty=True)
        self.assert_aflow_returns_0(
            """Taking topic description from previous merge of 2/a_v3.
Taking topic type from previous merge of 2/a_v3.
3/a_v3 merged into 3/develop successfully.
Branch 3/a_v3 deleted.""",
            'finish')
        self.assertEqual(
            commit.get_full_message('HEAD'),
            """Merge branch '3/a_v3' into 3/develop

DEV
Other description""")

    def test_auto_version(self):
        Fixture.from_scheme("""1:
                               d:-a1
                               a:-1a-a-""").actualize()
        misc.checkout('1/a')
        self.assert_aflow_returns_0(
            """Using topic version 2 as default.
Taking topic type from previous merge of 1/a_v1.
1/a_v2 merged into 1/develop successfully.
Branch 1/a deleted.""",
            'finish')

        commit.revert('HEAD', 1)
        self.assert_aflow_returns_0(None, 'checkout', 'a')
        self.assert_aflow_returns_0(
            """Using version 2 of already merged revision with same head SHA.
Taking topic type from previous merge of 1/a_v2.
1/a_v2 merged into 1/develop successfully.""",
            'finish', '-n', 'a')

    def test_checks(self):
        Fixture.from_scheme('''1:-b1
                               s:-b1
                               d:-b1
                               a:-a--1a
                               b:-1b
                               2:''').actualize()

        # no finish for develop, master and staging
        for branch_ in 'master', '1/develop', '1/staging':
            misc.checkout(branch_)
            self.assert_aflow_dies_with(
                'Finish failed for branch ' + branch_ + '. Cannot finish '
                'develop, master, staging or release/* branches.',
                'finish')

        # one topic is based on another
        branch.create('1/no_matter', '1/b')
        misc.checkout('1/no_matter')
        commit.commit('No matter', allow_empty=True)
        self.assert_aflow_dies_with(
            'TB of current topic is based on another topic, which is illegal. '
            'You should either merge other topic instead of basing on it or '
            'name topic you are finishing appropriately.',
            'finish')
        misc.checkout('1/develop')
        branch.delete('1/no_matter')

        # unable to determine topic name
        misc.checkout('1/a^')
        self.assert_aflow_dies_with(
            'You are in detached head state now. Please check out topic you '
            'want to finish, e.g. "git af checkout topicA" or specify name '
            '(like git af topic finish -n TopicName if you are going to merge '
            'a commit, not branch',
            'finish')

        # name format
        misc.checkout('1/a')
        self.assert_aflow_dies_with(
            'Error: invalid topic name 1/\_v1. "..", "~", "^", ":", "?", "*", '
            '"[", "@", "", spaces and ASCII control characters are not allowed.'
            ' */release/*, */develop, */staging and master are not allowed too.'
            ' Input something like "fix_issue18" or "do_api_refactoring"',
            'finish', '-n', '\\')

        # may lose untracked files
        with open('b', 'w') as b:
            b.write('Does not matter')
        self.assert_aflow_dies_with(
            'Error: you have some untracked files which you may loose when '
            'switching to 1/develop. Please, delete or commit them. '
            'Here they are: b.',
            'finish')

        # conflict
        misc.add('b')
        commit.commit('no matter')
        self.assert_aflow_dies_with(
            'Finish failed because of conflicts between current topic and '
            '1/b_v1 in file b', 'finish')
        os.remove('b')
        branch.reset('HEAD^')

        # working tree
        os.remove('a')
        self.assert_aflow_dies_with(
            'Error: your working tree is dirty. Please, stash or reset your '
            'changes before proceeding.',
            'finish')
        branch.reset('HEAD')

        # use topic name corresponding to some other iteration
        self.assert_aflow_dies_with(
            'It is not possible to finish in current iteration topic from '
            'other one. Finish failed.',
            'finish', '-n', '2/a_v1')

        # topic based on current one exists
        self.assert_aflow_returns_0(None, 'finish')
        misc.checkout('1/a_v1^')
        self.assert_aflow_dies_with(
            'Finish failed. There is another topic (1/a_v1) in 1/develop which '
            'is based on one you are trying to finish.',
            'finish', '-n', 'no_matter')

        # already finished
        self.assert_aflow_returns_0(None, 'checkout', 'a')
        self.assert_aflow_dies_with(
            '1/develop already contains this revision of a',
            'finish')

        # dependency not merged
        branch.create('dependency', '1')
        misc.checkout('dependency')
        commit.commit('No matter', allow_empty=True)
        self.assert_aflow_returns_0(None, 'continue', 'b')
        commit.merge('dependency')
        self.assert_aflow_dies_with(
            'Finish failed. Your topic depends on 1/dependency_v1 which is '
            'absent in 1/develop',
            'finish')

        # topic isn't based on its iteration
        branch.create('2/a')
        misc.checkout('2/a')
        self.assert_aflow_dies_with(
            'Finish failed. Current topic branch is not based on iteration '
            'start which is not allowed in git-aflow',
            'finish')

        # topic is based on later iteration
        branch.create('1/c', '2')
        misc.checkout('1/c')
        commit.commit('No matter', allow_empty=True)
        self.assert_aflow_dies_with(
            'Current topic branch is based on 2. Use "git af topic port" to '
            'bring it to current iteration and then call '
            '"git af topic finish"',
            'finish')

        # not based on previous revision
        branch.create('1/a_v2', '1')
        misc.checkout('1/a_v2')
        commit.commit('no matter', allow_empty=True)
        self.assert_aflow_dies_with(
            'Cannot finish. There is elder revision of this topic in 1/develop '
            'and SHA you are trying to finish is not based on it. Please '
            'rebase your work on 1/a_v1',
            'finish')

        # empty topic
        self.assert_aflow_returns_0(None, 'start', 'No_matter')
        self.assert_aflow_dies_with(
            'Finish failed. Topic must contain at least one commit.',
            'finish')

        # there already is a later revision of this topic and it isn't based on
        # one being finished now
        misc.checkout('1/develop')
        backup_sha = commit.get_current_sha()
        commit.merge('1/a_v2')
        commit.revert('HEAD', 1, True)
        commit.commit(allow_empty=True)
        commit.revert('HEAD^^', 1, True)
        commit.commit(allow_empty=True)
        branch.delete('1/a_v2')
        self.assert_aflow_returns_0(None, 'checkout', 'a_v1')
        self.assert_aflow_dies_with(
            'Cannot finish. Newer revision 1/a_v2 was merged into 1/develop '
            'and it is not based on revision you are trying to finish.',
            'finish')
        misc.checkout('1/develop')
        branch.reset(backup_sha)

        # same revision in develop has different SHA
        commit.revert('HEAD', 1, True)
        commit.commit(allow_empty=True)
        self.assert_aflow_returns_0(None, 'checkout', 'No_matter')
        commit.commit('No matter', allow_empty=True)
        self.assert_aflow_dies_with(
            '1/a_v1 was already merged in 1/develop with different head SHA. '
            'Finish failed.',
            'finish', '-n', 'a_v1')
        branch.reset(backup_sha)

        # finish _vN while there is no _v(N-1)
        self.assert_aflow_returns_0(None, 'continue', 'a')
        commit.commit('no matter', True)
        self.assert_aflow_dies_with(
            'Wrong topic version specified. Latest revision has version == 1. '
            'Increment version by 1',
            'finish', '-n', 'a_v3')

        # finish _vN while there is no _v(N-1) in current iteration
        misc.checkout('2/develop')
        self.assert_aflow_returns_0(None, 'start', 'No_matter')
        commit.commit('no matter', True)
        self.assert_aflow_dies_with(
            'You should finish version 1 before finishing 2/a_v2',
            'finish', '-n', 'a_v2')


if __name__ == '__main__':
    unittest.main(module='test_finish')
