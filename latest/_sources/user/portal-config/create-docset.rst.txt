.. _create-docset:

Creating Docsets
================

A "docset" is usually a specific "release" of a product. To define
a new docset, proceed as follows:

#. Determine the the "name" of a docset.

   This attribute acts as an identifier. The value should be short and
   descriptive. It is used in the doctype syntax, when you request a build, and
   has an impact when directories are created and it is visible in the URL.

   Let's assume, we want to create ``1.0`` release, hence you
   would set the value to ``1.0``.

#. Determine the docset ID.

   This unique ID is used in several places in the configuration.
   It is not used outside the Portal configuration.
   As the ID cannot start with a number due to the XML ID definition,
   it's recommended to prefix it with the product ID.

   In our example, with a product ID of ``nas`` the docset ID
   would become ``nas.1.0``.

#. Determine the lifecycle of the docset.

   Each product and its releases go through a product lifecycle:
   from a beta release, to supported, and finally to unsupported.

   A new release is likely be ``beta`` or ``supported``.
   Older, out-of-date releases becomes ``unsupported`` over time.

   An unsupported docset is not automatically selected during
   a build unless it's explicitly requested.

#. Add a docset/release.

   Each release is defined with a ``<docset>`` element.
   Depending on the amount of deliverables and the complexity
   of the release, you can either put the
   ``<docset>`` element directly into the product configuration
   file or create a separate file for each release and include
   it in the product configuration.
   See section :ref:`single-vs-multifile` for more details.

   We choose the second option and create a file named
   :file:`1.0.xml` for the 1.0 release of the NAS product:

   .. code-block:: xml
      :caption: The 1.0 release of the NAS product :file:`1.0.xml`
      :name: nas.docset

      <docset id="nas.1.0" path="1.0" lifecycle="supported">
        <version>1.0</version>
        <resources>
          <git remote="https://github.com/example/nas.git"/>
          <locale lang="en-us">
            <branch>main</branch>
            <!-- ... deliverables ... -->
          </locale>
        </resources>
      </docset>

#. Add a ``<resources>`` child element.

   Possible child elements are:

   * An optional ``<git>`` element to define the Git repository for
     the sources of this release.
     This is only needed if your product is built via DAPS.
     For other build systems like Antora, the deliverables are built
     outside of docbuild. In that case, omit this tag.

#. Add a ``<locale lang="en-us">`` element for English.

   This is the minimal element you need and holds all English
   deliverables.

   Possible child elements are:

   * ``<branch>`` (required): contains the branch from the Git repository.
     This is only useful when you defined a Git repository. For prebuilt
     deliverables, it's not needed.
   * ``<subdir>`` (optional): contains the directory where to look for the
     DC files. For prebuilt deliverables, it's not needed.

#. Optionally add translations in a ``<locale lang="...">`` element.

   The structure looks slightly different than for English.
   How to add this, look at section :ref:`add-translations`.

#. Add a deliverable in your ``<locale lang="en-us">`` element.

   Continue with section :ref:`add-deliverable`.

