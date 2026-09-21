---
name: portal-config-schema
description: Understand and modify the Portal Config schema (RELAX NG compact / RNC as source of truth) and migrate old Docserv (v6) configs to the new Portal (v7) config using the migration XSLT stylesheet.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: configuration
  audience: [developers]
---

# Portal Config Schema & Migration

## When to use this skill

Use when a task involves:

* Understanding, reading, or editing the Portal configuration **schema**.
* Adding, renaming, or removing elements/attributes in the schema.
* **Migrating** an old Docserv (v6) config to the new Portal (v7) config.
* Validating a Portal XML config against the schema.

For generating *example* config XML, use the `create-portal-example` skill instead.

## Source of truth: the RNC schema

The Portal schema is authored in **RELAX NG compact syntax (RNC)**. This one
file is the single source of truth:

```
src/docbuild/config/xml/data/portal-config.rnc
```

Rules:

* **Always edit the `.rnc` file.** Never hand-edit a generated `.rng`. If an
  `.rng` is needed, generate it from the `.rnc` (e.g. `trang portal-config.rnc portal-config.rng`).
* Element/attribute definitions use naming like `ds.product`, `ds.docset`,
  `ds.deliverable`. Refer to an existing definition by its `ds.*` pattern name.
* Every element/attribute carries **DocBook annotations** for documentation:
  * `db:refname [ "name" ]` and `db:refpurpose [ "..." ]` in a `[ ... ]` block
    before the `div`/pattern.
  * Two hashes (`##`) are inline RELAX NG annotations shown by XML editors.
* Companion stylesheets in the same directory:
  * `rng2docbook.xsl`: turns the schema (RNG form) into a DocBook 5 reference,
    driven by the `db:refname`/`db:refpurpose` annotations.
  * `simplify.xsl`: strips comments/PIs and deprecated bits for processing.

### Adding / changing an element

Follow the documented workflow in
`docs/source/developer/howto/xml-config.rst`. In short:

1. Add the definition to `portal-config.rnc` with `db:refname`/`db:refpurpose`
   annotations and a `##` description, wrapped in a `div { ... }`.
2. Reference it (e.g. `ds.new-element`) from the relevant parent pattern.
3. Adjust the matching Pydantic/XPath model under `src/docbuild/models/`.
4. Add positive **and** negative schema tests.
5. Update user/developer docs if user-facing.

## Migration: Docserv v6 -> Portal v7

The migration is a **one-time** process, only relevant for existing Docserv
installations, not for new users starting from scratch.

The easiest is to use the `tools/migrate-config.sh` script (see below).

Input is a Docserv **stitchfile** (all v6 config files merged with XIncludes
resolved into one XML). Full reference:
`docs/source/developer/migrate-config.rst`.

### Prerequisites

`xmllint`, `xsltproc`, and `jing` installed, plus a Docserv stitchfile
(copy from the Docserv server, or build locally per the docs).

### Two output shapes

* **Single file** (easy to search/debug): default, `use.xincludes=false`.
* **Split directory** (modular, recommended for maintenance): set
  `use.xincludes=true`; files are wired together with XInclude elements.

### Key XSLT parameters

* `use.xincludes` (default `false`): split output vs. single file. 
* `outputdir` (default `output/`): target directory (keep the trailing slash).
  The intended real target is usually `$HOME/.config/docbuild/config.d/`.
  **Always ask the user before writing there** — that directory may already
  hold a live config that would be overwritten. Write to a scratch dir first
  if unsure.
* `outputfile` (default `portal.xml`): main output base filename. Ususally you
  can keep this value.
* `schemafile` (default empty): RNC/RNG path written into the `<?xml-model?>`
  PI header; the stylesheet detects RNC vs. RNG automatically.
* `schemaversion` (default `7.0`): target schema version.
* `cat.prefix` (default `cat.`): prefix for category IDs to avoid collisions.
  Usually not need to be changed. You can keep the default.

### Convenience wrapper

`tools/migrate-config.sh` wraps the `xsltproc` call with
`-s/--schema`, `-o/--output`, `-d/--dir`, `-x/--xinclude` options. It takes the
Docserv stitchfile as a required positional argument.

Example (single file):

```shell
tools/migrate-config.sh --output "portal-$(date --iso-8601).xml" \
  --schema "portal-config.rnc" \
  --dir "./" \
  STITCHFILE.xml
```

Example (split, into the user config dir):

```shell
tools/migrate-config.sh --xinclude --output "portal-$(date --iso-8601).xml" \
  --schema "portal-config.rnc" \
  --dir "./" \
  STITCHFILE.xml
```

> **Ask before overwriting.** `$HOME/.config/docbuild/config.d/` may already
> contain a live Portal config. Confirm with the user before writing there;
> otherwise migrate into a scratch directory and let the user copy the result
> over themselves.

After migrating, point the env config at the result via
`paths.config_dir` and `paths.main_portal_config`.

### What the migration does (high level)

Renames v6 -> v7 (`<builddocs>`->`<resources>`, `<desc>`->`<descriptions>`,
`<language>` in resources -> `<locale>`, `@productid`/`@setid`/`@categoryid`
-> `@id`), drops removed items (`<buildcontainer>`, `<param>`, `@default`,
`@meta`, `@translation-type`), and adds the new `<portal>` root plus
family/series/spotlight structure. Full list: the "General/New/Renamed/Removed"
sections in `src/docbuild/config/xml/data/README.md`.

## Validation

Validate migrated or edited configs with the `validate-portal-config` skill
(CLI `docbuild portal validate`, or `jing -c` against `portal-config.rnc`
with `xmllint --xinclude` for split layouts).

## Reference files

* Schema (source of truth): `src/docbuild/config/xml/data/portal-config.rnc`
* Migration stylesheet: `src/docbuild/config/xml/data/convert-v6-to-v7.xsl`
* Wrappers: `tools/migrate-config.sh`
* Docs: `docs/source/developer/migrate-config.rst`,
  `docs/source/developer/howto/xml-config.rst`,
  `src/docbuild/config/xml/data/README.md`


