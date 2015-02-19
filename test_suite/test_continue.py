#!/usr/bin/python3

import os
import unittest

from fixture import Fixture
import utils
from thingitwrapper.cached import misc, commit


class ContinueTests(utils.LocalTest):
    def test_unfinish(self):
        Fixture.from_scheme("""1:
                               s:-a1
                               d:-a1-e1-b1-c1-B1-b1-B1-b1
                               a:-1a
                               b:-a1-e1-1b
                               c:----------1c
                               e:----1e""").actualize()
        self.assert_aflow_dies_with(
            "1/a_v1 was previously merged in 1/staging, so it's impossible to "
            "unfinish it.", 'continue', '-u', 'a')
        dev_head = misc.rev_parse('1/develop')
        self.assert_aflow_dies_with(
            'Failed to continue 1/e_v1. It is merged in 1/b_v1 which was later '
            'merged in 1/develop. 1/develop reset back to ' + dev_head + '.',
            'continue', '-u', 'e')
        self.assert_aflow_returns_0(
            '1/b_v1 created and checked out. Use "git af topic finish" to '
            'merge new revision of topic into develop', 'continue', '-u', 'b')
        self.assert_aflow_returns_0(
            """Using "End User Feature" as default topic type.
1/b_v1 merged into 1/develop successfully.
Branch 1/b_v1 deleted.""",
            'finish')
        self.assertEqual(Fixture.from_repo(), Fixture.from_scheme("""
            1:-
            s:-a1
            d:-a1-e1-c1-b1
            c:-1c
            e:-1e
            a:-1a
            b:-a1-e1-1b"""))

    def test_auto_name(self):
        Fixture.from_scheme("""1:
                               d:-a1
                               a:-1a""").actualize()
        misc.checkout('1/develop^2')
        self.assert_aflow_returns_0(
            '1/a_v2 created and checked out. Use "git af topic finish" to '
            'merge new revision of topic into develop',
            'continue')

    def test_cross_iteration(self):
        Fixture.from_scheme("""1:-a1
                               s:-a1
                               d:-a1
                               a:-1a
                               2:""").actualize()
        misc.checkout('2/develop')
        self.assert_aflow_returns_0(
            '2/a_v2 created and checked out. Use "git af topic finish" to '
            'merge new revision of topic into develop', 'continue', 'a')
        commit.commit('No matter', allow_empty=True)
        self.assert_aflow_returns_0(None, 'finish')
        self.assert_aflow_dies_with(
            'Failed to find merges of b in 2 and previous iterations.',
            'continue', 'b')
        self.assert_aflow_returns_0(
            'Please, note that a_v2'
            ' is already present in other iteration(s), so changes you will '
            'make for this revision in current iteration should correspond to '
            'changes made for same revision in other iterations. You may '
            'also use "git af port" to bring commits of some revision from '
            'one iteration to another.' + os.linesep +
            '1/a_v2 created and checked out. Use "git af topic finish" to '
            'merge new revision of topic into develop',
            'continue', '1/a')
        misc.checkout('2/staging')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        misc.checkout('master')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        self.assert_aflow_returns_0(None, 'rebase', '-n', '3')
        self.assert_aflow_returns_0(
            '3/a_v3 created and checked out. Use "git af topic finish" to '
            'merge new revision of topic into develop',
            'continue', 'a')
        commit.commit('No matter', allow_empty=True)
        self.assert_aflow_returns_0(None, 'finish')
        self.assertEqual(Fixture.from_repo(), Fixture.from_scheme("""
            1:-a1
            s:-a1
            d:-a1
            a:-1a
            2:-a2
            s:-a2
            d:-a2
            a:-2-
            3:
            d:-a3
            a:-3-"""))

    def test_checks(self):
        Fixture.from_scheme("""1:
                               d:-a1
                               a:-1a""").actualize()
        misc.checkout('1/develop')
        self.assert_aflow_dies_with(
            'No topic name was specified, neither HEAD is pointing to '
            'last commit of some topic. Nothing to continue.',
            'continue')
        self.assert_aflow_returns_0(
            'Version suffix ignored.' + os.linesep +
            '1/a_v2 created and checked out. Use "git af topic finish" to ' +
            'merge new revision of topic into develop',
            'continue', 'a_v1')
        self.assert_aflow_dies_with(
            '1/a_v2 already exists. Use "git af checkout 1/a_v2" to continue '
            'your work on topic',
            'continue', 'a')


if __name__ == '__main__':
    unittest.main(module='test_continue')
