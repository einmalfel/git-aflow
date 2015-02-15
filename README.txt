Git-aflow project consists of three packages:
 * thingitwrapper - thin wrapper able to parse git commands output.
 * gitconflict - a solution to detect potential merge conflicts between git treeishes without doing a merge. Gitconflict depends on gitwrapper package.
 * gitaflow - gitaflow itself. It depends on both gitconflict and thingitwrapper packages.

Documentation resides in gitaflow wiki: github.com/einmalfel/git-aflow/wiki

To install git-aflow from source use pip:
pip3 install thingitwrapper_package/ gitconflicts_package/ gitaflow_package/

Git-aflow is free software; you can redistribute it and/or modify it under the terms of the GNU LGPL as published by the Free Software Foundation; either version 2.1 of the GNU LGPL, or (at your option) any later version.
Git-aflow is distributed WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See included copy of GNU LGPLv2.1 for more details.
