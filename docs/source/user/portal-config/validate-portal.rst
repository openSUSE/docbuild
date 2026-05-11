.. _validate-portal:

Validating the Portal Configuration
===================================

The :command:`docbuild portal validate` subcommand is used to verify that your
XML configuration files are syntactically correct and conform to the required
Portal schema.

.. code-block:: shell
   :caption: Synopsis of :command:`docbuild portal validate`

   docbuild portal validate [OPTIONS]


Calling it with just the ENV configuration will validate it according to the
values inside the TOML configuration:

.. code-block:: shell
   :caption: Validate the portal configuration with environment settings

   $ docbuild --env-config=env.toml portal validate
   Validating
   - Portal XML config: /home/toms/.config/docbuild/config.d/portal.xml
   - Portal schema:     /home/toms/.config/docbuild/portal-config.rnc
   RNG validation => success

Use the following options in your TOML configuration:

* ``paths.main_portal_config``: The path to the main Portal XML configuration file.
* ``paths.portal_rncschema``: The path to the RNG Portal schema file for validation.

If you need to validate the Portal configuration against a different RNG
schema, specify the path to the alternative RNG schema file like this:

.. code-block:: shell
   :caption: Validate the portal configuration with an alternative RNG schema

   $ docbuild --env-config=env.toml portal validate --portal-schema /path/to/alternative/portal-config.rnc

Internally, the command uses the command :command:`jing` to perform the
RNG validation.


.. _validate-portal-checks:

Validation Checks Reference
---------------------------

Most structural requirements are handled by the Portal schema. However,
some additional checks cannot be easily expressed in RNG and performed
as Python checks after validation.

The following Python checks are executed after RNG validation as part
of portal validation (except where noted).

.. rubric:: check_dc_in_language

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

.. rubric:: check_duplicated_format_in_extralinks

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

.. rubric:: check_duplicated_url_in_extralinks

Check that url attributes in extralinks are unique within each language.

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

.. rubric:: check_enabled_format

Check if at least one format is enabled.

.. code-block:: xml

   <deliverable id="deli-1" type="dc">
     <dc file="DC-fake-doc">
        <!-- All formats here are disabled: -->
        <format epub="0" html="0" pdf="0" single-html="0"/>
     </dc>
   </deliverable>

.. rubric:: check_format_subdeliverable

Make sure that deliverables with subdeliverables have only HTML formats enabled.

.. code-block:: xml

   <deliverable id="deli-1" type="dc">
      <dc file="DC-fake-all">
         <!-- PDF enabled, but subdeliverables present: -->
         <format epub="0" html="1" pdf="1" single-html="1"/>
         <subdeliverable>book-1</subdeliverable>
      </dc>
   </deliverable>

.. rubric:: check_lang_code_in_desc

Ensure that each language code appears only once within ``<desc>``.

.. code-block:: xml

   <descriptions>
        <desc lang="en-us"/>
        <desc lang="en-us"/> <!-- Duplicate -->
   </descriptions>

.. rubric:: check_lang_code_in_docset

Ensure that each language code appears only once within ``<docset>``.

.. code-block:: xml

   <docset id="docset1" lifecycle="supported">
       <resources>
            <git remote="https://example.invalid/repo.git"/>
            <locale lang="en-us"><branch>main</branch></locale>
            <locale lang="en-us"><branch>main</branch></locale> <!-- Duplicate -->
       </resources>
   </docset>

.. rubric:: check_lang_code_in_extralinks

Ensure that each language code appears only once within
``external/link/url``.

.. note::

   This check currently exists in code but is not registered for execution.

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

.. rubric:: check_subdeliverable_in_deliverable

Check that site section is present in the XML tree.

.. code-block:: xml

   <deliverable id="deli-1" type="dc">
       <dc file="DC-fake-doc">
           <subdeliverable>sub-1</subdeliverable>
           <subdeliverable>sub-2</subdeliverable>
           <subdeliverable>sub-1</subdeliverable> <!-- Duplicate -->
       </dc>
   </deliverable>

.. rubric:: check_unsupported_language_code

Check for language codes that match the portal format but are not supported.

.. code-block:: xml

   <!-- Valid format but unsupported language: -->
   <locale lang="de-at"><branch>main</branch></locale>
