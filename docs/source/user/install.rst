Installing docbuild
===================

To install the docbuild tool, follow these steps:

#. :ref:`prepare-installation` - Prepare your environment for installation.

#. :ref:`installing-docbuild` - Install the docbuild tool itself.

#. :ref:`get-xml-config` - Get the XML configuration files required for building documentation.

#. :ref:`config-docbuild` - Configure the docbuild tool to suit your needs.


.. _prepare-installation:

Preparing environment
--------------------------

It is highly recommended to use the `package and project manager uv <https://docs.astral.sh/uv>`_
to install the docbuild tool. This ensures that all dependencies are managed correctly and that
the installation is reproducible across different environments.

1. **Install uv**

   There are different methods to install :command:`uv`. Preferably use your systems package manager,
   otherwise follow the `uv documentation <https://docs.astral.sh/uv/getting-started/installation/>`_.

   For (open)SUSE Linux run the following command in your terminal:

   .. code-block:: shell-session

      $ sudo zypper install python313-uv

2. **Check the installation**

   After the installation, verify that :command:`uv` is installed and in your PATH by running:

   .. code-block:: shell-session

      $ type uv
      uv is hashed (/path/to/uv)
      $ uv --version
      ...

   You should see the version of :command:`uv` printed in the terminal.

3. **Check the available Python versions**

   As of the time of writing, the docbuild tool requires Python 3.12 or higher.
   To list your currently installed Python versions run:

   .. code-block:: shell-session

      $ uv python list --only-installed
      cpython-3.14.4-linux-x86_64-gnu     /usr/bin/python3.14
      cpython-3.13.13-linux-x86_64-gnu    /usr/bin/python3.13
      cpython-3.13.13-linux-x86_64-gnu    /usr/bin/python3 -> python3.13
      ...

   If you don't have version 3.12 or higher, install one using uv:

   .. code-block:: shell-session

      $ uv python install 3.13

      This downloads and installs Python 3.13 in the directory :file:`~/.local/share/uv/python/<VERSION>`.

.. _installing-docbuild:

Installing docbuild
-------------------

1. **Clone the repository**

   Open your terminal and run the following command to clone the docbuild repository from GitHub:

   .. code-block:: shell-session

      $ git clone https://github.com/openSUSE/docbuild.git
      $ cd docbuild

2. **Create a virtual environment**

   It is recommended to create a virtual environment to isolate the docbuild
   tool and its dependencies from your system Python environment.
   Run the following command:

   .. code-block:: shell-session

      $ uv venv --prompt "venv313" .venv

   This will create a virtual environment in the directory :file:`.venv`.

4. **Install dependencies**

   Ensure you have Python 3.12 or higher installed, then install the required dependencies:

   .. code-block:: shell-session

      $ uv sync --frozen
      Resolved 29 packages in 586ms
      Built docbuild @ file:///.../docbuild
      Installed 15 packages in 2.11s

   The ``--frozen`` flag is used here to ensure that :command:`uv` installs dependencies
   exactly as specified in the :file:`uv.lock` file. This is crucial for
   **reproducible builds** and maintaining a **consistent environment** across
   different machines or deployments, as it prevents :command:`uv` from attempting to
   resolve and potentially update dependency versions.

.. _get-xml-config:

Getting the XML configuration
-----------------------------

Formerly known as the *Docserv XML configs*. These configuration files defines the :term:`products <Product>`, their :term:`releases <Docset>`, their :term:`lifecycle <Lifecycle>` status and more.

The tool needs the XML configuration to build the documentation correctly. The XML configuration is not part of the docbuild tool itself, but it is required to run the tool.

Clone the |gl_xmlconfig| to your machine where you can access it easily.
As an alternative, use the `RNC schema <https://www.oasis-open.org/committees/relax-ng/compact-20021121.html>_` from :gh_tree:`src/docbuild/config/xml/data/` to create your own configuration.
