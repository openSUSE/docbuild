.. _quickstart:

Quick Start
===========

Use this guide to get started with docbuild and build one example deliverable from a sample Portal configuration.

The steps below will guide you through preparing your environment, installing the necessary tools, and building a sample deliverable.

.. _qs-before-you-begin:

Before you begin...
-------------------

Make sure your environment meets these requirements before you start. Follow this check list:

#. Use Linux or macOS. Windows is not supported. If you are using Windows, consider using a virtual machine or WSL (Windows Subsystem for Linux). However, this path is currently untested.
#. Reserve sufficient disk space for the build process and the generated deliverables.
#. Install Git and make sure you can access the source repository used by the
   sample. For openSUSE, run:

   .. code-block:: console

      $ sudo zypper install git

#. Install :term:`DAPS` and its system dependencies either from your system package manager or by following the `DAPS installation
   guide <https://opensuse.github.io/daps/>`_. DAPS is required to build this
   sample. For openSUSE, run:

   .. code-block:: console

      $ sudo zypper install daps


..
   Perhaps we should consider to describe a Docker/Podman solution here.


.. _qs-clone-repo:

Cloning this repository
-----------------------

Open your terminal and run the following command to clone the docbuild repository from GitHub:

.. code-block:: console

  $ git clone https://github.com/openSUSE/docbuild.git
  $ cd docbuild



.. _qs-prepare-installation:

Preparing the uv environment
----------------------------

It is highly recommended to use the `package and project manager uv <https://docs.astral.sh/uv>`_
to install the docbuild tool. This ensures that all dependencies are managed correctly and that
the installation is reproducible across different environments.

#. **Install uv**

   There are different methods to install :command:`uv`. Preferably use your systems package manager, otherwise follow the uv documentation about `how to install uv <https://docs.astral.sh/uv/getting-started/installation/>`_.

   For (open)SUSE Linux run the following command in your terminal:

   .. code-block:: console

      $ sudo zypper install python313-uv

#. **Check the installation**

   After the installation, verify that :command:`uv` is installed and in your PATH by running:

   .. code-block:: console

      $ type uv
      uv is hashed (/path/to/uv)
      $ uv --version
      ...

   You should see the version of :command:`uv` printed in the terminal.

#. **Check the available Python versions**

   As of the time of writing, the docbuild tool requires Python 3.12 or higher.
   If you have a higher version of Python installed, use that version. Most Linux distributions provide multiple Python versions, so you can choose the one that meets the requirement.

   To list your currently installed Python versions run:

   .. code-block:: console

      $ uv python list --only-installed
      cpython-3.14.4-linux-x86_64-gnu     /usr/bin/python3.14
      cpython-3.13.13-linux-x86_64-gnu    /usr/bin/python3.13
      cpython-3.13.13-linux-x86_64-gnu    /usr/bin/python3 -> python3.13
      ...

#. Only if your system does not provide Python 3.12 or higher, install one using uv:

   .. code-block:: console

      $ uv python install 3.13

   This downloads and installs Python 3.13 in the directory :file:`~/.local/share/uv/python/<VERSION>`.


.. _qs-install-docbuild:

Installing docbuild
-------------------

#. **Create a virtual environment**

   It is recommended to create a virtual environment to isolate the docbuild
   tool and its dependencies from your system Python environment.
   Run the following command:

   .. code-block:: console

      $ uv venv --python 3.13 --prompt "venv313"

   Use the Python version that is available on your system or the one you installed with :command:`uv`.

   This will create a virtual environment in the directory :file:`.venv`.

#. **Install dependencies**

   Ensure you have Python 3.12 or higher installed, then install the required dependencies:

   .. code-block:: console

      $ uv sync --dev --frozen
      Resolved 29 packages in 586ms
      Built docbuild @ file:///.../docbuild
      Installed 15 packages in 2.11s

   The ``--frozen`` flag is used here to ensure that :command:`uv` installs dependencies
   exactly as specified in the :file:`uv.lock` file. This is crucial for
   **reproducible builds** and maintaining a **consistent environment** across
   different machines or deployments, as it prevents :command:`uv` from attempting to
   resolve and potentially update dependency versions.


