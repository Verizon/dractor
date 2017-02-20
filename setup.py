# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    setup.py
#     Author:  Phil Chandler, John Hickey
#     Date:    2017-02-17
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
# Imports
#

import distutils.cmd
import logging
import os
import setuptools
import setuptools.command.build_py
import setuptools.command.test
import subprocess
import sys

#
# Module level variables and calls
#

# package and module metadata
PACKAGE_NAME = 'dractor'
PACKAGE_VERSION = '0.0.1'
ROOT_MODULE_NAME = 'dractor'

# setup logging
logging.basicConfig(level=logging.WARNING)


#
# Utilities
#

def my_find_packages(*args):
    """A custom package finder to use instead of setuptools.find_packages()"""
    import os
    packages = []
    for root_module_dir in args:
        for root, dirs, files in os.walk(root_module_dir):
            if '__init__.py' in files:
                packages.append(root)
    return packages


#
# Custom Commands
#

class CustomBuildCommand(setuptools.command.build_py.build_py):
    """Custom build command that runs the codegen before the regular build"""

    def run(self):
        """Customized run"""
        #
        # do code gen first
        #

        # deferred import of codegen tooling
        import _code_generation

        # TODO - add a flag to activate debug logging via cli, but for now comment out
        # logging.getLogger().setLevel(logging.DEBUG)

        # iterate across supported dell versions and generate code for each
        py_root_output_path = os.path.abspath(os.path.join('dractor', 'dcim'))
        mof_translator = _code_generation.MOFTranslator(py_root_output_path)
        for dell_version in ['v2303030']:
            mof_translator.translate(dell_version)

        #
        # now call parent implementation via old style
        #
        setuptools.command.build_py.build_py.run(self)


class PylintCommand(distutils.cmd.Command):
    """Custom command to run Pylint"""

    description = "Run pylint on all source code"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """Run pylint"""
        subprocess.check_call(['pylint', '_code_generation', 'dractor'])


class CustomTestCommand(setuptools.command.test.test):
    """Custom unit test command that runs pytest"""
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        setuptools.command.test.test.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        setuptools.command.test.test.finalize_options(self)
        # New setuptools don't need this anymore, thus the try block.
        try:
            self.test_args = []
            self.test_suite = 'True'
        except AttributeError:
            pass

    def run_tests(self):
        """Customized run"""

        # deferred import
        import pytest

        # run pytest with empty array so pytest.ini takes complete control
        # need to use [] because of https://github.com/pytest-dev/pytest/issues/1110
        errno = pytest.main([])
        sys.exit(errno)


#
# Main logic
#

setuptools.setup(
    author='Anonymous', # TODO - Will update when ready for open sourcing
    author_email='anonymous@localhost.com', # TODO - Will update when ready for open sourcing
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: DCIM Users',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Private :: Do Not Upload', # TODO - Will remove this when its ready for open sourcing
   ],
   cmdclass={
       "build_py": CustomBuildCommand,
       "pylint": PylintCommand,
       'test': CustomTestCommand,
   },
   command_options={
        'build_sphinx': {
            'project': ('setup.py', PACKAGE_NAME),
            'version': ('setup.py', PACKAGE_VERSION),
            'release': ('setup.py', PACKAGE_VERSION)
        }
    },
    description=" ".join([
        'Python Bindings for the Dell CIM Extensions Library for programmatic control of ',
        'Dell servers',
    ]),
    install_requires=[
        'lxml>=3.6.4',
        'requests>=2.11.1',
        'click>=6.6',
        'jsonschema>=2.5.1',
    ],
    keywords=['development'],
    license='Apache 2.0',
    # TODO - Need to write up a long description for visibility in PyPI when open sourced
    long_description='TBD',
    name=PACKAGE_NAME,
    packages=my_find_packages(ROOT_MODULE_NAME),
    setup_requires=[
        'jinja2>=2.8',
        'pylint>=1.6.4',
        'Sphinx>=1.5a1',
        'textx>=1.4',
    ],
    test_suite='tests',
    tests_require=[
        'coverage>=4.1',
        'mock>=2.0.0',
        'pytest>=2.6.4',
        'pytest-cov>=1.8.1',
        'responses>=0.5.1',
        'testfixtures>=4.10.0',
    ],
    entry_points = {
        'console_scripts': ['dractor=dractor.util.cli:main'],
    },
    url='http://localhost', # TODO - Will update when ready for open sourcing
    version=PACKAGE_VERSION,
    zip_safe=False,
)
