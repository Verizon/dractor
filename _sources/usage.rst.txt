=======
 Usage
=======

REPLs and bpython
=================

dractor lends itself well to interactive use via a Python REPL.  We recommend
`bpython <https://bpython-interpreter.org/>`_ because it features autocompletion,
introspection, and docstrings.

Setting up an environment
=========================

Dractor is written for use with Python 3.5.  If you are on a system where this
is not the default python, you can create a virtualenv (provided by python-virtualenv
in Ubuntu/Debian).

::
   
   user@host:~$ virtualenv --python /usr/bin/python3.5 venvs/dractor_shed
   Running virtualenv with interpreter /usr/bin/python3.5
   Using base prefix '/usr'
   New python executable in /home/jjh/venvs/dractor_shed/bin/python3.5
   Also creating executable in /home/jjh/venvs/dractor_shed/bin/python
   Installing setuptools, pkg_resources, pip, wheel...done.

Once the virutalenv has been created, activate it.

::

   user@host:~$ source venvs/dractor_shed/bin/activate
   (dractor_shed) user@host:~$ 


Make sure ``tox`` is installed:

::

   (dractor_shed) user@host:~/Software/dractor$ pip install tox
   ...

   
Now you can create the dractor wheel by building and installing it.

::
   
   (dractor_shed) user@host:~/Software/dractor$ make 
   tox -- pylint
   < lots of output >
   _______________________________________________ summary ________________________________________________
   py35: commands succeeded
   congratulations :)

   
Install the dractor wheel into your virtualenv:

::
   
   (dractor_shed) user@host:~/Software/dractor$ pip install dist/dractor-0.0.1-py3-none-any.whl 
   Processing ./dist/dractor-0.0.1-py3-none-any.whl
   Requirement already satisfied: requests>=2.11.1 in /home/jjh/venvs/dractor_shed/lib/python3.5/site-packages (from dractor==0.0.1)
   Collecting jsonschema>=2.5.1 (from dractor==0.0.1)
     Using cached jsonschema-2.5.1-py2.py3-none-any.whl
   Collecting click>=6.6 (from dractor==0.0.1)
     Downloading click-6.7-py2.py3-none-any.whl (71kB)
       100% |████████████████████████████████| 71kB 2.7MB/s 
   Collecting lxml>=3.6.4 (from dractor==0.0.1)
     Downloading lxml-3.7.2-cp35-cp35m-manylinux1_x86_64.whl (7.2MB)
       100% |████████████████████████████████| 7.2MB 177kB/s 
   Installing collected packages: jsonschema, click, lxml, dractor
   Successfully installed click-6.7 dractor-0.0.1 jsonschema-2.5.1 lxml-3.7.2


Also install bpython.

::
   
   (dractor_shed) user@host:~/Software/dractor$ pip install bpython
   Collecting bpython
     Using cached bpython-0.16-py2.py3-none-any.whl
   < lots of output >
   Installing collected packages: bpython
   Successfully installed bpython-0.16

 

Basic connection
================

Connecting to a DRAC is fairly straight forward with dractor.  Launch
bpython and connect to the DRAC by creating a new Client object.

::

  >>> from dractor.dcim import Client
  >>> client = Client('192.168.0.120', 443, 'root', 'calvin')
  >>> client.connect()

Objects exposed by the client
=============================

When the client connects to the DRAC, it issues a WS-Man identify call.
The response to this call contains the version of the Lifecycle
controller.  Using this version, the client object dynamically
constructs all supported classes for that version of the Lifecycle
controller and adds them as attributes to itself.

There are two main kinds of classes created.  Classes that contain the
keyword Factory create objects using information from the DRAC via
WS-Man get or enumerate.  The classes that do not contain factory are
classes that only contain methods to call via WS-Man invoke.  One special
thing to note is that there are a few classes out there that are created
via a factory class but also contain methods.

::

   >>>>>> print("\n".join( [x for x in dir(client) if 'DCIM' in x]))
   DCIM_BIOSEnumerationFactory
   DCIM_BIOSIntegerFactory
   DCIM_BIOSPasswordFactory
   DCIM_BIOSService
   DCIM_BIOSStringFactory
   DCIM_BootConfigSettingFactory
   DCIM_BootSourceSettingFactory
   DCIM_CPUViewFactory
   DCIM_CSPowerManagementService
   DCIM_ComputerSystem
   DCIM_ControllerViewFactory
   DCIM_EnclosureViewFactory
   DCIM_JobServiceFactory
   DCIM_LCEnumerationFactory
   DCIM_LCLogEntryFactory
   DCIM_LCRecordLogFactory
   DCIM_LCService
   DCIM_LCStringFactory
   DCIM_LifecycleJobFactory
   DCIM_NICViewFactory
   DCIM_OSDeploymentService
   DCIM_PhysicalComputerSystemViewFactory
   DCIM_PhysicalDiskViewFactory
   DCIM_PowerSupplyViewFactory
   DCIM_RAIDAttributeFactory
   DCIM_RAIDEnumerationFactory
   DCIM_RAIDIntegerFactory
   DCIM_RAIDService
   DCIM_RAIDStringFactory
   DCIM_SELLogEntryFactory
   DCIM_SELRecordLog
   DCIM_SoftwareIdentityFactory
   DCIM_SoftwareInstallationService
   DCIM_SystemEnumerationFactory
   DCIM_SystemManagementService
   DCIM_SystemViewFactory
   DCIM_VirtualDiskViewFactory


