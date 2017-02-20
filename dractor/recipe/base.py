# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    base.py
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
This is the base recipe class
"""

import logging
import time
import os
import json
import glob

from pprint import pprint

from dractor.exceptions import RecipeConfigurationError, LCHalted, LCTimeout, LCJobError, LCDataError

# Third Party
import jsonschema

class Recipe(object):
    """ Based class for LC Recipes """

    # Terminal states for polling (We do lower() because LC1)
    _JOB_REBOOT_STATES = ['downloaded']
    _JOB_FAIL_STATES = ['failed', 'reboot failed', 'completed with errors']
    _JOB_SUCCESS_STATES = ['completed', 'reboot completed']

    def __init__(self, client, graceful_reboot=False):
        """ Base constructor """

        self._logger = logging.getLogger(__name__)
        self._client = client

        # For when we create a reboot job
        self._graceful_reboot = graceful_reboot

        self._system_id = None
        self._service_tag = None
        self._model = None
        self._lc_version = None
        self._system_view = None
        self._DCIM_JobService = None


    def poll_lc_ready(self, timeout=1800, poll_interval=20):
        """ Make sure the LC is ready """

        self._logger.info("Making sure the LC is ready for commands")

        # {'Message': 'The remote service is available',
        # 'MessageID': 'RSI0001',
        # 'ReturnValue': '0',
        # 'Status': 'Ready'}

        status = {}
        prev_status = {}
        countdown = CountdownIterator(timeout, poll_interval)

        for _ in countdown:

            # This call, introduced in LC Management 1.4.0 is way more reliable
            # Since there are value mappings present here, we will not use the
            # raw dictionary return
            status = self._client.DCIM_LCService.GetRemoteServicesAPIStatus()

            if prev_status.get('MessageID') != status['MessageID'].value:
                prev_status['MessageID'] = status['MessageID'].value
                self._logger.info("Status is '%s': %s: %s", status['Status'],
                                  status['MessageID'], status['Message'])

            message = ""

            server_status = status['ServerStatus']

            if prev_status.get('ServerStatus', 'Unknown') != server_status.value:
                prev_status['ServerStatus'] = server_status.value
                message = "Server Status is '{}'.  ".format(server_status.value)
                self._logger.info(message)

            # The MOF file doesn't list all possible values
            # '6': 'Server has halted at F1/F2 error prompt because of a POST error',
            # '7': 'Server has halted at F1/F2/F11 prompt because there are no bootable devices available',
            # '8': 'Server has entered F2 setup menu',
            # '9': 'Server has entered F11 Boot Manager menu',
            if server_status.unmapped_value in ['6', '8', '9']:
                message = ('Server is halted at F1/F2 error prompt or '
                           'in a configuration menu.')
                self._logger.error(message)
                raise LCHalted(message)

            lc_status = status['LCStatus']

            if prev_status.get('LCStatus') != lc_status.value:
                prev_status['LCStatus'] = lc_status.value
                message = "LCStatus is '{}'.".format(lc_status.value)
                self._logger.info(message)

            # These are in the valuemap:
            # {'1': 'Not Initialized', '0': 'Ready', '3': 'Disabled',
            #  '2': 'Reloading data', '5': 'In Use', '4': 'In Recovery'}
            if lc_status.unmapped_value in ['3', '4']:
                message = ("Server Lifecycle controller is '{}'."
                           "  Please enable and retry.").format(lc_status.value)

                self._logger.error(message)
                raise LCHalted(message)


            if status['Status'].unmapped_value == '0':
                break

            # This is debug because
            self._logger.debug("LC not ready.  Timeout in %s.", countdown)


        else: # No break
            message = ("Lifecycle controller not ready after "
                       "{} seconds.").format(timeout)
            self._logger.error(message)
            raise LCTimeout(message)


    def _get_jobservice(self, fresh=False):
        """ Return a DCIM_JobService object.  DCIM_JobService is a bit
        odd since it doesn't have a key, but it is an object that supports
        both enumeration and invoke.

        Arguments:
            fresh (bool): If set to true, we enumerate again to get a new DCIM_JobService object

        """

        if fresh or not self._DCIM_JobService:
            services = self._client.DCIM_JobServiceFactory.enumerate()
            self._DCIM_JobService = services['DCIM_JobService']

        return self._DCIM_JobService

    def poll_job(self, job_id, timeout=1800, poll_interval=10):
        """ Poll a LC job
            Returns (Did it work, reboot needed) """

        previous_status = None
        reboot_needed = False
        job_success = False

        self._logger.debug("BEGIN_POLLING JID: %s", job_id)

        while timeout > 0:
            cmd_start = time.time()
            self.poll_lc_ready()

            # Since there are no value mappings, we will work with the dictionary
            job_info = self._client.DCIM_LifecycleJobFactory.get(job_id).dictionary

            # lower because LC1
            current_status = job_info['JobStatus'].lower()
            message = job_info['Message']
            message_id = job_info['MessageID']

            if current_status != previous_status:
                self._logger.info("Job state transition from %s to %s",
                                  previous_status, current_status)
                previous_status = current_status

                # Validate new status
                if current_status in self._JOB_FAIL_STATES:
                    self._logger.error("Job %s failed: %s: %s",
                                       job_id, message_id,
                                       message)
                    break

                if current_status in self._JOB_SUCCESS_STATES:
                    self._logger.info("Job %s complete: %s: %s",
                                      job_id, message_id,
                                      message)
                    job_success = True
                    break

                # For firmware updates
                if current_status in self._JOB_REBOOT_STATES:
                    self._logger.info("Job %s complete: %s: %s",
                                      job_id, message_id,
                                      message)
                    job_success = True
                    reboot_needed = True
                    break

            timeout -= poll_interval + int(time.time() - cmd_start)
            time.sleep(poll_interval)
        else: # no break
            self._logger.error("LC job %s timed out.", job_id)

        self._logger.debug("END_POLLING JID: %s", job_id)

        return (job_success, reboot_needed)

    def normalize_job_queue(self):
        """ Right now we just nuke it, but we might want to
            validate in the future """

        self._logger.info("Clearing Job Queue")

        DCIM_JobService = self._get_jobservice()

        DCIM_JobService.DeleteJobQueue(JobID='JID_CLEARALL')

        # Check the LC is important for LC1
        self.poll_lc_ready()

    def poll_jobs(self, jobs):
        """ Poll an array of LC jobs """

        failed_jobs = []

        for job_id in jobs:
            (success, _) = self.poll_job(job_id)
            if success:
                self._logger.info("Job %s complete!", job_id)
            else:
                message = "Job {} failed!".format(job_id)
                self._logger.error(message)
                failed_jobs.append(job_id)

        if failed_jobs:
            raise LCJobError("LC configuration jobs %s failed."
                             " Aborting!", failed_jobs)

    def queue_jobs(self, jobs):
        """ Queue jobs that do not require a reboot """

        DCIM_JobService = self._get_jobservice()
        DCIM_JobService.SetupJobQueue(jobs)
        self.poll_jobs(jobs)

    def queue_jobs_and_reboot(self, jobs=None):
        """ Queue jobs, reboot, and wait for completion """

        DCIM_JobService = self._get_jobservice()

        if not jobs:
            self._logger.info("No jobs to run.  Assuming just a reboot is desired.")
            jobs = []

        # Create a graceful reboot job
        if self._graceful_reboot:
            reboot_desc = 'Graceful Reboot without forced shutdown'
            reboot_type = '2'
        else:
            reboot_desc = 'PowerCycle'
            reboot_type = '1'

        # Create a reboot job
        self._logger.info("Setting up reboot job of type '%s'", reboot_desc)
        reboot_result = DCIM_JobService.CreateRebootJob(RebootJobType=reboot_type)
        reboot_jid = reboot_result['Job']

        jobs.append(reboot_jid)
        self._logger.info("Setting up job queue")
        DCIM_JobService.SetupJobQueue(JobArray=jobs, StartTimeInterval='TIME_NOW')

        # Remove the reboot id now that the queue is setup since we poll it
        # first
        jobs.remove(reboot_jid)

        (success, _) = self.poll_job(reboot_jid)

        if success:
            self._logger.info("Reboot complete. Waiting for jobs to complete.")
            self.poll_jobs(jobs)
        else:
            message = "Reboot job failed."
            self._logger.error(message)
            raise LCJobError(message)


    def _populate_system_info(self):
        """ Get the system id from the LC """

        self._logger.info("Getting system ID")
        system_view = self._client.DCIM_SystemViewFactory.get('System.Embedded.1')

        self._system_id = system_view.SystemID.value
        self._service_tag = system_view.ServiceTag.value
        self._model = system_view.Model.value

        self._logger.info("SystemID: '%s', ServiceTag: '%s', Model: '%s'",
                          self._system_id, self._service_tag, self._model)

        # Sanity check system id.  Brain damaged DRACs in GIG were reporting 0.
        # A racadm racreset got them reporting the correct SystemID
        try:
            if int(self._system_id) == 0:
                raise LCDataError("DRAC thinks its SystemID is 0. "
                                  " DRAC has lost its mind and should be reset.")
        except ValueError:
            self._logger.exception("int('%s') failed", self._system_id)
            raise LCDataError("Got a SystemID from the DRAC that is not a "
                              "string containing a number greater than zero.")

        self._lc_version = system_view.LifecycleControllerVersion.value

        self._logger.info("Lifecycle Controller Version %s", self._lc_version)


    @property
    def service_tag(self):
        """ Service Tag """
        if self._service_tag is None:
            self._populate_system_info()

        return self._service_tag

    @property
    def system_id(self):
        """ System ID """
        if self._system_id is None:
            self._populate_system_info()

        return self._system_id

    @property
    def system_model(self):
        """ Model """
        if self._model is None:
            self._populate_system_info()

        return self._model

class CountdownIterator(object):
    """
    Simple iterator object to help with timeouts when polling
    """

    def __init__(self, timeout, interval=10, debug=False):
        self._timeout = timeout
        self._start_time = None
        self._interval = interval
        self._first_value = True
        self._debug = debug
        self._logger = logging.getLogger(__name__)

    def __iter__(self):
        return self

    def _seconds_left(self):
        """ Return how many seconds are left, if it is the first call,
        initialize the _start_time """
        if not self._start_time:
            self._start_time = time.time()

        seconds_left = self._timeout - (time.time() - self._start_time)
        return max(0, round(seconds_left, 2))

    def __str__(self):
        return str(self._seconds_left())

    def __next__(self):
        if self._seconds_left() > 0:
            if self._first_value:
                self._first_value = False
            else:
                if self._debug:
                    self._logger.debug("Sleeping for %s", self._interval)
                time.sleep(self._interval)
            return self._seconds_left()
        else:
            raise StopIteration()

class ConfiguredRecipe(Recipe):
    """ Base for recipes that use configuration files """

    JSON_SCHEMA=None

    def _load_configuration(self, config_file):
        """ Load and validate a configuration file """

        # To keep working with lc_worker, we check if we
        # have a directory or regular file
        if os.path.exists(config_file):
            if os.path.isdir(config_file):
                configuration_path = "{}/*.json".format(config_file)
                self._logger.info("Looking for configurations in %s",
                                  configuration_path)

                config_files = glob.glob(configuration_path)
                if len(config_files) == 0:
                    message = "No configuration files found!"
                    self._logger.error(message)
                    raise RecipeConfigurationError(message)
            else:
                # Just a plain, old file
                config_files = [config_file]

        else:
            message = "Configuration file or path '{}' does not exist".format(config_file)
            self._logger.error(message)
            raise RecipeConfigurationError(message)

        configurations = {}

        for config_file in config_files:
            try:
                with open(config_file) as inventory:
                    new_configuration = json.load(inventory)
            except:
                message = "Failed to read configuration file '{}'".format(config_file)
                self._logger.exception(message)
                raise RecipeConfigurationError(message)
            else:
                # Validate
                try:
                    jsonschema.validate(new_configuration, self.JSON_SCHEMA)

                except jsonschema.ValidationError:
                    message = "JSON validation failed for configuration file '{}'".format(config_file)
                    self._logger.exception(message)
                    raise RecipeConfigurationError(message)

                except Exception as e:
                    message = ("Unexpected error '{}' while validating "
                               "configuration file '{}'").format(e, config_file)
                    self._logger.exception(message)
                    raise RecipeConfigurationError(message)


                # Check for duplicate keys
                key_intersect = set(configurations.keys()).intersection(set(new_configuration.keys()))
                if key_intersect:
                    # We should only get duplicates if we have a path
                    # passed in as config_file
                    raise RecipeConfigurationError("Duplicate configuration '{}' "
                                                   "in path '{}'".format(key_intersect, config_file))

                # Ok, add to the configuration dictionary
                configurations.update(new_configuration)

        return configurations

    def _filter_by_service_tag(self, configurations):
        """ Filter profiles based on service tag """

        self._logger.info("Filtering by 'ServiceTags' selector")
        def service_match(selectors):
            return self.service_tag in selectors['ServiceTags']

        return self._filter(configurations, service_match, 'ServiceTags')

    def _filter_by_distinct(self, configurations):
        """ If any configuration contains Distinct, return
            no implicit matches, only the Distinct profile """

        self._logger.info("Filtering by 'Distinct' selector")
        return self._filter(configurations, lambda x: True, 'Distinct')

    def _filter_by_system_id(self, configurations):
        """ Filter Profiles by System ID """

        self._logger.info("Filtering by 'SystemIDs' selector")
        return self._filter(configurations, lambda x: self.system_id in x['SystemIDs'], 'SystemIDs')

    def _filter(self, configurations, match_function, selector_name):
        """ Filter by Dell's numeric System ID """

        implicit_matches = {}
        explicit_matches = {}

        for profile in configurations:
            self._logger.info("Evaluating profile '%s'", profile)
            selectors = configurations[profile].get('Selectors', {})

            if selector_name in selectors:
                result = match_function(selectors)
                if isinstance(result, bool):
                    match = result
                    explicit = True
                else:
                    # Uber purpose returns tuple
                    (match, explicit) = result

                if match:
                    if explicit:
                        self._logger.info("Explicit match for selector %s of profile '%s'",
                                          selector_name, profile)

                        explicit_matches[profile] = configurations[profile]
                    else:
                        self._logger.info("Implicit match for selector %s of profile '%s'",
                                          profile, selector_name)
                        implicit_matches[profile] = configurations[profile]

                else:
                    self._logger.info("Mismatch for selector '%s' of profile '%s'",
                                      selector_name, profile)
            else:
                self._logger.info("Implicit match for profile '%s' because selector"
                                  " '%s' is not present", profile, selector_name)
                implicit_matches[profile] = configurations[profile]

        return (implicit_matches, explicit_matches)

    def _select_configuration(self, config_file, profile):
        """ To be completed by child classes """

        raise NotImplementedError("This method is to be completed by children of ConfiguredRecipe")

    def show_selected_configuration(self, config_file, profile=None):
        """ Hook to run configuration selection logic from lc_worker """

        (my_config_name, my_config) = self._select_configuration(config_file, profile)
        print("Profile '{}' selected:".format(my_config_name))
        pprint(my_config)

    def get_selected_configuration(self, config_file, profile=None):
        """ Hook to run configuration selection logic from lc_worker """

        (my_config_name, my_config) = self._select_configuration(config_file, profile)
        return {
            'requested_profile': profile,
            'profile_name': my_config_name,
            'profile_config': my_config,
        }
