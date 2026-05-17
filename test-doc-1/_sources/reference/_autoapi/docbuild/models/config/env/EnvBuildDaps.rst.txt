docbuild.models.config.env.EnvBuildDaps
=======================================

.. py:class:: docbuild.models.config.env.EnvBuildDaps(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.config.env.EnvBuildDaps
      :parts: 1


   Configuration for daps command execution.


   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].



   .. py:attribute:: command
      :type:  str
      :value: None


      The base command used for DAPS execution.



   .. py:attribute:: meta
      :type:  str
      :value: None


      The command used to extract DAPS metadata.


