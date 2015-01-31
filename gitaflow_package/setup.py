#!/usr/bin/python3


"""
TODO: Importing gitaflow there may be unsafe, setup.py should not fail with
ImportError trying to import module dependencies
"""

from distutils.core import setup


setup(name='gitaflow',
      version='0.1',
      description='Implementation of git branching model, \
alternative to git-flow',
      packages=['gitaflow'],
      scripts=['git-af'],
      maintainer="Vasily Makarov",
      maintainer_email="einmalfel@gmail.com",
      url="https://github.com/einmalfel/git-aflow",
      long_description=open("README.txt").read(),
      install_requires=["gitconflict", "gitwrapper"],
      )
