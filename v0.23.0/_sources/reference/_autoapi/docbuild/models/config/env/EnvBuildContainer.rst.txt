docbuild.models.config.env.EnvBuildContainer
============================================

.. py:class:: docbuild.models.config.env.EnvBuildContainer(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.config.env.EnvBuildContainer
      :parts: 1


   Configuration for container usage.


   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].



   .. py:attribute:: container
      :type:  str
      :value: None


      The container image used for the build environment.


