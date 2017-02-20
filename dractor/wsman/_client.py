# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    _client.py
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
Client class for maintaining a connection to a DRAC
"""

import logging

# Third Party
import requests
import requests.adapters
import requests.exceptions
import requests.packages.urllib3
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# This project

from dractor.exceptions import (
    WSMANClientException,
    WSMANTransportError,
    WSMANConnectionError,
    WSMANAuthError,
    WSMANHTTPError,
)

from ._envelopes import (
    IdentifyEnvelope,
    EnumerateEnvelope,
    GetEnvelope,
    InvokeEnvelope,
    PullEnvelope,
)

from ._parsers import (
    IdentifyResponse,
    EnumerateResponse,
    GetResponse,
    InvokeResponse,
    PullResponse,
)


class HTTPConfig(object):
    """Configuration settings controlling the usage of HTTP by the WSMANClient

    Attributes:
        max_retries (int): The maximum number of retries allowed for failed HTTP requests.

        timeouts (tuple): A tuple containing the connection_timout and read_timeout values.

    Note:
        The ``max_retries`` field will indicate the maximum number of
        retries that should be made for 'failed' HTTP requests.  In this
        context, an HTTP request is considered to be a 'failed' one,
        if the HTTP status code was not in the success range (e.g. 200s).
    """

    DEFAULT_CONNECTION_TIMEOUT = 12.1
    """Default connection timeout value"""

    DEFAULT_READ_TIMEOUT = 120
    """Default read timeout value"""

    DEFAULT_MAX_RETRIES = 3
    """Default max retries"""

    DEFAULT_SSL_CERT_VERIFY= False
    """Default SSL cert verification mode"""

    def __init__(self, connection_timeout=None, read_timeout=None,
                 max_retries=None, verify_ssl_cert=None):
        """Constructor

        Arguments:
            connection_timeout (float, optional): The timeout (in seconds) for
                HTTP connections to establish.  If not given, then the value of
                ``HTTPConfig.DEFAULT_CONNECTION_TIMEOUT`` will be used.
            read_timeout (int, optional): The number of seconds that
                the client will wait for the server to send a response. If not
                given, then the value of ``HTTPConfig.DEFAULT_READ_TIMEOUT``
                will be used.
            max_retries (int, optional): The maximum number of retries allowed
                for failed HTTP requests. If not given, then the value for
                ``HTTPConfig.DEFAULT_MAX_RETRIES`` will be used.
            verify_ssl_cert (bool, optional): Toggles SSL cert verification on/off.  Defaults to
                False (off) because of wsman endpoint behaviors.
        """
        if connection_timeout is None:
            connection_timeout = HTTPConfig.DEFAULT_CONNECTION_TIMEOUT
        self.connection_timeout = connection_timeout

        if read_timeout is None:
            read_timeout = HTTPConfig.DEFAULT_READ_TIMEOUT
        self.read_timeout = read_timeout

        if max_retries is None:
            max_retries = HTTPConfig.DEFAULT_MAX_RETRIES
        self.max_retries = max_retries

        if verify_ssl_cert is None:
            verify_ssl_cert = HTTPConfig.DEFAULT_SSL_CERT_VERIFY
        self.verify_ssl_cert = verify_ssl_cert

    @property
    def timeouts(self):
        """Timeouts tuple for use with requests HttpClient"""
        return self.connection_timeout, self.read_timeout


class CustomHTTPAdapter(requests.adapters.HTTPAdapter):
    """
    Custom extensions to requests' HTTPAdapter

    Allows us to customize max retries and timeouts in one spot, rather than per call
    to request.send(...) every time.
    """

    def __init__(self, http_config):
        assert isinstance(http_config, HTTPConfig), "not an instance of HTTPConfig"
        self.http_config = http_config
        super(CustomHTTPAdapter, self).__init__(max_retries=http_config.max_retries)
        self._logger = logging.getLogger(__name__)

        if not http_config.verify_ssl_cert:
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    # pylint: disable=R0913
    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        """Override and inject a default set of timeouts if timeout=None"""
        if timeout is None:
            timeout = self.http_config.timeouts
        self._logger.debug("Sending request %s", {
            'method': request.method,
            'body': request.body,
            'headers': request.headers,
            'url': request.url,
        })
        response = super(CustomHTTPAdapter, self).send(
            request, stream=stream, timeout=timeout, verify=verify, proxies=proxies)
        self._logger.debug("Got response %s", {
            'encoding': response.encoding,
            'headers': response.headers,
            'content': response.content,
            'reason': response.reason,
            'status_code': response.status_code,
            'url': response.url,
            'is_permanent_redirect': response.is_permanent_redirect,
            'is_redirect': response.is_redirect
        })
        return response


class WSMANAuthConfig(object):
    """Parent class for WSMAN client authentication configurations"""


class WSMANBasicAuthConfig(WSMANAuthConfig):
    """Configuration settings for using HTTP Basic Auth to authenticate with the Drac WSMAN endpoint

    Attributes:
        username (str): The username
        password (str): The password
    """

    DEFAULT_USERNAME = "root"
    """Default username value"""

    DEFAULT_PASSWORD = "calvin"
    """Default password value"""

    def __init__(self, username=None, password=None):
        """Constructor

        Arguments:
            username (str, optional): The user name.
                Defaults to `WSMANBasicAuthConfig.DEFAULT_USERNAME``
            password (str, optional): The password.
                Defaults to `WSMANBasicAuthConfig.DEFAULT_PASSWORD``
        """
        if username is None:
            username = WSMANBasicAuthConfig.DEFAULT_USERNAME
        self.username = username

        if password is None:
            password = WSMANBasicAuthConfig.DEFAULT_PASSWORD
        self.password = password


class WSMANClient(object):
    """
    Low level WSMAN client for DRAC
    """

    def __init__(self, host, port=443, auth_config=None, http_config=None):
        self._logger = logging.getLogger(__name__)

        # check init parameters
        assert host
        assert isinstance(port, int)
        if auth_config is None:
            auth_config = WSMANBasicAuthConfig()
        assert isinstance(auth_config, WSMANBasicAuthConfig)
        if http_config is None:
            http_config = HTTPConfig()
        assert isinstance(http_config, HTTPConfig)

        # setup object fields based on the init params
        if ':' in host:         # Handle IPv6 raw IP
            self._url = "https://[{}]:{}/wsman".format(host, port)
        else:
            self._url = "https://{}:{}/wsman".format(host, port)

        self._auth = requests.auth.HTTPBasicAuth(auth_config.username, auth_config.password)
        self._http_adapter = CustomHTTPAdapter(http_config)
        self._verify = http_config.verify_ssl_cert
        self._invoke_selectors = {}

    def _do_post(self, payload):
        """
        Post the payload to the WSMAN endpoint.  Handle
        """
        self._logger.debug("Begin doing HTTP POST with SOAP message")

        # Prepare the http request
        with requests.Session() as session:
            self._logger.debug("Begin preparing POST request with payload:\n%s", payload)
            try:
                session.mount("https", self._http_adapter)
                request = requests.Request('POST', self._url, auth=self._auth, data=str(payload))
                prepared_request = request.prepare()
            except requests.exceptions.RequestException:
                error_message = "Error preparing HTTP request"
                self._logger.exception(error_message)
                raise WSMANConnectionError(error_message)
            else:
                self._logger.debug("Finished preparing POST request")

            # Submit the http request
            self._logger.debug("Begin submitting POST request")
            try:
                response = session.send(prepared_request, verify=self._verify)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                error_message = "HTTP connection error"
                self._logger.exception(error_message)
                raise WSMANConnectionError(error_message)
            except requests.exceptions.RequestException:
                error_message = "Error preparing HTTP request"
                self._logger.exception(error_message)
                raise WSMANTransportError(error_message)
            else:
                self._logger.debug("Finished submitting POST request")

            # now check response for errors
            self._logger.debug("Begin checking POST response")
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                error_message = (
                    "DRAC WSMAN endpoint returned HTTP code '{}' Reason '{}'"
                    ).format(response.status_code, response.reason)
                self._logger.exception(error_message)
                if response.status_code == 401:
                    raise WSMANAuthError(error_message)
                else:
                    raise WSMANHTTPError(error_message)
            else:
                self._logger.debug("Received non-error HTTP response")
            finally:
                self._logger.debug("Finished checking POST response")

            # make sure its a string
            reply = response.content # Avoid unicode difficulties
            self._logger.debug("Received SOAP reply:\n%s", reply)

        # return it
        return reply

    def identify(self):
        """ Perfrom a WSMAN Identify call """

        envelope = IdentifyEnvelope()

        xml_response = self._do_post(envelope.document)

        return IdentifyResponse(xml_response).dictionary

    def get(self, dcim_class, selectors):
        """ classname is the DCIM class name
        """

        envelope = GetEnvelope(self._url, dcim_class, selectors)

        xml_response = self._do_post(envelope.document)

        return GetResponse(xml_response, dcim_class).dictionary

    def enumerate(self, dcim_class):
        """ Enumerate """

        context = self._get_context(dcim_class)

        items = self._pull_context(dcim_class, context)

        return items


    def _get_context(self, dcim_class):
        """ Get the enumeration context """

        envelope = EnumerateEnvelope(self._url, dcim_class)
        xml_response = self._do_post(envelope.document)
        context = EnumerateResponse(xml_response).context

        return context

    def _pull_context(self, dcim_class, context):
        """ Pull an enumeration context """

        items = []
        end = False

        while not end:
            envelope = PullEnvelope(self._url, dcim_class, context)
            xml_response = self._do_post(envelope.document)
            pull = PullResponse(xml_response, dcim_class)

            items.extend(pull.items)

            # Are we done?
            end = pull.end_of_sequence

        return items

    def _get_invoke_selectors(self, dcim_class):
        """ Get the necessary selectors for a class """

        # Check if we have done this already
        if not dcim_class in self._invoke_selectors:
            self._discover_invoke_selector(dcim_class)

        return self._invoke_selectors[dcim_class]

    def _discover_invoke_selector(self, dcim_class):
        """ Selector Discovery """

        selectors = {'__cimnamespace': 'root/dcim'}
        required = ['CreationClassName', 'SystemCreationClassName',
                    'SystemName', 'Name', 'InstanceID']

        endpoint = self.enumerate(dcim_class)

        # No items/endpoint should be caught by enmuerate

        for key, value in endpoint[0].items():
            if key in required:
                selectors[key] = value

        self._invoke_selectors[dcim_class] = selectors

    def invoke(self, dcim_class, method, properties):
        """ Do an invoke """

        selectors = self._get_invoke_selectors(dcim_class)

        envelope = InvokeEnvelope(self._url, dcim_class, method, selectors, properties)

        xml_response = self._do_post(envelope.document)

        return InvokeResponse(xml_response, dcim_class, method).dictionary
