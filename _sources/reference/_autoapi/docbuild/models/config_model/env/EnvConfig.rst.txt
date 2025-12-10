docbuild.models.config.env.EnvConfig
==========================================

.. py:class:: docbuild.models.config.env.EnvConfig(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.config.env.EnvConfig
      :parts: 1


   Root model for the environment configuration (env.toml).


   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].



   .. py:attribute:: server
      :type:  Env_Server
      :value: None


      Server-related settings.



   .. py:attribute:: config
      :type:  Env_GeneralConfig
      :value: None


      General application settings.



   .. py:attribute:: paths
      :type:  Env_PathsConfig
      :value: None


      File system paths.



   .. py:attribute:: build
      :type:  Env_Build
      :value: None


      Build process settings.



   .. py:attribute:: xslt_params
      :type:  dict[str, Any]
      :value: None


      XSLT processing parameters.



   .. py:method:: from_dict(data: dict[str, Any]) -> Self
      :classmethod:


      Convenience method to validate and return an instance.


