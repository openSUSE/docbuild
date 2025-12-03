docbuild.models.config_model.env.Env_GeneralConfig
==================================================

.. py:class:: docbuild.models.config_model.env.Env_GeneralConfig(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`

   .. autoapi-inheritance-diagram:: docbuild.models.config_model.env.Env_GeneralConfig
      :parts: 1


   Defines general configuration.


   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].



   .. py:attribute:: default_lang
      :type:  docbuild.models.language.LanguageCode
      :value: None


      The default language code.



   .. py:attribute:: languages
      :type:  list[docbuild.models.language.LanguageCode]
      :value: None


      A list of supported language codes.



   .. py:attribute:: canonical_url_domain
      :type:  pydantic.HttpUrl
      :value: None


      The canonical domain for URLs.



   .. py:method:: serialize_default_lang(lang_obj: docbuild.models.language.LanguageCode) -> str

      Serializes the LanguageCode model back to a simple string (e.g., 'en-us').



   .. py:method:: serialize_languages(lang_list: list[docbuild.models.language.LanguageCode]) -> list[str]

      Serializes the list of LanguageCode models back to a list of strings.


