.. _user-config-files:

Configuration Files
===================

Docbuild uses two types of TOML configuration files:

* **Application configuration** (shortened "app config"): Controls tool-wide settings such as logging, themes, and concurrency limits.
* **Environment configuration** ("env config"): Controls environment-specific settings such as paths, repositories, products, and build targets.

Both types follow the same search hierarchy and precedence order.
Only the file names differ.


.. _config-search-locations:
.. _config-places:

Search Locations and Precedence
-------------------------------

Docbuild evaluates sources in order of increasing priority.
A higher-priority source overwrites the same setting from a lower-priority source:

#. **Built-in defaults:** Hard-coded base values (lowest priority). 
#. **System directory:** :file:`/etc/docbuild/`. This path is fixed; no XDG variable changes it.
#. **User directory:** OS-specific user configuration directory resolved via `platformdirs <https://platformdirs.readthedocs.io/>`_.
   On Linux, this follows the XDG Base Directory Specification.
   On macOS, the XDG variables also apply and take precedence over the platform defaults.
   The following XDG variables control the per-user directories:

   .. list-table::
      :header-rows: 1

      * - Directory
        - Environment variable
        - Default when unset (Linux)
        - Default when unset (macOS)
      * - Configuration (``CONFIG_HOME``)
        - :envvar:`XDG_CONFIG_HOME`
        - :file:`~/.config/docbuild/`
        - :file:`~/Library/Application Support/docbuild/`
      * - State (``STATE_HOME``)
        - :envvar:`XDG_STATE_HOME`
        - :file:`~/.local/state/docbuild/`
        - :file:`~/Library/Application Support/docbuild/`
      * - Data (``DATA_HOME``)
        - :envvar:`XDG_DATA_HOME`
        - :file:`~/.local/share/docbuild/`
        - :file:`~/Library/Application Support/docbuild/`
      * - Cache (``CACHE_HOME``)
        - :envvar:`XDG_CACHE_HOME`
        - :file:`~/.cache/docbuild/`
        - :file:`~/Library/Caches/docbuild/`
      * - Runtime (``RUNTIME_DIR``)
        - :envvar:`XDG_RUNTIME_DIR`
        - None; set by the login session (for example :file:`/run/user/1000/docbuild/`)
        - :file:`~/Library/Caches/TemporaryItems/docbuild/`
#. **Project directory:** The current working directory.
#. **Command-line overwrites:** Values set with ``-C`` or ``--set-env`` take precedence over all files (see :ref:`config-overwriting-cli`).
   These values have the highest priority.


.. _config-file-names:

Configuration File Names
------------------------

Application and environment configurations use different file names, but the search order is the same.

Application configuration
  In each search directory, Docbuild loads the first existing file from this list:

  #. :file:`.config.toml`
  #. :file:`config.toml`
  #. :file:`.docbuild.config.toml`
  #. :file:`docbuild.config.toml`

Environment configuration
  Environment configuration files follow the pattern :file:`env.<ROLE>.toml`, where ``<ROLE>`` is an environment role such as ``production``, ``staging``, or ``devel`` (see :ref:`config-env-role`).

  * **Default file name:** :file:`env.production.toml`, loaded automatically when present in a search directory.
  * **Role-based file names:** :file:`env.<role>.toml`, for example :file:`env.staging.toml` or :file:`env.devel.toml`.
    These files are not discovered automatically.