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

   docbuild.config.xml.checks.docset_id
   docbuild.config.xml.checks.dc_identifier
   docbuild.config.xml.checks.check_dc_in_language
   docbuild.config.xml.checks.check_duplicated_format_in_extralinks
   docbuild.config.xml.checks.check_duplicated_url_in_extralinks
   docbuild.config.xml.checks.check_enabled_format
   docbuild.config.xml.checks.check_format_subdeliverable
   docbuild.config.xml.checks.check_lang_code_in_desc
   docbuild.config.xml.checks.check_lang_code_in_docset
   docbuild.config.xml.checks.check_lang_code_in_extralinks
   docbuild.config.xml.checks.check_subdeliverable_in_deliverable
   docbuild.config.xml.checks.check_unsupported_language_code


Module Contents
---------------

.. py:function:: docset_id(node: lxml.etree._Element) -> str

   Return a stable docset identifier for error messages.


.. py:function:: dc_identifier(deliverable: lxml.etree._Element) -> str

   Return a DC identifier from legacy or current schema representation.


.. py:function:: check_dc_in_language(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Make sure each DC appears only once within a language.

   .. code-block:: xml

       <locale lang="en-us">
           <branch>main</branch>
           <deliverable id="deli-1" type="dc">
               <dc file="DC-foo">
                   <format html="1" pdf="0" single-html="0" epub="0"/>
               </dc>
           </deliverable>
           <deliverable id="deli-2" type="dc">
               <dc file="DC-foo">
                   <format html="1" pdf="0" single-html="0" epub="0"/>
               </dc>
           </deliverable>
       </locale>

   :param tree: The XML tree to check.
   :return: CheckResult with success status and any error messages.


.. py:function:: check_duplicated_format_in_extralinks(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check that format attributes in extralinks are unique.

   .. code-block:: xml

      <external>
          <link>
               <url lang="en-us" href="https://example.com/page1" format="html"/>
               <url lang="en-us" href="https://example.com/page1.pdf" format="pdf"/>
               <!-- Duplicate format: -->
               <url lang="en-us" href="https://example.com/page1-again" format="html"/>
               <descriptions>
                   <desc lang="en-us"/>
               </descriptions>
          </link>
      </external>

   :param tree: The XML tree to check.
   :return: CheckResult with success status and any error messages.


.. py:function:: check_duplicated_url_in_extralinks(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check that url attributes in extralinks are unique within each language.

   Make sure each URL appears only once within a given language in external
   links section.

   .. code-block:: xml

      <external>
          <link>
              <url lang="en-us" href="https://example.com/page1" format="html"/>
              <url lang="en-us" href="https://example.com/page1" format="pdf"/>
              <descriptions>
                 <desc lang="en-us"/>
              </descriptions>
          </link>
      </external>

   :param tree: The XML tree to check.
   :return: CheckResult with success status and any error messages.


.. py:function:: check_enabled_format(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check if at least one format is enabled.

   .. code-block:: xml

      <deliverable id="deli-1" type="dc">
        <dc file="DC-fake-doc">
           <!-- All formats here are disabled: -->
           <format epub="0" html="0" pdf="0" single-html="0"/>
        </dc>
      </deliverable>

   :param tree: The XML tree to check.
   :return: CheckResult with success status and any error messages.


.. py:function:: check_format_subdeliverable(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Make sure that deliverables with subdeliverables have only HTML formats enabled.

   .. code-block:: xml

      <deliverable id="deli-1" type="dc">
         <dc file="DC-fake-all">
            <!-- PDF enabled, but subdeliverables present: -->
            <format epub="0" html="1" pdf="1" single-html="1"/>
            <subdeliverable>book-1</subdeliverable>
         </dc>
      </deliverable>

   :param tree: The XML tree to check.
   :return: True if all subdeliverables have at least one enabled format,
       False otherwise.


.. py:function:: check_lang_code_in_desc(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Ensure that each language code appears only once within <desc>.

   .. code-block:: xml

      <descriptions>
           <desc lang="en-us"/>
           <desc lang="en-us"/> <!-- Duplicate -->
      </descriptions>

   :param tree: The XML tree to check.
   :return: True if all lang attributes in desc are valid, False otherwise.


.. py:function:: check_lang_code_in_docset(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Ensure that each language code appears only once within <docset>.

   .. code-block:: xml

      <docset id="docset1" lifecycle="supported">
          <resources>
               <git remote="https://example.invalid/repo.git"/>
               <locale lang="en-us"><branch>main</branch></locale>
               <locale lang="en-us"><branch>main</branch></locale> <!-- Duplicate -->
          </resources>
      </docset>

   :param tree: The XML tree to check.
   :return: True if all lang attributes in extralinks are valid, False otherwise.


.. py:function:: check_lang_code_in_extralinks(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Ensure that each language code appears only once within ``external/link/url``.

   .. code-block:: xml

      <external>
        <link>
           <url lang="en-us" href="https://example.invalid/one" format="html"/>
           <url lang="en-us" href="https://example.invalid/two" format="pdf"/><!-- Wrong: duplicate lang -->
           <descriptions>
               <desc lang="en-us"/>
           </descriptions>
        </link>
      </external>

   :param tree: The XML tree to check.
   :return: CheckResult with success status and any error messages.


.. py:function:: check_subdeliverable_in_deliverable(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check that site section is present in the XML tree.

   .. code-block:: xml

       <deliverable id="deli-1" type="dc">
           <dc file="DC-fake-doc">
               <subdeliverable>sub-1</subdeliverable>
               <subdeliverable>sub-2</subdeliverable>
               <subdeliverable>sub-1</subdeliverable> <!-- Duplicate -->
           </dc>
       </deliverable>

   :param tree: The XML tree to check.
   :return: True if site/section is present, False otherwise.


.. py:function:: check_unsupported_language_code(tree: lxml.etree._Element | lxml.etree._ElementTree) -> CheckResult

   Check for language codes that match the portal format but are not supported.

   Catches subtle mistakes like ``de-at`` which matches the ``xx-yy`` regex
   but is not in :data:`~docbuild.constants.ALLOWED_LANGUAGES`.

   .. code-block:: xml

       <!-- Valid format but unsupported language: -->
       <locale lang="de-at"><branch>main</branch></locale>

   :param tree: The XML tree to check.
   :return: CheckResult with success status and any error messages.


