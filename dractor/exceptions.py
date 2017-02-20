# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    exceptions.py
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
Exceptions for this project
"""


class PyDCIMException(Exception):
    """ Parent exception for all exceptions from this library """

class PyDCIMNotSupported(PyDCIMException):
    """ For calls that reference DCIM objects we do not know about """

# *****************************************************************
# Exceptions for WSMAN and lower level DRAC interactions
# *****************************************************************

class WSMANClientException(PyDCIMException):
    """ Base exception for WSMAN client exceptions """


# HTTP/Service level exceptions

class WSMANTransportError(WSMANClientException):
    """Transport level exception base (auth, connection, etc)"""


class WSMANConnectionError(WSMANTransportError):
    """ For HTTP level connection errors """


class WSMANHTTPError(WSMANTransportError):
    """ For HTTP status code errors """


class WSMANAuthError(WSMANHTTPError):
    """ For HTTP auth errors """


# Envelope Errors

class WSMANSOAPEnvelopeError(WSMANClientException):
    """ Base exception for making message envelopes """


#
# Parse Errors
#
class WSMANSOAPResponseError(WSMANClientException):
    """ For error that occur during parsing """


class WSMANFault(WSMANSOAPResponseError):
    """ For responses that contain a fault """


class WSMANElementNotFound(WSMANSOAPResponseError):
    """ For elements that we expected but weren't there """

#
# DCIM base class errors
#
class DCIMException(PyDCIMException):
    """ Base class for API exceptions """

class DCIMValueError(DCIMException):
    """ For missing values in return data, etc """

class DCIMCommandError(DCIMException):
    """ For asserting a return value """

    def __init__(self, message, message_id=None, return_value=None):
        self.message = message
        self.message_id = message_id
        self.return_value = return_value

class DCIMAttributeError(DCIMException):
    """ For problems with class attributes """

class DCIMArgumentError(DCIMException):
    """ For argument issues """

#
# dractor.dcim.Client exceptions
#
class DCIMClientException(PyDCIMException):
    """ Base class for client level problems """

class UnsupportedLCVersion(DCIMClientException):
    """ Exception for LC versions too old """

#
# dractor.recipe exceptions
#
class RecipeException(PyDCIMException):
    """ Base class for recipe exceptions """

class RecipeConfigurationError(RecipeException):
    """ For configuration errors """

class RecipeExecutionError(RecipeException):
    """ Failures to run recipe as expected """

class LCHalted(RecipeException):
    """ For when the server is stuck at a prompt """

class LCTimeout(RecipeException):
    """ General timeout """

class LCJobError(RecipeException):
    """ Job failed """

class LCDataError(RecipeException):
    """ DRAC yielding bad data """
