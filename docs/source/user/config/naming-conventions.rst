.. _config-key-naming-conventions:

Key Naming Conventions
======================

The keys follow specific naming conventions to indicate their purpose and expected value types. Here are some common patterns whereas the asterisk
(``*``) represents a variable part of the key:

* ``*_dir``: Contains a directory.

* ``tmp_*``: Indicates a temporary path.

* ``*_dyn``: Denotes a dynamic value that is expected to be resolved at runtime.

Directories are created automatically when the script runs. Additionally,
the script checks if the specified paths are readable, writeable and belongs
to the user running the script.
