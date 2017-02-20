# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    bios.py
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
BIOS Recipe

Basic BIOS configuration Recipe.
"""

from collections import OrderedDict
import heapq

from dractor.recipe.base import ConfiguredRecipe
from dractor.exceptions import DCIMCommandError, RecipeConfigurationError, RecipeExecutionError

class BIOSRecipe(ConfiguredRecipe):
    """ Object for dealing with BIOS settings """

    JSON_SCHEMA = {
        'type': 'object',
        'patternProperties': {
            '.*': {
                'properties': {
                    'Description': {
                        'type': 'string'
                    },
                    'Selectors': {
                        'type': 'object',
                        'required': ['Priority', 'SystemIDs'],
                        'additionalProperties': False,
                        'properties': {
                            'Distinct': {
                                'type': 'string'
                            },
                            'Priority': {
                                'maximum': 1024,
                                'minimum': 0,
                                'type': 'integer'
                            },
                            'ServiceTags': {
                                'description': 'Service Tags',
                                'items': {
                                    'pattern': '^[A-Z0-9]{7}$',
                                    'type': 'string'
                                },
                                'minItems': 1,
                                'type': 'array',
                                'uniqueItems': True
                            },
                            'SystemIDs': {
                                'description': 'System IDs provided by the LC',
                                'items': {
                                    'pattern': '^[0-9]+$',
                                    'type': 'string'
                                },
                                'minItems': 1,
                                'type': 'array',
                                'uniqueItems': True
                            }
                        }
                    },
                    'Settings': {
                        'additionalProperties': False,
                        'patternProperties': {
                            '^[0-9a-zA-Z]+$': {
                                'pattern': '^[0-9a-zA-Z.-]+$',
                                'type': 'string'
                            }
                        },
                        'type': 'object'
                    }
                },
                'required': ['Description', 'Selectors', 'Settings'],
                'type': 'object'
            }
        }
    }

    _Target = 'BIOS.Setup.1-1'

    def _select_configuration(self, config_file, profile):
        """ With BIOS settings, we can stack configurations """

        configurations = self._load_configuration(config_file)

        # Allow the specification of a particular profile for testing
        if profile:
            if profile in configurations:
                return configurations[profile]['Settings']
            else:
                raise RecipeConfigurationError("Unknown profile specified")

        matching_profiles = []

        #
        # Since we are stacking configurations, we don't differentiate between
        # implicit and explicit matches when filtering.  We do check for
        # the distinct selector at the end of the filtering and then
        # will only apply configurations containing that.
        #
        for func in [self._filter_by_service_tag, self._filter_by_system_id]:
            (implicit_profiles, explicit_profiles) = func(configurations)
            configurations = dict(list(implicit_profiles.items()) + list(explicit_profiles.items()))

        #
        # If profiles have the distinct selector, we get rid of everything else
        #
        (_, distinct_matches) = self._filter_by_distinct(configurations)
        if distinct_matches:
            self._logger.info("Distinct selector found, using only profiles %s",
                              distinct_matches.keys())
            configurations = distinct_matches

        #
        # Now order the profiles by priority
        #
        for profile in configurations:
            priority = configurations[profile]['Selectors'].get('Priority', 0)
            profile_tuple = (priority, profile)
            matching_profiles.append(profile_tuple)

        #
        # Now stack the configurations
        #
        stacked_config = OrderedDict()
        if matching_profiles:
            heapq.heapify(matching_profiles)
            while matching_profiles:
                profile = heapq.heappop(matching_profiles)[1]
                self._logger.info("Applying settings from '%s'", profile)

                for key in configurations[profile]['Settings']:
                    stacked_config[key] = configurations[profile]['Settings'][key]
        else:
            message = "No matching BIOS configuration found!"
            self._logger.error(message)
            raise RecipeConfigurationError(message)

        return ("Stacked Configuration", stacked_config)

    def inventory(self):
        """ List the current BIOS settings for the host """

        self.poll_lc_ready()
        self._logger.info("Enumerating BIOS settings...")

        bios_settings = self._client.DCIM_BIOSEnumerationFactory.enumerate()
        system_view = self._client.DCIM_SystemViewFactory.get('System.Embedded.1')

        description = ("Automatically from a {} ({})").format(system_view.Model,
                                                              system_view.ServiceTag)

        configuration = {
            "Example Configuration": {
                "Description": description,
                "Selectors": {
                    "SystemIDs": [system_view.SystemID.value],
                    "Priority": 20
                },
                "Settings": {}
            }
        }

        settings = {}

        for _, value in bios_settings.items():
            settings[value.AttributeName.value] = value.CurrentValue.value

        configuration["Example Configuration"]["Settings"] = settings

        return configuration

    def _clear_pending_configuration(self):
        """ Clear any pending configuration """

        self._logger.info("Clearing any pending BIOS configuration.")

        try:
            self._client.DCIM_BIOSService.DeletePendingConfiguration(Target=self._Target)
        except DCIMCommandError as exc:
            if exc.message_id == 'BIOS012':
                self._logger.info('No pending configuration to clear')
            else:
                message = 'Failed to clear pending BIOS configuration'
                self._logger.exception(message)
                raise RecipeExecutionError(exc)

    def configure_bios(self, config_file, profile=None):
        """ Apply BIOS settings from a JSON configuration file """

        self.poll_lc_ready()
        self.normalize_job_queue() # Delete any pending jobs

        (_, settings) = self._select_configuration(config_file, profile)

        self._clear_pending_configuration()

        # Flag for if we had to change a setting
        pending_settings = False

        for key in settings:
            self._logger.info("Getting current setting for %s", key)
            fqdd = "{}:{}".format(self._Target, key)
            bios_setting = self._client.DCIM_BIOSEnumerationFactory.get(fqdd)

            current_value = bios_setting.CurrentValue.value
            possible_values = [x.value for x in bios_setting.PossibleValues]
            expected_value = settings[key]

            if current_value != expected_value:
                if bios_setting.IsReadOnly.value == "true":
                    message = ("Attempt to change read only BIOS "
                               "setting: {}").format(key)
                    self._logger.error(message)
                    raise RecipeConfigurationError(message)

                elif expected_value in possible_values:
                    self._logger.info("Changing %s from %s to %s",
                                      key, current_value, expected_value)
                    self._client.DCIM_BIOSService.SetAttribute(self._Target, key, expected_value)
                    pending_settings = True
                else:
                    message = ("Changing BIOS setting {} to {} is not "
                               "in the list of allowed values: {}").format(
                                   key, expected_value, possible_values)
                    self._logger.error(message)
                    raise RecipeConfigurationError(message)
            else:
                self._logger.info("BIOS setting %s is already %s", key,
                                  current_value)

        # Apply the BIOS settings
        if pending_settings:
            result = self._client.DCIM_BIOSService.CreateTargetedConfigJob(Target=self._Target)
            job_id = result['Job'].value
            self._logger.info("Created BIOS configuration job %s", job_id)
            self.queue_jobs_and_reboot([job_id])
