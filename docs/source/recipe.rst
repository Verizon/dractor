Recipes
========

Dractor includes a number of 'recipes'.  A recipe is essentially a
workflow utilizing dractor.  Included are recipes to check the server
health, configure BIOS settings, configure RAID, etc.  These recipes
are intended to serve as examples of how to perform complicated
workflows with dractor.  The recipes are build upon a base class
that provides high level methods for common tasks such as queueing and
polling Lifecycle jobs or checking that the Lifecycle Controller is
ready to accept commands.

Recipe Concepts
---------------

The BIOS and RAID recipes are the more complicated examples.  There
are two main ideas behind how they are structured.  One idea is that
we want to keep the mechanics of the configuration separate from the
specification of the desired end state.  The other idea is that we
should leverage the information from the LC to make smart
configuration choices.

Declarative Configuration Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For the included BIOS and RAID recipes, configurations are stored as
JSON.  Example configuration files are located in
``dractor/examples/configuration``.  Included are examples for both the
RAID and BIOS recipes.  By keeping the desired configurations in a
static format like JSON we can apply schema validation to them to make
sure they are well formed.  We can also modify the recipes that
consume them with enhancements and fixes without having to change the
configurations themselves.

Leveraging Introspection with Selectors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Lifecycle Controller provides a wealth of information about the
system being configured.  Selectors allow for the creation and
automatic selection of configurations based on the hardware of the
machine being configured.  For example, assume there is a population
of servers with three drives where the last two drives are always a
matched pair of SSDs but the first drive may be mechanical or another
matched SSD.  It is possible to create two different configurations
for a two SSD RAID-1 volume.  One configuration will match servers
where the first drive is mechanical and use drives 2 and 3 to form the
array.  The other configuration will match servers where the first
drive is solid state and use drives 1 and 2 to create the RAID-1
volume.  We use 'Selectors' to perform this sort of matching.

In the RAID example configuration file there are multiple entries.
Each entry has a ``Settings`` section and a ``Selectors`` section.
The ``Selectors`` are used to select an appropriate configuration.

::

   "Selectors": {
       "HardwareAttributes": {
           "Disk.Bay.0": {
               "Model": "INTEL SSDSC2BB12"
           },
           "Disk.Bay.1": {
               "Model": "INTEL SSDSC2BB12"
           }
       }
   }

The ``HardwareAttributes`` are matched against the Disk, Enclosure,
and RAID controller enumerations from the Lifecycle Controller.  This
selector will match a server that has Intel SSDs in Bay 0 and Bay 1.
Configurations are selected on a most specific match wins basis.  If
there are multiple specific matches an error is generated.

High level interactions with the LC
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Recipes are all built upon the ``Recipe`` base class located in the
module ``dractor.recipe.base``.  This class provides methods to ease
common tasks that are above the LC API.  Here are some of the included
methods:

* ``poll_lc_ready``: This polls the Lifecycle Controller to make sure that it is ready to accept commands.
* ``normalize_job_queue``: This clears the Lifecycle Controller job queue.
* ``queue_jobs_and_reboot``: This method takes an array of JobIDs and queues them for execution along with a reboot job.
* ``service_tag`` and ``system_id``: These properties make it easy to leverage basic information about the system in order to make configuration decisions.

Running Recipes
---------------

A simple command line utility to run the recipes in included with dractor.
The utility is installed as the command ``dractor``.  The entry point for the
utility is ``dractor.util.cli:main``.  Activate the virtual environment that
has dractor installed to try the ``dractor`` utility.

::

    user@host:~$ source venvs/dractor_shed/bin/activate
    (dractor_shed) user@host:~$ dractor
    Usage: dractor [OPTIONS] HOSTNAME COMMAND [ARGS]...

      Main entry point for application

    Options:
      --username TEXT  Username for DRAC
      --password TEXT  Password for DRAC
      --port INTEGER   HTTPS port for DRAC
      --quiet          Set console logging to WARNING or higher
      --verbose        Set console logging to DEBUG
      --help           Show this message and exit.

    Commands:
      bios     Run the LC bios recipe
      chassis  Control Chassis LEDs
      health   System Health Recipe
      raid     RAID Recipe


Included Recipes
----------------

A number of simple and complex recipes have been included to give a range
of examples on how to use dractor.

**Warning**: The BIOS and RAID recipes will reboot your system.  Only
 use in a test environment.

Chassis
~~~~~~~

This is a very simple recipe that contains methods to control server
power and the UID LED.

Health
~~~~~~

This is a little more complicated recipe.  It checks the overall server
health and reports the areas where problems exist.

BIOS
~~~~

