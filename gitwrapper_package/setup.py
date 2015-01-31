#!/usr/bin/python3


from os import path

from setuptools import setup, find_packages


with open(path.join(path.abspath(path.dirname(__file__)), 'README.txt')) as f:
    readme_contents = f.read()


setup(name='gitwrapper',
      version='0.1',
      description='Wrapper for git command line tool. For now functionality is '
                  'limited to git commands needed for git-aflow project.',
      packages=find_packages(),
      author="Vasily Makarov",
      author_email="einmalfel@gmail.com",
      url="https://github.com/einmalfel/git-aflow",
      long_description=readme_contents,
      provides=["gitwrapper"],
      )
