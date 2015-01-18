#!/usr/bin/python3

import unittest

from fixture import Fixture
import utils
from gitwrapper.cached import misc


class StartTests(utils.LocalTest):
    def test_success(self):
        Fixture.from_scheme("""1:
                               a:""").actualize()
        self.assert_aflow_returns_0(
            'Topic a1 created. You are in 1/a1 branch',
            'start', 'a1')

    def test_checks(self):
        Fixture.from_scheme("""1:-a1
                               s:-a1
                               d:-a1
                               a:-1a
                               2:
                               b:""").actualize()
        misc.checkout('2/develop')
        self.assert_aflow_dies_with(
            'Error: invalid topic name 2/\ / @. "..", "~", "^", ":", "?", "*", '
            '"[", "@", "", spaces and ASCII control characters are not allowed.'
            ' */release/*, */develop, */staging and master are not allowed too.'
            ' Input something like "fix_issue18" or "do_api_refactoring"',
            'start', '\ / @')
        self.assert_aflow_dies_with(
            'Cannot start topic, it already has a branch(2/b) in current '
            'iteration(2).',
            'start', 'b')
        self.assert_aflow_dies_with(None, 'start', 'a')


if __name__ == '__main__':
    unittest.main(module='test_start')
