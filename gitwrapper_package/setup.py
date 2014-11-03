#!/usr/bin/python3


from distutils.core import setup


setup(name='gitwrapper',
      version='0.1',
      description='Wrapper for git command line tool. For now functionality is '
                  'limited to git commands needed for git-aflow project.',
      packages=['gitwrapper'],
      author="Vasily Makarov",
      author_email="einmalfel@gmail.com",
      url="https://github.com/einmalfel/git-aflow",
      long_description=open("README.txt").read(),
      provides=["gitwrapper"],
      )
