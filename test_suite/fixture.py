import os
import random
import re
import string
import abc

from gitwrapper.cached import misc, commit, branch, tag
from test_utils import check_aflow


class Fixture:
    class Iteration:
        def __init__(self, name, bp):
            self.branches = dict()
            self.name = name
            self.BP = bp

        def __eq__(self, other):
            return (type(other) == type(self) and
                    other.BP == self.BP and
                    other.name == self.name and
                    other.branches == self.branches)

        def __ne__(self, other):
            return not self.__eq__(other)

        def __str__(self):
            order = 'master', 'staging', 'develop'
            ordered_names = order + tuple(self.branches.keys() - set(order))
            return os.linesep.join(str(self.branches[b]) for b in ordered_names)

        @classmethod
        def from_tag_name(cls, name, prev, next_tag):
            """Everything not merged into develop, staging or master branch
            will be ignored
            """
            bp = prev.branches['master'][-1] if prev else None
            new = cls(name, bp)
            new.branches['master'] = Fixture.Branch.from_sha(
                'master', next_tag if next_tag else 'master', new)
            for b in branch.get_list([name + '/*']):
                branch_name = b.split('/')[1]
                if branch_name not in ('develop', 'staging'):
                    branch_name = branch_name[0]
                new.branches[branch_name] = Fixture.Branch.from_sha(
                    branch_name, b, new)
            return new

        @classmethod
        def from_str_list(cls, string_list, prev):
            if prev:
                new_i = cls(string_list[0][0],
                            prev.branches['master'].commits[-1])
            else:
                new_i = cls(string_list[0][0], Fixture.InitCommit())
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
            for b in 'develop', 'staging':
                if b not in new_i.branches:
                    new_i.branches[b] = Fixture.Branch.from_line(b, '', new_i)
            return new_i

        def topic_create_set_version(self, name, version, sha):
            if name not in self.branches:
                self.branches[name] = Fixture.Branch.from_sha(name, sha, self)
            for c in self.branches[name].commits:
                if c.SHA == sha:
                    c.set_revision = name + '_v' + version

        def actualize(self):
            if isinstance(self.BP, Fixture.InitCommit):
                self.BP.actualize()
            misc.checkout('master')
            tag.create(self.name)
            # create those branches in advance, otherwise aflow wouldn't be
            # able to detect iteration
            branch.create(self.name + '/develop')
            branch.create(self.name + '/staging')
            self.branches['develop'].actualize()
            self.branches['staging'].actualize()
            for b in self.branches:
                self.branches[b].actualize()

    class Branch:
        def __init__(self, name, iteration_):
            self.commits = []
            self.actualized = False
            self.iteration = iteration_
            self.name = name

        def __eq__(self, other):
            return (type(other) == type(self) and
                    other.name == self.name and
                    other.commits == self.commits)

        def __ne__(self, other):
            return not self.__eq__(other)

        def __str__(self):
            if self.name == 'master':
                short_name = self.iteration.name
            elif self.name == 'staging':
                short_name = 's'
            elif self.name == 'develop':
                short_name = 'd'
            else:
                short_name = self.name
            return short_name + ':-' + '-'.join(str(c) for c in self.commits)

        @classmethod
        def from_sha(cls, name, treeish, iteration_):
            new_commits = []
            if name in iteration_.branches:
                branch_ = iteration_.branches[name]
                for c in branch_.commits:
                    if c.SHA == misc.rev_parse(treeish):
                        return branch_
            else:
                branch_ = cls(name, iteration_)
            while (not iteration_.BP or not treeish == iteration_.BP.SHA or
                   (branch_.commits and branch_.commits[-1].SHA == treeish)):
                cmt = Fixture.Commit.from_treeish(treeish)
                if isinstance(cmt, Fixture.InitCommit):
                    iteration_.BP = cmt
                    break
                if name == 'develop':
                    second_parent = commit.get_parent(treeish, 2)
                    if second_parent:
                        iteration_.topic_create_set_version(
                            cmt.topic, cmt.version, second_parent)
                new_commits.insert(0, cmt)
                treeish = commit.get_parent(treeish)
            branch_.commits.extend(new_commits)
            return branch_

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
            if self.name == 'master':
                branch_name = 'master'
            else:
                branch_name = self.iteration.name + '/' + self.name
                if not branch.exists(branch_name):
                    branch.create(branch_name, self.iteration.BP.SHA)
            misc.checkout(branch_name)
            for c in self.commits:
                if isinstance(c, Fixture.DevelopMergeCommit):
                    self.iteration.branches[c.topic].actualize(c.version)
                    misc.checkout(branch_name)
                c.actualize()
                if (isinstance(c, Fixture.RegularCommit) and up_to and
                        c.set_revision and c.set_revision[-1] == up_to):
                    return
            self.actualized = True

    class Commit(abc.ABC):
        __merge_e = re.compile(
            "^Merge branch '\w*/(\w*)_v(\d)'(?: into 1/(\w*))?.*$")
        __commit_e = re.compile("^(?:change (\w*))? ?(?:del (\w*))?$")
        __revert_e = re.compile("^Revert \"Merge branch '\w*/(\w*)_v(\d)'.*\"$")

        def __init__(self):
            self.SHA = None

        @abc.abstractmethod
        def __eq__(self, other):
            pass

        def __ne__(self, other):
            return not self.__eq__(other)

        @abc.abstractmethod
        def __str__(self):
            pass

        @classmethod
        def from_treeish(cls, treeish):
            headline = commit.get_headline(treeish)
            re_result = cls.__merge_e.search(headline)
            if re_result:
                topic_name, version, target = re_result.groups()
                if target == 'develop':
                    result = Fixture.DevelopMergeCommit(topic_name, version)
                else:
                    result = Fixture.MergeCommit(topic_name, version)
            else:
                re_result = cls.__commit_e.search(headline)
                if re_result:
                    change, delete = (
                        None if g == 'None' else g for g in re_result.groups())
                    result = Fixture.RegularCommit(change, delete, None)
                else:
                    re_result = cls.__revert_e.search(headline)
                    if re_result:
                        topic_name, version = re_result.groups()
                        result = Fixture.RevertCommit(topic_name, version)
                    else:
                        result = Fixture.InitCommit()
            result.SHA = misc.rev_parse(treeish)
            return result

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
        def __eq__(self, other):
            return type(other) == type(self)

        def __str__(self):
            return 'Initial commit'

        def _commit(self):
            commit.commit('Initialize', allow_empty=True)

    class RegularCommit(Commit):
        def __init__(self, change_file, delete_file, set_revision):
            super().__init__()
            self.change = change_file
            self.delete = delete_file
            self.set_revision = set_revision

        def __str__(self):
            str_representation = ''
            if self.set_revision:
                str_representation += self.set_revision[-1]
            if self.delete:
                str_representation += self.delete.upper()
            if self.change:
                str_representation += self.change
            while len(str_representation) < 2:
                str_representation += '-'
            return str_representation

        def __eq__(self, other):
            return (type(other) == type(self) and
                    other.change == self.change and
                    other.delete == self.delete and
                    other.set_revision == self.set_revision)

        def _commit(self):
            if self.change:
                with open(self.change, 'w') as f:
                    f.write(''.join(
                        random.choice(string.printable) for _ in range(100)))
                misc.add(self.change)
            if self.delete:
                misc.rm(self.delete.lower())
            commit.commit(
                'change ' + str(self.change) + ' del ' + str(self.delete), True)
            if self.set_revision:
                branch.create(self.set_revision)

    class MergeCommit(Commit):
        def __init__(self, topic, version):
            super().__init__()
            self.topic = topic
            self.version = version

        def __str__(self):
            return self.topic + self.version

        def __eq__(self, other):
            return (type(other) == type(self) and
                    other.topic == self.topic and
                    other.version == self.version)

        def _commit(self):
            check_aflow('merge', self.topic + '_v' + self.version)

    class DevelopMergeCommit(MergeCommit):
        def __init__(self, topic, version):
            super().__init__(topic, version)

        def _commit(self):
            misc.checkout(self.topic + '_v' + self.version)
            check_aflow('topic', 'finish')

    class RevertCommit(Commit):
        def __init__(self, topic, version):
            super().__init__()
            self.topic = topic
            self.version = version

        def __str__(self):
            return self.topic + self.version

        def __eq__(self, other):
            return (type(other) == type(self) and
                    other.topic == self.topic and
                    other.version == self.version)

        def _commit(self):
            check_aflow('revert', self.topic + '_v' + self.version)

    def __init__(self, iteration_list):
        self.iteration_list = iteration_list

    def __eq__(self, other):
        return (type(other) == type(self) and
                self.iteration_list == other.iteration_list)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return os.linesep.join(str(i) for i in self.iteration_list)

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
            line = line.strip()
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
        iterations = []
        tags = misc.sort(tag.get_list())
        prev = None
        next_tag = tags.pop()
        while next_tag:
            current_tag = next_tag
            next_tag = tags.pop() if tags else None
            prev = Fixture.Iteration.from_tag_name(current_tag, prev, next_tag)
            iterations.append(prev)
        return cls(iterations)

    def actualize(self):
        misc.init()
        for i in self.iteration_list:
            i.actualize()
