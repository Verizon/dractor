# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    reference.py
#     Author:  John Hickey
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
Objects to express CIM Endpoint References
"""

class CIM_Reference(object):
    """
    Base class for endpoint references
    """

    ResourceURI = None
    """ Resource URI to be filled in by children """

    def __init__(self, value):

        self._value = value

    @property
    def resource_uri(self):
        """
        Return the resource URI for this reference
        """

        return self.ResourceURI

    @property
    def selector_set(self):
        """
        Return the selector set dictionary
        """

        return {"InstanceID": self._value}


class CIM_SoftwareIdentity(CIM_Reference):
    """
    CIM_SoftwareIdentity for the DCIM_SoftwareInstallationService
    """

    ResourceURI = 'http://schemas.dell.com/wbem/wscim/1/cimschema/2/DCIM_SoftwareIdentity'
