.. _update-changelog:

Updating the Changelog
======================

To manage the changelog for this project, it needs the following requirements:

* `towncrier`_: A tool to manage changelogs. This is installed automatically.
* News fragments: Short ReST-formatted files that describe changes.
* A new version: You need to create a new version with :ref:`bump-version.sh <devel-helpers>`.

.. include:: ../../../changelog.d/README.rst
   :start-after: -text-begin-