These classes have docstrings that are auto-generated from information
contained in the MOF files.  These docstrings are also used to
automatically generate documentation.

::
   
   >>> help(client.DCIM_LCService.CreateConfigJob)
   Help on method CreateConfigJob in module dractor.dcim.v2303030.DCIM_LCService:

   CreateConfigJob(ScheduledStartTime=None, RebootIfRequired=None) method of dractor.dcim.v2303030.DCIM_LCService.DCIM_LCService instance
    This method is called to apply the pending values set
    using the SetAttribute and SetAttributes methods

    Args:
            ScheduledStartTime (datetime):
                From the Dell MOF description::

                    Not documented

            RebootIfRequired (boolean):
                From the Dell MOF description::

                    Not documented


    Returns:
        dict:
            A dictionary possibly containing these keys:

            **Job** (*CIM_ConcreteJob*)
                From the Dell MOF description::

                    a reference to the ConcreteJob is returned

            **MessageID** (*string*)
                From the Dell MOF description::

                    Error MessageID is returned if the method fails
                        to execute.

            **Message** (*string*)
                From the Dell MOF description::

                    Error Message in english corresponding to the
                        MessageID

            **MessageArguments** (*list of string*)
                From the Dell MOF description::

                    Any dynamic string substitutions for the Message



Informational classes
=====================

The Lifecycle Controller has many classes that provide information
about the computer system.  For example, the ``DCIM_NICView`` class contains
many attributes about the NICs present on the system.  At the WS-Man
level this information is retrieved using Get and Enumerate calls.

The dractor client object exposes these informational classes via
factory objects.  These factory objects provide ``get()`` and
``enumerate()`` methods that return classes populated with information
from the Lifecycle controller.

If the MOF file defines a key attribute for the class, enumerate
returns a dictionary with the value as the index.  If a key is not
defined in the MOF file, common keys such as FQDD will be used or a
unique name will be generated as a last resort.

::

   >>> nic_inventory = client.DCIM_NICViewFactory.enumerate()
   >>> nic_inventory.keys()
   dict_keys(['NIC.Slot.1-1-1', 'NIC.Slot.1-2-1', 'NIC.Embedded.1-1-1', 'NIC.Slot.4-1-1'
   , 'NIC.Embedded.2-1-1', 'NIC.Slot.4-2-1'])


The dictionary returned by ``client.DCIM_NICViewFactory.enumerate()``
contains classes of the type ``DCIM_NICView``.

::
   
   >>> nic1 = nic_inventory['NIC.Slot.1-1-1']
   >>> type(nic1)
   <class 'dractor.dcim.v2303030.DCIM_NICView.DCIM_NICView'>

The ``DCIM_NICView`` object exposes all attributes defined in the
``DCIM_NICView`` MOF file.  These attributes are of type
``DCIMQualifiedValue``.  ``DCIMQualifiedvalue`` exists in order to
support mappings and metadata provided in the MOF file.

For example, the ``DCIM_NICView`` class provides an attribute called
``AutoNegotiation``.  This attribute is returned as an integer value from
the Lifecycle controller.  But there is a mapping specified in the MOF
file that will allow us to translate the integer to a human readable
value.  We manage this translation through the ``DCIMQualifiedvalue``
class so that the end user or program can use either the mapped value
or unmapped value.

::

  >>> type(nic1.AutoNegotiation)
  <class 'dractor.types.qualified.DCIMQualifiedValue'>
  >>> nic1.AutoNegotiation.description
  'Auto Negotiated.'
  >>> nic1.AutoNegotiation.valuemap
  {'0': 'Unknown', '2': 'Enabled', '3': 'Disabled'}
  >>> nic1.AutoNegotiation.value
  'Disabled'
  >>> nic1.AutoNegotiation.unmapped_value
  '3'


``DCIMQualifiedvalue`` objects will show the human readable mapping when
cast to a string.  The ``repr`` will show the current value mapping.

::

   >>> str(nic1.AutoNegotiation)
   'Disabled'
   >>> repr(nic1.AutoNegotiation)
   '<DCIMQualifiedValue 3 -> Disabled>'

Classes generated by factories also contain a special 'dictionary'
attribute.  This contains an unmapped dictionary of all values
returned by the DRAC.

