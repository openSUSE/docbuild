.. _work-docker:

Working with Docker Images
==========================

Sometimes it is easier to work with a Docker container that contains all
the necessary dependencies.


Requirements
------------

To build a Docker image and use it as container, check the following
requirements:

* Docker installed and running on your system:

  * For openSUSE: Run :command:`sudo zypper install docker` to install it and :command:`sudo systemctl start docker` to start the Docker daemon.

  * For MacOS: Refer to https://docs.docker.com/desktop/setup/install/mac-install/.

* Clone the respective configuration repository. Refer to :ref:`get-docserv-config`.


Creating a Docker image
-----------------------

To create a Docker image, use the following command:

.. code-block:: shell-session
   :caption: Building the image

   docker buildx build -t docbuild:latest .

This creates a Docker image ``docbuild`` with the tag ``latest``. After the successful build, you see:

.. code-block:: shell-session
   :caption: Listing the Docker image

   $ docker image ls docbuild
   REPOSITORY   TAG       IMAGE ID       CREATED          SIZE
   docbuild     latest    c13d36935907   16 minutes ago   643MB


Running the Docker container
----------------------------

Before you start the Docker container, you need to collect some paths and file names:

* The path to the configuration repository, marked as ``CONFIG_DIR``.
* The path to the environment file, marked as ``ENV_FILE``. Usually you want to use :file:`$PWD/etc/env-docker.toml` from this repository.
* The path to the cache directory, marked as ``CACHE_DIR``. Under Linux it's usually :file:`/var/cache/docbuild`
* The path of the target directory (the result of all ), marked as ``TARGET_DIR``.


.. admonition:: Make absolute paths

   Use absolute paths for the previous variables.


Running the Docker container based on the previous image, use this command:

.. code-block:: shell-session
   :caption: Running the Docker container

   export CONFIG_DIR="..."
   export ENV_FILE="..."
   export CACHE_DIR="..."
   export TARGET_DIR="..."
   docker run --it \
      -v $CONFIG_DIR:/etc/docbuild \
      -v $ENV_FILE:/app/.env-production.toml \
      -v $CACHE_DIR:/var/cache/docbuild/ \
      -v $TARGET_DIR:/data/docbuild/external-builds/ \
      docbuild:latest \
      DOCBUILD_COMMAND
