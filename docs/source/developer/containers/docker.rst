
Working with Docker Container Images
====================================

In the following sections, we will create a Docker container image ``docbuild:leap160`` and demonstrate how to build, use, and debug it.

Building a Docker Container Image
---------------------------------

To build a Docker container image, you need to have a :file:`Containerfile` or :file:`Dockerfile` that defines the image's contents and build instructions.

To build the container image, run the following command:

.. code-block:: console

    $ ./docker/build.sh
    [...]
     => => naming to docker.io/library/docbuild:leap160
    [...]
    All system dependencies look good!

Internally, it runs the :command:`docker build` command. The container image has the following properties:

* The user and group IDs are the same than on your host (build parameters ``APP_UID`` and ``APP_GID``). This is needed so have the same user and group mapping without running into permission issues.
* The user home is the same as on your host (build parameter ``APP_HOME``).


Using the Docker Container Image
--------------------------------

To use a Docker container image with the :command:`docbuild` tool, run it using the :command:`docker run` command. In its simplest form, run it like this:

.. code-block:: console

   $ docker run --rm -it docbuild:leap160 <COMMAND> <ARGS>


However, this command does not take into account your local environment, such as mounted volumes or environment variables. To properly use the `docbuild` tool with your local files, you may need to mount directories and pass necessary environment variables to the container.

You can use a shell function (it expects that the necessary host directories are already created) to run the `docbuild` tool with Docker:

.. literalinclude:: ddocbuild.sh
   :language: bash
   :caption: Shell script to run docbuild with Docker


The function uses these :command:`docker run` options and mounts:

* ``--cpus="$cpu_limit"`` sets the CPU quota for the container based on the host's available processing units or the value of :envvar:`DDOCBUILD_CPUS`.
* ``--rm`` removes the container after it exits. It does not remove the image
   or data in bind-mounted host directories.
* ``-it`` keeps standard input open and allocates a terminal for interactive
   use.
* ``--init`` runs a small init process to forward signals and reap orphaned
   child processes.
* ``--network=host`` shares the host network stack. Use it only when the
   container needs host networking; otherwise, Docker's default network provides
   more isolation.
   The practical advantage is more reliable signal forwarding and cleanup of orphaned child processes. That can matter when you interrupt a build or stop the container while DAPS or another subprocess is running.
* Each ``-v`` mount uses the form ``host-path:container-path[:options]``. The
   XDG variables, when set, select the host-side config, cache, and state
   directories; otherwise, the paths under ``$HOME`` are used. The config mount
   is read-only (``:ro``), while the cache and state mounts are writable.
* ``-v "$PWD:$PWD"`` makes the current host directory available at the same
   path inside the container, and ``-w "$PWD"`` sets it as the working
   directory.
* ``docbuild:leap160`` selects the image, and ``"$@"`` forwards the function's
   arguments to its entrypoint.



Debugging the Docker Container Image
------------------------------------

To debug the Docker container image, you can run it interactively with a shell:

.. code-block:: console

    $ docker run --rm -it --entrypoint /bin/bash docbuild:leap160
