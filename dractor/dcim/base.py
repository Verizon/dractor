# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    base.py
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
These are the base classes for the auto-generated DCIM classes
"""

import logging

from dractor.types import CIM_Reference, DCIMQualifiedValue
from dractor.exceptions import DCIMAttributeError, DCIMCommandError, DCIMArgumentError, DCIMValueError

# pylint: disable=too-few-public-methods
class DCIM(object):
    """ Base class for all DCIM objects """

    def __init__(self, wsman_client):

        self._logger = logging.getLogger(__name__)
        self._wsman_client = wsman_client

class DCIMFactory(DCIM):
    """
    Factory base class for DCIM objects that support Get/Enumerate
    """

    _CREATES = None
    """ This is the class created by the factory """
    _KEY = None
    """ This is the field that acts as the key for Get calls """
    _DEFAULT_KEYS = ['InstanceID', 'FQDD', 'CreationClassName']
    """ For MOF files that don't have Key defined in them """


    def enumerate(self):
        """ Enumerate and return all instances as a dictionary """

        results = self._wsman_client.enumerate(self._CREATES.__name__)

        instances = {}

        count = 0
        for value in results:
            # If we don't have a key, try to autodetect.  This is
            # because we haven't implemented CIM inheritance for
            # autogeneration and sometimes the InstanceID is in the
            # parent mof
            if not self._KEY:
                for default_key in self._DEFAULT_KEYS:
                    if default_key in value:
                        key = value[default_key]
                        setattr(self.__class__, "_KEY", default_key) # Make subsequent get calls work
                        break
                else:           # No break
                    # If all else fails, return UnknownKey
                    key = "UnknownKey.{}".format(count)
            else:
                key = value[self._KEY]

            instances[key] = self._CREATES(self._wsman_client, value) # pylint: disable=not-callable
            count += 1

        return instances

    @property
    def key(self):
        """ Return what field is being used as our key """

        return self._KEY

    @property
    def creates(self):
        """ Return what class this factory creates """

        return self._CREATES.__name__

    def get(self, fqdd):
        """ Return an instance of self.creates populated with data returned from the DRAC

        Args:
            fqdd (string): This is the descriptor used to lookup the object.  Typically this is the InstanceID.

        Returns:
            object: This returns an populated DCIMAttributeObject child of type self.creates

        Raises:
            DCIMAttributeError: Some classes don't have a key, so the only way to get instances is via enumerate()
        """

        if not self._KEY:
            message = "Class {} does not have a primary key, attempting to use InstanceID.".format(self.__class__.__name__)
            self._logger.debug(message)
            key = 'InstanceID'  # We don't set self._KEY here because enumerate can figure it out for sure
        else:
            key = self._KEY

        # Be liberal with what you accept.  We can easily get DCIMQualifiedvalue objects
        # being fed back into the DRAC
        if isinstance(fqdd, DCIMQualifiedValue):
            fqdd = fqdd.unmapped_value

        selectors = {key: fqdd}

        result = self._wsman_client.get(self.creates, selectors)

        return self._CREATES(self._wsman_client, result) # pylint: disable=not-callable


class DCIMAttributeObject(DCIM):
    """ Base class for objects with attributes created by DCIMFactory
    children via get and enumerate
    """

    _ATTRIBUTE_METADATA = {}
    """ Attribute metedata contains the valuemaps and qualifiers for the
    various class properties
    """

    def __init__(self, wsman_client, attributes):
        """ Create an instance
        Args:
            wsman_client (wsman.WSMANClient): WSMAN Client
            attributes (dict): Attributes returned by get() or enumerate() calls
        """

        super(DCIMAttributeObject, self).__init__(wsman_client)

        self._attributes = attributes

        self._dcim_qualified = {}

        # The reason for all the GETs here is to support
        # extra values returned by the DRAC not defined in the
        # MOF file
        for name, value in attributes.items():
            meta = self._ATTRIBUTE_METADATA.get(name, {})
            qualifiers = meta.get('qualifiers', {})
            valuemap = meta.get('valuemap', {})

            if isinstance(value, list): # Handle Arrays
                self._dcim_qualified[name] = []
                for item in value:
                    self._dcim_qualified[name].append(DCIMQualifiedValue(item, valuemap, qualifiers))
            else:
                self._dcim_qualified[name] = DCIMQualifiedValue(value, valuemap, qualifiers)

            # Generate a property if we don't have one from the MOF file
            if not hasattr(self, name):
                self._make_property(name)

    def _make_property(self, name):
        """ Create a dynamic property """

        def getter(self):
            return self._get_dcim_attribute(name)

        prop = property(getter, None, None, "Runtime generated (Not in MOF)")

        setattr(self.__class__, name, prop)


    def _get_dcim_attribute(self, name):
        """ Method called by auto-generated properties """

        if not name in self._dcim_qualified:
            message = "Attribute '{}' was not returned by the LifeCycle Controller".format(name)
            raise DCIMAttributeError(message)

        return self._dcim_qualified[name]

    def __contains__(self, item):
        """ Support if x in DCIM... """

        return item in self._dcim_qualified

    def __getitem__(self, key):
        """ Support [name] """

        return self._dcim_qualified[key]

    @property
    def dictionary(self):
        """
        Return the RAW dictionary returned by WSMAN. This method is useful
        for introspection.  Although we auto-generate attributes with
        doc strings for classes, we may get back more than that from
        the DRAC.

        Returns:
            dict: Key/Values returned by DRAC without translation
        """

        return self._attributes


