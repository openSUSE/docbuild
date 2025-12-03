docbuild.models.path.EnsureWritableDirectory
============================================

.. py:class:: docbuild.models.path.EnsureWritableDirectory(path: str | pathlib.Path)

   A Pydantic custom type that ensures a directory exists and is writable.

   Behavior:
   1. Expands user paths (e.g., "~/data" -> "/home/user/data").
   2. Validates input is a path.
   3. If path DOES NOT exist: It creates it (including parents).
   4. If path DOES exist (or was just created): It checks is_dir() and R/W/X permissions.


   .. py:method:: __get_pydantic_core_schema__(source_type: Any, handler: pydantic.GetCoreSchemaHandler) -> pydantic_core.core_schema.CoreSchema
      :classmethod:


      Define Validation AND Serialization logic.



   .. py:method:: validate_and_create(path: pathlib.Path) -> Self
      :classmethod:


      Expands user, checks if path exists. If not, creates it. Then checks permissions.


