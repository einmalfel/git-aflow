#!/usr/bin/python3


from distutils.core import setup
import gitaflow

setup(name='gitaflow',
      version=gitaflow.VERSION,
      description='Implementation of git branching model, alternative to git-flow',
      packages=['gitaflow', 'gitwrapper'],
      scripts=['git-af'],
      maintainer="Vasily Makarov",
      maintainer_email="einmalfel@gmail.com",
      url="https://github.com/einmalfel/git-aflow",
      long_description=open("README.txt", "r").read(),
      install_requires=["conflicts"],
      )
