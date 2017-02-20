Background
==========

.. contents::
    :local:
    :depth: 1
    :backlinks: entry

Overview
--------

The Dell Lifecycle Controller provides a way to programatically
manage servers.  An end user can perform BIOS configuration, firmware
upgrades, and RAID configuration all through the Lifecycle Controller
by using the DMTF's Web Services Management standard (WS-Man or
WSMAN).  The dractor library targets the second generation of this API
which is available on 12G Dell servers and greater.  The goal of
dractor is to provide simple, programmatic access to this API via
Python3.

Web Services Management
-----------------------

`Web Services Management <http://www.dmtf.org/standards/wsman>`_ is a
DMTF standard.  It is a `SOAP-based
<https://en.wikipedia.org/wiki/SOAP>`_ protocol that allows for
management of computer systems.  Multiple vendors adopted this
protocol, but dractor is focused solely on supporting Dell 12G and
greater servers.

Dell's Lifecycle Controller runs as a process on the iDRAC.  Dractor uses
WS-Man to communicate with the Lifecycle Controller over HTTPS.

WS-Man supports a number of fundamental operations.  The most important are:

* **Enumerate**: Enumeration will return all instances of a particular type.  For example, to obtain information about all the NICs in a server, you can enumerate the ``DCIM_NICView`` class.

* **Get**: Get retrieves information about a particular hardware or software component for a given class.  Components are usually referenced by their FQDD (Fully Qualified Device Descriptor).  For example, to request information about the first NIC in a system, you would perform a ``get`` of the class ``DCIM_NICView`` for the FQDD ``NIC.Slot.1-1-1``.

* **Invoke**: Invoke calls a remote method on the Lifecycle Controller.  For example, to power cycle a server, you would ``invoke`` the method ``RequestPowerStateChange`` provided by the ``DCIM_CSPowerManagementService`` class.

Dractor abstracts these operations for you, but it is still important to be
familiar with them.

Dell DCIM Profile Documents
---------------------------

The Dell DCIM Profiles are a set of documents grouped into general
areas that document the classes and methods supported by the Lifecycle
Controller via WS-Man.  These classes are extensions of the classes
defined in the `DMTF's Common Information Model
<http://www.dmtf.org/standards/cim>`_.  This model defines a set of
classes that structure how information is provided by the Lifecycle
Controller.  Dell has extended the CIM as `DCIM - Dell CIM Extensions
<http://en.community.dell.com/techcenter/systems-management/w/wiki/1837>`_

In the previous section on WS-Man a few classes like ``DCIM_NICView`` were
mentioned in passing.  The ``DCIM_NICView`` class is part of the `DCIM
Simple NIC Profile
<http://en.community.dell.com/techcenter/extras/m/white_papers/20347676>`_.
This profile contains extensive documentation on the ``DCIM_NICView`` and
related classes.

It is worthwhile browsing the `DCIM Extensions Library Profile
Collection
<http://en.community.dell.com/techcenter/systems-management/w/wiki/1906.dcim-library-profile>`_
to get a feel for what is possible through the Lifecycle Controller.

Managed Object Format
---------------------

`Dell Managed Object Format
<http://en.community.dell.com/techcenter/systems-management/w/wiki/1840.dcim-library-mof>`_
files provide a computer friendly description of the classes and
methods supported by the Lifecycle Controller.  A bundle of MOF files
are released with every iDRAC + Lifecycle Controller software release.
In addition to documenting supported classes, attributes and methods,
they contain valuable metadata such as docstrings or how to translate
values returned by the Lifecycle Controller.  Dractor uses these MOF
files to auto-generate Python code and documentation.


Using the Lifecycle API through dractor
---------------------------------------

Dractor attempts to present the Dell CIM Extensions provided by the
Lifecycle Controller directly in Python.  It does things to make the
API work well in Python, but overall takes great care to present the
API as-is.

For example, to power cycle using WS-Man from the command line:

::

    wsman invoke -a "RequestStateChange" http://schemas.dell.com/wbem/
    wscim/1/cim-schema/2/root/dcim/DCIM_ComputerSystem?CreationClassName=
    "DCIM_ComputerSystem",Name="srv:system" -h 192.168.0.120 -P 443 -u root
    -p calvin -c Dummy -y basic -V –v -k "RequestedState=2"

