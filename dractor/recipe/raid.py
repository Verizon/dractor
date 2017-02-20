# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    raid.py
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
RAID Recipe

"""
from pprint import pprint
import re
import logging

from dractor.recipe.base import ConfiguredRecipe
from dractor.exceptions import (DCIMCommandError, RecipeConfigurationError,
                                RecipeExecutionError, LCDataError)

class RAIDRecipe(ConfiguredRecipe):
    """
    Recipe for configuring RAID
    """

    JSON_SCHEMA = {
        'patternProperties': {
            '.*': {
                'properties': {
                    'Description': {
                        'type': 'string'
                    },
                    'Selectors': {
                        'additionalProperties': False,
                        'properties': {
                            'HardwareAttributes': {
                                'patternProperties': {
                                    '^(Controller|Enclosure|Disk[.]Bay[.][0-9]+)$': {
                                        'patternProperties': {
                                            '^[0-9a-zA-Z]+$': {
                                                'pattern': '.*',
                                                'type': 'string'
                                            }
                                        },
                                        'type': 'object'
                                    }
                                },
                                'type': 'object'
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
                        },
                        'type': 'object'
                    },
                    'Settings': {
                        'additionalProperties': False,
                        'patternProperties': {
                            '^Disk.Virtual.[0-9]+$': {
                                'additionalProperties': False,
                                'properties': {
                                    'Mode': {
                                        'pattern': '^RAID(0|1|10|5|6|50|60)$$',
                                        'type': 'string'
                                    },
                                    'PhysicalDiskIDs': {
                                        'items': {
                                            'pattern': '^Disk.Bay.[0-9]+$',
                                            'type': 'string'
                                        },
                                        'minItems': 1,
                                        'type': 'array',
                                        'uniqueItems': True
                                    },
                                    'SpanDepth': {
                                        'maximum': 1024,
                                        'minimum': 0,
                                        'type': 'integer'
                                    },
                                    'SpanLength': {
                                        'maximum': 1024,
                                        'minimum': 0,
                                        'type': 'integer'
                                    },
                                    'VirtualDiskName': {
                                        'type': 'string'
                                    }
                                },
                                'required': ['Mode', 'SpanDepth', 'SpanLength', 'PhysicalDiskIDs'],
                                'type': 'object'
                            },
                            '^Disk[.]Bay[.][0-9]+$': {
                                'additionalProperties': False,
                                'properties': {
                                    'RaidStatus': {
                                        'pattern': '^(Non-RAID)|(Spare)$',
                                        'type': 'string'
                                    }
                                },
                                'type': 'object'
                            }
                        },
                        'type': 'object'
                    }
                },
                'required': ['Description', 'Selectors', 'Settings'],
                'type': 'object'
            }
        },
        'type': 'object'
    }

    def blink_drive(self, target):
        """
        Blink a drive light

        Arguments:
            target (string): Drive FQDD to blink
        """

        self._logger.info("Blinking drive FQDD %s", target)
        self._client.DCIM_RAIDService.BlinkTarget(target)

    def unblink_drive(self, target):
        """
        UnBlink a drive light

        Arguments:
            target (string): Drive FQDD to UnBlink

        """

        self._logger.info("Unblinking drive FQDD %s", target)
        self._client.DCIM_RAIDService.UnBlinkTarget(target)



    def __init__(self, client, graceful_reboot=True):

        super(RAIDRecipe, self).__init__(client, graceful_reboot)

        # Enumerations to be filled in later
        self._virtual_disks = None
        self._enclosures = None
        self._controllers = None
        self._pdisks = None


    def _select_configuration(self, config_file, profile=None):
        """ Filter out the list of potential RAID configurations by
            applying a series of filter functions against them """

        # We need introspection to get our config
        self._get_enumerations()

        self._logger.info("Picking RAID configuration")

        #
        # Load the confiuration JSON
        #
        config = None
        config_name = None

        configurations = self._load_configuration(config_file)

        # Flatten expands shorthand for raid, enclosure, disk if possible
        configurations = self._flatten_raid_configurations(configurations)

        # If a specific profile was requested, we use that
        if profile:
            if profile in configurations:
                self._logger.info("Picking specified profile '%s'",
                                  profile)
                return (profile, configurations[profile])
            else:
                raise RecipeConfigurationError("The requested profile '{}' does not"
                                               "exist.".format(profile))

        self._logger.debug("Starting with %s potential configurations.  "
                           "Checking for service tag match against %s",
                           len(configurations),
                           self.service_tag)

        for func in [self._filter_by_service_tag, self._filter_by_hardware]:

            (implicit_matches, explicit_matches) = func(configurations)

            if explicit_matches:
                self._logger.info("Proceeding with explicit matches")
                configurations = explicit_matches
            elif implicit_matches:
                self._logger.info("Proceeding with implicit matches")
                configurations = implicit_matches
            else:
                message = "No RAID configuration matches found!"
                self._logger.error(message)
                raise RecipeConfigurationError(message)

        if len(configurations) == 1:
            # This returns a tuple of key, value
            (config_name, config) = configurations.popitem()
            self._logger.info("RAID configuration '%s' matches!",
                              config_name)
        else:
            message = ("Multiple configurations ({}) match host {}!").format(
                ",".join(configurations.keys()), self.service_tag)
            self._logger.error(message)
            raise RecipeConfigurationError(message)

        return (config_name, config)

    def _filter_by_hardware(self, configurations):
        """ Keep only profiles that match our hardware profile """

        self._logger.debug("Filtering based on hardware attributes")

        # Now build an ideal selector for our hardware.  by using this selector,
        # checking for hardware based matches becomes a simple set operation.
        all_flattened = []
        all_flattened.extend(flatten_enumeration(self._pdisks))
        all_flattened.extend(flatten_enumeration(self._controllers))
        all_flattened.extend(flatten_enumeration(self._enclosures))

        attribute_super = set(all_flattened)


        def hardware_filter(selectors):
            """ Function to filter configurations """

            hw_attrib = flatten_dict(selectors['HardwareAttributes'])
            subset = set(hw_attrib)

            if not subset.issubset(attribute_super):
                mismatched = subset.difference(attribute_super)
                for fqdd, attribute, value in mismatched:
                    self._logger.info("Profile requires '%s' for '%s' be '%s'",
                                      attribute, fqdd, value)
                    for i in [self._pdisks, self._controllers, self._enclosures]:
                        if fqdd in i:
                            self._logger.info("Hardware reports '%s' for '%s' is '%s'",
                                              attribute, fqdd, i[fqdd][attribute])
                            break
                    else: # no break
                        self._logger.warning("Can't locate attribute from sources")
                return False
            else:
                return True

        return self._filter(configurations, hardware_filter, 'HardwareAttributes')

    def _flatten_raid_configurations(self, configurations):
        """ We take relative entries like Controller and fill them out
            with complete FQDDs if we have only one enclosure and controller """

        # We can create a controller and enclosure set that includes the
        # 'Controller' and 'Enclosure' defaults.  We need to make sure
        # that all disks are on the same controller and enclosure before
        # expanding shorthand in the configurations
        controllers = set()
        enclosures = set()

        # Enumerate through the physical disk FQDDs
        for disk in self._pdisks:
            try:
                (_, enclosure, controller) = disk.split(':')
            except ValueError:
                self._logger.exception("Failed to split %s into disk, enclosure, and controller",
                                       disk)
                raise LCDataError("Got strange RAID controller data from LC.  Contact SI")

            controllers.add(controller)
            # Remember here, enclosures FQDDs are associated with a
            # controller, so we need to join the controller back in.
            enclosures.add('{}:{}'.format(enclosure, controller))

        # So is everything hanging off the same controller?
        if len(controllers) == 1 and len(enclosures) == 1:

            self._logger.info("Only one controller and enclosure on host, "
                              "allowing implicit Controller, Enclosure, and "
                              "Disk matching")
            self._logger.info("Autoexpanding Enclosure to '%s' and Controller to '%s'",
                              enclosure, controller)

            if len(self._controllers) > 1:
                self._logger.warning("Multiple controllers are on this system (%s), "
                                     "but only one has drives: %s",
                                     ", ".join(self._controllers.keys()), controller)

            if len(self._enclosures) > 1:
                self._logger.warning("Multiple enclosures are on this system (%s), "
                                     "but only one has drives: %s",
                                     ", ".join(self._enclosures.keys()), enclosure)

            enclosure = enclosures.pop()
            controller = controllers.pop()

            def translator(key):
                """ Function for translating implicit keys to FQDDs """

                key = str(key)
                if key == "Enclosure":
                    key = enclosure
                elif key == "Controller":
                    key = controller
                elif re.match(r'Disk\.Virtual\.[0-9]+$', key):
                    key = '{}:{}'.format(key, controller)
                elif re.match(r'Disk\.Bay\.[0-9]+$', key):
                    key = '{}:{}'.format(key, enclosure)

                return key

            configurations = replace_keys(configurations, translator)
        else:
            self._logger.info("Drives exist on multiple controllers/enclosures."
                              "  Skipping configuration implicit matching")

        return configurations


    def _get_enumerations(self):
        """ Grab the various enumerations we will need """

        self._logger.debug("Enumerating host raid attributes")

        self._virtual_disks = self._client.DCIM_VirtualDiskViewFactory.enumerate()
        self._enclosures = self._client.DCIM_EnclosureViewFactory.enumerate()
        self._controllers = self._client.DCIM_ControllerViewFactory.enumerate()
        self._pdisks = self._client.DCIM_PhysicalDiskViewFactory.enumerate()

    def _check_health(self):
        """ Some basic health checks """
        #
        # Check PV status
        #
        bad_disk_status = {
            'RaidStatus': ['Offline', 'Blocked', 'Failed', 'Degraded'],
            'PrimaryStatus': ['Degraded', 'Error'],
            'PredictiveFailureState': ['Smart Alert Present']
        }

        bad_status = {
            'PrimaryStatus': ['Degraded', 'Error']
        }

        self._check_enumeration(self._controllers, bad_status)
        self._check_enumeration(self._enclosures, bad_status)
        self._check_enumeration(self._pdisks, bad_disk_status)

    def _check_enumeration(self, enumeration, bad_status):
        """ For use by _check_health.  See if the there is a degraded element. """

        for fqdd, element_attributes in enumeration.items():
            for attribute, bad_values in bad_status.items():
                status = getattr(element_attributes, attribute).value
                if status in bad_values:
                    message = ("Storage Element {} is bad/degraded.  Attribute {} is {}"
                              ).format(fqdd, attribute,
                                       status)
                    self._logger.error(message)
                    raise RecipeExecutionError(message)

    def _clear_foreign_config(self):
        """ Clear foreign config, if any """

        self._logger.info("Checking for foreign drives")

        controllers_to_clear = []

        for fqdd, attributes in self._pdisks.items():
            if attributes.RaidStatus.value == 'Foreign':
                self._logger.warning("Disk %s is foreign.", fqdd)
                controllers_to_clear.append(fqdd.split(':')[2])

        reboot_needed = False
        if controllers_to_clear:
            for controller in controllers_to_clear:
                result = self._client.DCIM_RAIDService.ClearForeignConfig(Target=controller)
                if result['RebootRequired'].value != 'OPTIONAL':
                    reboot_needed = True

        if reboot_needed:
            self._logger.info("Reboot needed to clear foreign configuration")
            self.queue_jobs_and_reboot([])


    def _reset_config(self):
        """ Clear all RAID configuration """

        self._logger.info("Calling ResetConfig on all controllers")

        reboot_needed = False
        for controller in self._controllers:
            result = self._client.DCIM_RAIDService.ResetConfig(Target=controller)
            if result['RebootRequired'].value != 'OPTIONAL':
                reboot_needed = True

        if reboot_needed:
            self._logger.info("Reboot needed to complete RAID configuration reset")
            self.queue_jobs_and_reboot([])

        # We have changed the config, so enumerate
        self._get_enumerations()

    def _clear_pending_configuration(self, controllers):
        """ Clear any pending configuration on the RAID controller """

        # DeleteVirtualDisk Target=Disk.Virtual.0:RAID.Integrated.1-1
        for target in controllers:
            self._logger.info("Clearing any pending configuration on %s",
                              target)
            try:
                self._client.DCIM_RAIDService.DeletePendingConfiguration(Target=target)
            except Exception as exc: # XXX: This is too wide
                self._logger.exception("Caught Exception clearing pending configuration")
                # This call works if there is or isn't any pending configuration
                # to clear.  So we raise an exception if we get here.
                raise RecipeExecutionError(exc)

    def _clear_virtual_disks(self, controllers):
        """ Remove all virtual disks on the specified controllers """

        virtual_disks = self._client.DCIM_VirtualDiskViewFactory.enumerate()

        for vdisk in virtual_disks:
            for controller in controllers:
                if controller in vdisk:
                    break
            else:               # no break
                self._logger.info("Not removing Virtual Disk %s because"
                                  " we are not configuring that controller",
                                  vdisk)
                continue # This Virtual disk is on a different controller
            self._logger.info("Removing Virtual Disk %s", vdisk)
            try:
                self._client.DCIM_RAIDService.DeleteVirtualDisk(Target=vdisk)
            except Exception: # XXX: This is too wide
                self._logger.exception("Caught Exception clearing Virtual"
                                       "disk configuration.  This isn't OK.")
                raise RecipeExecutionError("Unable to delete Virtual disk %s",
                                           vdisk)


    def _normalize_hotspares(self, raid_conf):
        """ Unassign any hot spares that are no longer hot spares """

        self._logger.info("Normalizing hot spares")

        for disk in raid_conf.all_drives.difference(raid_conf.global_spare_drive_fqdds):
            pd_status = self._client.DCIM_PhysicalDiskViewFactory.get(disk)

            if pd_status.HotSpareStatus.value != 'No':
                self._logger.info("Unassigning spare disk %s", disk)
                self._client.DCIM_RAIDService.UnassignSpare(disk)

    def _normalize_raid_drives(self, raid_conf):
        """ Make sure drives that are to be members of a RAID are in RAID mode """

        self._logger.info("Normalizing RAID drives")

        pd_array = []

        for disk in raid_conf.raid_drive_fqdds.union(raid_conf.global_spare_drive_fqdds):
            pd_status = self._client.DCIM_PhysicalDiskViewFactory.get(disk)

            if pd_status.RaidStatus.value == 'Non-RAID':
                self._logger.info("Converting %s to RAID", disk)
                pd_array.append(disk)

        if pd_array:
            self._client.DCIM_RAIDService.ConvertToRAID(PDArray=pd_array)


    def _create_virtual_disks(self, raid_conf):
        """ Create virtual disks base upon our RAIDConfiguation object """

        for name, conf in raid_conf.virtual_disks.items():
            self._logger.info("Creating virtual disk %s (%s)", name, ", ".join(conf.drive_fqdds))
            self._client.DCIM_RAIDService.CreateVirtualDisk(Target=conf.target,
                                                            PDArray=conf.drive_fqdds,
                                                            VDPropNameArray=conf.vdnames,
                                                            VDPropValueArray=conf.vdvalues)

    def _assign_hot_spares(self, raid_conf):
        """ Assign the hot spares listed in our configuration """

        for disk in raid_conf.global_spare_drive_fqdds:
            pd_status = self._client.DCIM_PhysicalDiskViewFactory.get(disk)

            if pd_status.HotSpareStatus.value != 'Global':
                self._logger.info("Converting %s to global spare", disk)
                # Currently allows only one drive at a time according to MOF
                self._client.DCIM_RAIDService.AssignSpare(disk)

    def _assign_jbods(self, raid_conf):
        """
        Make sure non-raid drives are setup properly
        If there are VDs defined, we need to make each
        drive a single RAID0 volume.  This is because JBOD
        disks show up on bus 2 while jbod show up on bus 1.
        When linux boots, sda then is a JBOD instead of a
        RAID1 (our normal use case).

        If a configuration with Virtual Disks contains drives
        put into JBOD mode, assume that the desired outcome is
        a mix of JBOD and VD
        """

        if raid_conf.virtual_disks and not raid_conf.explicit_jbod:
            for disk in sorted(raid_conf.jbod_drive_fqdds):

                pd_status = self._client.DCIM_PhysicalDiskViewFactory.get(disk)

                if pd_status.RaidStatus.value == 'Non-RAID':
                    self._logger.info("Converting %s to RAID", disk)
                    self._client.DCIM_RAIDService.ConvertToRAID(PDArray=disk)

                self._logger.info("Creating implicit single volume RAID0 for %s", disk)
                target = disk.split(':')[2]
                vdname = "VirtualDisk:{}".format(target)
                vdict = {
                    'Mode': 'RAID0',
                    'SpanDepth': '1',
                    'SpanLength': '1',
                    'PhysicalDiskIDs': [disk]
                }

                new_vd = VirtualDisk("autogenerated", vdname, vdict)
                self._client.DCIM_RAIDService.CreateVirtualDisk(Target=new_vd.target,
                                                                PDArray=new_vd.drive_fqdds,
                                                                VDPropNameArray=new_vd.vdnames,
                                                                VDPropValueArray=new_vd.vdvalues)
        else:
            # Just JBODs
            pd_array = []
            for disk in raid_conf.jbod_drive_fqdds:
                pd_status = self._client.DCIM_PhysicalDiskViewFactory.get(disk)

                if pd_status.RaidStatus.value != 'Non-RAID':
                    self._logger.info("Converting %s to Non-RAID", disk)
                    pd_array.append(disk)

            if pd_array:
                self._client.DCIM_RAIDService.ConvertToNonRAID(PDArray=disk)


    def get_inventory(self):
        """ Print a semi-readable dump of current configuration """

        self._get_enumerations()

        inventory = {}
        inventory['Virtual Disks'] = {k: v.dictionary for k, v in self._virtual_disks.items()}
        inventory['Enclosures'] = {k: v.dictionary for k, v in self._enclosures.items()}
        inventory['Controllers'] = {k: v.dictionary for k, v in self._controllers.items()}
        inventory['Physical Disks'] = {k: v.dictionary for k, v in self._pdisks.items()}

        return inventory

    def configure_raid(self, config_file, profile=None):
        """ Configure RAID """

        self.poll_lc_ready()
        self.normalize_job_queue()

        #
        # Load Configuration
        #
        (my_config_name, my_config) = self._select_configuration(config_file, profile)

        if my_config is None:
            raise RecipeConfigurationError("Somehow got None from _select_configuration.  This"
                                           " should not happen.")

        raid_conf = RAIDConfiguration(my_config_name, my_config, self._pdisks.keys())

        #
        # Clear foreign config
        #
        self._clear_foreign_config()

        #
        # Basic Drive, Enclosure, and Controller Health Check
        #
        self._check_health()

        #
        # Clean up controller, normalize drives
        #
        self._clear_pending_configuration(raid_conf.controllers)
        self._clear_virtual_disks(raid_conf.controllers)
        self._normalize_hotspares(raid_conf)
        self._normalize_raid_drives(raid_conf)

        #
        # Create virtual disks
        #
        self._create_virtual_disks(raid_conf)

        #
        # Hot spares must be assigned after the Vdisks are created
        #
        self._assign_hot_spares(raid_conf)

        #
        # Create any JBODs or single drive RAID0 vds based on configuration
        #
        self._assign_jbods(raid_conf)


        #
        # Create the RAID configuration jobs
        #
        raid_jobs = []
        for target in raid_conf.controllers:
            self._logger.info("Creating configuration job for target %s",
                              target)
            try:
                result = self._client.DCIM_RAIDService.CreateTargetedConfigJob(Target=target)
                raid_jobs.append(result['Job'])
            except DCIMCommandError as exc:
                if exc.message_id == 'STOR026':
                    self._logger.info('No configuration changes were necessary for %s', target)
                else:
                    raise RecipeExecutionError(exc)

        if raid_jobs:
            self.queue_jobs_and_reboot(raid_jobs)

#
# Configuration objects
#
class RAIDConfiguration(object): # pylint: disable=too-many-instance-attributes
    """ Object to represent a RAID configuration """

    def __init__(self, name, configuration, physical_drive_fqdds):
        """ Break down the configuration into an intermediate form """

        self._logger = logging.getLogger(__name__)

        self.name = name
        self._physical_drive_fqdds = set(physical_drive_fqdds)
        self._controllers = None
        self._raid_fqdds = []
        self._jbod_fqdds = []
        self._global_spare_fqdds = []
        self._virtual_disks = {}
        self._explicit_jbod = False # Are any drives explicitly set to JBOD

        for key, setting in configuration['Settings'].items():

            if key.startswith("Disk.Bay"):
                if setting.get('RaidStatus') == 'Non-RAID':
                    self._jbod_fqdds.append(key)
                    self._explicit_jbod = True
                elif setting.get('RaidStatus') == 'Spare':
                    self._global_spare_fqdds.append(key)
                else:
                    raise RecipeConfigurationError("Unknown configuration settings"
                                                   "for {}".format(key))
            elif key.startswith("Disk.Virtual"):
                # Create a VirtualDisk object to represent the virtual disk
                self._virtual_disks[key] = VirtualDisk(name, key, setting)

                # Add the virtual disk members to the list of RAID PDs
                self._raid_fqdds.extend(self._virtual_disks[key].drive_fqdds)
            else:
                self._logger.warning("Configuration '%s': Unknown key in "
                                     "settings: %s", name, key)


        # Perform sanity checks
        self._sanity_raid()
        self._sanity_spares()
        self._santiy_present()

        # Map unmentioned drives to JBOD
        self._implied_drives()

        # Populate controllers
        self._controller_set_from_drives()

    def _sanity_raid(self):
        """ Sanity check RAID vs NON-RAID.  There should be no intersection """

        disk_intersection = set(self._raid_fqdds).intersection(set(self._jbod_fqdds))
        if disk_intersection:
            message = ("Configuration '{}': Drives are configured for "
                       "both raid and non-raid: {}").format(self.name,
                                                            disk_intersection)

            self._logger.error(message)
            raise RecipeConfigurationError(message)

    def _sanity_spares(self):
        """ Sanity check hot spares """

        disk_intersection = set(self._raid_fqdds).intersection(set(self._global_spare_fqdds))
        if disk_intersection:
            message = ("Configuration '{}': Drives are configured for "
                       "both RAID and hot spare: {}"
                      ).format(self.name, disk_intersection)

            self._logger.error(message)
            raise RecipeConfigurationError(message)

        disk_intersection = set(self._jbod_fqdds).intersection(set(self._global_spare_fqdds))
        if disk_intersection:
            message = ("Configuration '{}': Drives are configured for "
                       "both Non-RAID and hot spare: {}"
                      ).format(self.name, disk_intersection)

            self._logger.error(message)
            raise RecipeConfigurationError(message)

    def _santiy_present(self):
        """
        Sanity check that all disks are present (our profile selection should
        catch this, but if a profile is forced, we should cry loudly)
        """

        disks_not_present = self.all_drives - self._physical_drive_fqdds

        if disks_not_present:
            message = ("Configuration '{}': Drives not present on physical "
                       "host: {}").format(self.name, disks_not_present)
            self._logger.error(message)
            raise RecipeConfigurationError(message)

    def _implied_drives(self):
        """
        Default PDs that are not mentioned to Non-RAID
        """

        implied_disks = self._physical_drive_fqdds - self.all_drives

        for disk in implied_disks:
            self._logger.info("Disk %s not mentioned in configuration.  Setting"
                              " to JBOD/single RAID0 mode.", disk)

            self._jbod_fqdds.append(disk)

    def _controller_set_from_drives(self):
        """ Take a list of controllers and return a set of controllers """

        controllers = set()
        for drive in self.all_drives:
            match = re.match(r'Disk\.Bay\.[0-9]+:Enclosure.\w+\.[0-9]-[0-9]:'
                             r'(RAID\.\w+\.[0-9]-[0-9])$', drive)
            if match:
                controllers.add(match.group(1))
            else:
                message = "Malformed drive: {}".format(drive)
                self._logger.error(message)
                raise RecipeConfigurationError(message)

        self._controllers = controllers

    @property
    def all_drives(self):
        """ Return all the drives we are configuring """

        return set(self._raid_fqdds + self._jbod_fqdds + self._global_spare_fqdds)

    @property
    def raid_drive_fqdds(self):
        """ Return an array of FQDDs of drives that are members of virtual disks """

        return set(self._raid_fqdds)

    @property
    def jbod_drive_fqdds(self):
        """ Returns an array of FQDDs of drives that should be in JBOD mode """

        return set(self._jbod_fqdds)

    @property
    def global_spare_drive_fqdds(self):
        """ Returns an array of FQDDs of drives that should be global spares """

        return set(self._global_spare_fqdds)

    @property
    def virtual_disks(self):
        """ Returns a dictionary of Virtual Disk Objects """

        return self._virtual_disks

    @property
    def explicit_jbod(self):
        """ Does this configuration have explicit JBOD drives defined? """

        return self._explicit_jbod

    @property
    def controllers(self):
        """ Return a list of controllers we are targeting """

        return set(self._controllers)

class VirtualDisk(object):
    """ Object to represent a virtual disk """

    RAID0 = 2
    RAID1 = 4
    RAID5 = 64
    RAID6 = 128
    RAID10 = 2048
    RAID50 = 8192
    RAID60 = 16384

    def __init__(self, config_name, virtual_disk, vdict):

        self._config_name = config_name
        self._virtual_disk = virtual_disk

        # We need to make sure to not pass PhysicalDiskIDs to the DRAC
        self._drive_fqdds = vdict.pop('PhysicalDiskIDs')
        self._vdict = vdict
        self._logger = logging.getLogger(__name__)

        mode_string = vdict.pop('Mode')
        if not hasattr(self, mode_string):
            message = ("Configuration {}: Unknown RAID level "
                       "{}").format(config_name, mode_string)
            self._logger.error(message)
            raise RecipeConfigurationError(message)

        self._vdict['RAIDLevel'] = getattr(self, mode_string)

        names, values = dict_to_prop_array(vdict)

        self._names = names
        self._values = values

    @property
    def target(self):
        """ Return the controller FQDD for this virtual disk """

        return self.virtual_disk.split(':')[1]

    @property
    def drive_fqdds(self):
        """ Return an array of the drive FQDDs belonging to this vritual disk """

        return self._drive_fqdds

    @property
    def vdnames(self):
        """ Return an array of configuration names """

        return self._names

    @property
    def vdvalues(self):
        """ Return an array of configuration values """

        return self._values

    @property
    def virtual_disk(self):
        """ Return the virtual disk FQDD defined in the configuration file """

        return self._virtual_disk

    @property
    def config_dict(self):
        """ Return the configuration dictionary for diagnostics """

        return self._vdict
#
# Helper functions
#
def replace_keys(my_dict, transform_key):
    """ Filter through our datastructure  """

    #
    # The idea here is to transform key values and list items
    #
    for key in my_dict.keys():

        new_key = transform_key(key)

        if new_key != key:
            my_dict[new_key] = my_dict.pop(key)
            key = new_key

        if isinstance(my_dict[key], dict):
            replace_keys(my_dict[key], transform_key)
        elif isinstance(my_dict[key], list):
            my_dict[key] = [transform_key(x) for x in my_dict[key]]

    return my_dict

def flatten_enumeration(my_enumeration):
    """ Flatten a dictionary of DCIMAttributeObjects """

    pure_dictionary = {k: v.dictionary for k, v in my_enumeration.items()}

    return flatten_dict(pure_dictionary)


def flatten_dict(my_dict):
    """ Take a nested dictionary and flatten it in to key.lower_key """

    flattened_list = []

    for key in my_dict:
        element = my_dict[key]
        if isinstance(element, dict):
            lower_down = flatten_dict(element)
            for tup in lower_down:
                flattened_list.append((key,) + tup)
        else:
            flattened_list.append((key, element))

    return flattened_list

def dict_to_prop_array(my_dict):
    """ Take a dictionary and return a MOF prop array """

    names = []
    values = []

    for key, value in my_dict.items():
        names.append(key)
        values.append(value)

    return names, values
