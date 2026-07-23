docbuild.utils.sysdeps
======================

.. py:module:: docbuild.utils.sysdeps

.. autoapi-nested-parse::

   System dependency validation and version checking.



Classes
-------

.. toctree::
   :hidden:

   /reference/_autoapi/docbuild/utils/sysdeps/DependencyStatus

.. autoapisummary::

   docbuild.utils.sysdeps.DependencyStatus


Functions
---------

.. autoapisummary::

   docbuild.utils.sysdeps.get_binary_version
   docbuild.utils.sysdeps.check_dependencies
   docbuild.utils.sysdeps.requires_system_tools


Module Contents
---------------

.. py:function:: get_binary_version(name: str) -> str | None

   Run a tool and attempt to extract its version string using regex.


.. py:function:: check_dependencies() -> list[DependencyStatus]

   Check all defined system dependencies and return their status.


.. py:function:: requires_system_tools(tools: list[str] | None = None) -> collections.abc.Callable[[collections.abc.Callable[P, T]], collections.abc.Callable[P, T]]

   Enforce system dependencies on specific CLI commands.

   :param tools: A list of tool names. Defaults to all SYSTEM_DEPENDENCIES.