::
   
   >>> pprint(nic1.dictionary)
   {'AutoNegotiation': '3',
   'BusNumber': '10',
   'ControllerBIOSVersion': None,
   'CurrentMACAddress': 'A0:36:9F:CD:41:14',
   'DataBusWidth': '000B',
   'DeviceDescription': 'NIC in Slot 1 Port 1 Partition 1',
   'DeviceNumber': '0',
   'EFIVersion': '5.3.14',
   'FCoEOffloadMode': '3',
   'FCoEWWNN': 'a0:36:9f:cd:41:15',
   'FQDD': 'NIC.Slot.1-1-1',
   'FamilyVersion': '17.5.10',
   'FunctionNumber': '0',
   'InstanceID': 'NIC.Slot.1-1-1',
   'LastSystemInventoryTime': '20161206003601.000000+000',
   'LastUpdateTime': '20161001005420.000000+000',
   'LinkDuplex': '0',
   'LinkSpeed': '0',
   'MaxBandwidth': '0',
   'MediaType': 'SFP_PLUS',
   'MinBandwidth': '0',
   'NicMode': '3',
   'PCIDeviceID': '154d',
   'PCISubDeviceID': '7b11',
   'PCISubVendorID': '8086',
   'PCIVendorID': '8086',
   'PermanentFCOEMACAddress': None,
   'PermanentMACAddress': 'A0:36:9F:CD:41:14',
   'PermanentiSCSIMACAddress': None,
   'ProductName': 'Intel(R) Ethernet 10G 2P X520 Adapter - A0:36:9F:CD:41:14',
   'Protocol': 'NIC',
   'ReceiveFlowControl': '3',
   'SlotLength': '0004',
   'SlotType': '00AB',
   'TransmitFlowControl': '3',
   'VendorName': 'Intel Corp',
   'VirtWWN': '20:00:A0:36:9F:CD:41:15',
   'VirtWWPN': '20:01:A0:36:9F:CD:41:15',
   'WWN': None,
   'WWPN': '20:00:A0:36:9F:CD:41:15',
   'iScsiOffloadMode': '3'}


Invoking methods
================

Let's do a simple example of blinking the chassis UID LED.  The method
to do this is a member of the ``DCIM_SystemManagementService`` class
called ``IdentifyChassis``.  We can use ``help()`` to get the
documentation for this method from the REPL:

::
   
   >>> help(client.DCIM_SystemManagementService.IdentifyChassis)
   Help on method IdentifyChassis in module dractor.dcim.v2303030.DCIM_SystemManagementService:

   IdentifyChassis(IdentifyState, DurationLimit=None) method of dractor.dcim.v2303030.DCIM_SystemManagementService.DCIM_SystemManagementService instance
    This method is used to turn on and off LEDs on the chassis in
    order to identify it.

    Args:
            IdentifyState (int, optional):
                From the Dell MOF description::

                    This parameter represents the requested state of the identifying LED.

                Value Mappings::

                                                    '0' <-> 'Disabled'
                                                    '1' <-> 'Enabled'
                                                    '2' <-> 'Time Limited Enabled'

            DurationLimit (int):
                From the Dell MOF description::

                    This parameter represents the requested time limit in seconds for identifying
                    chassis before the identifying LED turns back off.
                    The parameter shall be specified and non-NULL, if the IdentifyState parameter has
                    value 2 - Time Limited Enabled.


    Returns:
        dict:
            A dictionary possibly containing these keys:

            **MessageID** (*string*)
                From the Dell MOF description::

                    Error MessageID is returned if the method fails
                        to execute.

            **Message** (*string*)
                From the Dell MOF description::

                    Error Message in english corresponding to the
                        MessageID

            **MessageArguments** (*list of string*)
                From the Dell MOF description::

                    Any dynamic string substitutions for the Message


So it looks to be pretty clear how to blink the LED using our client.
Since ``IdentifyState`` is a mapped value, we can supply either '1' or
'Enable' to turn on the LED:

::

   >>> client.DCIM_SystemManagementService.IdentifyChassis(IdentifyState='1')
   {'Message': <DCIMQualifiedValue The command was successful -> The command was successful>, 'MessageID': <DCIMQualifiedValue SYS001 -> SYS001>, 'ReturnValue': <DCIMQualifiedValue 0 -> Completed with No Error>}
   >>> client.DCIM_SystemManagementService.IdentifyChassis(IdentifyState='Disabled')
   {'Message': <DCIMQualifiedValue The command was successful -> The command was successful>, 'MessageID': <DCIMQualifiedValue SYS001 -> SYS001>, 'ReturnValue': <DCIMQualifiedValue 0 -> Completed with No Error>}



Further Reading
===============

From here it would be worthwhile taking a look at the recipe examples
included with dractor to see more complicated usage.
   
