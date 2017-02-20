# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    qualified.py
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
Our standard return type
"""

class DCIMQualifiedValue(object):
    """
    Simple object to incorporate metadata from the MOF files
    """

    def __init__(self, value, valuemap, qualifiers):

        self._qualifiers = qualifiers
        self._valuemap = valuemap
        self._value = value

        # See if there is a mapping for this value
        if value in valuemap:
            self._mapped = True
            self._mapped_value = valuemap.get(value)
        else:
            self._mapped_value = value
            self._mapped = False

        # Map units for human readability
        units = qualifiers.get("units")
        punit = qualifiers.get("punit")

        if units:
            self._mapped_value = "{} {}".format(self._mapped_value, units)
        elif punit:
            self._mapped_value = "{} {}".format(self._mapped_value, punit)

    @property
    def qualifiers(self):
        """ Return the qualifier dictionary """

        return self._qualifiers

    @property
    def units(self):
        """ Return the Unit qualifier """

        return self._qualifiers.get("units")

    @property
    def punit(self):
        """ Return the PUnit qualifier """

        return self._qualifiers.get("punits")

    @property
    def description(self):
        """ Return the description for this value if any """

        description = self._qualifiers.get("description", ["No description provided"])

        return "\n".join(description)

    @property
    def unmapped_value(self):
        """ Return the original integer value from the DRAC """

        return self._value

    @property
    def value(self):
        """
        Return the string that corresponds to the integer value returned
        by the DRAC
        """

        return self._mapped_value

    @property
    def valuemap(self):
        """
        Return the valuemap we are using
        """

        return self._valuemap

    def __str__(self):
        return self._mapped_value

    def __repr__(self):
        return "<{} {} -> {}>".format(self.__class__.__name__,
                                      self._value,
                                      self._mapped_value)
