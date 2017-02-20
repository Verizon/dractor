# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    client.py
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
Client Interface for the LC API
"""
import inspect
import importlib
import logging

from dractor.wsman import WSMANBasicAuthConfig, WSMANClient
from dractor.dcim.base import DCIMFactory, DCIMMethodObject, DCIMAttributeObject
from dractor.exceptions import DCIMClientException, UnsupportedLCVersion

DCIM_VERSION_MAP = {'2.30.30.30': 'dractor.dcim.v2303030'}

class Client(object):
    """
    Dynamic interface to the Lifecycle Controller API
    """

    def __init__(self, host, port, username, password):

        self._logger = logging.getLogger(__name__)

        auth = WSMANBasicAuthConfig(username=username, password=password)

        # We use the default HTTP settings
        self._wsman_client = WSMANClient(host, port=port, auth_config=auth)

        self._property_classes = {}


    def _resolve_module(self, lc_version):
        """ Pick the correct set of DCIM modules based on LC Version
        Args:
            lc_version (string): A string representation of the LC version

        Returns:
            string: The name of the module we should import
        Raises:
            UpsupportedLCVersion: If the LC is older than any supported version, we raise an exception
        """

        best_match = None

        for version in DCIM_VERSION_MAP:
            # We don't have that many versions, and will never use the split
            # representation, so just split all the things...
            if version.split('.') <= lc_version.split('.'):
                if not best_match or best_match.split('.') < version.split('.'):
                    best_match = version

        if not best_match:
            message = "LifeCycle controller version '{}' is not supported".format(lc_version)
            raise UnsupportedLCVersion(message)

        return DCIM_VERSION_MAP[best_match]

    def connect(self):
        """ Connect to the DRAC and instantiate the supported set of DCIM classes as client attributes """

        identify = self._wsman_client.identify()

        lc_version = identify.get('LifecycleControllerVersion')

        dcim_module_name = self._resolve_module(lc_version)

        dcim_module = importlib.import_module(dcim_module_name)

        for name, obj in inspect.getmembers(dcim_module):

            if inspect.isclass(obj):
                setattr(self, name, obj(self._wsman_client))
