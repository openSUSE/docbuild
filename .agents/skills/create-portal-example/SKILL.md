---
name: create-portal-example
description: Create example Portal XML configuration
---

# Create Example Portal XML Configuration

## When to use this skill

Use when a user requests a sample Portal XML config that is compatible with the project's RELAX NG schema.

## Available RELAX NG schema

The Portal XML configuration must conform to the RELAX NG schema defined in
`src/docbuild/config/xml/data/portal-config.rnc`.

## Template structure

Templates are in `templates/` and use placeholders with
`{{ PLACEHOLDER_NAME }}`.

Build order (top to bottom):

* `templates/portal.xml`: Root container.
  Replace `{{ products }}` with one or more `<product>` blocks.

* `templates/product.xml`: One product.
  Replace `{{ docsets }}` with one or more `<docset>` blocks.

* `templates/docset.xml`: One release/docset.
  Replace the inner placeholder ``{{ deliverables }}`` with one or more `<deliverable>` blocks.

* `templates/deliverable-dc.xml`: Deliverable built by `daps`.

* `templates/deliverable-prebuilt.xml`: Prebuilt deliverable (for
  content generated outside `daps`, for example existing HTML/PDF).

If you add a product, include at least one docset.
If you add a docset, include at least one deliverable.

## How to use it

1. Request minimal required values: product id/name/acronym, docset id/version/path, deliverable type (`dc` or `prebuilt`), and language (default `en-us`).

2. Ask which root element to generate (`portal`, `product`, `docset`, or
   `deliverable`).
   If not specified, default to `portal`.

3. If generating a `portal`, start from `templates/portal.xml`.
   Insert one or more rendered `product.xml` blocks at
   `{{ products }}`.

4. If generating a `product`, start from `templates/product.xml`.
   Insert one or more rendered `docset.xml` blocks at `{{ docsets }}`.

5. If generating a `docset`, start from `templates/docset.xml`.
   Insert one or more rendered deliverables into the locale block.
   Use `deliverable-dc.xml` or `deliverable-prebuilt.xml`.

6. Keep IDs and references consistent.
   Ensure product/docset/deliverable IDs are unique and naming stays
   aligned (for example prefix deliverables with product+docset IDs).

7. Return only final XML unless user asks for explanation.
   Do not leave unresolved placeholders.

## Output quality checks

* XML is well-formed.
* No unresolved `{{ ... }}` placeholders remain.
* At least one product, one docset per product, and one deliverable per docset.
* `prebuilt` deliverables include a valid URL and title.
* `dc` deliverables include a `dc file` and at least one output format.

## Validation

If the config uses XIncludes (split-file layout), resolve them first:

```shell
xmllint --xinclude --noout CONFIG.xml
```

Validate a single (or resolved) config against the schema. Checks
ID/IDREF/IDREFS by default:

```shell
jing -c src/docbuild/config/xml/data/portal-config.rnc CONFIG.xml
```

If you don't need the ID/IDREF/IDREFS check, use the option `-i`:

```shell
jing -i -c src/docbuild/config/xml/data/portal-config.rnc CONFIG.xml
```
