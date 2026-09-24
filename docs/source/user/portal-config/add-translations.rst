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
      :caption: Adding a ``<locale>`` Element for German
      :name: locale

      <locale lang="de-de">
        <branch>translations</branch>
        <subdir>l10n/de-de</subdir>
        <!-- NO deliverables! -->
      </locale>

   As translations are usually stored in a separate Git branch and
   perhaps also in a different directory, the ``<locale>`` element
   provides an optional ``<branch>`` and ``<subdir>`` element.

#. Done.


Translations are derived from the default language (English) and act
as a *blueprint*. The Docbuild tool automatically
retrieves the list of deliverables from the default language and
tries to find them as in the translation. No need to explicitly add
deliverables. This will work for the most part of our products.

In case you have to deviate from the default language, you can still
add deliverables manually. In such a case, it will *overwrite* the
list of deliverables in the default language.
