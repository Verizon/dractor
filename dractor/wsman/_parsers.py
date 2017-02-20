# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    _parsers.py
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

from lxml import etree

from dractor.exceptions import WSMANFault, WSMANElementNotFound
from ._namespace import NS


class WSMANResponse(object):
    """
    Take XML SOAP responses and parse out the useful bits
    """


    def __init__(self, document, additional_namespaces=None):
        self._logger = logging.getLogger(__name__)

        self._nsmap = copy.deepcopy(NS)
        if additional_namespaces:
            self._nsmap.update(additional_namespaces)
        self._dict = {}

        self._document = document
        parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        self._root = etree.fromstring(self._document, parser=parser)

        self._check_fault()
        self._parse()


    def _parse(self):
        """ Parse and populate internal datastructres """

        pass


    def _check_fault(self):
        """ Check for any WSMAN faults """

        fault = self._root.xpath("/s:Envelope/s:Body/s:Fault", namespaces=self._nsmap)

        if fault:
            fault = fault.pop()
            code = fault.xpath("//s:Code/s:Value", namespaces=self._nsmap)
            subcode = fault.xpath("//s:Code/s:Subcode/s:Value", namespaces=self._nsmap)
            reason = fault.xpath("//s:Reason/s:Text", namespaces=self._nsmap)

            results = {}

            if code:
                results['Code'] = code[0].text

            if subcode:
                results['Subcode'] = subcode[0].text

            if reason:
                results['Reason'] = reason[0].text

            message = "WSMAN call failed: Code: {}, Subcode: {}, Reason: {}".format(results.get('Code', ""),
                                                                                    results.get('Subcode', ""),
                                                                                    results.get('Reason', ""))
            raise WSMANFault(message)

    @property
    def dictionary(self):
        return self._dict

    def get(self, key, default=None):
        """ Check for item """

        return self._dict.get(key, default=default)

    def __getitem__(self, key):

        return self._dict[key]

    def __str__(self):

        pretty = etree.tostring(self._root, pretty_print=True, encoding='unicode')

        return pretty

    def _elements_to_dict(self, results):
        """ Take simple elements and turn to dictionary """

        for element in results:
            tag = etree.QName(element.tag)

            if tag.localname in self._dict: # handle arrays!
                if not isinstance(self._dict[tag.localname], list):
                    values = [self._dict[tag.localname]] # Grab the original
                    self._dict[tag.localname] = values

                self._dict[tag.localname].append(element.text)
            else:
                self._dict[tag.localname] = element.text


class IdentifyResponse(WSMANResponse):
    """
    Take an Identify response and make it useful
    """

    def __init__(self, document):
        additional_namespaces = {
            "dellident": "http://schemas.dell.com/wbem/wscim/1/cim-schema/2/wsmanidentity.xsd"
        }
        super(IdentifyResponse, self).__init__(document, additional_namespaces)

    def _parse(self):
        """ Parse the Response """

        results = self._root.xpath("/s:Envelope/s:Body/wsmid:IdentifyResponse/dellident:*", namespaces=self._nsmap)

        self._elements_to_dict(results)


class WSMANClassResponse(WSMANResponse):
    """
    For responses the contain a DCIM class namespace
    """

    def __init__(self, document, dcim_class):

        # Class specific namespaces
        self._dcim_class = dcim_class
        class_ns = "{}/{}".format(NS['dcim'], self._dcim_class)
        additional_namespaces = {'dcim_class': class_ns}

        super(WSMANClassResponse, self).__init__(document, additional_namespaces)

class GetResponse(WSMANClassResponse):
    """
    Parse the return from a Get
    """

    def _parse(self):

        path = "/s:Envelope/s:Body/dcim_class:{}/dcim_class:*".format(self._dcim_class)
        results = self._root.xpath(path, namespaces=self._nsmap)
        self._elements_to_dict(results)


class EnumerateResponse(WSMANResponse):
    """
    Parse the return from a Enumerate
    We just want the context!
    """

    @property
    def context(self):
        return self._context

    def _parse(self):

        path = "/s:Envelope/s:Body/wsen:EnumerateResponse/wsen:EnumerationContext"

        context = self._root.xpath(path, namespaces=self._nsmap)

        if not context:
            raise WSMANElementNotFound("Failed to find EnumerationContext in Enumerate response")

        self._context = context[0].text


class PullResponse(WSMANClassResponse):
    """
    Parse the return from a Pull
    """

    @property
    def end_of_sequence(self):
        """ Is the the last pull? """

        return self._end_of_sequence

    @property
    def dictionary(self):
        raise NotImplementedError("Pull responses contain a list, use .items")

    @property
    def items(self):
        return self._items

    def _parse(self):

        # Is this the last pull request
        end_of_sequence = self._root.xpath("/s:Envelope/s:Body/wsen:PullResponse/wsen:EndOfSequence",
                                           namespaces=self._nsmap)

        self._end_of_sequence = bool(end_of_sequence)

        path = "/s:Envelope/s:Body/wsen:PullResponse/wsen:Items/dcim_class:{}".format(self._dcim_class)
        items = self._root.xpath(path, namespaces=self._nsmap)

        if not items:
            self._logger.debug("XPath '%s' with map '%s' found no items for doc:\n%s", path, self._nsmap, self._document)

        self._items = []

        for item in items:

            item_dict = {}
            for element in item.getchildren():
                tag = etree.QName(element.tag)
                item_dict[tag.localname] = element.text

            self._items.append(item_dict)


class InvokeResponse(WSMANClassResponse):
    """
    Parse the return from an Invoke
    """

    def __init__(self, document, dcim_class, method):

        self._method = method
        super(InvokeResponse, self).__init__(document, dcim_class)



    def _parse(self):

        path = "/s:Envelope/s:Body/dcim_class:{}_OUTPUT/dcim_class:*".format(self._method)
        items = self._root.xpath(path, namespaces=self._nsmap)

        # Filter any jobs first by translating them
        self._parse_jobid()

        if not items:
            self._logger.error("XPath '%s' with map '%s' failed for doc:\n%s", path, self._nsmap, self._document)
            raise WSMANElementNotFound("No elements found in pull response")

        self._elements_to_dict(items)

    def _parse_jobid(self):
        """ Look for a job id in the body
        <n1:Job>
        <wsa:EndpointReference>
            <wsa:Address>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address>
            <wsa:ReferenceParameters>
               <wsman:ResourceURI>http://schemas.dell.com/wbem/wscim/1/cim-schema/2/DCIM_LifecycleJob</wsman:ResourceURI>
            <wsman:SelectorSet>
                 <wsman:Selector Name="InstanceID">JID_757491269724</wsman:Selector>
                <wsman:Selector Name="__cimnamespace">root/dcim</wsman:Selector>
                </wsman:SelectorSet>
            </wsa:ReferenceParameters>
         </wsa:EndpointReference>
        <n1>
        """



        jobs_path = "//dcim_class:{}_OUTPUT/dcim_class:*[./wsa:EndpointReference]".format(self._method)
        jid_path = ".//wsman:Selector[@Name='InstanceID']"

        jobs = self._root.xpath(jobs_path, namespaces=self._nsmap)

        if len(jobs) > 1:
            # XXX Make a different exception
            raise WSMANElementNotFound("Found too many job ids!")

        if jobs:
            job = jobs.pop()

            jids = job.xpath(jid_path, namespaces=self._nsmap)

            if len(jids) != 1:
                # XXX Make a different exception
                raise WSMANElementNotFound("Found too many InstanceIDs")

            jid = jids[0].text

            job.clear()
            job.text = jid
