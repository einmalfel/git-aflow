import random
import re
import string
import abc

from gitwrapper import misc, commit, branch
from test_utils import check_aflow


class Fixture:
    class Iteration:
        def __init__(self, name, bp):
            self.branches = dict()
            self.name = name
            self.BP = bp

        @classmethod
        def from_str_list(cls, string_list, prev):
            new_i = cls(
                string_list[0][0],
                prev.branches['master'][-1] if prev else Fixture.InitCommit())
            for string_ in string_list:
                name, colon, *ln = string_
                assert colon == ':'
                if name.isdigit():
                    name = 'master'
                elif name == 'd':
                    name = 'develop'
                elif name == 's':
                    name = 'staging'
                new_i.branches[name] = Fixture.Branch.from_line(name, ln, new_i)
            return new_i

        def actualize(self):
            if isinstance(self.BP, Fixture.InitCommit):
                self.BP.actualize()
                check_aflow('init', self.name)
            else:
                check_aflow('rebase', '-n', self.name)
            for b in 'develop', 'staging', 'master':
                self.branches[b].actualize()

    class Branch:
        def __init__(self, name, iteration_):
            self.commits = []
            self.actualized = False
            self.iteration = iteration_
            self.name = name

        @classmethod
        def from_line(cls, name, string_, iteration_):
            new = cls(name, iteration_)
            while len(string_) >= 3:
                dash, first, second, *string_ = string_
                assert dash == '-'
                commit_ = Fixture.Commit.from_letters(first, second, name)
                if commit_:
                    new.commits.append(commit_)
            return new

        def actualize(self, up_to=None):
            if self.actualized:
                return
            if not self.name == 'master':
                branch_name = self.iteration.name + '/' + self.name
                if not branch.exists(branch_name):
                    branch.create(branch_name, self.iteration.BP.SHA)
            check_aflow('checkout', self.name)
            for c in self.commits:
                if isinstance(c, Fixture.DevelopMergeCommit):
                    self.iteration.branches[c.topic].actualize(c.version)
                    check_aflow('checkout', self.name)
                c.actualize()
                if (isinstance(c, Fixture.RegularCommit) and up_to and
                        c.set_revision[-1] == up_to):
                    return
            self.actualized = True

    class Commit(abc.ABC):
        def __init__(self):
            self.SHA = None

        @staticmethod
        def from_letters(first, second, branch_name):
            if first == second == '-':
                return None
            if first.isalpha() and second.isdigit():
                if first.islower():
                    if branch_name == 'develop':
                        return Fixture.DevelopMergeCommit(first, second)
                    else:
                        return Fixture.MergeCommit(first, second)
                else:
                    return Fixture.RevertCommit(first.lower(), second)
            else:
                change = delete = set_revision = None
                for char in first, second:
                    if char.isalpha():
                        if char.islower():
                            change = char
                        else:
                            delete = char
                    elif char.isdigit():
                        set_revision = branch_name + '_v' + char
                return Fixture.RegularCommit(change, delete, set_revision)

        @abc.abstractclassmethod
        def _commit(self):
            pass

        def actualize(self):
            if not self.SHA:
                self._commit()
                self.SHA = commit.get_current_sha()

    class InitCommit(Commit):
        def _commit(self):
            commit.commit('Initialize', allow_empty=True)

    class RegularCommit(Commit):
        def __init__(self, change_file, delete_file, set_revision):
            super().__init__()
            self.change = change_file
            self.delete = delete_file
            self.set_revision = set_revision

        def _commit(self):
            if self.change:
                with open(self.change, 'w') as f:
                    f.write(''.join(
                        random.choice(string.printable) for _ in range(100)))
                misc.add(self.change)
            if self.delete:
                misc.rm(self.delete)
            commit.commit(
                'change ' + str(self.change) + ' del ' + str(self.delete), True)
            if self.set_revision:
                branch.create(self.set_revision)

    class MergeCommit(Commit):
        def __init__(self, topic, version):
            super().__init__()
            self.topic = topic
            self.version = version

        def _commit(self):
            check_aflow('merge', self.topic + '_v' + self.version)

    class DevelopMergeCommit(MergeCommit):
        def __init__(self, topic, version):
            super().__init__(topic, version)

        def _commit(self):
            check_aflow('checkout', self.topic + '_v' + self.version)
            check_aflow('topic', 'finish')

    class RevertCommit(Commit):
        def __init__(self, topic, version):
            super().__init__()
            self.topic = topic
            self.version = version

        def _commit(self):
            check_aflow('revert', self.topic + '_v' + self.version)

    def __eq__(self, other):
        raise NotImplementedError

    def __init__(self, iteration_list):
        self.iteration_list = iteration_list

    @classmethod
    def from_scheme(cls, scheme):
        """Constructs state object from a 'scheme' string:
        1: - iteration 1 start
        s: d: - staging and develop
        a: - topic a
        a1 - merge of topic A_v1
        A1 - revert of A_v1
        1b - randomly change file b and set revision _v1 head
        1B - delete file b and set revision _v1 head
        Ba, aB - change a, delete b
        a-, aa - change a
        -B, BB - delete B
        """
        iteration_lines = []
        prev = None
        iters = []
        for line in scheme.splitlines():
            if re.search('^\d:.*$', line):
                if iteration_lines:
                    i = Fixture.Iteration.from_str_list(iteration_lines, prev)
                    iters.append(i)
                    prev = i
                    iteration_lines = []
            if line:
                iteration_lines.append(line)
        iters.append(Fixture.Iteration.from_str_list(iteration_lines, prev))
        return cls(iters)

    @classmethod
    def from_repo(cls):
        raise NotImplementedError

    def actualize(self):
        misc.init()
        for i in self.iteration_list:
            i.actualize()
