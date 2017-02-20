# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    mof2py.py
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
Tools for converting Dell MOF files into Python code.
"""

#
# Imports
#

# Python standard library
import glob
import logging
import os
import sys
from collections import defaultdict

# this project
import _code_generation.exceptions as my_exceptions
import _code_generation.mof as my_mof
import _code_generation.template as my_template

#
# Module variables
#

# logger
_LOGGER = logging.getLogger(__name__)

#
# Driver for translation
#
#
#
# def old_translate_mof_to_py(dell_version, root_py_output_path):
#     """Entry point for translations"""
#
#     _LOGGER.info("Begin translating mof to python for dell version %s", dell_version)
#     py_module_output_path = os.path.join(root_py_output_path, dell_version)
#     try:
#         # Make sure the output path exists
#         if not os.path.exists(py_module_output_path):
#             os.makedirs(py_module_output_path)
#
#         # Load textX parser
#         metamodel = my_mof.load_metamodel()
#
#         # Parse the MOF files
#         classnames = {}
#         avail_mof_files = my_mof.find_avail_mof_files(dell_version)
#         for mof_file in avail_mof_files:
#             classname = mof_file.base_name.replace(".mof", "")
#             py_file_name = "{}.py".format(classname)
#             py_path = os.path.join(py_module_output_path, py_file_name)
#
#             try:
#                 _LOGGER.debug("Translating mof file %s to py file %s", mof_file.path, py_path)
#                 classes, py_src_text = process_mof(metamodel, mof_file.path)
#             except Exception:   # pylint: disable=broad-except
#                 _LOGGER.exception("Failed to parse %s", mof_file.path)
#                 continue
#             else:
#                 classnames.update(classes)
#                 with open(py_path, 'w') as output_file:
#                     output_file.write(py_src_text)
#
#         # Write imports for __init__.py
#         init_py = os.path.join(py_module_output_path, '__init__.py')
#
#         with open(init_py, 'w') as output_file:
#             for classname, classes in classnames.items():
#                 imports = ", ".join(classes)
#                 output_file.write("from .{} import {}\n".format(classname, imports))
#
#     except Exception as error:  # pylint: disable=broad-except
#         _LOGGER.exception("Fatal error while trying to translate mof to python: %s", str(error))
#     else:
#         _LOGGER.info("Finished translating mof to python")


class MOFTranslator(object):
    """Translates MOF data files into Python source code files"""

    def __init__(self, root_output_path):
        """Takes root output path for python code as an argument"""

        # setup delegate parser and renderer
        self._parser = my_mof.MOFParser()
        self._renderer = my_template.PySrcRenderer()

        # generate output path
        assert os.path.exists(root_output_path), "Root output path does not exist"
        self._root_output_path = root_output_path
        _LOGGER.debug("Using root output path: %s", self._root_output_path)

    def _make_parent_module_path(self, dell_version):
        """Ensure that the parent module path exists on the file system"""
        parent_module_path = os.path.join(self._root_output_path, dell_version)
        if os.path.exists(parent_module_path):
            _LOGGER.info("Using existing parent module path %s", parent_module_path)
        else:
            os.makedirs(parent_module_path)
            _LOGGER.info("Created directory at parent module path %s", parent_module_path)
        return parent_module_path

    @staticmethod
    def _write_python_file(py_src_text, module_name, parent_path):
        """Write a Python source file based on the text, the module name of the file and the path"""
        assert py_src_text is not None
        assert module_name
        assert os.path.exists(parent_path)
        output_path = os.path.join(parent_path, "{base_name}.py".format(base_name=module_name))
        _LOGGER.info("Begin writing Python source file %s", output_path)
        try:
            with open(output_path, 'w') as output_file:
                output_file.write(py_src_text)
        except Exception as error:
            raise my_exceptions.CodeGenError(
                "Fatal error writing Python source file {}".format(output_path), error)
        else:
            _LOGGER.info("Finished writing Python source file %s", output_path)

    def translate(self, dell_version):
        """Translates MOF to Python"""
        assert dell_version
        _LOGGER.info("Begin translating mof to python code for dell version %s", dell_version)
        try:
            parent_module_path = self._make_parent_module_path(dell_version)
            parent_module_contents = {}

            # iterate across the available mof files and produce python sub-modules
            for mof_file_entry in my_mof.MOFParser.find_avail_mof_files(dell_version):
                # first parse the mof file into a mof class object
                try:
                    mof_class = self._parser.parser_mof_file(mof_file_entry)
                except my_exceptions.SkipMOFFile as e:
                    _LOGGER.warning(str(e))
                    continue

                # now render it into python source code text and write it out
                py_sub_module_src_text = self._renderer.render_sub_module(dell_version,
                                                                          mof_class)
                py_sub_module_name = mof_file_entry.base_name.replace(".mof", "")
                MOFTranslator._write_python_file(
                    py_sub_module_src_text, py_sub_module_name, parent_module_path)

                # update the manifest of the module contents
                if mof_class.attributes:
                    py_class_name = "{class_name}Factory".format(class_name=mof_class.name)
                else:
                    py_class_name = mof_class.name
                parent_module_contents[mof_class.name] = [py_class_name]

            # after writing out all the sub-modules, write out the parent's __init__.py
            py_parent_module_src_text = self._renderer.render_parent_module(
                dell_version, parent_module_contents)
            MOFTranslator._write_python_file(
                py_parent_module_src_text, '__init__', parent_module_path)
        except my_exceptions.CodeGenException as e:
            raise e
        except Exception as error:  # pylint: disable=broad-except
            raise my_exceptions.CodeGenError(
                "Fatal error while trying to translate mof to python for dell "
                "version: {}".format(dell_version), error)
        else:
            _LOGGER.info("Finished translating mof to python for dell version %s", dell_version)
