docbuild.models.config_model.app.AppConfig
==========================================

.. py:class:: docbuild.models.config_model.app.AppConfig(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.config_model.app.AppConfig
      :parts: 1


   Root model for application configuration (config.toml).


   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].



   .. py:method:: from_dict(data: dict[str, Any]) -> Self
      :classmethod:


      Convenience method to validate and return an instance.


