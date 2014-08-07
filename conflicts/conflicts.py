#!/usr/bin/python3


"""TODO:

1 Add support for cross-merges
2 Detect binary file conflicts
3 Use more regexps for parsing
4 Support non-UTF-8 encodings
5 Speed up parsing by grepping git output

"""


import os
import re
import subprocess
import sys


init()


def env_is_set(name):
    return 1 if name in os.environ and os.environ[name] == '1' else 0


def dprint(string):
    if dprint.enable:
        print(string)
dprint.enable = env_is_set("DEBUG")


def vprint(string):
    if vprint.enable:
        print(string)
vprint.enable = env_is_set("VERBOSE")


def mix_name(branch1, branch2):
    return min(branch1, branch2) + '|' + max(branch1, branch2)


def unmix_name(name):
    return [name[:name.index('|')], name[name.index('|') + 1:]]


def launch_and_get_stdout(command_and_args):
    result = subprocess.check_output(command_and_args).decode()[:-1]
    vprint('calling ' + ' '.join(command_and_args) + '. Result:\n' + result)
    return result


def git_base(heads):
    return launch_and_get_stdout(["git", "merge-base", "--octopus"] + heads)


def git_diff(from_treeish, to_treeish):
    return launch_and_get_stdout(["git", "diff", from_treeish,
                                  to_treeish, '--'])


def init():
    global regex
    regex = re.compile('^@@ -\S+ +\S+ @@.*$')


def get_first_conflict(heads_list):
    """ Returns tuple describing first found conflict: (HEAD1, HEAD2, filename)
    If no conflicts, returns None
    """
    global regex
    bases = {}
    groups = []

    for head1 in heads_list:
        for head2 in heads_list[heads_list.index(head1) + 1:]:
            bases[mix_name(head1, head2)] = git_base([head1, head2])

    for mix in list(bases.keys()):
        added_to_some_group = 0
        for group in groups:
            if group[0] == bases[mix]:
                added_to_some_group = 1
                for head1 in group[1:]:
                    for head2 in unmix_name(mix):
                        if not head1 == head2:
                            if not group[0] == bases[mix_name(head1, head2)]:
                                added_to_some_group = 0
            if added_to_some_group:
                group += (set(unmix_name(mix)) - set(group))
                break
        if not added_to_some_group:
            groups.append([bases[mix]] + unmix_name(mix))

    groups.sort(key=lambda group: group[0])

    dprint("groups:")
    dprint(groups)

    prev_group = [0]
    for group in groups:
        dprint('processing group. Base: ' + group[0] +
              ' Branches: ' + ', '.join(group[1:]))
        if not prev_group[0] == group[0]:
            diffs = {}
        prev_group = group
        diffs_to_add = set(group[1:]) - set(diffs.keys())

        for head in diffs_to_add:
            dprint("reading diff for branch " + head)
            diffs[head] = {}
            for line in git_diff(group[0], head).split('\n'):
                if 'diff --git a/' in line:
                    filename = line.split('/')[-1]
                    diffs[head][filename] = []
                    dprint("processing file " + filename)
                if regex.match(line):
                    vprint('processing hunk ' + line)
                    minus, plus = [part[1:] for part in line.split(' ')[1:3]]
                    lines_removed = int(minus.split(',')[-1])\
                            if ',' in minus else 0 if minus == '0' else 1
                    if lines_removed:
                        hunk_scope = minus
                        lines_changed = int(lines_removed)
                    else:
                        hunk_scope = plus
                        lines_changed = 1
                    first_line = int(hunk_scope.split(',')[0])
                    last_line = first_line + lines_changed
                    diffs[head][filename] += [(first_line, last_line)]
                    vprint('hunk scope is: ' + str(first_line) + '-' +
                           str(last_line))

        comp_with = group[1:]
        for head in group[1:]:
            comp_with.remove(head)
            dprint("comparing " + head + " with " + ', '.join(comp_with))
            for filename in diffs[head].keys():
                for head_to_comp in comp_with:
                    if filename not in diffs[head_to_comp].keys():
                        continue
                    vprint("comparing changes to " + filename + " branch1: " +
                           head + " (" + str(diffs[head][filename]) +
                           ") branch2: " + head_to_comp +
                           " (" + str(diffs[head_to_comp][filename]) + ")")
                    for comp_first, comp_last in diffs[head_to_comp][filename]:
                        for first, last in diffs[head][filename]:
                            if not (comp_last < first or comp_first > last):
                                return (head, head_to_comp, filename)
    return None
