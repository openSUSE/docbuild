Environment Config Changes
==========================

In this section, we cover how to modify the environment configuration settings, including changing file paths and names for environment configuration files.

Find additional information in section :ref:`user-config`.

.. _env-config-add-new-key:

Adding a new config key
-----------------------

To add a new configuration key ``config.new_xyz_feature``, follow these steps:

#. Edit the example file :file:`etc/docbuild/env.example.toml`:

   #. Add the new key into the ``config`` section and follow :ref:`config-key-naming-conventions` to ensure consistency with existing keys.

   #. Add a comment *above* the new key to explain its purpose and usage:

      .. code-block:: toml
         :caption: Example of adding a new config key to the environment configuration

         [config]
         # ...
         # new_xyz_feature(bool): Enable the new XYZ feature for enhanced functionality.
         new_xyz_feature = true

      This comment will be included in the generated reference documentation.

#. Adjust the appropriate model in :mod:`docbuild.models.config.env`:

   #. Locate the correct Pydantic model class that corresponds to the
      section of the configuration where your new key belongs.
      In our case it is :class:`~docbuild.models.config.env.EnvConfig`.

   #. Add a new field to the model class with the same name as the new key,
      its expected datatype, and add a :func:`~pydantic.Field` definition.
      This will look something like this:

      .. code-block:: python
         :caption: Example of adding a new field to a Pydantic model for environment configuration

         class EnvConfig(BaseModel):
             # existing fields...

             new_xyz_feature: bool = Field(
                 title="Enable XYZ Feature",
                 description="Enable the new XYZ feature for enhanced ABC functionality.",
                 # default=True,  # Set a default value if appropriate
             )

      If the datatype would be other than boolean, you would add some examples in the Field definition to clarify the expected format.

   #. Decide if you need a custom validator for the new key.

      In most cases it's not necessary and Pydantic's built-in validation will
      be sufficient. However, if you need to enforce specific rules or constraints, implement a custom validator method by adding the following
      decorated method with :func:`~pydantic.model_validator`:

      .. code-block:: python

             # Only add it if you need it.
             @model_validator(mode="after")
             def validate_new_xyz_feature(cls, values):
                 # Implement any necessary validation logic for the new key here
                 return values

      If everything is fine, return the value. However, if there is an issue with the value, raise a :class:`ValueError` to indicate that the
      configuration is invalid.

      Find more details about validators in the Pydantic documentation, especially when the validation logic happens after the initial parsing of the config values.

#. Integrate the key ``config.new_xyz_feature`` into
   :data:`~docbuild.cli.defaults.DEFAULT_ENV_CONFIG`.

   As the key was in the ``config`` section, add it under the ``config``
   key in the nested dictionary structure.

#. Access the value of the new configuration key through the environment
   configuration object in your code.

   For example, if you want to access the configuration in the context
   of a Click command, retrieve it from the :class:`click.Context` object:

   .. code-block:: python
      :caption: Example of accessing the new config key in code

      def cmd_mycommand(ctx: click.Context):
         env: EnvConfig = ctx.obj.envconfig
         if env.config.new_xyz_feature:
            # Implement the functionality that should be enabled
            # when the feature is turned on

   When this function is called, Pydantic already validated the configuration.
   You can expect that all config values are available and have the correct
   datatype.

#. Write tests.

#. Decide if this is something you need to document in the user or
   developer documentation.
