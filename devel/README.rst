Development helper tools
========================

The directory :code:`devel/` contains some helper tools to make development easier:

* :command:`activate-aliases.sh`
    Activates helpful aliases for the development environment. It provides
    shortcuts for common commands:

    * :command:`docbuild`
       The project's main command.
    * :command:`makedocs`
       Builds the project's documentation.
    * :command:`towncrier`
       Manages changelog and news entries.
    * :command:`upytest`
       Runs the project's test suite through pytest.
    * :command:`uipython`
       Starts an interactive IPython shell using start-up scripts
       in the :file:`.ipython/` directory.

    It is recommended to enable the aliases in your shell by sourcing the shell script in the root directory of the project:

    .. code-block:: shell-session
       :caption: Activating development aliases

       $ source devel/activate-aliases.sh

    Run the aliases in the root directory of the project to ensure they work correctly.

* :command:`bump-version.sh`
   Bumps the version of the project. To bump the minor version, use
    :code:`bump-version.sh minor`.

* :command:`lines-of-code.sh`
   Prints a summary of code lines, comments, and blank lines in the project
   for each file type.