The LC allows the changing of BIOS settings.  This recipe only changes
settings that need changing.  An example configuration for the recipe
is present in ``dractor/examples/configuration``.  Configurations are
matched against the Dell SystemID.

Configurations are applied in order of priority.  This allows settings
that are dependent on each other, such as performance settings, to be
applied in a general order.  General order means each dictionary of
settings is added by priority to an ordered dictionary.  This means
that all lower priority operations will be completed before higher
priority ones.  Also, higher priority settings can override base
settings.

Example configuratoins may be generated using ``dractor <drac> bios
inventory``.  The inventory command will present a configuration based
on the current settings for the system:

::


    (dractor_shed) user@host:~$ dractor 192.168.0.120 bios inventory
    INFO:dractor.recipe.base:Making sure the LC is ready for commands
    INFO:dractor.recipe.base:Status is 'Ready': LC061: Lifecycle Controller Remote Services is ready.
    INFO:dractor.recipe.base:Server Status is 'Powered Off'.
    INFO:dractor.recipe.base:LCStatus is 'Ready'.
    INFO:dractor.recipe.base:Enumerating BIOS settings...
    {
        "Example Configuration": {
            "Description": "Automatically from a PowerEdge T430 (9X92SD2)",
            "Selectors": {
                "Priority": 20,
                "SystemIDs": [
                    "1595"
                ]
            },
            "Settings": {
                "AcPwrRcvry": "Last",
                "AcPwrRcvryDelay": "Immediate",
                "BootMode": "Bios",
                "BootSeqRetry": "Enabled",
                "CollaborativeCpuPerfCtrl": "Disabled",
                "ConTermType": "Vt100Vt220",
                "CorrEccSmi": "Enabled",
                "DcuIpPrefetcher": "Enabled",
                "DcuStreamerPrefetcher": "Enabled",
                "DynamicCoreAllocation": "Disabled",
                "EmbNic1Nic2": "Enabled",
                "EmbSata": "AhciMode",
                "EmbVideo": "Enabled",
                "EnergyEfficientTurbo": "Disabled",
                "EnergyPerformanceBias": "MaxPower",
                "ErrPrompt": "Enabled",
                "ExtSerialConnector": "Serial1",
                "FailSafeBaud": "115200",
                "ForceInt10": "Disabled",
                "GlobalSlotDriverDisable": "Disabled",
                "HddFailover": "Disabled",
                ...
                "UncoreFrequency": "MaxUFS",
                "Usb3Setting": "Disabled",
                "UsbPorts": "AllOn",
                "WorkloadProfile": "NotAvailable",
                "WriteCache": "Disabled",
                "WriteDataCrc": "Disabled"
            }
        }
    }


RAID Recipe
~~~~~~~~~~~

The RAID recipe allows the creation of virtual disks, allocation of
global spares, and setting drives to JBOD mode.  It is a destructive
operation and clears any existing configurations/virtual drives (even
if they are not explicitly mentioned in the configuration file).

If a host only has drives attached a single RAID controller and
Enclosure, we can use shorthand for the controller, enclosure, and
drive FQDDs.  The RAID recipe is designed to support multiple
enclosures and controllers, but right now we enforce this shorthand
via JSON validation.  The RAID controller FQDD ``RAID.Integrated.1-1``
can be referred to as ``Controller``. The Enclosure FQDD can be
referred to as ``Enclosure.Internal.0-1:RAID.Integrated.1-1``. The
Drive FQDD ``Disk.Bay.9:Enclosure.Internal.0-1:RAID.Integrated.1-1``
becomes simply ``Disk.Bay.9``.  This shorthand makes creating
configurations much more compact:

::

   "Disk.Virtual.0": {
       "Mode": "RAID-1",
       "SpanDepth": 1,
       "SpanLength": 2,
       "VirtualDiskName": "OS",
       "PhysicalDiskIDs": [ "Disk.Bay.0", "Disk.Bay.1" ]
   }

This shorthand also appliect in the ``HardwareAttributes`` selector.
If we wanted ot match all machines with a single PERC H710 card and a
26 bay enclosure, we can do:

::

   "HardwareAttributes": {
       "Controller": {
           "ProductName": "PERC H710 Mini"
       },
       "Enclosure": {
           "SlotCount": 26
       }
   }

To discover more selectors, use ``dractor <drac> raid inventory``.

To put a disk into JBOD mode:

::

   "Disk.Bay.0": {
       "RaidStatus": "Non-RAID"
    },

To make a disk a global hot spare:

::

    "Disk.Bay.2": {
        "RaidStatus": "Spare"
    }


Unallocated drives will be either set to a single drive RAID-1 volume
or JBOD depending on if the matcing configruation has virtual disks.
This is done to preserve boot order.  A JBOD drive will probe before
any virtual disks.
