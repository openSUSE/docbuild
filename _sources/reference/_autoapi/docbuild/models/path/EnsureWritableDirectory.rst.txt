docbuild.models.path.EnsureWritableDirectory
============================================

.. py:class:: docbuild.models.path.EnsureWritableDirectory(path: str | pathlib.Path)

   A Pydantic custom type that ensures a directory exists and is writable.

   Behavior:

   1. Expands user paths (e.g., ``~/data`` -> ``/home/user/data``).
   2. Validates input is a path.
   3. If path DOES NOT exist: It creates it (including parents).
   4. If path DOES exist (or was just created): It checks if it's a directory and has R/W/X permissions.


   .. py:method:: __get_pydantic_core_schema__(source_type: type[pathlib.Path], handler: pydantic.GetCoreSchemaHandler) -> pydantic_core.core_schema.CoreSchema
      :classmethod:


      Define Validation AND Serialization logic.



   .. py:method:: validate_and_create(path: pathlib.Path) -> type[Self]
      :classmethod:


      Expand user, check existence/permissions, or check parent for creation.



   .. py:method:: __str__() -> str

      Return the string representation of the path.



   .. py:method:: __repr__() -> str

      Return the developer-friendly representation of the object.



   .. py:method:: __truediv__(other: str) -> pathlib.Path

      Implement the / operator to delegate to the underlying Path object.



   .. py:method:: __getattr__(name: str) -> object

      Delegate attribute access to the underlying Path object.



   .. py:method:: __fspath__() -> str

      Return the string path for os.PathLike compatibility.


