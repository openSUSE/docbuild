Listing dependencies
====================

If you want to get an overview of the dependencies used in the project, you can use the `uv` command to list them:

.. code-block:: shell-session

   $ uv tree
   Resolved 53 packages in 15ms
   docbuild
   ├── click v8.2.1
   ├── jinja2 v3.1.6
   │   └── markupsafe v3.0.2
   ├── lxml v5.4.0
   ├── pydantic v2.11.5
   │   ├── annotated-types v0.7.0
   │   ├── pydantic-core v2.33.2
   │   │   └── typing-extensions v4.14.0
   │   ├── typing-extensions v4.14.0
   │   └── typing-inspection v0.4.1
   │       └── typing-extensions v4.14.0
   ├── rich v14.0.0
   │   ├── markdown-it-py v3.0.0
   │   │   └── mdurl v0.1.2
   │   └── pygments v2.19.1
   └── tomlkit v0.13.3

This gives a tree-like structure of the dependencies, showing the main packages and their sub-dependencies. The output includes the package names and their versions, allowing you to see which libraries are being used in the project.

In case you want to list outdated dependencies, use the option ``--outdated``:

.. code-block:: shell-session

   $ uv tree --outdated
   Resolved 53 packages in 15ms
   docbuild
   ├── click v8.2.1
   ├── jinja2 v3.1.6
   │   └── markupsafe v3.0.2
   ├── lxml v5.4.0
   ├── pydantic v2.11.5
   │   ├── annotated-types v0.7.0
   │   ├── pydantic-core v2.33.2 (latest: v2.34.1)
   │   │   └── typing-extensions v4.14.0
   │   ├── typing-extensions v4.14.0
   │   └── typing-inspection v0.4.1
   │       └── typing-extensions v4.14.0
   ├── rich v14.0.0
   │   ├── markdown-it-py v3.0.0
   │   │   └── mdurl v0.1.2
   │   └── pygments v2.19.1
   └── tomlkit v0.13.3

As you can see, the output indicates that the package ``pydantic-core`` has a newer version available (v2.34.1), while the others are up to date.