#!/usr/bin/env bash

#
# Assuming the use of the "python" language config in travis ci
#

set -e

echo "Installing pre-requisites for travis build"

#
# Using a ppa for python3.5 that is well curated and in common use by the "community":
#     https://launchpad.net/~fkrull/+archive/ubuntu/deadsnakes
# Doing this instead of using travis' support for Python 3.5 because the
# deadsnakes ppa usage is repeatable outside of travis for debugging any
# incompatilibites that come up.
#
add-apt-repository -y ppa:fkrull/deadsnakes

# update and upgrade as temporary hack
apt-get update

# install python dependencies for bravado's use of python cryptography package
apt-get install -y build-essential libssl-dev libffi-dev python3.5-dev

# now install tox to system python
pip install -U tox
