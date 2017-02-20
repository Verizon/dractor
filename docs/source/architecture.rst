Architecture
============

.. contents::
   :local:
   :depth: 1
   :backlinks: entry


Overview
--------

The dractor client is split into two main components.  These break
down into roughly the How and the What.  The how is how do we talk to
the WS-Man endpoint on the Lifecycle Controller.  How do properly put
together a SOAP request and process the response?  How do we
authenticate?  How do we call a WS-Man method in a generic way?  The
other part is the What.  What API calls are supported by the Lifecycle
Controller?  What arguments are required and optional?  The what part
is the handled via auto-code generation which takes the MOF definition
files provided by Dell and use Jinja2 to auto-generate Python code to
present the Lifecycle Controller WS-Man API.  This auto-generated code
calls the 'how' part of dractor.

Required Reading
----------------

These links will provide the background necessary to understand the
architecture of dractor.

* The :doc:`background document <background>` included with dractor.

* `How to Build and Execute WSMAN Method Commands <http://en.community.dell.com/techcenter/systems-management/w/wiki/4374.how-to-build-and-execute-wsman-method-commands>`_ will give a good understanding of the many things dractor takes care of under the hood.


Dractor Components
-------------------

The main components to dractor are:

* A low level Python WS-Man client.

* A higher level client that provides the DCIM classes to the end user.

* A MOF parser and template engine to auto-generate DCIM classes from the Dell provided MOF files.

* Base classes for the auto-generated DCIM classes to inherit from.

* Special types for data returned by the Lifecycle Controller and required by certain methods (e.g., ``DCIM_SoftwareInstallationService``).

* A collection of recipes to demonstrate how to utilize the dractor client to perform useful tasks.

Python WS-Man client
----------------------

We interact with the Lifecycle Controller via `Web Services Management
(WS-Man or WSMan) <https://en.wikipedia.org/wiki/WS-Management>`_.
This is protocol is built on top of `SOAP
<https://en.wikipedia.org/wiki/SOAP>`_ using HTTPS as the transport.
WS-Man supports a number of basic operations:

 * **Get** and **Enumerate**: Get information from the Lifecycle Controller such as the current value for a BIOS setting or a list of all settings.

 * **Invoke**: Call a remote method such as blinking the chassis identification LED.

 * **Identify**: Returns basic information about the endpoint including the Lifecycle Controller version.

In order to handle these primitive operations, dractor features an
internal low-level WS-MAN client.  This client, ``WSMANClient``, is
located in ``dractor.wsman`` module.  ``WSMANClient`` is responsible
for handling network communication, shielding the rest of dractor from
SOAP/XML, and exposing the fundamental WS-Man methods above.  The
``dractor.wsman`` module is roughly divided into three parts.

* **Transport and interface**: The ``dractor.wsman._client`` module contains ``WSMANClient``.  The client uses `Requests <http://docs.python-requests.org/en/master/>`_ to handle the HTTPS transport layer to talk to the WS-Man endpoint on the Lifecycle Controller.  The WS-Man SOAP endpoint is ``https://<drac-ip>/wsman``.   The client provides get, enumerate, identify and invoke.  The client also performs auto-discovery for Invoke method selectors by performing a WS-Man enumeration on the class being called to determine the proper selectors.
* **SOAP Request Generation**: The ``dractor.wsman._envelopes`` module contains routines used by ``WSMANClient`` to compose SOAP WS-Man requests for Get, Enumerate, Invoke, and Identify.  The SOAP XML documents are composed using `lxml <http://lxml.de/index.html>`_ and basic templates.
* **SOAP Response Parser**: The ``dractor.wsman._parsers`` module contains routines used by ``WSMANClient`` to parse the SOAP responses received from the Lifecycle Controller.  Responses are transformed from XML into Python dictionaries.

The dractor DCIM client
-----------------------

This layer is built on top of the WS-Man client layer.  It provides the
methods called by the code auto-generated from Dell's MOF files.  It
also contains the client exposed to end users of dractor.  This layer
is located in ``dractor.dcim``.

Client Autocreation
~~~~~~~~~~~~~~~~~~~

The client automatically loads and exposes the classes that were
auto-generated from Dell's MOF files based on Lifecycle Controller
version.  The client object exposes, as attributes, classes and
factories supported by the Lifecycle Controller.  The client is
designed to be easy to interact with via a python REPL such as
`bpython <https://bpython-interpreter.org/>`_.

