.. _config-key-naming-conventions:

Key Naming Conventions
======================

The keys follow specific naming conventions to indicate their purpose and expected value types. Here are some common patterns whereas the asterisk
(``*``) represents a variable part of the key:

* ``*_dir``: Contains a directory.

* ``tmp_*``: Indicates a temporary path.

* ``*_dyn``: Denotes a dynamic value that is expected to be resolved at runtime.

Directories configured as writable paths are created automatically during
configuration validation. Docbuild checks that these directories are readable,
writable, and executable.
