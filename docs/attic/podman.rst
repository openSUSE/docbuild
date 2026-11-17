
Working with Podman Container Images
====================================

In the following sections, we will create a Podman container image ``docbuild:leap160`` and demonstrate how to build, use, and debug it.


Building a Podman Container Image
---------------------------------

To build a Podman container image, you need to have a :file:`Containerfile` or :file:`Dockerfile` that defines the image's contents and build instructions.

Use the :command:`podman build` command to create the image:

.. code-block:: console

    $ podman build -t docbuild:leap160 .
    [...]
    Successfully tagged localhost/docbuild:leap160

In case you have different file names for your container definition, you can specify them using the ``-f`` flag with the :command:`podman build` command. For example:

.. code-block:: console

    $ podman build -f Containerfile.leap160 -t docbuild:leap16 .
    [...]
    Successfully tagged localhost/docbuild:leap160


Using the Podman Container Image
--------------------------------

To use a Podman container image with the :command:`docbuild` tool, run it using the :command:`podman run` command. In its simplest form, run it like this:

.. code-block:: console

    $ podman run --rm -it docbuild:leap160

         █          █         ▀ █     █
      █▀▀█ █▀▀█ █▀▀ █▀▀█ █  █ █ █  █▀▀█
      █  █ █  █ █   █  █ █  █ █ █  █  █
      ▀▀▀▀ ▀▀▀▀ ▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀ ▀▀ ▀▀▀▀

    Usage: docbuild [OPTIONS] [COMMAND] [ARGS]...

      Main CLI tool for document operations.

However, this command does not take into account your local environment, such as mounted volumes or environment variables. To properly use the `docbuild` tool with your local files, you may need to mount directories and pass necessary environment variables to the container.

You can run:

.. code-block:: console

    $ podman run --rm \
      --userns=keep-id:uid=1000,gid=1000 \
      -v "$HOME/.config/docbuild:$HOME/.config/docbuild:ro,Z" \
      -v "$HOME/.cache/docbuild:$HOME/.cache/docbuild:Z" \
      -v "$HOME/.local/state/docbuild:$HOME/.local/state/docbuild:Z" \
      docbuild:leap160 <COMMAND> <ARGS>



Using a Podman Module
---------------------

Writing all the volume mounts and user namespace options every time you run a container can be tedious.

For this reason, Podman allows you to create a "module". A module is a configuration file that contains predefined options for running containers, such as volume mounts and user namespace settings.

.. code-block:: console
   :caption: Creating the module directory

   $ mkdir -p ~/.config/containers/containers.conf.modules


.. code-block:: console
   :caption: A docbuild.conf Podman module

   $ cat << 'EOF' > ~/.config/containers/containers.conf.modules/docbuild.conf
   [containers]
   env = ["HOME"]
   userns = "keep-id:uid=1000,gid=1000"
   volumes = [
        "$HOME/.config/docbuild:/home/app/.config/docbuild:ro,Z",
        "$HOME/.cache/docbuild:/home/app/.cache/docbuild:Z",
        "$HOME/.local/state/docbuild:/home/app/.local/state/docbuild:Z",
   ]
   EOF

Run the container with the module loaded:

.. code-block:: console

    $ podman --module docbuild.conf run --rm docbuild:leap160 <COMMAND> <ARGS>

Or use a small script that you define in your home directory:

.. code-block:: bash
    :caption: Shell function for running docbuild with Podman

    pdocbuild() {
      podman run --rm -it \
        --userns=keep-id:uid=1000,gid=1000 \
        -v "$HOME/.config/docbuild:/home/app/.config/docbuild:Z" \
        -v "$HOME/.cache/docbuild:/home/app/.cache/docbuild:Z" \
        -v "$HOME/.local/state/docbuild:/home/app/.local/state/docbuild:Z" \
        -v "$PWD:$PWD:Z" -w "$PWD" \
        docbuild:leap160 "$@"
    }
