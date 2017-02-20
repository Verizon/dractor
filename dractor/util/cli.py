# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    cli.py
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
Utility for working the DRAC via LifeCycle controller (and sometimes even ssh)
"""

import logging
import json
import sys

# Our module
from dractor.dcim import Client
from dractor.recipe import HealthRecipe, ChassisRecipe, RAIDRecipe, BIOSRecipe
from dractor.exceptions import RecipeException, WSMANConnectionError

# Third Party
import click

LOGGER = logging.getLogger(__name__)

#
# MAIN Group, sets up context
#
@click.group()
@click.option('--username', default='root', help='Username for DRAC')
@click.option('--password', default='calvin', help='Password for DRAC')
@click.option('--port', default=443, help='HTTPS port for DRAC')
@click.option('--quiet', is_flag=True, help='Set console logging to WARNING or higher')
@click.option('--verbose', is_flag=True, help='Set console logging to DEBUG')
@click.argument('hostname')
@click.pass_context
def cli(ctx, hostname, username, password, port, quiet, verbose): # pylint: disable=too-many-arguments
    """ Main entry point for application """

    #
    # Configure Logging
    #
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    logging.basicConfig(level=level)

    if level != logging.DEBUG:
        # Make requests quiet unless we are debugging
        logging.getLogger("requests").setLevel(logging.WARNING)

    try:
        client = Client(hostname, port, username, password)
        client.connect()
    except WSMANConnectionError:
        print("\nFailed to connect to iDRAC")
        sys.exit(1)
    except Exception as exc:
        print("\nGeneral problem creating client")
        sys.exit(1)

    ctx.obj['client'] = client

#
# Recipe Commands
#

#
# RAID group
#
@cli.group(short_help="RAID Recipe")
def raid():
    """ Group for all RAID recipe functions """
    pass

@raid.command(name='apply', help="Run the LC RAID recipe")
@click.option("--profile", help="Force profile selection for testing")
@click.option("--configuration", help="Directory or JSON file contaning configuration")
@click.pass_context
def configure_raid(ctx, profile, configuration):
    """ Use the RAID recipe to configure RAID """

    raid_recipe = RAIDRecipe(ctx.obj['client'])
    raid_recipe.configure_raid(configuration, profile=profile)


@raid.command(name='profile', help="Show what profile matches the host")
@click.option("--profile", help="Force profile selection for testing")
@click.option("--configuration", help="Directory or JSON file contaning configuration")
@click.pass_context
def show_raid_configuration(ctx, profile, configuration):
    """ Get the matching RAID profile or fail """

    raid_recipe = RAIDRecipe(ctx.obj['client'])
    config_data = raid_recipe.get_selected_configuration(configuration, profile=profile)
    print(json.dumps(config_data, indent=4, sort_keys=True))


@raid.command(name='inventory', help="Show how host RAID is currently configured")
@click.pass_context
def get_raid_inventory(ctx):
    """ Ask the LC about the RAID properties necessary for creating configurations """

    raid_recipe = RAIDRecipe(ctx.obj['client'])
    inventory = raid_recipe.get_inventory()

    print(json.dumps(inventory, indent=4, sort_keys=True))

#
# BIOS Group
#
@cli.group(help="Run the LC bios recipe")
def bios():
    """ BIOS Recipe Commands """
    pass


@bios.command(name='inventory', help="Show how host BIOS is currently configured")
@click.pass_context
def get_bios_inventory(ctx):
    """ Get list of BIOS settings """

    bios_recipe = BIOSRecipe(ctx.obj['client'])
    settings = bios_recipe.inventory()

    print(json.dumps(settings, indent=4, sort_keys=True))


@bios.command(name='profile', help="Show how host is currently configured")
@click.option("--profile", help="Force profile selection for testing")
@click.option("--configuration", help="Directory or JSON file containing configuration")
@click.pass_context
def show_bios_configuration(ctx, profile, configuration):
    """ Show matching BIOS configuration """

    bios_recipe = BIOSRecipe(ctx.obj['client'])
    config_data = bios_recipe.get_selected_configuration(configuration, profile=profile)
    print(json.dumps(config_data, indent=4, sort_keys=True))


@bios.command(name='apply', help="Show how host is currently configured")
@click.option("--configuration", help="Directory or JSON file contaning configuration")
@click.pass_context
def configure_bios(ctx, configuration):
    """ Configure system BIOS """

    bios_recipe = BIOSRecipe(ctx.obj['client'])
    bios_recipe.configure_bios(configuration)


#
# Health Group
#

@cli.group(help="System Health Recipe")
def health():
    """ Group for Health commands """
    pass


@health.command('status', help="Check HEALTH attributes")
@click.pass_context
def health_status(ctx):
    """ Call set_health_attributes """

    health_recipe = HealthRecipe(ctx.obj['client'])
    status = health_recipe.check_health_status()

    print(status)

@cli.group(help="Control Chassis LEDs")
def chassis():
    """ Group for chassis LED """

@chassis.command('blinkuid', help="Blink the chassis UID LED")
@click.pass_context
def blink_uid(ctx):
    """ Turn on the Identify LED """

    chassis_recipe = ChassisRecipe(ctx.obj['client'])
    chassis_recipe.uid_led_on()

@chassis.command('unblinkuid', help="UnBlink the chassis UID LED")
@click.pass_context
def unblink_uid(ctx):
    """ Turn off the Identify LED """

    chassis_recipe = ChassisRecipe(ctx.obj['client'])
    chassis_recipe.uid_led_off()

@chassis.command('power_on', help="Turn on the system")
@click.pass_context
def power_on(ctx):
    """ Turn on the system """

    chassis_recipe = ChassisRecipe(ctx.obj['client'])
    chassis_recipe.power_on()

@chassis.command('power_off', help="Turn off the system")
@click.pass_context
def power_off(ctx):
    """ Turn off the system """

    chassis_recipe = ChassisRecipe(ctx.obj['client'])
    chassis_recipe.power_off()

@chassis.command('power_cycle', help="Power cycle the system")
@click.pass_context
def power_cycle(ctx):
    """ Power cycle the system """

    chassis_recipe = ChassisRecipe(ctx.obj['client'])
    chassis_recipe.power_cycle()

@chassis.command('status', help="Status of the system")
@click.pass_context
def status(ctx):
    """ Power cycle the system """

    chassis_recipe = ChassisRecipe(ctx.obj['client'])
    chassis_recipe.status()

def main():
    """ setuptools entrypoint """
    # The decorators handle all missing keyword args, so disable them:
    # pylint: disable=no-value-for-parameter,unexpected-keyword-arg
    cli(obj={})
