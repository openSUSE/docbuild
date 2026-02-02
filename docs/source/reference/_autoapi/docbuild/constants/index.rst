docbuild.constants
==================

.. py:module:: docbuild.constants

.. autoapi-nested-parse::

   Constants for the CLI application.



Attributes
----------

.. autoapisummary::

   docbuild.constants.APP_NAME
   docbuild.constants.DEFAULT_LANGS
   docbuild.constants.ALLOWED_LANGUAGES
   docbuild.constants.DEFAULT_DELIVERABLES
   docbuild.constants.SERVER_ROLES
   docbuild.constants.SERVER_ROLES_ALIASES
   docbuild.constants.DEFAULT_LIFECYCLE
   docbuild.constants.ALLOWED_LIFECYCLES
   docbuild.constants.VALID_PRODUCTS
   docbuild.constants.ALLOWED_PRODUCTS
   docbuild.constants.SINGLE_LANG_REGEX
   docbuild.constants.MULTIPLE_LANG_REGEX
   docbuild.constants.LIFECYCLES_STR
   docbuild.constants.PROJECT_DIR
   docbuild.constants.USER_CONFIG_DIR
   docbuild.constants.SYSTEM_CONFIG_DIR
   docbuild.constants.CONFIG_PATHS
   docbuild.constants.APP_CONFIG_BASENAMES
   docbuild.constants.PROJECT_LEVEL_APP_CONFIG_FILENAMES
   docbuild.constants.APP_CONFIG_FILENAME
   docbuild.constants.ENV_CONFIG_FILENAME
   docbuild.constants.DEFAULT_ENV_CONFIG_FILENAME
   docbuild.constants.GIT_CONFIG_FILENAME
   docbuild.constants.BASE_STATE_DIR
   docbuild.constants.GITLOGGER_NAME
   docbuild.constants.BASE_LOG_DIR
   docbuild.constants.BASE_LOCK_DIR
   docbuild.constants.XMLDATADIR


Module Contents
---------------

.. py:data:: APP_NAME
   :value: 'docbuild'


   The name of the application, used in paths and config files.


.. py:data:: DEFAULT_LANGS
   :value: ('en-us',)


   The default languages used by the application.


.. py:data:: ALLOWED_LANGUAGES

   The languages supported by the documentation portal.


.. py:data:: DEFAULT_DELIVERABLES
   :value: '*/@supported/en-us'


   The default deliverables when no specific doctype is provided.


.. py:data:: SERVER_ROLES

   The unique primary server role values.


.. py:data:: SERVER_ROLES_ALIASES
   :value: ('PRODUCTION', 'STAGING', 'TESTING', 'PROD', 'P', 'prod', 'p', 'STAGE', 'S', 'stage', 's',...


   All valid server role names and aliases for validation and testing.


.. py:data:: DEFAULT_LIFECYCLE
   :value: 'supported'


   The default lifecycle state for a docset.


.. py:data:: ALLOWED_LIFECYCLES
   :type:  tuple[str]

   The available lifecycle states for a docset (without 'unknown').


.. py:data:: VALID_PRODUCTS
   :type:  dict[str, str]

   A dictionary of valid products acronyms and their full names.


.. py:data:: ALLOWED_PRODUCTS

   A tuple of valid product acronyms.


.. py:data:: SINGLE_LANG_REGEX

   Regex for a single language code in the format 'xx-XX' (e.g., 'en-us').


.. py:data:: MULTIPLE_LANG_REGEX

   Regex for multiple languages, separated by commas.


.. py:data:: LIFECYCLES_STR
   :value: ''


   Regex for lifecycle states, separated by pipe (|).


.. py:data:: PROJECT_DIR

   The current working directory, used as the project directory.


.. py:data:: USER_CONFIG_DIR

   The user-specific configuration directory, typically located
   at ~/.config/docbuild.


.. py:data:: SYSTEM_CONFIG_DIR

   The system-wide configuration directory, typically located
   at /etc/docbuild.


.. py:data:: CONFIG_PATHS

   The paths where the application will look for configuration files.


.. py:data:: APP_CONFIG_BASENAMES
   :value: ('.config.toml', 'config.toml')


   The base filenames for the application configuration files, in
   order of priority.


.. py:data:: PROJECT_LEVEL_APP_CONFIG_FILENAMES

   Additional configuration filenames at the project level.


.. py:data:: APP_CONFIG_FILENAME
   :value: 'config.toml'


   The filename of the application's config file without any paths.


.. py:data:: ENV_CONFIG_FILENAME
   :value: 'env.{role}.toml'


   The filename of the environment's config file without any paths.


.. py:data:: DEFAULT_ENV_CONFIG_FILENAME
   :value: 'env.production.toml'


   The default filename for the environment's config file, typically
   used in production.


.. py:data:: GIT_CONFIG_FILENAME

   The project-specific Git configuration file (relative to this project)


.. py:data:: BASE_STATE_DIR

   The directory where application state, logs, and locks are stored,
   per XDG Base Directory Specification.


.. py:data:: GITLOGGER_NAME
   :value: 'docbuild.git'


   The standardized name for the Git-related logger.


.. py:data:: BASE_LOG_DIR

   The directory where log files will be stored.


.. py:data:: BASE_LOCK_DIR

   The directory where PID lock files will be stored.


.. py:data:: XMLDATADIR

   Directory where additional files (RNC, XSLT) for XML processing are stored.


