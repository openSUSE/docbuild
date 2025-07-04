docbuild.cli.context.DocBuildContext
====================================

.. py:class:: docbuild.cli.context.DocBuildContext

   The CLI context shared between different subcommands.


   .. py:attribute:: dry_run
      :type:  bool
      :value: False


      If set, just pretend to run the command without making any changes



   .. py:attribute:: verbose
      :type:  int
      :value: 0


      verbosity level



   .. py:attribute:: appconfigfiles
      :type:  tuple[str | pathlib.Path, Ellipsis] | None
      :value: None


      The app's config files to load, if any



   .. py:attribute:: appconfig_from_defaults
      :type:  bool
      :value: False


      If set, the app's config was loaded from defaults



   .. py:attribute:: appconfig
      :type:  dict[str, Any] | None
      :value: None


      The accumulated content of all app config files



   .. py:attribute:: envconfigfiles
      :type:  tuple[str | pathlib.Path, Ellipsis] | None
      :value: None


      The env's config files to load, if any



   .. py:attribute:: envconfig_from_defaults
      :type:  bool
      :value: False


      Internal flag to indicate if the env's config was loaded from defaults



   .. py:attribute:: envconfig
      :type:  dict[str, Any] | None
      :value: None


      The accumulated content of all env config files



   .. py:attribute:: doctypes
      :type:  list[docbuild.models.doctype.Doctype] | None
      :value: None


      The doctypes to process, if any



   .. py:attribute:: debug
      :type:  bool
      :value: False


      If set, enable debug mode


