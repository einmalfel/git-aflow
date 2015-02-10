#!/usr/bin/python3


from os import path

from setuptools import setup, find_packages


with open(path.join(path.abspath(path.dirname(__file__)), 'README.txt')) as f:
    readme_contents = f.read()


setup(name='thingitwrapper',
      version='0.1',
      description='Wrapper for git command line tool. For now functionality is '
                  'limited to git commands needed for git-aflow project.',
      packages=find_packages(),
      author="Vasily Makarov",
      license='GNU LGPL 2.1',
      classifiers=['Development Status :: 2 - Pre-Alpha',
                   'Environment :: Console',
                   'Operating System :: POSIX :: Linux',
                   'Programming Language :: Python :: 3 :: Only',
                   'Programming Language :: Python :: 3.2',
                   'Topic :: Software Development :: Version Control',
                   'License :: OSI Approved :: GNU Lesser General Public '
                   'License v2 or later (LGPLv2+)'],
      keywords='git wrapper parser git-aflow',
      author_email="einmalfel@gmail.com",
      url="https://github.com/einmalfel/git-aflow",
      long_description=readme_contents,
      provides=["thingitwrapper"],
      )
