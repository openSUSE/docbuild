docbuild.models.serverroles.ServerRole
======================================

.. py:class:: docbuild.models.serverroles.ServerRole

   Bases: :py:obj:`enum.StrEnum`

   .. autoapi-inheritance-diagram:: docbuild.models.serverroles.ServerRole
      :parts: 1


   The server role.


   .. py:attribute:: PRODUCTION
      :value: 'production'


      Server is in production mode, serving live traffic.



   .. py:attribute:: STAGING
      :value: 'staging'


      Server is in staging mode, used for testing before production.



   .. py:attribute:: TESTING
      :value: 'testing'


      Server is in testing mode, used for development and QA.


