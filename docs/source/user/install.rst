Installing docbuild
===================

To install the docbuild tool, follow these steps:

#. :ref:`prepare-installation` - Prepare your environment for installation.

#. :ref:`installing-docbuild` - Install the docbuild tool itself.

#. :ref:`get-xml-config` - Get the XML configuration files required for building documentation.

#. :ref:`configuring-docbuild` - Configure the docbuild tool to suit your needs.


.. _prepare-installation:

Preparing for Installation
--------------------------

It is highly recommended to use the `package and project manager uv <https://docs.astral.sh/uv>`_ to install the docbuild tool. This ensures that all dependencies are managed correctly and that the installation is reproducible across different environments.

There are different methods to install the :command:`uv` package manager
(see `Installing uv <https://docs.astral.sh/uv/getting-started/installation/>`_.). In this case, use the standalone installer:


1. **Install uv**

   Run the following command in your terminal:

   .. code-block:: shell-session

      $ curl -sSfL https://astral.sh/uv/install.sh | sh


   This will install two commands :command:`uv` and :command:`uvx` in :file:`~/.local/bin/`. Make sure this directory is in your :envvar:`PATH` environment variable.

2. **Check the installation**

   After the installation, verify that :command:`uv` is installed correctly by running:

   .. code-block:: shell-session

      $ type uv
      uv is hashed (/home/tux/.local/bin/uv)
      $ uv --version
      ...

   You should see the version of :command:`uv` printed in the terminal.

3. **Install Python 3.12 or higher**

   As of the time of writing, the docbuild tool requires Python 3.12 or higher. Install the Python version using :command:`uv`:

   .. code-block:: shell-session

      $ uv python install 3.13

   The previous command downloads Python 3.13 and install it in the directory :file:`~/.local/share/uv/python/<VERSION>`.

4. **Check the available Python versions**

   To see the installed Python versions, run:

   .. code-block:: shell-session

      $ uv python list
      cpython-3.14.0b1-linux-x86_64-gnu                 <download available>
      cpython-3.14.0b1+freethreaded-linux-x86_64-gnu    <download available>
      cpython-3.13.4-linux-x86_64-gnu                   /home/tux/.local/share/uv/python/cpython-3.13.4-linux-x86_64-gnu/bin/python3.13
      [...]

   You should see Python 3.13 listed among the available versions.


.. _installing-docbuild:

Installing the tool
-------------------

1. **Clone the repository**

   Open your terminal and run the following command to clone the docbuild repository from GitHub:

   .. code-block:: shell-session

      $ git clone https://github.com/openSUSE/docbuild.git
      $ cd docbuild

2. **Create a virtual environment**

   It is recommended to create a virtual environment to isolate the docbuild tool and its dependencies from your system Python environment.
   Run the following command:

   .. code-block:: shell-session

      $ uv venv --prompt "venv313" .venv

   This will create a virtual environment in the directory `.venv`.

4. **Install dependencies**

   Ensure you have Python 3.12 or higher installed, then install the required dependencies using pip:

   .. code-block:: shell-session

      $ uv sync --frozen
      Resolved 29 packages in 586ms
      Built docbuild @ file:///.../docbuild
      Installed 15 packages in 2.11s


.. _get-xml-config:

Getting the XML configuration
-----------------------------

Formerly known as the *Docserv XML configs*. These configuration files defines the :term:`products <Product>`, their :term:`releases <Docset>`, their :term:`lifecycle <Lifecycle>` status and more.

The tool needs the XML configuration to build the documentation correctly. The XML configuration is not part of the docbuild tool itself, but it is required to run the tool.

Clone the |gl_xmlconfig| to your machine where you can access it easily.
As an alternative, use the RNC schema from :gh_tree:`src/docbuild/config/xml/data/` to create your own configuration.