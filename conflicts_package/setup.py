#!/usr/bin/python3


from distutils.core import setup


setup(name='conflicts',
      version='0.1',
      description='Git merge-conflicts checker',
      py_modules=['conflicts'],
      scripts=['git-conflict'],
      author="Vasily Makarov",
      author_email="einmalfel@gmail.com",
      url="https://github.com/einmalfel/git-aflow",
      install_requires=["gitwrapper"],
      provides=["conflicts"],
      long_description=open("README.txt").read(),
      )
