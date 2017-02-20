# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    test_client.py
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

# core python
import copy
import logging
import unittest

# third party
import mock
import pytest
import responses
import testfixtures

# this project
from dractor.wsman._client import WSMANClient, HTTPConfig, WSMANBasicAuthConfig

#
# Tests
#


def test_init_w_defaults():
    """Test the WSMANClient.__init__() method with defaults"""
    host = "localhost"
    client = WSMANClient(host)
    assert client


@responses.activate
@pytest.mark.parametrize("init_kwargs", [
    {'host': 'localhost'},
    {'host': 'localhost', 'port': 8888},
    {'host': 'localhost', 'http_config': HTTPConfig(verify_ssl_cert=True)},
    {'host': 'localhost', 'auth_config': WSMANBasicAuthConfig(password="foo")},
])
def test_do_post(init_kwargs):
    """Exercise the private _do_post() method"""

    # create instance of client under test
    client = WSMANClient(**init_kwargs)
    assert client

    # setup responses
    expected_url = "https://{host}:{port}/wsman".format(
        host=init_kwargs['host'],
        port=init_kwargs.get('port', 443))
    fake_response_text = b"fake response from wsman"
    responses.add(
        responses.POST,
        expected_url,
        body=fake_response_text,
        status=200,
        content_type='application/xml')
    payload = "fake"
    reply = client._do_post(payload)
    assert reply == fake_response_text
