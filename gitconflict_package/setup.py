#!/usr/bin/python3


from os import path

from setuptools import setup


with open(path.join(path.abspath(path.dirname(__file__)), 'README.txt')) as f:
    readme_contents = f.read()


setup(name='gitconflict',
      version='0.1',
      description='Git merge-conflicts checker',
      py_modules=['git_conflict'],
      classifiers=['Development Status :: 2 - Pre-Alpha',
                   'Environment :: Console',
                   'Operating System :: POSIX :: Linux',
                   'Programming Language :: Python :: 3 :: Only',
                   'Programming Language :: Python :: 3.2',
                   'Topic :: Software Development :: Version Control',
                   'License :: OSI Approved :: GNU Lesser General Public '
                   'License v2 or later (LGPLv2+)'],
      author="Vasily Makarov",
      entry_points={'console_scripts': [
          'git-conflict = git_conflict:test_and_print_first_conflict']},
      keywords='git merge conflict detector git-aflow',
      author_email="einmalfel@gmail.com",
      url="https://github.com/einmalfel/git-aflow",
      install_requires=["gitwrapper"],
      provides=["gitconflict"],
      long_description=readme_contents,
      )
