Installing docbuild
===================

To install the docbuild tool, follow these steps:

1. :ref:`prepare-installation` - Prepare your environment for installation.

2. :ref:`installing-docbuild` - Install the docbuild tool itself.

3. :ref:`configuring-docbuild` - Configure the docbuild tool to suit your needs.


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

3. **Install Python 3.13 or higher**

   As of the time of writing, the docbuild tool requires Python 3.12 or higher. Install the Python version using :command:`uv`:

   .. code-block:: shell-session

      $ uv python install 3.13

   This command will download Python 3.13 and install it in the directory :file:`~/.local/share/uv/python/<VERSION>`.

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

      $ uv sync
      Resolved 29 packages in 586ms
      Built docbuild @ file:///.../docbuild
      Installed 15 packages in 2.11s


.. _configuring-docbuild:

Configuring the tool
---------------------

TODO