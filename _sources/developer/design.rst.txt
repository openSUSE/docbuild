Design
======

This document outlines the design philosophy and structure of the project.
It covers the core principles that guide development, the overall project layout,
and the specific design patterns used for the command-line interface,
configuration, and documentation. Understanding these concepts is key for
making effective contributions.


High-level build workflow
-------------------------

The following diagram illustrates the high-level workflow of the ``docbuild``
tool, from parsing command-line arguments to generating the final documentation
output. The core of the process involves concurrent tasks that are executed for
each deliverable.


.. graphviz::
   :name: fig-high-level-build-workflow
   :align: center
   :caption: High-level build workflow

   digraph "docbuild High-Level Workflow" {
      graph [rankdir="TB", splines=true, nodesep=0.6, ranksep=0.8];
      node [shape=box, style="rounded,filled", fillcolor="#E6F2FF"];
      edge [fontname="Helvetica", fontsize=10];

      // Inputs
      CLI [label="Command-line Input", fillcolor="#DAE8FC"];
      XML_Configs [label="XML Configs", shape=cylinder, style=filled, fillcolor="#F5F5F5"];
      Jinja_Templates [label="Jinja Templates", shape=cylinder, style=filled, fillcolor="#F5F5F5"];

      // Processing Steps
      Parse_CLI [label="Parse CLI & Configs"];
      Read_XML [label="Read XML & Get Deliverables"];

      subgraph cluster_async {
          label="Concurrent Processing (per deliverable)";
          style="dashed";
          bgcolor="#FFFFE0";
          node [fillcolor="#FFF2CC"];

          Extract_Metadata [label="Extract Metadata"];
          Build_Targets [label="Build Target Formats"];
          Combine_Info [label="Combine Info"];
          Render_Pages [label="Render Index Pages"];
          Fix_Canonicals [label="Fix Canonicals"];
      }

      // Finalization Steps
      Sync_Files [label="Sync Built Files"];
      Build_Sitemap [label="Build Sitemap"];

      // Output
      Final_Docs [label="Final Documentation", shape=folder, fillcolor="#D5E8D4", style=filled];

      // Edges
      CLI -> Parse_CLI;
      XML_Configs -> Read_XML;
      Parse_CLI -> Read_XML;

      Read_XML -> Extract_Metadata;
      Read_XML -> Build_Targets;

      Extract_Metadata -> Combine_Info;
      Read_XML -> Combine_Info [label="Config Info", style=dashed, constraint=false];

      Combine_Info -> Render_Pages;
      Jinja_Templates -> Render_Pages [style=dashed];

      // Build_Targets -> Sync_Files;
      Build_Targets -> Fix_Canonicals;
      Render_Pages -> Sync_Files;

      Fix_Canonicals -> Sync_Files;
      // Fix_Canonicals -> Build_Sitemap;
      Build_Sitemap -> Final_Docs;
      Sync_Files -> Final_Docs;
   }


Principles
----------

The code is based on the following principles:

* **Simplicity**: The code should be easy to understand using clean code practices and pythonic idioms.

* **Modularity**: The code should be organized into modules that can be easily reused and extended.

* **Testability**: The code should be easy to test, with a focus on unit tests and integration tests.

* **Performance**: The code should be efficient, with a focus on minimizing resource usage and maximizing speed.

* **Maintainability**: The code should be easy to modify and extend, with a focus on keeping the codebase clean and organized for future development.


Project design structure
-------------------------

The project follows a modular design structure, with the following main components:

* **Package Manager:** The project uses :command:`uv` as a package manager to manage dependencies and virtual environments. This allows for easy installation and management of project dependencies.

* **Modern project configuration**: The main configuration file ``pyproject.toml`` is used to define the project metadata and its dependencies.

* **Source directory**: This project follows a source layout, where the source code is stored in the :file:`src` directory. This helps to avoid issues with namespace collisions and makes it easier to manage dependencies.

* **Tests directory**: The tests are stored in the :file:`tests` directory, which contains unit tests and integration tests for the project.

* **Documentation directory**: The documentation is stored in the :file:`docs` directory, which contains the Sphinx documentation source files.

* **Changelog**: The project maintains a :file:`CHANGELOG.rst` file, which documents the changes made in each version of the project. The changelog is automatically generated using the towncrier tool. It uses the :file:`changelog.d` directory to store individual change files.



Commandline design patterns
---------------------------

The commandline interface is designed to be intuitive and user-friendly, following these patterns:

* **Dependency**: The CLI is built using the :mod:`click` library, which provides a simple and powerful way to create command-line interfaces in Python.

* **Subcommands**: The CLI uses subcommands to organize functionality.

* **Options and Arguments**: Options are used to modify the behavior of commands, while arguments are used to specify input data.

* **Help and Documentation**: Each command and option has a help message that can be accessed using the ``--help`` flag. This provides users with information on how to use the command and its options.

* **Error Handling**: The CLI provides clear error messages when commands fail, helping users understand what went wrong and how to fix it. The tool should never expose a traceback to the user, as this is considered a bug in the tool itself.

* **Code conventions**: All CLI commands are stored in the :mod:`docbuild.cli` module and follow the filename pattern :file:`cmd_*.py`.


Configuration design patterns
-----------------------------

The configuration system is designed to be flexible and easy to use, following these patterns:

* **Configuration types**: The tool differentiates between two types:

  * **Tool Configuration**: This configuration applies to the tool as a whole and contains settings that affect the behavior of the tool. The tool configuration is stored under the :mod:`docbuild.cli.config.application` module.

  * **Environment Configuration**: This configuration applies to a specific environment and contains settings that affect the behavior of the tool in that environment. The environment configuration is stored under the :mod:`docbuild.cli.config.environment` module.

* **File Format**: Both configuration files uses the TOML format.


Documentation design patterns
------------------------------

The documentation focuses on two target groups: users and developers. It follows these patterns:

* **RST Format**: The documentation is written in reStructuredText (RST) format.

* **Sphinx**: The documentation is built using Sphinx using extensions to create automatically API documentation from docstrings and CLI documentation from the :mod:`docbuild.cli` module.

* **User Documentation**: The user documentation is stored in the :file:`docs/source/user` directory and provides information on how to use the tool, including installation, configuration, and usage examples.

* **Developer Documentation**: The developer documentation is stored in the :file:`docs/source/developer` directory and provides information on how to contribute to the project, including design principles, code structure, and development practices.

* **API Documentation**: The API documentation is generated from the docstrings in the source code and is stored in the :file:`docs/source/reference/_autoapi` directory. This provides a reference for developers on how to use the project's classes and functions.