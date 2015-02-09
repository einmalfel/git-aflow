#!/usr/bin/python3


"""TODO:

1 Add support for cross-merges
2 Detect binary file conflicts
3 Support non-UTF-8 encodings

"""

import os
import re
import logging
import itertools

from gitwrapper.cached import misc


def _hunk_to_scope(hunk):
    if hunk[1] and hunk[1] != '0':
        start = int(hunk[0])
        return start, start + int(hunk[1])
    else:
        return int(hunk[2]), 1


def _get_scopes(base, head, file):
    return tuple(_hunk_to_scope(h) for h in _get_scopes.hunk_re.findall(
        misc.get_diff(base, head, [file])))
_get_scopes.hunk_re = re.compile(
    '^@@ \-(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$', re.MULTILINE)


def _scopes_differ(scopes1, scopes2):
    for scope1, scope2 in itertools.product(scopes1, scopes2):
        if not (scope1[0] > scope2[1] or scope1[1] < scope2[0]):
            return True
    return False


def get_first_conflict_for_treeish(treeish, others):
    """ Checks whether treeish conflicts with any others. Processes others in
    order they are given and return first encountered conflict in a form of
    tuple (other_treeish, absolute filename). Returns None, None if no
    conflicts found
    """

    treeish_diffs = {}  # caches diffs between treeish and merge bases
                        # values are dicts filename: scopes
    root = misc.get_root_dir()
    for other in others:
        base = misc.get_merge_base([treeish, other])
        if base not in treeish_diffs:
            treeish_diffs[base] = {os.path.join(root, file): None for file in
                                   misc.list_files_differ(base, treeish)}
        changed_in_other = frozenset(os.path.join(root, file) for file in
                                     misc.list_files_differ(base, other))
        for file in treeish_diffs[base].keys() & changed_in_other:
            if treeish_diffs[base][file] is None:
                treeish_diffs[base][file] = _get_scopes(base, treeish, file)
            other_scopes = _get_scopes(base, other, file)
            if _scopes_differ(treeish_diffs[base][file], other_scopes):
                logging.info('Conflict detected between ' + treeish + ' and ' +
                             other + ' in a file ' + file)
                return other, file
    return None, None


def get_first_conflict(heads_list):
    """ Returns tuple describing first found conflict: (HEAD1, HEAD2, filename)
    If no conflicts, returns None
    """

    # bases is a dictionary of merge bases which keys are frozensets of 2 heads
    bases = {frozenset((head1, head2)): misc.get_merge_base([head1, head2])
             for head1, head2 in itertools.combinations(heads_list, 2)}
    logging.info('Bases: ' + os.linesep + str(bases))

    # groups is a dictionary of lists of groups. Each group is a set of head
    # which could be compared together. Keys are merge bases
    groups = dict.fromkeys(frozenset(bases.values()))
    for heads_pair_frozen, base in bases.items():
        if not groups[base]:
            groups[base] = [set(heads_pair_frozen)]
        else:
            for group in groups[base]:
                # AC base is not necessarily D if AB and BC bases are both D
                for head1, head2 in itertools.product(heads_pair_frozen, group):
                    if (not head1 == head2 and
                            not base == bases[frozenset((head1, head2))]):
                        break
                else:  # group is OK to add heads
                    group.update(heads_pair_frozen)
                    break
            else:  # not added to a group
                groups[base].append(set(heads_pair_frozen))
    logging.info('Groups: ' + os.linesep + str(groups))

    root = misc.get_root_dir()
    for base, group_list in groups.items():
        diffs = {}  # dictionary of dictionaries of diffs for current base.
                    # First key is head, second is filename. Diffs are
                    # represented as a list of hunk scopes which are tuples
                    # (first_line, last_line)
        for group in group_list:
            logging.info('Processing group. Base: ' + base + ' Branches: ' +
                         ', '.join(group))
            for head1, head2 in itertools.combinations(group, 2):
                for head in head1, head2:
                    if head not in diffs:
                        logging.info('Reading files changed for head ' + head +
                                     ' relative to base ' + base)
                        diffs[head] = {os.path.join(root, f): None for f in
                                       misc.list_files_differ(base, head)}
                for file in diffs[head1].keys() & diffs[head2].keys():
                    logging.info('File ' + file + ' was changed in both ' +
                                 head1 + ' and ' + head2)
                    for head in head1, head2:
                        if not diffs[head][file]:
                            diffs[head][file] = _get_scopes(base, head, file)
                            logging.debug('File ' + file + ' changes in ' +
                                          head + ' relative to ' + base + ': ' +
                                          str(list(diffs[head][file])))
                    if _scopes_differ(diffs[head1][file], diffs[head2][file]):
                        logging.info('Found conflict in ' + file + ' between ' +
                                     head1 + ' and ' + head2)
                        return head1, head2, file
    return None
