docbuild.config.xml.checks
==========================

.. py:module:: docbuild.config.xml.checks

.. autoapi-nested-parse::

   Contain different checks against the XML config.



Classes
-------

.. toctree::
   :hidden:

   /reference/_autoapi/docbuild/config/xml/checks/CheckResult

.. autoapisummary::

   docbuild.config.xml.checks.CheckResult


Functions
---------

.. autoapisummary::

   docbuild.config.xml.checks.check_dc_in_language
   docbuild.config.xml.checks.check_duplicated_categoryid
   docbuild.config.xml.checks.check_duplicated_format_in_extralinks
   docbuild.config.xml.checks.check_duplicated_linkid
   docbuild.config.xml.checks.check_duplicated_url_in_extralinks
   docbuild.config.xml.checks.check_enabled_format
   docbuild.config.xml.checks.check_format_subdeliverable
   docbuild.config.xml.checks.check_lang_code_in_category
   docbuild.config.xml.checks.check_lang_code_in_desc
   docbuild.config.xml.checks.check_lang_code_in_docset
   docbuild.config.xml.checks.check_lang_code_in_extralinks
   docbuild.config.xml.checks.check_lang_code_in_overridedesc
   docbuild.config.xml.checks.check_subdeliverable_in_deliverable
   docbuild.config.xml.checks.check_translation_deliverables
   docbuild.config.xml.checks.check_valid_languages


Module Contents
---------------

