Running the Test Suite
======================

To run the test suite for this project, you need to have completed the setup of your development environment as described in the :ref:`prepare-devel-env` topic.

To run the full test suite, use the following command:

.. code-block:: shell-session
   :caption: Running pytest directly with |uv|
   :name: running-pytest-with-uv

   uv run --frozen pytest

or use the alias (see :ref:`devel-helpers` for more information):

.. code-block:: shell-session
   :caption: Running pytest using |uv| with alias :ref:`upytest <devel-helpers>`
   :name: running-upytest

   upytest

This command will execute all the tests defined in the project. The test suite is designed to ensure that all components of the project are functioning correctly and to catch any regressions.

In case you want to run a specific test or a subset of tests, specify the path to the test file or the test function. For example:

.. code-block:: shell-session
   :caption: Running specific tests
   :name: running-specific-tests

   upytest tests/test_module.py
   upytest tests/test_module.py::test_function_name

In the first example, all tests in `test_module.py` will be executed, while in the second example, only the specific test function `test_function_name` will be run.

If one of the test fails and you want to repeat the test run after you have fixed the issue, use the ``--lf``/``--last-failed`` option. For example:

.. code-block:: shell-session
   :caption: Running only the last failed tests
   :name: running-last-failed-tests

   upytest --lf