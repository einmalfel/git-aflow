"""Use this module to enable git wrapper caching. E.g. use
'from thingitwrapper.cached import branch' instead of
'from thingitwrapper import branch'
thingitwrapper will cache results of git commands run in CWD, so take care of
invalidating cache when changing directory or when modifying repository not via
thingitwrapper.
Mixing thingitwrapper and thingitwrapper.cached in one python context is not
supported as this makes it hard to predict which mode will actually be used.
"""

from thingitwrapper import tag, branch, commit, misc
