.. _config-theme:

Configuring the Terminal Theme
==============================

Docbuild uses `Rich <https://rich.readthedocs.io/>`_ to format terminal output with consistent, semantic styles across all CLI commands.
You can use the built-in dark or light presets, or customize individual styles to match your terminal preferences in the application configuration file (:file:`config.toml`).


Semantic Style Tags and Presets
-------------------------------

Output styling is organized into semantic tags rather than hardcoded colors.
Docbuild provides two built-in presets:

* **Dark Theme (default):** Optimized for black and dark-gray terminal backgrounds.
* **Light Theme:** Optimized for white and light-gray terminal backgrounds (such as Solarized Light).

.. list-table:: Semantic Style Tag Presets
   :header-rows: 1
   :widths: 15 25 25 35

   * - Tag Name
     - Dark Preset (Default)
     - Light Preset
     - Purpose
   * - ``header``
     - ``bold cyan``
     - ``bold blue``
     - Section titles and major headers.
   * - ``error``
     - ``bold red``
     - ``bold red``
     - Error messages and failure indicators.
   * - ``warning``
     - ``bold yellow``
     - ``bold dark_goldenrod``
     - Warning notices and cautions.
   * - ``info``
     - ``bold bright_blue``
     - ``bold dark_cyan``
     - Informational messages and progress updates.
   * - ``success``
     - ``bold green``
     - ``bold dark_green``
     - Success notices and completed stages.
   * - ``hint``
     - ``dim italic cyan``
     - ``italic dark_cyan``
     - Helpful suggestions and usage hints.
   * - ``muted``
     - ``dim white``
     - ``dim black``
     - Secondary details and dimmed footer text.


Customizing Styles in Configuration
-----------------------------------

To customize styles, add a ``[theme]`` table to your application configuration file (:file:`config.toml` or :file:`.config.toml`).

Selecting a Preset
~~~~~~~~~~~~~~~~~~

If you use a light terminal background, set the ``preset`` option to ``light``:

.. code-block:: toml
   :caption: Switch to light theme preset
   :name: toml-theme-light-preset

   [theme]
   preset = "light"

Individual Style Overrides
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can override any specific style tag on top of the active preset.
Docbuild supports two equivalent formats for defining styles:

1. **String shorthand:** Specify the complete style expression as a single string.
2. **Structured style table:** Define individual attributes such as ``color``, ``bgcolor``, ``bold``, or ``italic`` in a sub-table.

You can use whichever format you prefer, or combine both in the same file.

.. code-block:: toml
   :caption: Custom theme using string shorthand
   :name: toml-custom-theme-shorthand

   [theme]
   error = "bold magenta"
   warning = "bold yellow"
   success = "bold #30ba78"

.. code-block:: toml
   :caption: Custom theme using structured style tables
   :name: toml-custom-theme-structured

   [theme]
   preset = "light"
   warning = "bold dark_orange3"

   [theme.error]
   color = "red"
   bold = true
   bgcolor = "white"

   [theme.success]
   color = "#30ba78"
   bold = true


Previewing Preset Palettes and Active Themes
--------------------------------------------

To see a visual showcase of all semantic tokens directly in your terminal, use the ``docbuild config theme`` command:

.. code-block:: console
   :caption: Preview built-in presets and active theme

   docbuild config theme

By default, this command displays both the Dark and Light built-in presets, along with an **Active Configuration Theme** table if custom styles or a preset are configured in your application configuration.

To view a specific preset only, use the ``--preset`` option:

.. code-block:: console
   :caption: Preview a specific preset

   docbuild config theme --preset light

You can also run the theme module directly:

.. code-block:: console
   :caption: Run the theme module directly

   python -m docbuild.cli.theme


Supported Style Syntax
----------------------

Docbuild supports Rich's full style syntax:

* **Standard ANSI colors**: ``red``, ``green``, ``yellow``, ``blue``, ``magenta``, ``cyan``, ``white``, etc.
* **Bright colors**: ``bright_red``, ``bright_green``, ``bright_cyan``, etc.
* **24-bit TrueColor hex codes**: ``#30ba78``, ``#ff5500``, etc.
* **Style modifiers**: ``bold``, ``dim``, ``italic``, ``underline``, ``reverse``.
* **Background colors**: Prefix with ``on``, such as ``bold white on red``.


Procedure: Customizing and Verifying Your Theme
-----------------------------------------------

Follow these steps to customize your theme and verify the changes:

#. Open or create your :file:`config.toml` in your project or configuration directory.

#. Add the ``[theme]`` section with your desired overrides:

   .. code-block:: toml
      :caption: Define custom theme overrides

      [theme]
      preset = "dark"
      error = "bold magenta"
      hint = "italic cyan"

#. Verify that your custom theme values are loaded:

   .. code-block:: console
      :caption: Inspect active theme settings

      docbuild config list --app --flat

   The output displays your overrides alongside the preserved defaults:

   .. code-block:: text

      app.theme.header = 'bold cyan'
      app.theme.error = 'bold magenta'
      app.theme.warning = 'bold yellow'
      app.theme.info = 'bold bright_blue'
      app.theme.success = 'bold green'
      app.theme.hint = 'italic cyan'
      app.theme.muted = 'dim white'

#. Validate the configuration file syntax:

   .. code-block:: console
      :caption: Validate configuration

      docbuild config validate

   If an invalid color or an unknown tag name is configured, Docbuild catches the error and reports it with exact field details:

   .. code-block:: text

      1 Validation error in config file 'config.toml':

      (1) In 'theme.eror':
          Input should be 'header', 'error', 'warning', 'info', 'success', 'hint' or 'muted'
          See: https://opensuse.github.io/docbuild/latest/errors/enum.html
