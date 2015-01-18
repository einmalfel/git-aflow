#!/usr/bin/python3

import unittest

from fixture import Fixture
from gitwrapper import commit
import utils
from gitwrapper.cached import misc


class ListTests(utils.LocalTest):
    def test_filter(self):
        Fixture.from_scheme("""1:
                               d:-a1
                               a:-1a""").actualize()
        self.assert_aflow_returns_0(None, 'start', 'refactoring')
        commit.commit('No matter1', allow_empty=True)
        self.assert_aflow_returns_0(None, 'finish', '-D', 'Blah blah.')
        self.assert_aflow_returns_0(None, 'start', 'fix')
        commit.commit('No matter2', allow_empty=True)
        self.assert_aflow_returns_0(
            None, 'finish', '-F',
            'Very long description very long description very long description')
        self.assert_aflow_returns_0("""\
Using default topic source(s): develop
1/develop-----------Type |Ver| Description--------------------------------------
fix                  FIX | 1 | Very long description very long description ve...
refactoring          DEV | 1 | Blah blah.""", 'list', '-FD')
        self.assert_aflow_returns_0("""\
Using default topic source(s): develop
1/develop-----------Type |Ver| Description--------------------------------------
refactoring          DEV | 1 | Blah blah.
a                    EUF | 1 | N/A""", 'list', '-D', '--EUF')

    def test_sources(self):
        Fixture.from_scheme("""1:-a1
                               s:-a1
                               d:-a1
                               a:-1a
                               2:
                               d:-a2
                               a:-2a""").actualize()
        self.assert_aflow_returns_0("""\
master--------------Type |Ver| Description--------------------------------------
2/staging-----------Type |Ver| Description--------------------------------------
2/develop-----------Type |Ver| Description--------------------------------------
a                    EUF | 2 | N/A""", 'list', '-a')
        misc.checkout('2/staging')
        self.assert_aflow_returns_0(None, 'merge', 'a')
        self.assert_aflow_returns_0("""\
Using default topic source(s): develop
2/develop-----------Type |Ver| Description--------------------------------------
a                    EUF | 2 | N/A""", 'list')
        self.assert_aflow_returns_0("""\
master--------------Type |Ver| Description--------------------------------------
1/develop-----------Type |Ver| Description--------------------------------------
a                    EUF | 1 | N/A""", 'list', 'master', '1/develop')

if __name__ == '__main__':
    unittest.main(module='test_list')