Using dractor, this call becomes much more straight forward:

.. code-block:: python

   from dractor.dcim import Client
   client = Client('192.168.0.120', 443, 'root', 'calvin')
   client.connect()
   client.DCIM_ComputerSystem.StateChange(RequestedState=2)


To get a feel for what dractor does behind the scenes, you can take a look at
the process of interacting with WS-Man via the command line in
`How to Build and Execute WSMAN Method Commands <http://en.community.dell.com/techcenter/systems-management/w/wiki/4374.how-to-build-and-execute-wsman-method-commands>`_.

Dractor recipes
---------------

Dractor contains a number of recipes to demonstrate using the
Lifecycle Controller API to do useful things.  Recipes are based
on a class that provides higher level functionality such as polling
for Lifecycle Controller readiness.

----

Additional Resources
--------------------

Dell
~~~~

* `Dell's Tech Center <http://en.community.dell.com/techcenter/>`_:

  * `Tech Center's Wiki <http://en.community.dell.com/techcenter/systems-management/w/wiki/1837>`_

  * `How to Build and Execute WSMAN Method Commands <http://en.community.dell.com/techcenter/systems-management/w/wiki/4374.how-to-build-and-execute-wsman-method-commands>`_

  * `DRAC <http://en.community.dell.com/techcenter/systems-management/w/wiki/3204.dell-remote-access-controller-drac-idrac>`_

DMTF
~~~~

The Distributed Management Task Force (DMTF) maintains a website with various specifications etc.

* Several PDFs are available for various specifications associated with `WS-Man <https://www.dmtf.org/standards/wsman>`_

----

Terminology
-----------

.. list-table::
   :header-rows: 1

   * - Term
     - Definition
   * - Common Information Model (CIM)
     -
           The Common Information Model (CIM) is an open standard that defines how managed elements in an IT
           environment are represented as a common set of objects and relationships between them. This is
           intended to allow consistent management of these managed elements, independent of their manufacturer
           or provider. CIM provides a common definition of management information for systems, networks,
           applications and services, and allows for vendor extensions.

           -- From `http://en.community.dell.com/techcenter/systems-management/w/wiki/1838`
   * - Dell CIM Extensions Library (DCIM)
     -
           Welcome to the Dell CIM Extensions Library. This DCIM area contains specifications of Dell-specific system
           management instrumentation for server, desktop, and mobile platforms. Read more about the purpose and scope of this library.

           Dell systems are moving to employ the DMTF Common Information Model (CIM) as the data format for local and
           remote system management. In some cases, Dell needs some extended properties and functions that are not
           described in the current CIM standards, and we create "extension" specs to cover these cases. Extension specs are published here.

           The library also contains other informative documents, such as white papers and diagrams of CIM class structures and instance structures.

           -- From `http://en.community.dell.com/techcenter/systems-management/w/wiki/1837`
   * - Web Services Management (WS-Man or WSMAN)
     -
           The DMTF’s Web Services Management (WS-Man) provides interoperability between management applications and managed resources, and
           identifies a core set of web service specifications and usage requirements that expose a common set of operations central to all systems
           management. WS-Man has been adopted and published by the International Organization for Standardization (ISO) as ISO/IEC 17963:2013.

           A SOAP-based protocol for managing computer systems (e.g., personal computers, workstations, servers, smart devices), WS-Man supports web
           services and helps constellations of computer systems and network-based services collaborate seamlessly.

           The standard has the ability to:

           * Get, put (update), create, and delete individual resource instances, such as settings and dynamic values
           * Enumerate the contents of containers and collections, such as large tables and logs
           * Subscribe to events emitted by managed resources
           * Execute specific management methods with strongly typed input and output parameters

           The protocol and transport in WS-Man have been decoupled, to ensure interoperability is not dependent on specific versions of
           encryption algorithms, such as Transport Layer Security (TLS).

           -- From the `DMTF page on wsman <https://www.dmtf.org/standards/wsman>`_
   * - FQDD
     -

           Fully Qualified Device Descriptor.  It is a string that references a particular part of the computer system (such as a NIC) or software instance.  It can be thought of as a primary key in a database.