Versioning is done by the iDRAC + Lifecycle Controller release
version, starting with 2.30.30.30 as the minimum supported version.
Given that future DRAC releases are generally backwards compatible,
the client will work with newer versions by choosing the most recent
set of objects.

Get and Enumeratable Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Object that support get or enumerate WS-Man calls need to be created.
This is accomplished via the ``DCIMFactory`` parent class.  A single
instance is returned for calls to the ``get`` factory method while a
dictionary of instances is returned by ``enumerate``.  The keys for
the dictionary are typically FQDDs, as defined by the MOF files.  If
the MOF file does not define a key, there is some logic to
automatically discover a key.  For example, if no key for enumerations is
defined in the MOF file, but there is a FQDD attribute returned by the
Lifecycle Controller, that will be used as the key for the dictionary.


Code Generation
---------------

In order to present the Lifecycle controller API as python modules, we
rely on parsing Dell provided MOF files.  This part of dractor lives
in ``dractor/_code_generation``.  The MOF files are used to
auto-generate code when the dractor wheel is built, there is no
auto-generation when the client itself is run.  The code that is
generated resides in the ``dractor.dcim.v2303030`` for version
2.30.30.30 of the MOF files.  Future versions will be their own
modules following the same pattern.  It should be noted that new
iDRAC + Lifecycle Controller are generally backwards compatible.
This means that there is no hard requirement to ingest MOF files
for every new firmware release unless new calls are desired. 

MOF Files
~~~~~~~~~

Dell provides MOF files with every iDRAC + Lifecycle controller
release.  The files contain information the Lifecycle controller API.
The contain the supported classes, methods, and arguments.  The also
contain valuable metadata like documentation strings or whether a
particular argument is required or optional.

Parsing MOF files
~~~~~~~~~~~~~~~~~

Dractor uses `Igor Dejanovic's textX
<http://igordejanovic.net/textX/>`_ to implement a parser for MOF
files.  The definition for the parser is located in
``_code_generation/data/textex``.  This parser is used to turn a MOF file
into a collection of objects.  The object definitions are in
``_code_generation/mof.py``.


Generating Code to reflect the Dell Lifecycle API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The objects created by the textX parser are used directly in a Jinja2
template to auto-generate a python module from each MOF file.  Here is
where the docstrings are defined.  The template uses generic internal
dractor calls to implement each call.  The templates are located in
``dractor/_code_generation/data/templates``. 

DCIM Base Classes
-----------------

The base classes for the auto-generated code are located in ``dractor.dcim.base``.
The automatically generated code uses these classes as base classes.

* ``DCIMFactory``: This is the base class for any DCIM object that support get or enumerate.

* ``DCIMAttributeObject``: This is the base class for objects returned by ``DCIMFactory`` children.  For example, ``DCIM_NICViewFactory`` yields objects derived from ``DCIMAttributeObject``.

* ``DCIMMethodObject``: This is the base class for any object that have methods.  It contains methods to allow end users to pass in mapped or unmapped values as arguments.  It is responsible for raising an exception if we get back an error from the Lifecycle Controller.  It also performs converts the list of arguments supplied to the method into an array of properties for use at the ``dcim.wsman`` layer.

Some classes support both enumeration and invoke.  We use multiple inheritance in this case.

Types
-----

There are some special data types that are generally used in dractor.
They are defined in ``dractor.types``.

DCIMQualifiedValue
~~~~~~~~~~~~~~~~~~

This is a class that encapsulates every value returned by the
Lifecycle Controller.  The reason for this is that the Dell MOF files
contain metadata on how to handle certain values.  A common form of
metadata is a ``ValueMap``.  This maps between integer values returned or
accepted by the Lifecycle Controller API and human readable
representations.

CIM_Reference
~~~~~~~~~~~~~

While the majority of data passed to the Lifecycle Controller via
WS-Man are just strings, there are occasional ``CIM_Reference`` types that
need to be passed in.  These values need to be enclosed with
additional XML when passed into the Lifecycle Controller.  Since these
types span ``dractor.dcim`` and ``dractor.wsman`` modules, they are in
``dractor.types``.

CIM_SoftwareIdentity
~~~~~~~~~~~~~~~~~~~~

Methods in ``DCIM_SoftwareInstallationService`` require this type in order
to perform software updates.


Recipes
-------

This is where we use the API to do useful things.  The bundled recipes
are included to demonstrate the API and dractor.  Information about
recipes is covered in the :doc:`Recipe documentation<recipe>`
