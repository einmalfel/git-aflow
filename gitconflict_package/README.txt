Conflicts is a solution to check whether git branches conflict with each other or not without doing actual merge.

get_first_conflict(list_of_heads) will return a tuple (HEAD1, HEAD2, file_containing_conflicting_changes) describing first found or None if there are no conflicts at all.
The package also provides "git-conflict" script.
Run it as "git conflict HEAD1 HEAD2...". It returns 1 if its arguments are heads which do not conflict with each other, and 0 otherwise.
Both function and script accept arguments in tree-ish form, for instance: master, 123abcde(SHA), HEAD^^.

Written and tested with Python 3.2 runtime.
