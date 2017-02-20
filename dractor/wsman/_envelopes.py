# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    _envelopes.py
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

import copy
import logging
import uuid

# Third Party
from lxml import etree

# Module
from dractor.exceptions import WSMANSOAPEnvelopeError
from dractor.types import CIM_Reference
from ._namespace import NS

LOGGER = logging.getLogger(__name__)

class IdentifyEnvelope(object):
    """
    This is a little bit of an odd one.  It is not derived from our WSMANSoapEnvelope.  I don't know
    if it is worth adding a more fundamental SOAP Envelope class since it would only be for this,
    which is just a template.

    From DSP0266:

    Note the absence of any WS-Addressing namespace, WS-Management namespace, or other versionspecific
    concepts. This message is compatible only with the basic SOAP specification, and the presence
    of the wsmid:Identify block in the s:Body is the embodiment of the request operation.
    """

    ENVELOPE_TEMPLATE = """<?xml version="1.0"?>
    <s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:wsmid="http://schemas.dmtf.org/wbem/wsman/identity/1/wsmanidentity.xsd">
    <s:Header></s:Header>
    <s:Body>
    <wsmid:Identify>
    </wsmid:Identify>
    </s:Body>
    </s:Envelope>
    """

    @property
    def document(self):
        """ Return xml document as string for consumption """

        # Back and forth to make sure our Template is valid XML
        root = etree.fromstring(self.ENVELOPE_TEMPLATE)
        xml = etree.tostring(root, pretty_print=True, encoding='unicode')

        return xml

class WSMANSOAPEnvelope(object):
    """
    This is our basic message structure.  It contains the necessary
    Addressing and WSMAN namespaces that are fundamental to the basic
    wsman calls.

    I use XPath to update the required addressing tags rather than adding them
    dynamically.  I do this to make the basic required structure more clear, as
    far as xml can be clear, in the template itself.
    """

    ENVELOPE_TEMPLATE = """<?xml version="1.0"?>
        <s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
        xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"
        xmlns:wsman="http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd">
            <s:Header>
                <wsa:Action s:mustUnderstand="true"></wsa:Action>
                <wsa:To s:mustUnderstand="true"></wsa:To>
                <wsman:ResourceURI s:mustUnderstand="true"></wsman:ResourceURI>
                <wsa:MessageID s:mustUnderstand="true"></wsa:MessageID>
                <wsa:ReplyTo>
                    <wsa:Address>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address>
                </wsa:ReplyTo>
             </s:Header>
             <s:Body>
            </s:Body>
       </s:Envelope>
    """

    def __init__(self, to_url, action_ns_prefix, action, resource_uri, additional_namespaces=None):

        self._nsmap = copy.deepcopy(NS)

        if additional_namespaces:
            self._nsmap.update(additional_namespaces)

        # NS shortcuts
        self._action_ns_prefix = action_ns_prefix
        self._resource_uri = resource_uri

        # Use a WSMAN SOAP Template to save on the boiler plate
        self._root = etree.fromstring(self.ENVELOPE_TEMPLATE)

        # Update the To
        self._set_text("/s:Envelope/s:Header/wsa:To", to_url)

        # Set the action
        action_uri = "{}/{}".format(self._nsmap[action_ns_prefix], action)
        self._set_text("/s:Envelope/s:Header/wsa:Action", action_uri)

        # Set the Resource URI
        self._set_text("/s:Envelope/s:Header/wsman:ResourceURI", resource_uri)

    def _set_message_id(self):
        """ Set a UUID for each message """

        message_id = self._get_one_xpath("/s:Envelope/s:Header/wsa:MessageID")
        message_id.text = "uuid:{}".format(str(uuid.uuid4()))

    @property
    def document(self):
        """ Return as string for consumption """

        self._set_message_id()  # Make sure to generate a fresh UUID

        xml = etree.tostring(self._root, pretty_print=True, encoding='unicode')

        return xml

    def _get_one_xpath(self, path):
        """ Make sure our path exists and returns one element """

        # Xpath returns an array of matches
        element = self._root.xpath(path, namespaces=self._nsmap)

        if not element:
            raise WSMANSOAPEnvelopeError("Xpath '{}' did not return element".format(path))

        if len(element) != 1:
            raise WSMANSOAPEnvelopeError("Xpath '{}' returned multiple elements".format(path))

        return element.pop()

    def _set_text(self, path, text):
        """ Set the text of the single element returned by path """

        element = self._get_one_xpath(path)
        element.text = text

    def _add_wsman_selectors(self, selectors):
        """ Add the selectors """

        header = self._get_one_xpath("/s:Envelope/s:Header")
        selectorset = etree.SubElement(header, "{{{wsman}}}SelectorSet".format(**self._nsmap))

        for key, value in selectors.items():
            selector = etree.SubElement(selectorset, "{{{wsman}}}Selector".format(**self._nsmap))
            selector.set("{{{wsman}}}Name".format(**self._nsmap), key)
            selector.text = value


