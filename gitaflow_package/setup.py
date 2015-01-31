#!/usr/bin/python3


"""
TODO: Importing gitaflow there may be unsafe, setup.py should not fail with
ImportError trying to import module dependencies
"""

from os import path

from setuptools import setup


with open(path.join(path.abspath(path.dirname(__file__)), 'README.txt')) as f:
    readme_contents = f.read()


setup(name='gitaflow',
      version='0.1',
      description='Implementation of git branching model, \
alternative to git-flow',
      packages=['gitaflow'],
      scripts=['git-af'],
      maintainer="Vasily Makarov",
      maintainer_email="einmalfel@gmail.com",
      url="https://github.com/einmalfel/git-aflow",
      long_description=readme_contents,
      install_requires=["gitconflict", "gitwrapper"],
      )
