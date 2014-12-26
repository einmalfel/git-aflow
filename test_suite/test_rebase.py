#!/usr/bin/python3

import unittest
from fixture import Fixture

import utils
from gitwrapper.cached import misc, commit


class RebaseTests(utils.LocalTest):
    def test_check(self):
        misc.init()
        commit.commit('initialize', allow_empty=True)
        self.assert_aflow_returns_0(None, 'init', 'iteration1')
        self.assert_aflow_dies_with(
            'There is already an iteration iteration1 started from the top of '
            'master branch',
            'rebase', '-n', 'iteration2')

    def test_success(self):
        Fixture.from_scheme("""1:-a1
                               s:-a1
                               d:-a1
                               a:-1a""").actualize()
        self.assert_aflow_returns_0(
            'Iteration 2 created successfully',
            'rebase', '-n', '2')
        self.assertEqual(Fixture.from_repo(), Fixture.from_scheme("""
            1:-a1
            s:-a1
            d:-a1
            a:-1a
            2:"""))


if __name__ == '__main__':
    unittest.main(module='test_rebase')
