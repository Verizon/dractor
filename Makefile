# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    Makefile
#     Author:  Phil Chandler, John Hickey
#     Date:    2017-02-20
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

#
# Set variables
#

# Source files
MAIN_SRC_DIR = dractor
MAIN_PYC_FILES := $(shell find $(MAIN_SRC_DIR) -name "*.pyc")

# Test files
TESTS_SRC_DIR = tests
TESTS_PYC_FILES := $(shell find $(TESTS_SRC_DIR) -name "*.pyc")
TESTS_PYCACHE_FILES := $(shell find $(TESTS_SRC_DIR) -name "__pycache__")

#
# Set general targets
#

.DEFAULT_GOAL := all

.PHONY: all clean clean_all clean_generated_code clean_dist clean_docs clean_logs clean_pyc clean_tox lint tests unit_tests wheel docs test_wheel test_wheel_in_py35 wheel_test_prep

all: build lint tests docs wheel

#
# Tox targets
#

## setup pre-requisites

# no op tox call to establish the .tox dir for the py35 tox env
.tox/py35/bin/activate:
	tox -e py35

## build
build:
	tox -- build

## lint in all python envs cause of variations in how pylint runs

lint:
	tox -- pylint

## only need to gen the docs once and doesn't seem to vary between the python environments

docs:
	-rm -r docs/build/*
	tox -e py35 -- build_sphinx -b html

## unit tests

unit_tests:
	tox -e py35 -- test

## all tests

tests: unit_tests

## distribution package build(s)

# only build the wheel in one python environment
wheel: clean_dist
	tox -e py35 -- bdist_wheel

# prep the project's install-time dependencies as wheels themselves
wheel_test_prep: wheel
	/bin/bash -c ".tox/py35/bin/pip wheel --wheel-dir=./wheelhouse -r requirements.txt"

test_wheel_in_py35: wheel_test_prep .tox/py35/bin/activate
	/bin/bash -c ".tox/py35/bin/pip install --no-index --find-links=./wheelhouse dist/dractor-*.whl"
	/bin/bash -c ".tox/py35/bin/pip freeze | grep dractor"
	/bin/bash -c ".tox/py35/bin/pip uninstall -y dractor"

test_wheel: test_wheel_in_py35

#
# Clean targets
#

clean: clean_dist clean_docs clean_pyc clean_generated_code clean_logs clean_tox

clean_all: clean clean_tox

clean_generated_code:
	-rm -r dractor/dcim/v*

clean_pyc:
	-rm -r $(MAIN_PYC_FILES) $(TESTS_PYC_FILES) $(TESTS_PYCACHE_FILES)

clean_dist:
	-rm -r .Python env/ bin/ build/ develop-eggs/ dist/ eggs/ .eggs/ lib/ lib64/ parts/ sdist/ var/ *.egg-info/ .installed.cfg *.egg .eggs wheelhouse/*.whl

clean_docs:
	-rm -r docs/build/*

clean_logs:
	-rm -r *.log

clean_tox:
	-rm -r .tox
