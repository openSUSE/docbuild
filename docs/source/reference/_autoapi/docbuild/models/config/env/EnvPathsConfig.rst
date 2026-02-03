docbuild.models.config.env.EnvPathsConfig
=========================================

.. py:class:: docbuild.models.config.env.EnvPathsConfig(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.config.env.EnvPathsConfig
      :parts: 1


   Defines various application paths, including permanent storage and cache.


   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].



   .. py:attribute:: config_dir
      :type:  pathlib.Path
      :value: None


      Path to configuration files.



   .. py:attribute:: root_config_dir
      :type:  pathlib.Path
      :value: None


      Path to the root configuration files.



   .. py:attribute:: jinja_dir
      :type:  pathlib.Path
      :value: None


      Path for Jinja templates.



   .. py:attribute:: server_rootfiles_dir
      :type:  pathlib.Path
      :value: None


      Path for server root files.



   .. py:attribute:: repo_dir
      :type:  pathlib.Path
      :value: None


      Path for permanent bare Git repositories.



   .. py:attribute:: tmp_repo_dir
      :type:  pathlib.Path
      :value: None


      Directory for temporary working copies.



   .. py:attribute:: base_cache_dir
      :type:  pathlib.Path
      :value: None


      Base path for all caches.



   .. py:attribute:: base_server_cache_dir
      :type:  pathlib.Path
      :value: None


      Base path for server caches.



   .. py:attribute:: meta_cache_dir
      :type:  pathlib.Path
      :value: None


      Metadata cache path.



   .. py:attribute:: base_tmp_dir
      :type:  pathlib.Path
      :value: None


      Base system temporary path.



   .. py:attribute:: tmp
      :type:  EnvTmpPaths

      Temporary build paths.



   .. py:attribute:: target
      :type:  EnvTargetPaths

      Target deployment and backup paths.


