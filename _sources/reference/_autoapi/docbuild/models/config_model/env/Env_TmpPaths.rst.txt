docbuild.models.config_model.env.Env_TmpPaths
=============================================

.. py:class:: docbuild.models.config_model.env.Env_TmpPaths(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.config_model.env.Env_TmpPaths
      :parts: 1


   Defines temporary paths.


   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].



   .. py:attribute:: tmp_base_dir
      :type:  docbuild.models.path.EnsureWritableDirectory
      :value: None


      Root path for temporary files.



   .. py:attribute:: tmp_path
      :type:  docbuild.models.path.EnsureWritableDirectory
      :value: None


      General temporary path.



   .. py:attribute:: tmp_deliverable_path
      :type:  docbuild.models.path.EnsureWritableDirectory
      :value: None


      Path for temporary deliverable clones.



   .. py:attribute:: tmp_metadata_dir
      :type:  docbuild.models.path.EnsureWritableDirectory
      :value: None


      Temporary metadata directory.



   .. py:attribute:: tmp_build_dir
      :type:  str
      :value: None


      Temporary build output directory.



   .. py:attribute:: tmp_out_path
      :type:  docbuild.models.path.EnsureWritableDirectory
      :value: None


      Temporary final output path.



   .. py:attribute:: log_path
      :type:  docbuild.models.path.EnsureWritableDirectory
      :value: None


      Path for log files.



   .. py:attribute:: tmp_deliverable_name
      :type:  str
      :value: None


      Temporary deliverable name.


