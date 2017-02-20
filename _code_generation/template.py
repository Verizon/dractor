# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    template.py
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

"""
Plumbing for generating Python source code with templates based on MOF classes from our parser.
"""
#
# Imports
#

# Python standard library
import logging
import os
import sys

# Third party
import jinja2

# this project
import _code_generation.exceptions as my_exceptions

#
# Module variables
#

# logger
_LOGGER = logging.getLogger(__name__)

# templates


#
# Template renderer
#

class PySrcRenderer(object):
    """Renders Python src using Jinja2 and data objects from MOF parser"""

    TEMPLATES_PATH = os.path.join(os.path.dirname(__file__), 'data', 'templates')
    SUB_MODULE_TEMPLATE_NAME = 'sub_module.jinja2'
    PARENT_MODULE_TEMPLATE_NAME = 'parent_module.jinja2'

    @staticmethod
    def _load_template(j2_env, template_name):
        assert isinstance(j2_env, jinja2.Environment)
        _LOGGER.debug("Begin loading template %s", template_name)
        try:
            j2_template = j2_env.get_template(template_name)
        except Exception as error:
            raise my_exceptions.CodeGenError(
                "Couldn't load jinja2 template {} from env path {}".format(
                    template_name, PySrcRenderer.TEMPLATES_PATH), error)
        else:
            _LOGGER.debug("Finished loading template %s", template_name)
            return j2_template

    def __init__(self):
        _LOGGER.debug("Begin setting up jinja2 environment")
        try:
            j2_loader = jinja2.FileSystemLoader(PySrcRenderer.TEMPLATES_PATH)
            j2_env = jinja2.Environment(loader=j2_loader, trim_blocks=True)
        except Exception as error:
            raise my_exceptions.CodeGenError(
                "Couldn't setup jinja environment using path {}".format(
                    PySrcRenderer.TEMPLATES_PATH), error)
        else:
            _LOGGER.debug("Finished setting up jinja2 environment")

        _LOGGER.debug("Begin loading templates")
        self._parent_module_template = PySrcRenderer._load_template(
            j2_env, PySrcRenderer.PARENT_MODULE_TEMPLATE_NAME)
        self._sub_module_template = PySrcRenderer._load_template(
            j2_env, PySrcRenderer.SUB_MODULE_TEMPLATE_NAME)
        _LOGGER.debug("Finished loading templates")

    def render_sub_module(self, dell_version, mof_class):
        """Render a Python sub-module based on the mof class object"""
        _LOGGER.info("Begin rendering sub-module based on mof class %s", mof_class.name)
        try:
            # pylint: disable=no-member
            rendered_mof = self._sub_module_template.render(dell_version=dell_version,
                                                            mof_class=mof_class)
            _LOGGER.debug("Successfully rendered with jinja template")
        except Exception as error:
            raise my_exceptions.CodeGenError(
                "Fatal error rendering mof class {} to python sub-module".format(
                    mof_class.name), error)
        else:
            _LOGGER.info("Finished rendering sub-module based on mof class %s", mof_class.name)
            return rendered_mof

    def render_parent_module(self, dell_version, module_contents):
        """Render the Python parent-module based on dell version and module contents"""
        _LOGGER.info("Begin rendering parent module for dell version %s", dell_version)
        try:
            module_all = sorted(module_contents.keys())

            # pylint: disable=no-member
            rendered_text = self._parent_module_template.render(
                dell_version=dell_version, module_all=module_all, module_contents=module_contents)
            _LOGGER.debug("Successfully rendered with jinja template")
        except Exception as error:
            raise my_exceptions.CodeGenError(
                "Fatal error rendering parent module for dell version {}".format(dell_version),
                error)
        else:
            _LOGGER.info("Finished rendering parent module for dell version %s", dell_version)
            return rendered_text
