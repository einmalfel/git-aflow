#!/usr/bin/python3


"""
TODO: Importing gitaflow there may be unsafe, setup.py should not fail with
ImportError trying to import module dependencies
"""

from distutils.core import setup

import gitaflow


setup(name='gitaflow',
      version=gitaflow.VERSION,
      description='Implementation of git branching model, \
alternative to git-flow',
      packages=['gitaflow'],
      scripts=['git-af'],
      maintainer="Vasily Makarov",
      maintainer_email="einmalfel@gmail.com",
      url="https://github.com/einmalfel/git-aflow",
      long_description=open("README.txt").read(),
      install_requires=["conflicts", "gitwrapper"],
      )
