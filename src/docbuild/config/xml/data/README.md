# Portal Configuration

This directory contains:

* A RELAX NG schema (`src/docbuild/config/xml/data/product-config-schema.rnc`).
  It's the successor of the previous Docserv product schema.
* An example `config.d` directory.

## File structure

The `config.d` directory contains several subdirectories

```text
config.d/
├── categories/
│   ├── [... more languages ...]
│   ├── de-de.xml
│   └── en-us.xml
├── cloudnative/
│   ├── [... similar to sles/... ]
│   └── cloudnative.xml
├── portal.xml
└── sles/
    ├── desc
    │   ├── [... more languages ...]
    │   ├── descriptions.xml
    │   ├── de-de.xml
    │   └── en-us.xml
    ├── docsets
    │   ├── [... more docsets ...]
    │   └── 16.0.xml
    └── sles.xml
```

* `config.d/`: the configuration directory with all portal configuration
* `categories/`: A directory that contains all categories.
* `portal.xml`: The main entry file which references all categories and
  product configuration.
* `sles/sles.xml`: The main product configuration for SLES.
* `sles/desc/`: contains all language specific descriptions.
* `sles/docsets/`: contains all docsets of a product.
  Depending on the complexity of the product, this may not always be
  needed. For SLES, it would probably useful.

## Creating combined config

To create a single XML config, use the following command:

```shell
xmllint --xinclude \
  --output portal-$(date --iso-8601).xml \
  src/docbuild/config/xml/data/config.d/portal.xml
```

## Migrating to the new portal schema

To migrate an old Docserv stitchfile to a _single portal XML config_, use
the following command:

```shell
$ xsltproc --param use.xincludes "0" \
         --stringparam outputdir "./" \
         --stringparam outputfile portal-test.xml \
         --stringparam schemafile "portal-config.rnc" \
convert-v6-to-v7.xsl docserv-stitch-2026-??-??.xml
Written file: "portal-test.xml"
```

The result is written to the file `portal-test.xml`.

The XSLT parameters have the following meaning:

* `use.xinclude` (default: `false()`): split the result config into different files and use XInclude elements to refer to.
* `outputdir` (default `output/`): determines the directory to write output files to. Mind the trailing slash.
* `outputfile` (default: `portal.xml`): The main output base filename.
* `schemafile` (default: empty): The RNG or RNC schema file that is referenced in a `<?xml-model?>` processing instruction at the header.
  The stylesheet takes care of the format and creates the appropriate PI.

To create a splited XML config, use the following command:


```shell
xsltproc --xinclude \
  --param use.xinclude 1 \
  --stringparam outputdir "config.d/" \
  convert-v6-to-v7.xsl \
  docserv-stitch-2026-??-??.xml
```

## General Changes
These changes reflect broad architectural shifts and naming conventions throughout the entire configuration system.

* **Rebranding**: The naming convention has shifted from "Docserv²" to "Portal."

* **Enhanced Modularity**: The schema now explicitly supports splitting large configuration files into smaller, more manageable parts. By utilizing inclusion mechanisms, you can maintain different sections of the portal (like `<categories>` or specific products) in separate files, leading to a cleaner and more maintainable structure.

* **Documentation-First Design**: The schema now heavily utilizes `db:refname` and `db:refpurpose` annotations for almost every element and attribute. This allows for automated generation of human-readable documentation directly from the RNC file.

* **Implicit Language Logic**: Master/source language identification has shifted from a boolean attribute (`@default`) to a value-based system. The schema now assumes `en-us` is the default language for products and deliverables.

* **Migration Tooling**: To facilitate the transition, an XSLT migration stylesheet is available. This tool automates the conversion of version 6.0 configuration files to the 7.0 format, handling the renaming of elements, restructuring of attributes, and the removal of deprecated metadata.

* **Resolving Ambiguity**: Some elements were used in multiple contexts, for example, the multipurpose `<language>` element. The new portal schema resolves this ambiguity.

## New Elements and Attributes
Version 7.0 introduces several elements to support a more hierarchical portal structure and better metadata documentation.

