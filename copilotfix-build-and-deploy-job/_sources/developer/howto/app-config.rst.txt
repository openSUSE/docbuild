Application Config Changes
==========================

In this section, we cover how to modify the application's configuration settings, including changing file paths and names for configuration files.

Find additional information in section :ref:`user-config`.


Changing the app's config file names
------------------------------------

When you want to change the default names of the app's configuration files, adjust the constant :data:`docbuild.constants.APP_CONFIG_BASENAMES`, :data:`docbuild.constants.PROJECT_LEVEL_APP_CONFIG_FILENAMES`, or both.


Changing the app's config paths
-------------------------------

When you want to change the default paths where the app looks for its configuration files, adjust the constant :data:`docbuild.constants.CONFIG_PATHS`.


.. _app-config-add-new-key:

Adding a new config key
-----------------------

To add a new configuration key ``new_app_feature``, follow these steps:

#. Decide if you want to add the new key at the root level or introduce
   a new section for it.

#. Edit the example file :file:`etc/docbuild/app.example.toml` and add
   your new key.

#.  Adjust the appropriate model in :mod:`docbuild.models.config.app`:

    #. Locate the correct Pydantic model class that corresponds to the
       section of the configuration where your new key belongs.

    #. Add a new field to the model class with the same name as the new key,
       its expected datatype, and add a :func:`~pydantic.Field` definition.

    #. Decide if you need a custom validator for the new key.

#. Integrate the key ``new_app_feature`` into
   :data:`~docbuild.cli.defaults.DEFAULT_APP_CONFIG`.

#. Access the value of the new configuration key through the environment
   configuration object in your code.

#. Write tests.

#. Decide if this is something you need to document in the user or
   developer documentation.