.. py:function:: check_dc_in_language(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Make sure each DC appears only once within a language.

   .. code-block:: xml

       <language lang="en-us" default="1">
           <deliverable>
               <dc>DC-foo</dc>
               <format html="1" pdf="1" single-html="0"/>
           </deliverable>
           <deliverable>
               <dc>DC-foo</dc>
               <format html="1" pdf="1" single-html="0"/>
           </deliverable>
       </language>

   :param tree: The XML tree to check.
   :return: CheckResult with success status and any error messages.


.. py:function:: check_duplicated_categoryid(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check that categoryid is unique within a product.

   .. code-block:: xml

       <category categoryid="container"> ... </category>
       <category categoryid="container"> ... </category>

   :param tree: The XML tree to check.
   :return: CheckResult with success status and any error messages.


.. py:function:: check_duplicated_format_in_extralinks(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check that format attributes in extralinks are unique.

   .. code-block:: xml

       <external>
         <link>
           <language>
             <url href="https://example.com/page1" format="html" lang="en-us"/>
             <url href="https://example.com/page1.pdf" format="pdf" lang="en-us"/>
             <!-- Duplicate format: -->
             <url href="https://example.com/page1_again" format="html" lang="en-us"/>
           </language>
         </link>
       </external>

   :param tree: The XML tree to check.
   :return: CheckResult with success status and any error messages.


.. py:function:: check_duplicated_linkid(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check that linkid is unique within an external element.

   .. code-block:: xml

       <external>
         <link linkid="fake-link">
           <language>
             <url href="https://example.com/page1" format="html" lang="en-US"/>
           </language>
         </link>
         <link linkid="fake-link"> <!-- Duplicate linkid -->
           <language>
             <url href="https://example.com/page2" format="html" lang="en-US"/>
           </language>
         </link>
       </external>

   :param tree: The XML tree to check.
   :return: CheckResult with success status and any error messages.


.. py:function:: check_duplicated_url_in_extralinks(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check that url attributes in extralinks are unique.

   Make sure each URL appears only once within a given external links section.

   .. code-block:: xml

       <external>
         <link>
           <language lang="en-US">
             <url href="https://example.com/page1" lang="en-US"/>
           </language>
         </link>
         <link>
           <language lang="en-US">
             <url href="https://example.com/page1" lang="en-US"/><!-- Duplicate -->
           </language>
         </link>
       </external>

   :param tree: The XML tree to check.
   :return: True if all url attributes in extralinks are unique, False otherwise.


.. py:function:: check_enabled_format(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check if at least one format is enabled.

   .. code-block:: xml

       <deliverable>
         <dc>DC-fake-doc</dc>
         <!-- All formats here are disabled: -->
         <format epub="0" html="0" pdf="0" single-html="0"/>
       </deliverable>

   :param tree: The XML tree to check.
   :return: CheckResult with success status and any error messages.


.. py:function:: check_format_subdeliverable(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Make sure that deliverables with subdeliverables have only HTML formats enabled.

   ... code-block:: xml

       <deliverable>
           <dc>DC-fake-all</dc>
           <!-- PDF enabled, but subdeliverables present: -->
           <format epub="0" html="1" pdf="1" single-html="1"/>
           <subdeliverable> ... </subdeliverable>
       </deliverable>

   :param tree: The XML tree to check.
   :return: True if all subdeliverables have at least one enabled format,
       False otherwise.


.. py:function:: check_lang_code_in_category(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Ensure that each language code appears only once within <category>.

   .. code-block:: xml
       <category categoryid="container">
           <language lang="en-us" title="..." />
           <language lang="en-us" title="..."/> <!-- Duplicate -->
       </category>

   :param tree: The XML tree to check.
   :return: True if all lang attributes in categories are valid, False otherwise.


.. py:function:: check_lang_code_in_desc(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Ensure that each language code appears only once within <desc>.

   .. code-block:: xml
       <product>
          <!-- ... -->
          <desc lang="en-us">...</desc>
          <desc lang="en-us">...</desc> <!-- Duplicate -->
       </product>

   :param tree: The XML tree to check.
   :return: True if all lang attributes in desc are valid, False otherwise.


.. py:function:: check_lang_code_in_docset(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Ensure that each language code appears only once within <docset>.

   .. code-block:: xml
       <docset setid="..." lifecycle="...">
           <!-- ... -->
           <builddocs>
               <git remote="..." />
               <language lang="en-us" default="1">...</language>
               <language lang="en-us" default="1">...</language> <!-- Duplicate -->
           </builddocs>
       </external>

   :param tree: The XML tree to check.
   :return: True if all lang attributes in extralinks are valid, False otherwise.


.. py:function:: check_lang_code_in_extralinks(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Ensure that each language code appears only once within <external>.

   .. code-block:: xml
       <external>
           <link>
               <language lang="en-us" default="1">...</language>
               <language lang="en-us" default="1">...</language> <!-- Duplicate -->
           </link>
       </external>

   :param tree: The XML tree to check.
   :return: True if all lang attributes in extralinks are valid, False otherwise.


.. py:function:: check_lang_code_in_overridedesc(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Ensure that each language code appears only once within <overridedesc>.

   .. code-block:: xml
       <overridedesc>
           <language lang="en-us" default="1">...</language>
           <language lang="en-us" default="1">...</language> <!-- Duplicate -->
       </overridedesc>

   :param tree: The XML tree to check.
   :return: True if all lang attributes in overridedesc are valid, False otherwise.


.. py:function:: check_subdeliverable_in_deliverable(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check that site section is present in the XML tree.

   .. code-block:: xml

       <deliverable>
           <dc>DC-fake-doc</dc>
           <subdeliverable>sub-1</subdeliverable>
           <subdeliverable>sub-2</subdeliverable>
           <subdeliverable>sub-1</subdeliverable> <!-- Duplicate -->
       </deliverable>

   :param tree: The XML tree to check.
   :return: True if site/section is present, False otherwise.


.. py:function:: check_translation_deliverables(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check that deliverables have translations in all languages.

   Make sure that deliverables defined in translations are a subset
   of the deliverables defined in the default language.

   .. code-block:: xml

   <language default="1" lang="en-us">
       <branch>main</branch>
       <deliverable>
         <dc>DC-SLES-all</dc>
         <format epub="0" html="1" pdf="0" single-html="0"/>
         <subdeliverable>book-rmt</subdeliverable>
       </deliverable>
   </language>
   <language  lang="de-de">
       <branch>main</branch>
       <deliverable>
         <dc>DC-SLES-all</dc>
         <!-- This subdeliverable is not present in the default language: -->
         <subdeliverable>book-abc</subdeliverable>
       </deliverable>
   </language>

   :param tree: The XML tree to check.
   :return: True if all deliverables have translations in all languages,
       False otherwise.


.. py:function:: check_valid_languages(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check that all languages are valid.

   .. code-block:: xml
       <language lang="en-us" default="1">...</language>
       <language lang="invalid-lang" default="0">...</language> <!-- Invalid -->

   :param tree: The XML tree to check.
   :return: CheckResult with success status and any error messages.


