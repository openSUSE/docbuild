.. _run-testsuite:

Running the Test Suite
======================

To run the test suite for this project, you need to have completed the setup of your development environment as described in the :ref:`prepare-devel-env` topic.


Running the full test suite
----------------------------

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

Running specific tests
----------------------

In case you want to run a specific test or a subset of tests, specify the path to the test file or the test function. For example:

.. code-block:: shell-session
   :caption: Running specific tests
   :name: running-specific-tests

   upytest tests/test_module.py
   upytest tests/test_module.py::test_function_name

In the first example, all tests in `test_module.py` will be executed, while in the second example, only the specific test function `test_function_name` will be run.

Running failed tests only
-------------------------

If one of the test fails and you want to repeat the test run after you have fixed the issue, use the ``--lf``/``--last-failed`` option. For example:

.. code-block:: shell-session
   :caption: Running only the last failed tests
   :name: running-last-failed-tests

   upytest --lf


.. _interprete-coverage:

Interpreting coverage
---------------------

Coverage is a measure of how much of your code is executed during the tests. The coverage report is only generated when all tests pass.

.. code-block:: text
   :caption: Coverate report

   [...]
   src/docbuild/cli/cmd_validate/process.py  142      3     42      2  97.3%   217->219, 299-303
   [...]
   src/docbuild/utils/doc.py                  20      0      0      0 100.0%
   src/docbuild/utils/merge.py                74      0     34      0 100.0%
   src/docbuild/utils/paths.py                13      0      6      0 100.0%
   --------------------------------------------------------------------------
   TOTAL                                    1866     23    478      6  98.6%

If you look through the report, you will see which lines are not covered by tests indicated by a test coverage lower than 100%. The numbers in the report indicate the line numbers where the code is not executed during the tests.

In this example, the coverage report shows that 98.6% of the code is covered by tests. The file :file:`src/docbuild/cli/cmd_validate/process.py` has a coverage of 97.3%, meaning that some lines in this file are not executed during the tests. These lines are indicated by the numbers in the report, such as ``217->219`` and ``299-303``.

Depending on your code, you might want to improve the test coverage by adding more tests for the uncovered lines. This will help ensure that your code is thoroughly tested and behaves as expected.
