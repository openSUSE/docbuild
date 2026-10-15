.. _publishing-deliverables:

Publishing Deliverables
=======================

After a successful build, :command:`docbuild build` uses rsync to copy the
contents of each format's build directory into the local target configured by
``paths.target.target_base_dir`` and ``paths.target.target_dir_dyn``.
The exclusions below apply to this transfer and to callers using the default
:class:`~docbuild.utils.sync.RsyncOptions`.

The current CLI does not provide a :command:`docbuild publish` command.
The ``[remote]`` section describes a remote destination, but these settings
do not introduce a remote upload step.

Default exclusions
------------------

By default, rsync skips these version-control directories and temporary files:

.. code-block:: text

   .git/
   .svn/
   .hg/
   .bzr/
   *~
   *.old
   *.bak
   *.BAK
   *.orig
   *.rej
   *.html.new

These are rsync filter patterns, not shell-expanded paths. A trailing slash
matches directories only. Unanchored names can match at any depth within the
transfer, and patterns are case-sensitive (hence both ``*.bak`` and ``*.BAK``).
The source files remain unchanged. Exclusion does not remove matching files
already present in the target.

Customize the exclusions
------------------------

Configure ``[rsync]`` in your ENV TOML file (see :ref:`config-tomlfile`).
To keep the defaults and add more patterns:

.. code-block:: toml

   [rsync]
   exclude_extra = ["*.tmp", "drafts/"]

An explicit ``exclude`` list **replaces** the defaults. For example, to exclude
only Git directories and temporary files:

.. code-block:: toml

   [rsync]
   exclude = [".git/"]
   exclude_extra = ["*.tmp"]

To disable all exclusions, set both lists to empty:

.. code-block:: toml

   [rsync]
   exclude = []
   exclude_extra = []

If another configuration layer already sets ``exclude_extra``, setting only
``exclude = []`` leaves those additional patterns active. Each list follows
the usual configuration precedence: a later list replaces the earlier list;
lists are not concatenated across configuration files. After merging,
``exclude_extra`` is appended to the selected ``exclude`` list.

Use :command:`docbuild config list --env` to inspect the effective settings.
In Python, passing ``RsyncOptions(exclude=[...])`` also replaces the defaults;
passing ``RsyncOptions(exclude=[])`` disables them. The ENV ``exclude_extra``
option combines the two lists before creating those options.
