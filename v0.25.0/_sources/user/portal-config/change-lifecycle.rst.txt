.. _change-lifecycle:

Changing the Lifecycle of a Release
===================================

Every product has a lifecycle that defines the stages it goes
through from initial development to end-of-life:

* ``beta``

  The release is in the beta stage, meaning it is still
  under development and may contain bugs.
  It is not recommended for production use, however, it is
  visible in the portal but marked as "Beta" to indicate
  its status.

* ``supported``

  The release is actively maintained and supported and
  receives regular updates and bug fixes.
  It can be built without restrictions.

* ``unsupported``

  The release is no longer supported and does not receive
  updates or bug fixes.
  Product versions can be built without restrictions, but
  they are not visible on the portal. Only the ZIP archives
  of the product versions are available for download.

The lifecycle of a release is defined in the ``<docset>``
element in the .

To change the lifecycle of a release, change the ``lifecycle``
attribute to the desired value.