### Elements
* `<portal>`: The new root element for the entire portal configuration.
* `<spotlight>`: Used to highlight specific products or deliverables on the entry page.
* `<productfamilies>`: A container for defining product family groupings.
* `<series>`: Defines series/tabs (e.g., SBP, TRD, Products & Solutions).
* `<item>`: Generic element for entries within a family or series.
* `<descriptions>`: A unified wrapper for product or version descriptions.
* `<categories>`: A wrapper for grouping category definitions.
* `<resources>`: Replaces the old `<builddocs>` element for defining deliverables.
* `<prebuilt>`: Specifically for defining pre-built content links with metadata.
* `<xi:include>`:  An XInclude element pointing to an external XML resource to facilitate modularity.

### Attributes

* `@schemaversion`: Replaces the previous versioning logic for stricter validation against the 7.0 spec.  
* `@rank`: Determines the sorting order of products on the portal homepage.  
* `@family`: Links a product to a specific product family via `IDREF`.  
* `@series`: Links a product to a specific series/tab via IDREF.  
* `@path`: Used on products and docsets to specify relative directory names.  
* `@linkend`: Used in `<ref\>` elements to point to external link identifiers.  
* `@treatment`: Defines how version-specific descriptions interact with global ones (append, prepend, or replace).
* `@sitemap`: Determines whether the resource is included in the sitemap. Default is `true`.

## Renamed Elements and Attributes

Many elements were renamed to move away from "Docserv²" terminology and adopt a cleaner "Portal" naming convention.

| Old Name (v6.0) | New Name (v7.0) | Context |
| :---- | :---- | :---- |
| `<desc>`         | `<descriptions>` | Move a single description into a parent `<descriptions>` |
| `<builddocs>`    | `<resources>` | Container for definitions of resources |
| `<overridedesc>` | `<descriptions>` | Version-specific content |
| `<language>` (in resources) | `<locale>` | Regional build definitions |
| `@productid`     | `@id` (type ID) | Unique identifier for products |
| `@setid`         | `@id` (type ID) | Unique identifier for docsets |
| `@categoryid`    | `@id` (type ID) | Unique identifier for categories |
| `@linkid`        | `@id` (type ID) | Unique identifier for external links |

## Removed Elements and Attributes

The following items were deprecated or removed to simplify the build process and clean up the configuration.

* `<buildcontainer>`: Support for specifying custom Docker images per version has been removed.  
* `<param>`: Support for custom XSLT parameters via the config file is removed.  
* `@translation-type`: The distinction between "list" and "full" translations has been replaced by a more flexible \<locale\> and reference model.
* `@default`: This attribute (previously used in `<desc>` and `<language>` to flag the source/master language) has been removed. Language master ship is now determined by the explicit `en-us` value in the `@lang` attribute.
* `@meta` from `<deliverable>`

## Changed Content Models
The structure of the schema has evolved to be more modular and better documented.

### Modularization (XInclude)
Major elements now support `xi:include`, allowing configuration files to be broken into smaller, manageable chunks.

## link
Allows multiple URLs in `<link>`. This makes it possible to have different formats. Additionally allow a `<desc>` element to describe the resource.

The minimum structure is this:

```xml
<external>
    <link category="about" gated="false">
      <!-- Cardinality for <url>: one or more -->
      <url href="http://example.com" format="html"/>
      <descriptions>
    <desc lang="en-us">
      <title></title>
    </desc>
    <!-- more <desc> for other languages -->
      </descriptions>
    </link>
</external>
```

### Deliverable References
In version 7.0, translations of deliverables are primarily handled as references (`<ref\>`) back to the source DC file in the en-us locale, rather than duplicating the full deliverable metadata.

Additionally, the `<ref/>` contains only a `@linkend` attribute to link to a resource. You don't need `dc`, `product`, or other strange combinations anymore.

### Expanded Root Element Support
The schema no longer restricts the start of a document to just a product definition. It now allows for much more variety in valid root elements, supporting the standalone definition of `<product>`s, `<docset>`s, `<categories>`, and more.

### Simplified External Link Model
The model for external links has been significantly flattened. The previous hierarchical structure involving nested `<language>` elements has been removed. Now, a `<link>` directly contains a list of `<url>` elements and a unified `<descriptions>` block, simplifying how external resources are defined across different locales.


## Additional Sources

* https://github.com/openSUSE/docbuild/pull/197
* https://confluence.suse.com/x/0QB5e
