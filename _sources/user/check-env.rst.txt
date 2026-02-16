.. _check-environment:

Checking your Environment
=========================

.. NOTE: This section is work in progress and related to issue #9


.. _check-dc-files:

Checking DC Files
-----------------

From time to time it makes sense to check if the DC files referred in
the Docbuild XML configuration exist in the repos.

To check all DC files in all repositories, use the following command:

.. code-block:: shell-session
   :caption: Checking DC files in all repositories

   docbuild --env-config ENV_CONFIG_FILE check dc-files

To check DC files only for a specific product and docset, use the doctype
syntax:

.. code-block:: shell-session
   :caption: Checking DC files for SLES 16.0 in English only

   docbuild --env-config ENV_CONFIG_FILE check dc-files 'sles/16.0/en-us'

If a DC file is missing, the tool will report it, allowing you to take
corrective action.
