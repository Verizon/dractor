# Contributing to Dractor

Thank you for your interest in contributing to Dractor!

* [Feedback](#feedback)
* [Building](#building)
* [Version Control](#version-control)

----

## Feedback

For questions, feature requests, and bug reports, please make a GitHub issue in this repository on GitHub.

----

## Building

The build system for this project consists of `Make` calling `tox` which itself calls `setuptools`.

### Pre-requisites

* Python 3.5
* Make

### Using Make

Make targets are used to represent distinct steps in the "canonical" build process,
and leverage `tox` for the final mile of build tasking.

Please see the `Makefile` itself for more details.  Some basic examples are given below.

#### Run all default build targets

```
cd <repo-clone>
make clean all
```

#### Just build the source code

Uses code generation under the hood.

```
cd <repo-clone>
make build
```

### Using tox

You can pass positional arguments for `setuptools` to the `tox` build.  You should do
this for adhoc builds or to debug the build plumbing itself.

The "canonical" builds are driven by the Makefile targets.

If you run tox without any arguments, it **will* error out.  This is the expected
behavior due to tox's own `{posargs}` behaviors.

#### Setup a "develop" environment

```
cd <repo-clone>
tox -- develop
```

### Do a build

```
cd <repo-clone>
tox -- build
```

#### Run pylint

Using a very forgiving pylintrc.

```
cd <repo-clone>
tox -- pylint
```

#### Run some tests

```
cd <repo-clone>
tox -- test
```

#### Build a wheel

```
cd <repo-clone>
tox -- bdist_wheel
```

#### Run sphinx

```
cd <repo-clone>
tox -- build_sphinx
```

#### Get setuptools help

```
cd <repo-clone>
tox -- --help
```

----

### With Vagrant

A barebones vagrant dev environment has been included.

It is rsync'd with the host machine, but with .git etc. excluded.

Two VMs are provided:

* `trusty64`
  * Based on the `ubuntu/trusty64` public box
  * Tailored with the right dependencies/config to allow running tox
  * This vm *is* the "primary" vagrant vm and *is* set to auto start.
* `xenial64`
  * Based on the `ubuntu/xenial64` public box
  * Tailored with the right dependencies/config to allow running tox
  * This vm is *not* the primary vm and is *not* set to autostart.

For both VMs, this repository's source code is staged to `/home/ubuntu/dractor` via Vagrant's rsync
folder capabilities.

### Examples

These are some examples of a typical pattern for running tox within the Vagrant VMs.

Running the setuptools 'develop' command in a trusty and a xenial build environment

```
cd <repo-clone>
vagrant up trusty64
vagrant ssh trusty64 -c "cd /home/ubuntu/dractor && tox -- develop"
vagrant up xenial64
vagrant ssh xenial64 -c "cd /home/ubuntu/dractor && tox -- develop"
```

Generating the sphinx docs inside the default VM and then opening them up from your host machine

```
cd <repo-clone>
vagrant up
vagrant ssh -c "cd /home/ubuntu/dractor ; rm -r ./docs/build/html/ ; tox -- build_sphinx"
# now open docs/build/html/index.html in your browser
```

Generating the wheel inside the default VM and having it available on your host machine for upload to PyPI etc.

```
cd <repo-clone>
vagrant up
vagrant ssh -c "cd /home/ubuntu/dractor ; rm -r ./dist/*.whl ; tox -- bdist_wheel"
ls -la ./dist
```

----

## Version Control

As you can tell, we use GitHub to host this project and orchestrate work on it.

### Branches

We use the `master` branch as the current good cut of the code-base.

### Pull Requests

Please make pull requests against the `master` branch by default.  If we need you to repoint it to a different
branch, we'll let you know.

### Tags and Releases

We use the Git tags and GitHub releases to mark our releases.

In addition, we will *eventually* release to PyPI.
