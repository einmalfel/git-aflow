#!/usr/bin/python3


from os import path

from setuptools import setup


with open(path.join(path.abspath(path.dirname(__file__)), 'README.txt')) as f:
    readme_contents = f.read()


setup(name='gitconflict',
      version='0.1',
      description='Git merge-conflicts checker',
      py_modules=['git_conflict'],
      author="Vasily Makarov",
      entry_points={'console_scripts': [
          'git-conflict = git_conflict:test_and_print_first_conflict']},
      author_email="einmalfel@gmail.com",
      url="https://github.com/einmalfel/git-aflow",
      install_requires=["gitwrapper"],
      provides=["gitconflict"],
      long_description=readme_contents,
      )
