#!/usr/bin/python3


from setuptools import setup


setup(name='gitconflict',
      version='0.1',
      description='Git merge-conflicts checker',
      py_modules=['git_conflict'],
      scripts=['git-conflict'],
      author="Vasily Makarov",
      author_email="einmalfel@gmail.com",
      url="https://github.com/einmalfel/git-aflow",
      install_requires=["gitwrapper"],
      provides=["gitconflict"],
      long_description=open("README.txt").read(),
      )
