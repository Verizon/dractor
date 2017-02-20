# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    _namespace.py
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
Directory for consistent namespace prefixes
"""

NS = {
    's': "http://www.w3.org/2003/05/soap-envelope", # Standard
    'wsa': "http://schemas.xmlsoap.org/ws/2004/08/addressing", # Standard
    'wsman': "http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd", # Standard
    'wsmid': "http://schemas.dmtf.org/wbem/wsman/identity/1/wsmanidentity.xsd", # Standard
    'wstransfer': "http://schemas.xmlsoap.org/ws/2004/09/transfer", # Standard
    'wsen': "http://schemas.xmlsoap.org/ws/2004/09/enumeration", # Standard
    'dcim': "http://schemas.dell.com/wbem/wscim/1/cim-schema/2", # Not Standard
}
