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

.. autoapisummary::

   docbuild.utils.contextmgr.TimerData


Functions
---------

.. autoapisummary::

   docbuild.utils.contextmgr.make_timer


Module Contents
---------------

.. py:function:: make_timer(name: str, method: collections.abc.Callable = time.perf_counter)

   Create independant context managers to measure elapsed time.

   Each timer is independent and can be used in a context manager.
   The name is used to identify the timer.

   :param name: Name of the timer.
   :param method: Method to use for measuring time, defaults
       to :func:`time.perf_counter`.
   :return: A context manager that yields a dictionary with start, end,
       and elapsed time.

   .. code-block:: python

       timer = make_timer('example_timer')

       with timer() as timer_data:
           # Code to be timed
           pass

       timer_data.elapsed  # Access the elapsed time


