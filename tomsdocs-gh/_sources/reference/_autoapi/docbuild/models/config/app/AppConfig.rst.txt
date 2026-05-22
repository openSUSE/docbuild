docbuild.models.config.app.AppConfig
====================================

.. py:class:: docbuild.models.config.app.AppConfig(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.config.app.AppConfig
      :parts: 1


   Root model for application configuration (:file:`config.toml`).


   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].



   .. py:method:: from_dict(data: dict[str, Any]) -> Self
      :classmethod:


      Create an AppConfig instance from a dictionary.


