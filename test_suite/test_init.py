#!/usr/bin/python3

import utils
from gitwrapper.cached import misc, branch, commit


class InitTests(utils.LocalTest):
    def test_check(self):
        misc.init()
        commit.commit('initialize', allow_empty=True)
        branch.create('iteration1/staging')
        self.assert_aflow_dies_with(
            'Cannot start iteration, branch iteration1/staging exists',
            'init', 'iteration1')
        branch.delete('iteration1/staging')
        self.assert_aflow_returns_0(None, 'init', 'iteration1')
        self.assert_aflow_dies_with(
            'There is a git-aflow repo already, aborting',
            'init', 'iteration1')

    def test_success(self):
        misc.init()
        commit.commit('initialize', allow_empty=True)
        initial = commit.get_current_sha()
        self.assert_aflow_returns_0(
            """Iteration iteration1 created successfully
Git-aflow initialized successfully""",
            'init', 'iteration1')
        self.assertEqual(initial, misc.rev_parse('iteration1'))
        self.assertEqual(initial, misc.rev_parse('iteration1/develop'))
        self.assertEqual(initial, misc.rev_parse('iteration1/staging'))


if __name__ == '__main__':
    utils.run_tests()
