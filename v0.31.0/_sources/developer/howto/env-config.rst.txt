Environment Config Changes
==========================

In this section, we cover how to modify the environment configuration settings, including changing file paths and names for environment configuration files.

Find additional information in section :ref:`user-config`.

.. _env-config-add-new-key:

Adding a new config key
-----------------------

To add a new configuration key, follow these steps. In this example, we'll add a key named ``new_xyz_feature`` to the ``[general]`` section. The feature is configured with a string like ``"on:5"``, where ``on`` is the status and ``5`` is the level.

#. Define a data class (if necessary).

   For complex data, it's a good practice to define a :func:`~dataclasses.dataclass` to hold the structured data.

   .. code-block:: python

      from dataclasses import dataclass

      @dataclass
      class FeatureSetting:
          status: str
          level: int

#. Edit the example file :file:`etc/docbuild/env.example.toml`.

   Add the new key and a comment explaining its purpose and format.

   .. code-block:: toml
      :caption: Example of adding a new config key to the environment configuration

      [general]
      # ...
      # new_xyz_feature(string): Enable the new XYZ feature.
      # Format: "status:level", e.g., "on:5"
      new_xyz_feature = "on:5"

#. Adjust the appropriate model in :mod:`docbuild.models.config.env`.

   a. Add a new field to the model. The type hint should be the custom class you defined.

      .. code-block:: python
         :caption: Example of adding a new field to a Pydantic model

         class EnvGeneral(BaseModel):
             # ...
             new_xyz_feature: FeatureSetting = Field(
                 default="on:5",
                 title="XYZ Feature Setting",
                 description="Setting for the new XYZ feature.",
             )

   b. Add a :func:`~pydantic.field_validator` to parse the input string into your custom object.

      The validator takes the raw string from the TOML file and returns an instance of your ``FeatureSetting`` class.

      .. code-block:: python

         @field_validator("new_xyz_feature", mode="before")
         @classmethod
         def validate_new_xyz_feature(cls, v: str) -> FeatureSetting:
             if not isinstance(v, str):
                 raise ValueError("must be a string in format 'status:level'")
             try:
                 status, level_str = v.split(":")
                 level = int(level_str)
                 if status not in ("on", "off"):
                     raise ValueError("status must be 'on' or 'off'")
                 return FeatureSetting(status=status, level=level)
             except (ValueError, TypeError) as e:
                 raise ValueError(f"invalid format: {e}") from e

   c. Consider if a custom serializer is needed.

      To control how the ``FeatureSetting`` object is converted back to a string (e.g., for :meth:`~pydantic.BaseModel.model_dump`), add a :func:`~pydantic.field_serializer`.

      .. code-block:: python

         @field_serializer("new_xyz_feature")
         def serialize_new_xyz_feature(self, feature: FeatureSetting) -> str:
             return f"{feature.status}:{feature.level}"

#. Access the value in your code.

   You can now access the structured data from the configuration object.

   .. code-block:: python
      :caption: Example of accessing the new config key in code

      def cmd_mycommand(ctx: click.Context):
         env: EnvConfig = ctx.obj.envconfig
         feature_setting = env.general.new_xyz_feature
         if feature_setting.status == "on":
             # Use feature_setting.level
             ...

#. Write tests.

#. Decide if this is something you need to document in the user or developer documentation.
