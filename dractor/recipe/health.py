# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    health.py
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
Check Health

This is a basic program to check system health
"""
import logging

from .base import Recipe

class HealthRecipe(Recipe):

    def check_health_status(self):
        """
        Check the rollup status of the system
        """

        system_view = self._client.DCIM_SystemViewFactory.get('System.Embedded.1')

        # First just check the Primary status
        response = ("The health of your {} {} with service tag {} is "
                    "'{}'").format(system_view.Manufacturer,
                                   system_view.Model,
                                   system_view.ServiceTag,
                                   system_view.PrimaryStatus)

        # All system_view Status attributes are ValueMapped, so we can use
        # int() or ValueMap.unmapped to get the integer value returned by the
        # DRAC.  We can also use str() or ValueMap.mapped to get the string
        # meaning of that integer

        # Use the raw response dictionary to find all status entries
        status_attributes = [x for x in system_view.dictionary.keys() if 'Status' in x]
        status_attributes.remove('PrimaryStatus') # We already saw this
        status_attributes.remove('RollupStatus')  # We don't need the overall rollup status

        # loop through
        for status_attribute in status_attributes:
            status = getattr(system_view, status_attribute)

            if status.unmapped_value != "1": # Use the unmapped value for status
                response += "\nThe status '{}' is reporting '{}'".format(status_attribute,
                                                                         status)


        return response
