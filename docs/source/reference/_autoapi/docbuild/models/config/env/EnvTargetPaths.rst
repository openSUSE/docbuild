docbuild.models.config.env.EnvTargetPaths
=========================================

.. py:class:: docbuild.models.config.env.EnvTargetPaths(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.config.env.EnvTargetPaths
      :parts: 1


   Defines target paths.


   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].



   .. py:attribute:: target_dir
      :type:  str
      :value: None


      The destination directory for final built documentation.



   .. py:attribute:: backup_dir
      :type:  pathlib.Path
      :value: None


      Directory for backups.


