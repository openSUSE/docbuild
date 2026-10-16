.. _publishing-deliverables:

Publishing Deliverables
=======================

After a successful build, :command:`docbuild build` copies each format's output
from its fresh temporary build directory into the local target configured by
``paths.target.target_base_dir`` and ``paths.target.target_dir_dyn``. This output
normally contains only deliverables, so there should be no version-control or
backup files to filter at this stage.

The local target may later accumulate version-control metadata or temporary
files. Those should be excluded when transferring the local target to a remote
server. The current CLI does not provide a :command:`docbuild publish` command;
configuring ``[remote]`` does not itself upload files.

The policy below is already applied to the active build-to-local-target transfer.
It also applies to every Python caller that omits explicit rsync options,
including remote-source pulls. See :func:`~docbuild.utils.sync.rsync` for how to
replace or disable this policy when those files are needed.

Default exclusions
------------------

By default, rsync skips version-control directories and temporary files listed
in :py:data:`~docbuild.constants.DEFAULT_RSYNC_EXCLUDES`.

The patterns are rsync *filter patterns*, matched by rsync itself, not
shell-expanded paths. The rules that matter in practice:

* ``*`` matches any sequence of characters except ``/``, and ``**`` also
  crosses directory boundaries.
* ``?`` matches a single character, and ``[...]`` matches a character class.
* A pattern without a slash matches at any depth. ``*.bak`` excludes every
  ``.bak`` file in the tree.
* A leading ``/`` anchors the pattern to the transfer root.
* A trailing ``/`` matches directories only. ``.git/`` excludes every directory
  named ``.git``.
* Rules are case-sensitive, so ``*.bak`` and ``*.BAK`` match different files.

For the complete syntax, see the `rsync Filter Rules
<https://download.samba.org/pub/rsync/rsync.1#FILTER_RULES>`_.

Source files remain unchanged. Exclusion does not remove matching files
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

Patterns must not be empty or whitespace-only. Duplicate patterns within either
list or across the two lists are rejected. Nonblank patterns are preserved
exactly, including spaces that may be significant to rsync.
