Howto
=====

This section contains various how-to instructions for developers working with the project.


Adding or removing a new product
--------------------------------

Product names are checked against typos. Whenever you change a product acronym,
you need to update the constant :data:`docbuild.constants.VALID_PRODUCTS`.


Changing the language set
-------------------------

When you want to add or remove a language, adjust the constant :data:`docbuild.constants.ALLOWED_LANGUAGES`.


Changing the lifecycle set
----------------------------

When you want to add or remove a lifecycle, adjust the constant :data:`docbuild.constants.ALLOWED_LIFECYCLES`.


Changing the app's config paths
-------------------------------

When you want to change the default paths where the app looks for its configuration files, adjust the constant :data:`docbuild.constants.CONFIG_PATHS`.

Changing the app's config file names
------------------------------------

When you want to change the default names of the app's configuration files, adjust the constant :data:`docbuild.constants.APP_CONFIG_BASENAMES`, :data:`docbuild.constants.PROJECT_LEVEL_APP_CONFIG_FILENAMES`, or both.