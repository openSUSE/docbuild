
Working with Docker Container Images
====================================

In the following sections, we will create a Docker container image ``docbuild:leap160`` and demonstrate how to build, use, and debug it.

Building a Docker Container Image
---------------------------------

To build a Docker container image, you need to have a :file:`Containerfile` or :file:`Dockerfile` that defines the image's contents and build instructions.

Use the :command:`docker build` command to create the image:

.. code-block:: console

    $ docker build \
      -f docker/Dockerfile \
      --build-arg APP_UID="$(id -u)" \
      --build-arg APP_GID="$(id -g)" \
      -t docbuild:leap160 .
    [...]
     => => naming to docker.io/library/docbuild:leap160

If you have an older version of Docker, you might try the following approach:

.. code-block:: console

    $ DOCKER_BUILDKIT=1 docker build \
      --network=host \
      -f docker/Dockerfile \
      --build-arg APP_UID="$(id -u)" \
      --build-arg APP_GID="$(id -g)" \
      -t docbuild:leap160 .


Using the Docker Container Image
--------------------------------

To use a Docker container image with the :command:`docbuild` tool, run it using the :command:`docker run` command. In its simplest form, run it like this:

.. code-block:: console

   $ docker run --rm -it docbuild:leap160 <COMMAND> <ARGS>


However, this command does not take into account your local environment, such as mounted volumes or environment variables. To properly use the `docbuild` tool with your local files, you may need to mount directories and pass necessary environment variables to the container.

You can use a shell function (it expects that the necessary host directories are already created) to run the `docbuild` tool with Docker:

.. code-block:: bash
   :caption: Shell function to run docbuild with Docker

   # use --network=host only for trusted containers.
   # Impose CPU limits with:
   #   --cpu=4: limits total CPU time to roughly four core's capacity
   #   --cpuset-cpus=0-3: restrict execution to thos specific logical CPUs
   ddocbuild() {
      docker run --rm -it \
        --network=host \
        -v "$HOME/.config/docbuild:/home/app/.config/docbuild:ro" \
        -v "$HOME/.cache/docbuild:/home/app/.cache/docbuild" \
        -v "$HOME/.local/state/docbuild:/home/app/.local/state/docbuild" \
        -v "$PWD:$PWD" \
        -w "$PWD" \
        docbuild:leap160 "$@"
   }

Debugging the Docker Container Image
------------------------------------

To debug the Docker container image, you can run it interactively with a shell:

.. code-block:: console

    $ docker run --rm -it --entrypoint /bin/bash docbuild:leap160
