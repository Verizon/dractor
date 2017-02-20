# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    mof.py
#     Author:  John Hickey, Phil Chandler
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
Plumbing for converting Dell MOF files into Python objects.
"""

#
# Imports
#

# Python standard library
import collections
import glob
import logging
import os

# Third party
import textx.metamodel

# this project
import _code_generation.exceptions as my_exceptions

#
# Module variables
#

# logger
_LOGGER = logging.getLogger(__name__)


#
# Custom classes for text meta model
#


class Qualified(object):
    """
    We have qualifiers at class, function, and argument levels in MOF
    files.  This is an attempt to unify the parsing of qualifiers and
    provide the name property.
    """

    def __init__(self, name, qualifiers):

        self._name = name
        self.qualifiers = {}

        for qualifier in qualifiers:
            if hasattr(qualifier, 'value'):
                value = qualifier.value
            elif hasattr(qualifier, 'values'):
                value = qualifier.values
            elif qualifier.__class__.__name__ == 'NegativeKeyword':
                value = False
            else:
                value = True

            # All qualifiers have a 'name'
            # Since the capitalization of qualifiers is inconsistent,
            # we are just going to squash case for everything
            self.qualifiers[qualifier.name.lower()] = value

        # Make sure we don't have multiple cases of the same key
        assert len(self.qualifiers) == len(qualifiers)

    @property
    def name(self):
        """ Return the Pythonic Name """

        return self._name.replace("[]", "")

    @property
    def valuemap(self):
        """ Return the ValueMap from the qualifiers as a python dictionary """

        values = self.qualifiers.get('values')
        valuemap = self.qualifiers.get('valuemap')

        final_mapping = {}
        if values and valuemap:
            raw_mapping = dict(zip(valuemap, values))
            final_mapping = {}
            for raw_key, raw_value in raw_mapping.items():
                final_mapping[raw_key.strip()] = raw_value.strip()
        return final_mapping

    @property
    def docstring(self):
        """ Return a docstring generated from the qualifiers """
        raw_description = self.qualifiers.get("description")

        # short circuit if there isn't a description to process
        if not raw_description:
            _LOGGER.debug("No raw description found in MOF, substituting placeholder")
            return "No documentation in MOF"

        # process the raw description, normalizing whitespace and special characters
        _LOGGER.debug("Normalizing raw description from MOF:\n%s", raw_description)
        normalized_lines = []
        for raw_line in raw_description:
            # split to normalize \n in the entry
            normalized_line_elements = []
            for text in raw_line.split():
                # strip leading/trailing whitespace
                stripped_text = text.strip()
                # escape any special rst characters
                escaped_text = stripped_text.replace('*', '\*')
                # add to normalized line elements
                normalized_line_elements.append(escaped_text)
            # create normalized line and save it
            normalized_line = " ".join(normalized_line_elements)
            normalized_lines.append(normalized_line)

        # create and return the normalized line block
        normalized_description = "\n".join(normalized_lines)
        _LOGGER.debug("Normalized description is:\n%s", normalized_description)
        return normalized_description


class MOFClass(Qualified):
    """ MOF Class """

    def __init__(self, name, qualifiers, parent_class, members):
        """
        Our MOF classes consist of members, which are functions, and
        qualifiers
        """

        self.parent_class = parent_class
        self.members = members

        super(MOFClass, self).__init__(name, qualifiers)

    @property
    def attributes(self):
        """
        Return all methods that don't take arguments, these are populated
        by get/enumerate factory classes
        """

        attributes = []

        for member in self.members:
            if member.attribute:
                attributes.append(member)

        return attributes

    @property
    def attributes_metadata(self):
        """
        Return the value mapping and qualifiers for every attribute as a dictionary.
        We can't do fancy things if we embed these in the functions like we do for
        methods.
        """

        attribute_meta = collections.defaultdict(dict)

        for attribute in self.attributes:
            attribute_meta[attribute.name]['valuemap'] = attribute.valuemap
            attribute_meta[attribute.name]['qualifiers'] = attribute.qualifiers

        return dict(attribute_meta)

    @property
    def methods(self):
        """ Return all methods that require invoke """
        methods = []

        for member in self.members:
            if not member.attribute:
                methods.append(member)

        return methods

    @property
    def dcim_parents(self):
        """ Return parent classes in dractor/DCIM.py for code autogeneration """

        parents = []
        if self.attributes:
            parents.append('DCIMAttributeObject')
        if self.methods:
            parents.append('DCIMMethodObject')

        return parents

    @property
    def key(self):
        """ Return the name of our key """

        for member in self.members:
            if member.key:
                return member.name

    @property
    def mof_metadata(self):
        """ Return a dictionary representation of the MOF file """

        mof_dict = collections.defaultdict(dict)

        mof_dict['class'] = self.name
        mof_dict['parent_class'] = self.parent_class
        mof_dict['qualifiers'] = self.qualifiers

        for func in self.members:
            mof_dict['functions'].update(func.mof_metadata)

        return dict(mof_dict)


class Function(Qualified):
    """ Member function """

    def __init__(self, name, parent, qualifiers, return_type, arguments,
                 default):  # pylint: disable=too-many-arguments

        super(Function, self).__init__(name, qualifiers)

        self.parent = parent
        self.arguments = arguments
        self.return_type = return_type
        self.default = default

    @property
    def key(self):
        """ Is this a key property? """

        return self.qualifiers.get("key", False)

    @property
    def required_inputs(self):
        """ Return arguments that have a Required qualifier """

        inputs = []
        for arg in self.arguments:
            if arg.IN and arg.required:
                inputs.append(arg)

        return inputs

    @property
    def optional_inputs(self):
        """ Return all arguments without the Required qualifier """

        inputs = []
        for arg in self.arguments:
            if arg.IN and not arg.required:
                inputs.append(arg)

        return inputs

    @property
    def inputs(self):
        """ Return all arguments, required and optional """

        inputs = []
        for arg in self.arguments:
            if arg.IN:
                inputs.append(arg)

        return inputs

    @property
    def outputs(self):
        """ Return all return values """

        outputs = []
        for arg in self.arguments:
            if arg.OUT:
                outputs.append(arg)

        return outputs

    @property
    def arg_str(self):
        """ Return a pythonic string of args """

        args = ['self']
        args.extend([x.name for x in self.required_inputs])
        args.extend(["{}=None".format(x.name) for x in self.optional_inputs])

        return ", ".join(args)

    @property
    def attribute(self):
        """ Is this function an attribute or method """

        return not bool(self.arguments)

    @property
    def mof_metadata(self):
        """ Return all metadata """

        func_dict = collections.defaultdict(dict)

        func_dict[self.name]['qualifiers'] = self.qualifiers
        func_dict[self.name]['valuemap'] = self.valuemap
        func_dict[self.name]['return_type'] = self.return_type

        func_dict[self.name]['optional_inputs'] = {}
        func_dict[self.name]['required_inputs'] = {}
        func_dict[self.name]['outputs'] = {}

        for arg in self.required_inputs:
            func_dict[self.name]['required_inputs'].update(arg.mof_metadata)

        for arg in self.optional_inputs:
            func_dict[self.name]['optional_inputs'].update(arg.mof_metadata)

        for arg in self.outputs:
            func_dict[self.name]['outputs'].update(arg.mof_metadata)

        # For the return value

        return dict(func_dict)


class FunctionArg(Qualified):
    """ Arguments have metadata too """

    def __init__(self, name, parent, qualifiers, ctype):

        super(FunctionArg, self).__init__(name, qualifiers)
        self.parent = parent
        self.ctype = ctype

        if '[]' in name or '[]' in ctype:  # pylint: disable=simplifiable-if-statement
            self.is_list = True
        else:
            self.is_list = False

    @property
    def IN(self):  # pylint: disable=invalid-name
        """ Is this a return value or input value """

        # This is complicated a little bit by args like
        # DCIM_PhysicalComputerSystemView.SetOneTimeBootSource
        # which has a required arg that specifies neither in
        # or out.

        if 'out' in self.qualifiers:
            return False

        return self.qualifiers.get("in", True)

    @property
    def OUT(self):  # pylint: disable=invalid-name
        """ Is this a return value or input value """

        # Most mof files are OUT, but some say Out...

        return self.qualifiers.get("out", False)

    @property
    def required(self):
        """ Is this a required arg """

        return bool(self.qualifiers.get("required", False))

    @property
    def arg_type(self):
        """ Return a pythonic type for this argument """

        arg_type = self.ctype

        if 'int' in arg_type:
            arg_type = 'int'

        if self.is_list:
            arg_type = 'list of {}'.format(arg_type)

        if 'required' in self.qualifiers:
            arg_type = "{}, optional".format(arg_type)

        return arg_type

    @property
    def mapping_description(self):
        """
        Return a docstring friendly explanation of how this argument is
        mapped
        """

        mapping_description_lines = []

        if self.valuemap:
            for value in sorted(self.valuemap.keys()):
                mapping = self.valuemap[value]
                mapping_description_lines.append("'{}' <-> '{}'\n".format(value, mapping))
        return mapping_description_lines

    @property
    def mof_metadata(self):
        """ Return all the information we know about this arg as a dictionary """

        arg_dict = collections.defaultdict(dict)

        arg_dict[self.name]['type'] = self.arg_type
        arg_dict[self.name]['qualifiers'] = self.qualifiers
        arg_dict[self.name]['valuemap'] = self.valuemap

        return dict(arg_dict)


#
# MOF parser class
#

class MOFParser(object):
    """Parser for MOF data files"""

    # location of textx metamodel config
    META_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'textex', 'dcim_mof_parse.tx')

    # custom meta model classes
    META_MODEL_CLASSES = [MOFClass, Function, FunctionArg]

    # location of mof files
    MOF_DIR = os.path.join(os.path.dirname(__file__), 'data', 'mof')

    # info on a candidate MOF file
    MOFFileEntry = collections.namedtuple('MOFFileEntry', field_names=['base_name', 'path'])

    @staticmethod
    def find_avail_mof_files(dell_version):
        """Collect list of available MOF files given the dell version"""
        assert dell_version is not None
        mof_path = os.path.join(MOFParser.MOF_DIR, dell_version)
        entries = []
        for mof_file_name in glob.glob('{}/*.[Mm][Oo][Ff]'.format(mof_path)):
            mof_file_path = os.path.join(mof_path, mof_file_name)
            mof_file_base_name = os.path.basename(mof_file_name)
            entry = MOFParser.MOFFileEntry(base_name=mof_file_base_name, path=mof_file_path)
            entries.append(entry)
        _LOGGER.debug("Collected this list of available mof files for dell version %s : %s",
                      dell_version, entries)
        return entries

    def __init__(self):
        _LOGGER.debug("Load textx metamodel for MOF parsing")
        try:
            metamodel = textx.metamodel.metamodel_from_file(
                MOFParser.META_MODEL_PATH, classes=MOFParser.META_MODEL_CLASSES)
        except Exception as error:
            raise my_exceptions.CodeGenError("Fatal error loading textx metamodel for MOF parsing",
                                             error)
        else:
            _LOGGER.debug("Successfully loaded text metamodel from %s : %s",
                          MOFParser.META_MODEL_PATH, metamodel)
            self._meta_model = metamodel

    def parser_mof_file(self, mof_file_entry):
        assert isinstance(mof_file_entry, MOFParser.MOFFileEntry)
        _LOGGER.info("Begin parsing MOF file: %s", mof_file_entry)
        try:
            mof_class = self._meta_model.model_from_file(mof_file_entry.path)
            _LOGGER.debug("successfully parsed mof file")
        except Exception as error:
            raise my_exceptions.CodeGenError(
                "Fatal error while parsing MOF file {}".format(mof_file_entry.path), error)

        # now check if it has members
        if not mof_class.members:
            raise my_exceptions.SkipMOFFile(
                "MOF class in MOF file {} has no members, so skipping it".format(
                    mof_file_entry.path))

        _LOGGER.info("Finished parsing MOF file: %s", mof_file_entry)
        return mof_class
