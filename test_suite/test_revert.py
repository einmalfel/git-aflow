#!/usr/bin/python3

import unittest

from fixture import Fixture
from gitwrapper import branch
import utils
from gitwrapper.cached import misc, commit


class RevertTests(utils.LocalTest):
    def test_fake_merge(self):
        Fixture.from_scheme("""1:
                               s:-a1
                               d:-a1
                               a:-1a""").actualize()
        misc.checkout('1/staging')
        self.assert_aflow_returns_0('1/a_v1 reverted successfully.',
                                    'revert', 'a')
        self.assert_aflow_returns_0("""Using default topic source(s): develop
1/a_v1 merged successfully""", 'merge', 'a')
        self.assert_aflow_returns_0('1/a_v1 reverted successfully.',
                                    'revert', 'a')
        self.assertEqual(Fixture.from_repo(), Fixture.from_scheme("""
            1:-
            s:-a1-A1-a1-A1
            d:-a1
            a:-1a"""))

    def test_versions(self):
        Fixture.from_scheme("""1:
                               d:-a1-b1-a2-c1-b2-a3
                               a:-1a-b1-2a-c1-b2-3a
                               b:-a1-1b-a2-c1-2b
                               c:-a1-b1-a2-1c""").actualize()
        misc.checkout('1/develop')
        self.assert_aflow_returns_0("""1/a_v3 reverted successfully.
1/b_v2 reverted successfully.
1/c_v1 reverted successfully.
1/a_v2 reverted successfully.""", 'revert', 'a_v2', '-d')
        self.assertEqual(Fixture.from_repo(), Fixture.from_scheme("""
            1:-
            s:-
            d:-a1-b1-a2-c1-b2-a3-A3-B2-C1-A2
            b:-a1-1b-a2-c1-2b
            a:-1a-b1-2a-c1-b2-3a
            c:-a1-b1-a2-1c"""))

    def test_dependents(self):
        Fixture.from_scheme("""1:
                               d:-a1-b1-c1
                               a:-1a
                               b:-a1-1b
                               c:-a1-b1-1c""").actualize()
        misc.checkout('1/develop')
        self.assert_aflow_dies_with(
            'Unable to revert 1/a_v1 since 1/c_v1 depends on it. '
            'Revert it first or use "git af revert -d" revert dependent '
            'topics automatically.', 'revert', 'a')
        self.assert_aflow_returns_0("""1/c_v1 reverted successfully.
1/b_v1 reverted successfully.
1/a_v1 reverted successfully.""", 'revert', 'a', '-d')
        self.assertEqual(Fixture.from_repo(), Fixture.from_scheme("""
            1:-
            d:-a1-b1-c1-C1-B1-A1
            b:-a1-1b
            a:-1a
            c:-a1-b1-1c"""))
        branch.reset('HEAD^^^')
        self.assert_aflow_returns_0("""1/c_v1 reverted successfully.
1/b_v1 reverted successfully.""", 'revert', 'b', 'c')
        self.assertEqual(Fixture.from_repo(), Fixture.from_scheme("""
            1:-
            d:-a1-b1-c1-C1-B1
            b:-a1-1b
            a:-1a
            c:-a1-b1-1c"""))

    def test_upstream(self):
        Fixture.from_scheme("""1:-a1
                               s:-a1
                               d:-a1
                               a:-1a
                               2:-a2
                               s:-a2
                               d:-a2
                               a:-2a""").actualize()
        misc.checkout('1/staging')
        self.assert_aflow_dies_with(
            'Error: 1/a_v1 is merged in master. In git-aflow you cannot revert '
            'a topic until it is reverted from the upstream branch.',
            'revert', 'a')
        misc.checkout('1/develop')
        self.assert_aflow_dies_with(
            'Error: 1/a_v1 is merged in 1/staging. In git-aflow you cannot '
            'revert a topic until it is reverted from the upstream branch.',
            'revert', 'a')
        misc.checkout('2/staging')
        self.assert_aflow_dies_with(
            'Error: 2/a_v2 is merged in master. In git-aflow you cannot revert '
            'a topic until it is reverted from the upstream branch.',
            'revert', 'a')
        self.assert_aflow_returns_0(None, 'start', 'integration')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        self.assert_aflow_returns_0('2/a_v2 reverted successfully.',
                                    'revert', 'a')

    def test_unexpected_conflict(self):
        Fixture.from_scheme("""1:
                               d:-a1
                               a:-1a""").actualize()
        misc.checkout('1/develop')
        with open('a', 'w') as b:
            b.write('Does not matter')
        misc.add('a')
        commit.commit('No matter')
        self.assert_aflow_dies_with('Revert failed unexpectedly, aborting..',
                                    'revert', 'a')

    def test_checks(self):
        Fixture.from_scheme("""1:
                               d:-a1
                               a:-1a""").actualize()
        misc.checkout('1/develop')
        self.assert_aflow_dies_with('Error: topic a specified more than once',
                                    'revert', 'a', 'a_v1')
        self.assert_aflow_dies_with("Didn't found non-reverted merges of a_v2 "
                                    "in 1/develop", 'revert', 'a_v2')
        self.assert_aflow_dies_with("Didn't found non-reverted merges of b in "
                                    "1/develop", 'revert', 'b')


if __name__ == '__main__':
    unittest.main(module='test_revert')
