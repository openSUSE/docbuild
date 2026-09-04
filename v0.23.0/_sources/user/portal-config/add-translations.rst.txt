.. _add-translations:

Adding Translations
===================

To add translations for a product, proceed as follows:

#. Identify the product and release you want to add the translations to.

   If you haven't created a release yet, create one as described in
   section :ref:`create-product`.

#. Open the file with the configuration for the release.

   In our example, we want to add translations for the example
   :file:`1.0.xml` for the 1.0 release of the NAS product.

#. Add a ``<locale>`` element for the language you want to
   add the translation for.

   For example, to add a translation for German , add a
   ``<locale>`` element with the ``lang`` attribute set to ``de-de``:

   .. code-block:: xml
      :caption: Adding a Locale Element for German
      :name: locale

      <locale lang="de-de">
        <branch>translations</branch>
        <subdir>l10n/de-de</subdir>
        <!-- ... translated deliverables ... -->
      </locale>

   As translations are usually stored in a separate Git branch and
   perhaps also in a different directory, the ``<locale>`` element
   provides an optional ``<branch>`` and ``<subdir>`` element.


#. Add translated deliverables.

   For translated deliverables, use a ``<deliverable>`` element
   with ``type="ref"`` and a ``<ref>`` element like this:

   .. code-block:: xml
      :caption: Adding a Translated Deliverable
      :name: translated-deliverable

      <deliverable type="ref">
        <ref linkend="nas.1.0.overview"/>
      </deliverable>

   The ``linkend`` attribute of the ``<ref>`` element
   points to the ID of the original deliverable.
