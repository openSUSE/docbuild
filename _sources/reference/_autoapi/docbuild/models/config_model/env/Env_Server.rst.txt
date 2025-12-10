docbuild.models.config.env.Env_Server
===========================================

.. py:class:: docbuild.models.config.env.Env_Server(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.config.env.Env_Server
      :parts: 1


   Defines server settings.


   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].



   .. py:attribute:: name
      :type:  str
      :value: None


      The descriptive name of the server.



   .. py:attribute:: role
      :type:  docbuild.models.serverroles.ServerRole
      :value: None


      The environment type, used for build behavior differences.



   .. py:attribute:: host
      :type:  pydantic.IPvAnyAddress | DomainName
      :value: None


      The host address for the server.



   .. py:attribute:: enable_mail
      :type:  bool
      :value: None


      Whether email functionality should be active.