.. _qs-activate-venv:

Activating the Virtual Python Environment
-----------------------------------------

After you have created the :term:`VENV`, it's recommended to activate it before proceeding with further steps:

.. code-block:: console

   $ source .venv/bin/activate && source devel/activate-aliases.sh

The file :file:`devel/activate-aliases.sh` contains some shell aliases that make working with the virtual environment more convenient.


.. _qs-show-portal:

Showing the Portal Configuration
--------------------------------

To view the current Portal configuration, use the following command:

.. code-block:: console

   $ docbuild --env-config etc/docbuild/env.quickstart.toml portal ls
   en-us/
   └── sles
       └── 16.1
           ├── sles.16.1.dc-sle-comparison (DC-SLE-comparison)
           ├── sles.16.1.dc-sle-os-identification (DC-SLE-os-identification)
           ├── sles.16.1.dc-sles-klp (DC-SLES-klp)
           └── sles.16.1.dc-sles-ansible-roles (DC-SLES-ansible-roles)

This gives you an overview of what the Portal configuration contains without actually opening the configuration files.

If you want to have a more compact view, use the ``--flat`` option. This helps when you need to grep for specific entries:

.. code-block:: console

   $ docbuild --env-config etc/docbuild/env.quickstart.toml portal ls --flat
   en-us/sles/16.1:sles.16.1.dc-sle-comparison (DC-SLE-comparison)
   en-us/sles/16.1:sles.16.1.dc-sle-os-identification (DC-SLE-os-identification)
   en-us/sles/16.1:sles.16.1.dc-sles-klp (DC-SLES-klp)
   en-us/sles/16.1:sles.16.1.dc-sles-ansible-roles (DC-SLES-ansible-roles)


.. _qs-use-sample-config:

Using the sample configuration
------------------------------

The sample environment configuration points to the :term:`Portal configuration <Portal Config>` in
:file:`etc/docbuild/config.d`. No copying is needed. Its paths are relative to
the current working directory, so run the following commands from the repository
root.

Validate the sample Portal configuration with:

.. code-block:: console

  $ docbuild --env-config etc/docbuild/env.quickstart.toml portal validate
  Validating
  - Portal XML config: etc/docbuild/config.d/portal.xml
  - Portal schema:     src/docbuild/config/xml/data/portal-config.rnc

  Stage 1 (RNG schema via jing): success
  Stage 2 (Python checks): success
  Portal XML validation successful.


Checking if all files are present
---------------------------------

Before you start building the SLES 16.1 English docset, it's always a good
idea to check whether all required files are present.
Use the following command to make sure all required files are present in the repository.

.. code-block:: console

   $ docbuild --env-config etc/docbuild/env.quickstart.toml check files 'sles/16.1/en-us'
   sles/16.1@supported/en-us
   └── gh://suse/doc-modular@main
       ├── DC-SLE-comparison ✓ OK
       ├── DC-SLE-os-identification ✓ OK
       ├── DC-SLES-klp ✓ OK
       └── DC-SLES-ansible-roles ✓ OK

   Found 4 files, 0 skipped, 0 error.

Docbuild clones the referenced source repository if it has not been cloned already.
Then it checks each required :term:`DC File` if it's available.

This command does NOT validate the content of the DC files.


Building the SLES 16.1 English docset
-------------------------------------

The sample configuration includes a predefined setup for building the SLES 16.1
English docset. It does not cover the full set of possible configurations or
docsets available for the SUSE documentation.

Build the SLES 16.1 English docset:

.. code-block:: console

   $ docbuild --env-config etc/docbuild/env.quickstart.toml build run sles/16.1/en-us

On a high-level overview, here is what |project| does:

1. Clones the configured source repository if it has not been cloned already.
2. Extracts the metadata for each deliverable.
3. Builds the deliverables using DAPS.
4. Creates the index pages for the product/docset.

Find the generated deliverables and index pages in the output directory.
By default, it's :file:`~/Documents/docbuild/target`.

Next steps
----------

* To create or change Portal configuration, see :doc:`../user/portal-config/index`.
* To configure repositories and build paths, see :ref:`user-config`.
* To check the available build commands, see :ref:`build-deliverables`.
