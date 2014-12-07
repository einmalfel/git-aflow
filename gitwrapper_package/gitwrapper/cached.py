"""Use this module to enable git wrapper caching. E.g. use
'from gitwrapper.cached import branch' instead of
'from gitwrapper import branch'
Gitwrapper will cache results of git commands run in CWD, so take care of
invalidating cache when changing directory or when modifying repository not via
gitwrapper.
Mixing gitwrapper and gitwrapper.cached in one python context is not
supported as this makes it hard to predict which mode will actually be used.
"""

from gitwrapper import tag, branch, commit, misc
