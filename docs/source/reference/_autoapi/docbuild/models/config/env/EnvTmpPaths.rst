docbuild.models.config.env.EnvTmpPaths
======================================

.. py:class:: docbuild.models.config.env.EnvTmpPaths(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.config.env.EnvTmpPaths
      :parts: 1


   Defines temporary paths.


   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].



   .. py:attribute:: tmp_base_dir
      :type:  docbuild.models.path.EnsureWritableDirectory
      :value: None


      Root path for temporary files.



   .. py:attribute:: tmp_dir
      :type:  docbuild.models.path.EnsureWritableDirectory
      :value: None


      General temporary directory.



   .. py:attribute:: tmp_deliverable_dir
      :type:  docbuild.models.path.EnsureWritableDirectory
      :value: None


      Directory for temporary deliverable clones.



   .. py:attribute:: tmp_metadata_dir
      :type:  docbuild.models.path.EnsureWritableDirectory
      :value: None


      Temporary metadata directory.



   .. py:attribute:: tmp_build_dir
      :type:  str
      :value: None


      Temporary build output directory.



   .. py:attribute:: tmp_out_dir
      :type:  docbuild.models.path.EnsureWritableDirectory
      :value: None


      Temporary final output directory.



   .. py:attribute:: log_dir
      :type:  docbuild.models.path.EnsureWritableDirectory
      :value: None


      Directory for log files.



   .. py:attribute:: tmp_deliverable_name
      :type:  str
      :value: None


      Temporary deliverable name.


