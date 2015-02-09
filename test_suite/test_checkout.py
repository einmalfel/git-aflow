#!/usr/bin/python3

import os
import unittest

from fixture import Fixture
import utils
from gitwrapper.cached import misc, branch


class CheckoutTests(utils.LocalTest):
    def test_existing_branch(self):
        Fixture.from_scheme("""1:
                               a:-1a-2a""").actualize()
        self.assert_aflow_returns_0('1/a_v1 checked out.',
                                    'checkout', '1/a_v1')
        branch.delete('1/a')
        self.assert_aflow_returns_0('1/develop checked out.',
                                    'checkout', 'develop')
        self.assert_aflow_returns_0('1/a_v2 checked out.',
                                    'checkout', 'a')
        self.assert_aflow_returns_0('1/a_v1 checked out.',
                                    'checkout', 'a_v1')

    def test_finished_topic(self):
        Fixture.from_scheme("""1:
                               d:-a1-a2
                               a:-1a-2a""").actualize()
        sha_a1 = misc.rev_parse('1/a^')
        sha_a2 = misc.rev_parse('1/a')
        misc.checkout('1/develop')
        branch.delete('1/a')
        self.assert_aflow_returns_0(
            sha_a1 + ' checked out. You are in "detached HEAD" state now.',
            'checkout', 'a_v1')
        self.assert_aflow_returns_0(
            sha_a2 + ' checked out. You are in "detached HEAD" state now.',
            'checkout', 'a')

    def test_cross_iteration(self):
        Fixture.from_scheme("""1:-a1
                               s:-a1
                               d:-a1
                               a:-1a
                               2:
                               a:-2a""").actualize()
        branch.delete('1/a')
        self.assert_aflow_returns_0(
            'Iteration switched from 2 to 1' + os.linesep +
            misc.rev_parse('1/develop^2') +
            ' checked out. You are in "detached HEAD" state now.',
            'checkout', '1/a')
        branch.delete('2/a')
        self.assert_aflow_returns_0(
            """Iteration switched from 1 to 2
2/a_v2 checked out.""",
            'checkout', '2/a')

    def test_checks(self):
        Fixture.from_scheme("""1:
                               a:-1a""").actualize()
        self.assert_aflow_dies_with(
            'Failed to found b in iteration 1.',
            'checkout', 'b')
        misc.checkout('1/a')
        os.remove('a')
        self.assert_aflow_dies_with(
            'Error: your working tree is dirty. Please, stash or reset your '
            'changes before proceeding.',
            'checkout', 'develop')


if __name__ == '__main__':
    unittest.main(module='test_checkout')
