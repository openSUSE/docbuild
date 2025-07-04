Validating XML configuration
============================

The :command:`docbuild build` subcommand is used to validate XML configuration files. It checks the syntax and structure of the XML files against a RelaxNG schema to ensure they conform to the expected format.

.. code-block:: shell
   :caption: Synopsis of :command:`docbuild validate`

   docbuild validate [OPTIONS]

The process is a two step approach:

1. It first validates the XML config file individually against the RNG schema to ensure it is structurally correct. After this, it applies several check rules to ensure the XML file is semantically correct.
2. If the first step is successful, it then creates a combined XML file that includes all the individual XML files ("stitchfile"). This combined file is checked if references inside are correct.

