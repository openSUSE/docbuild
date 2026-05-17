docbuild.utils.concurrency.TaskFailedError
==========================================

.. py:exception:: docbuild.utils.concurrency.TaskFailedError[T](item: T, original_exception: Exception)

   Bases: :py:obj:`Exception`

   .. autoapi-inheritance-diagram:: docbuild.utils.concurrency.TaskFailedError
      :parts: 1


   Exception raised when a task fails during processing.

   This wrapper preserves the context of a failure in concurrent processing pipelines.
   Since results may be returned out of order or aggregated later, wrapping the
   exception allows the caller to link a failure back to the specific input item
   that caused it.

   :param item: The item that was being processed.
   :param original_exception: The exception that caused the failure.

