#!/usr/bin/python3
import os

from fixture import Fixture
import utils
from gitwrapper.cached import misc, commit


class ContinueTests(utils.LocalTest):
    def test_auto_name(self):
        Fixture.from_scheme("""1:
                               d:-a1
                               a:-1a""").actualize()
        misc.checkout('1/develop^2')
        self.assert_aflow_returns_0(
            '1/a_v2 created and checked out. Use "git af topic finish" to '
            'merge new revision of topic into develop',
            'topic', 'continue')

    def test_cross_iteration(self):
        Fixture.from_scheme("""1:-a1
                               s:-a1
                               d:-a1
                               a:-1a
                               2:
                               d:-a2
                               a:-2a""").actualize()
        self.assert_aflow_dies_with(
            'Failed to find merges of b in iterations: 2, 1.',
            'topic', 'continue', 'b')
        self.assert_aflow_returns_0(
            'Please, note that a_v2'
            ' is already present in other iteration(s), so changes you will '
            'make for this revision in current iteration should correspond to '
            'changes made for same revision in other iterations. You may '
            'also use "git af port" to bring commits of some revision from '
            'one iteration to another.' + os.linesep +
            '1/a_v2 created and checked out. Use "git af topic finish" to '
            'merge new revision of topic into develop',
            'topic', 'continue', '1/a')
        misc.checkout('2/staging')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        misc.checkout('master')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        self.assert_aflow_returns_0(None, 'rebase', '-n', '3')
        self.assert_aflow_returns_0(
            '3/a_v3 created and checked out. Use "git af topic finish" to '
            'merge new revision of topic into develop',
            'topic', 'continue', 'a')

    def test_checks(self):
        Fixture.from_scheme("""1:
                               d:-a1
                               a:-1a""").actualize()
        misc.checkout('1/develop')
        self.assert_aflow_dies_with(
            'No topic name was specified, neither HEAD is pointing to '
            'last commit of some topic. Nothing to continue.',
            'topic', 'continue')
        self.assert_aflow_returns_0(
            'Version suffix ignored.' + os.linesep +
            '1/a_v2 created and checked out. Use "git af topic finish" to ' +
            'merge new revision of topic into develop',
            'topic', 'continue', 'a_v1')
        self.assert_aflow_dies_with(
            '1/a_v2 already exists. Use "git af checkout 1/a_v2" to continue '
            'your work on topic',
            'topic', 'continue', 'a')


if __name__ == '__main__':
    utils.run_tests()
