#!/usr/bin/python3


from distutils.core import setup


setup(name='conflicts',
      version='0.1',
      description='Git merge-conflicts checker',
      py_modules=['conflicts'],
      scripts=['do_not_conflict'],
      author="Vasily Makarov",
      author_email="einmalfel@gmail.com",
      url="https://github.com/einmalfel/git-aflow",
      long_description="""
Conflicts is a solution to check whether git branches conflict with each other
or not without doing actual merge.
conflict(list_of_heads) will return a tuple
(HEAD1, HEAD2, file_containing_conflicting_changes) describing first found
conflict or None if there are no conflicts at all.
The package also provides do_not_conflict script. It returns 0 if its arguments
are heads which do not conflict with each other, and 1 otherwise.
Both function and script accept arguments in tree-ish form, for instance:
master, 123abcde(SHA), HEAD^^.

Written and tested with Python 3.3 runtime.
"""
      )