class GetEnvelope(WSMANSOAPEnvelope):
    """ SOAP Envelop for Get request """

    ACTION_NS_PREFIX = "wstransfer" # Not used
    ACTION = "Get"

    def __init__(self, to_uri, dcim_class, selectors):
        """ Setup an Enumeration for resource, such as DCIM_NICView """

        resource_uri = "{}/{}".format(NS['dcim'], dcim_class)

        super(GetEnvelope, self).__init__(to_uri,
                                          self.ACTION_NS_PREFIX,
                                          self.ACTION,
                                          resource_uri)
        self._add_wsman_selectors(selectors)


class EnumerationEnvelopes(WSMANSOAPEnvelope):
    """ This forms the basis of our two Enumeration calls, Enumerate and Pull """

    ACTION_NS_PREFIX = "wsen"
    ACTION = None

    def _setup_body(self):
        pass

    def __init__(self, to_uri, dcim_class):
        """ Setup an Enumeration for dcim_class, such as DCIM_NICView """

        resource_uri = "{}/{}".format(NS['dcim'], dcim_class)

        super(EnumerationEnvelopes, self).__init__(to_uri,
                                                   self.ACTION_NS_PREFIX,
                                                   self.ACTION,
                                                   resource_uri)
        self._setup_body()

class EnumerateEnvelope(EnumerationEnvelopes):

    ACTION = "Enumerate"

    def _setup_body(self):
        """ Add the Enumeration element to the body """

        body = self._get_one_xpath("/s:Envelope/s:Body")
        etree.SubElement(body, "{{{wsen}}}Enumerate".format(**self._nsmap))

class PullEnvelope(EnumerationEnvelopes):

    ACTION = "Pull"

    def __init__(self, to_uri, dcim_class, context, max_elements=50):

        self._context = context
        self._max_elements = int(max_elements)

        super(PullEnvelope, self).__init__(to_uri, dcim_class)

    def _setup_body(self):

        body = self._get_one_xpath("/s:Envelope/s:Body")
        pull = etree.SubElement(body, "{{{wsen}}}Pull".format(**self._nsmap))

        context_xml = etree.SubElement(pull, "{{{wsen}}}EnumerationContext".format(**self._nsmap))
        context_xml.text = self._context

        if self._max_elements > 1:
            etree.SubElement(pull, "{{{wsman}}}OptimizeEnumeration".format(**self._nsmap))
            max_elements = etree.SubElement(pull, "{{{wsman}}}MaxElements".format(**self._nsmap))
            max_elements.text = str(self._max_elements)


class InvokeEnvelope(WSMANSOAPEnvelope):


    def __init__(self, to_uri, dcim_class, method, selectors, properties):

        resource_uri = "{}/{}".format(NS['dcim'], dcim_class)
        action = "{}/{}".format(resource_uri, method)

        additional_namespaces = {'dcim_class': resource_uri}
        super(InvokeEnvelope, self).__init__(to_uri, 'dcim_class', method, resource_uri,
                                             additional_namespaces)

        self._add_wsman_selectors(selectors)
        self._add_wsman_properties(method, properties)

    def _add_wsman_properties(self, method, properties):

        body = self._get_one_xpath("/s:Envelope/s:Body")
        element_name = "{{{}}}{}_INPUT".format(self._resource_uri, method)

        input_element = etree.SubElement(body, element_name)

        for key, value in properties:
            prop_name = "{{{}}}{}".format(self._resource_uri, key)
            prop_element = etree.SubElement(input_element, prop_name)

            if isinstance(value, str):
                prop_element.text = value
            elif isinstance(value, CIM_Reference):
                # Construct a cim_reference
                address = etree.SubElement(prop_element,
                                           "{{{wsa}}}Address".format(**self._nsmap))
                address.text = "http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous"
                ref_params = etree.SubElement(prop_element,
                                               "{{{wsa}}}ReferenceParameters".format(**self._nsmap))
                resource_uri = etree.SubElement(ref_params,
                                                "{{{wsman}}}ResourceURI".format(**self._nsmap))
                resource_uri.text = value.resource_uri
                selector_set = etree.SubElement(ref_params,
                                                "{{{wsman}}}SelectorSet".format(**self._nsmap))

                for name, value in value.selector_set.items():
                    selector = etree.SubElement(selector_set,
                                                "{{{wsman}}}Selector".format(**self._nsmap))
                    selector.set("Name", name)
                    selector.text = value
            else:
                message = ("Unkown value type for {}: {} ({})").format(key, type(value), value)
                raise WSMANSOAPEnvelopeError(message)
