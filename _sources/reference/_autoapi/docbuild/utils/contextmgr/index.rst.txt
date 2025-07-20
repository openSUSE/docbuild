docbuild.utils.contextmgr
=========================

.. py:module:: docbuild.utils.contextmgr

.. autoapi-nested-parse::

   Provides context managers.



Classes
-------

.. toctree::
   :hidden:

   /reference/_autoapi/docbuild/utils/contextmgr/TimerData
   /reference/_autoapi/docbuild/utils/contextmgr/PersistentOnErrorTemporaryDirectory

.. autoapisummary::

   docbuild.utils.contextmgr.TimerData
   docbuild.utils.contextmgr.PersistentOnErrorTemporaryDirectory


Functions
---------

.. autoapisummary::

   docbuild.utils.contextmgr.make_timer


Module Contents
---------------

.. py:function:: make_timer(name: str, method: collections.abc.Callable[[], float] = time.perf_counter) -> collections.abc.Callable[[], contextlib.AbstractContextManager[TimerData]]

   Create independant context managers to measure elapsed time.

   Each timer is independent and can be used in a context manager.
   The name is used to identify the timer.

   :param name: Name of the timer.
   :param method: A callable that returns a float, used for measuring time.
       Defaults to :func:`time.perf_counter`.
   :return: A callable that returns a context manager. The context manager
       yields a :class:`TimerData` object.

   .. code-block:: python

       timer = make_timer('example_timer')

       with timer() as timer_data:
           # Code to be timed
           pass

       timer_data.elapsed  # Access the elapsed time