class DCIMMethodObject(DCIM):
    """ Base class for objects with properties """

    @staticmethod
    def _make_properties(parameters):
        """ Translate to WSMAN properties """

        properties = []

        for prop_name, prop_dict in parameters['input'].items():

            prop_value = prop_dict['value']

            # We are picky about None here to be able to pass empty
            # strings
            if prop_value is None:
                continue

            # Make python arrays WSMANy, make sure we pass in strings,
            # unless we know about the object (CIM_References for now)
            if isinstance(prop_value, CIM_Reference):
                properties.append((prop_name, prop_value))
            elif isinstance(prop_value, list):
                for item in prop_value:
                    properties.append((prop_name, str(item)))
            else:
                properties.append((prop_name, str(prop_value)))

        return properties

    def _assert_return_value(self, result, expected_values):
        """ Error handling routine for LC return codes """

        # Make sure we are dealing with strings
        expected_values = [str(x) for x in expected_values]

        if 'ReturnValue' not in result:
            message = "No key 'ReturnValue' found in result '{}'".format(str(result))
            self._logger.error(message)
            raise DCIMValueError(message)

        return_value = result.get('ReturnValue', "No Return Found")

        if return_value not in expected_values:
            message = result.get('Message')
            message_id = result.get('MessageID')
            return_value = result.get('ReturnValue')

            self._logger.error("Expected %s, got %s: %s: %s",
                               expected_values, return_value, message_id, message)
            raise DCIMCommandError(return_value, message_id, message)

    @staticmethod
    def _unmap_arguments(parameters):
        """ Look and resolve any arguments that are have mappings """

        for prop_name, prop_dict in parameters['input'].items():

            prop_value = prop_dict['value']

            prop_valuemap = prop_dict['valuemap']

            if not prop_valuemap:
                continue

            if not isinstance(prop_value, str):
                continue

            reverse_arg_map = {value.lower(): key for key, value in prop_valuemap.items()}
            if prop_value.lower() in reverse_arg_map:
                prop_dict['value'] = reverse_arg_map[prop_value.lower()]
            elif not prop_value in prop_valuemap:
                message = ("The provided value '{}' for argument '{}' "
                           "is not in the list of mapped values: {}").format(prop_value,
                                                                             prop_name,
                                                                             prop_valuemap)
                raise DCIMArgumentError(message)

        return parameters

    @staticmethod
    def _map_return_values(result, parameters):
        """ Translate any returned fields to ValueMap objects """

        mapped = {}

        for key, value in result.items():
            meta = parameters['output'].get(key, {})
            valuemap = meta.get('valuemap', {})
            qualifiers = meta.get('qualifiers', {})
            mapped[key] = DCIMQualifiedValue(value, valuemap, qualifiers)

        return mapped


    def _invoke_method(self, method, parameters):
        """ Invoke a method! """

        # Do any translations
        mapped_args = self._unmap_arguments(parameters)

        # Generate the WSMAN properties
        properties = self._make_properties(mapped_args)

        result = self._wsman_client.invoke(self.__class__.__name__, method, properties)

        self._assert_return_value(result, [0, 4096])

        result = self._map_return_values(result, parameters)

        return result
