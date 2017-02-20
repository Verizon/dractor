# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    chassis.py
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
Chassis Recipe

Some basic chassis routines, mainly for the command line interface
"""

from dractor.recipe.base import Recipe
from dractor.exceptions import DCIMCommandError

class ChassisRecipe(Recipe):
    """
    Control some of the blinky lights
    """

    def uid_led_on(self):
        """
        Turn on the Chassis Identify LED
        """

        self._logger.info("Turning on the chassis Identify LED")
        self._client.DCIM_SystemManagementService.IdentifyChassis('1')

    def uid_led_off(self):
        """
        Turn off the Chassis Identify LED
        """

        self._logger.info("Turning off the chassis Identify LED")
        self._client.DCIM_SystemManagementService.IdentifyChassis('0')

    def power_off(self):
        """
        Chassis Power Off
        """

        self._logger.info("Turning off system")
        try:
            self._client.DCIM_CSPowerManagementService.RequestPowerStateChange(PowerState='8')
        except DCIMCommandError as exc:
            self._logger.exception("Failed to set power state")
            self._logger.error("Failed to set the system power to on, perhaps system is already on")

    def power_on(self):
        """
        Chassis Power On
        """

        self._logger.info("Turning on system")
        try:
            self._client.DCIM_CSPowerManagementService.RequestPowerStateChange(PowerState='2')
        except DCIMCommandError as exc:
            self._logger.exception("Failed to set power state")
            self._logger.error("Failed to set the system power to on, perhaps system is already on")

    def power_cycle(self):
        """
        Cycle Chassis Power
        """

        self._logger.info("Power cycling system")
        try:
            self._client.DCIM_CSPowerManagementService.RequestPowerStateChange(PowerState='9')
        except DCIMCommandError as exc:
            self._logger.exception("Failed to set power state")

    def status(self):
        """
        Return a chassis status summary
        """

        status = self._client.DCIM_LCService.GetRemoteServicesAPIStatus()
        self._logger.info("LC status is %s", status['LCStatus'].value)
        self._logger.info("Server status is %s", status['ServerStatus'].value)
