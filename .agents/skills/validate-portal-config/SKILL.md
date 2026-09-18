---
name: validate-portal-config
description: Validate a Portal XML configuration against the RELAX NG (RNC) schema, using either the `docbuild portal validate` CLI or jing/xmllint directly, including XInclude and ID/IDREF handling.
---

# Validate Portal Config

## When to use this skill

Use whenever a Portal XML configuration needs to be checked against the schema.
Referenced by the `create-portal-example`, `portal-config-schema`, and
migration workflows.

The RNC schema (source of truth) is:

```
src/docbuild/config/xml/data/portal-config.rnc
```

## Preferred: the CLI

The easiest and recommended way:

```shell
docbuild portal validate
```

This is the **preferred** method: besides the schema checks it also runs
additional Portal-specific checks that `jing` cannot perform.
See `docs/source/user/portal-config/validate-portal.rst` for options.

## Manual: jing / xmllint

`jing` works too, but it **only** validates against the RELAX NG schema:
structure, datatypes, and parent-child relationships. The additional
Portal-specific checks are **not** executed — use `docbuild portal validate`
for those.

If you need to validate a specific file directly:

1. If the config uses XIncludes (split-file layout), resolve them first:

   ```shell
   xmllint --xinclude --noout CONFIG.xml
   ```

2. Validate against the schema. The schema is RNC, so pass `-c`.
   ID/IDREF/IDREFS are checked by default:

   ```shell
   jing -c src/docbuild/config/xml/data/portal-config.rnc CONFIG.xml
   ```

   To skip the ID/IDREF/IDREFS check, add `-i`:

   ```shell
   jing -i -c src/docbuild/config/xml/data/portal-config.rnc CONFIG.xml
   ```

## Validating a split config in place

To let `jing` resolve XIncludes itself (instead of pre-resolving with
`xmllint`), set the Xerces XInclude parser property. The env var name depends
on the distro's jing wrapper — set all three to be safe:

```shell
XINCLUDE_PROP="-Dorg.apache.xerces.xni.parser.XMLParserConfiguration=org.apache.xerces.parsers.XIncludeParserConfiguration"

ADDITIONAL_FLAGS="$XINCLUDE_PROP" JAVA_OPTS="$XINCLUDE_PROP" JAVA_ARGS="$XINCLUDE_PROP" \
  jing -c src/docbuild/config/xml/data/portal-config.rnc config.d/portal.xml
```

(`ADDITIONAL_FLAGS` = openSUSE, `JAVA_ARGS` = Debian/Ubuntu, `JAVA_OPTS` = Fedora/RHEL.)
