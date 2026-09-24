# Proposal: Handling Multi-URL Prebuilt Deliverables

## The Problem

The current v6-to-v7 migration stylesheet has three issues handling `prebuilt` deliverables derived from v6 `<link>` elements:

1.  **Data Loss:** It silently drops any `<link>` that contains a `<url format="pdf">`. This affects at least 32 distinct documents from the source `docserv-stitch-2026-09-24.xml` file. The filter is inconsistent, as some PDFs do get through via a different template path.
2.  **Schema Under-utilization:** The v7 `portal-config.rnc` schema explicitly allows a `<prebuilt>` element to contain multiple `<url>` children (`url+`). This is the correct way to model a single deliverable available in multiple formats (e.g., HTML and PDF). The current stylesheet only ever produces one URL per deliverable.
3.  **ID Collisions:** The current ID generation scheme, based on the first English URL, creates duplicate `xml:id`s when multiple v6 `<link>`s point to the same target (e.g., release notes for different products but the same version). This results in invalid XML.

## Proposed Solution

The goal is to produce schema-valid XML that correctly represents all available formats for a prebuilt deliverable without data loss and with unique IDs.

This can be achieved with three changes within the `convert-v6-to-v7.xsl` stylesheet:

### 1. Stop Dropping PDF Links

*   **Where:** The `<xsl:template name="docset-without-builddocs">` and `<xsl:template match="docset/external" mode="builddocs">`.
*   **Change:** Remove the `and not(language/url/@format = 'pdf')` predicate from the link selection variables (`$eligible-links`) and `xsl:apply-templates` calls. The filter should only exclude external `https://` and `external-tree` links.
*   **Result:** This will prevent the stylesheet from discarding the 32 links that currently get dropped, ensuring all source documents are migrated.

### 2. Emit All URLs for English Deliverables

*   **Where:** The `<xsl:template match="link" mode="external-link-deliverable">`.
*   **Change:** Modify the `xsl:for-each` that currently selects `language[@lang = $lang]/url` to iterate over *all* `<url>` children of the corresponding English `<language>` element.
*   **Result:** The generated `<prebuilt>` element will correctly contain multiple `<url>` children, one for each format (HTML, PDF, ZIP), matching the schema's intent (`url+`).

```xml
<!-- EXAMPLE: Correct Output -->
<deliverable type="prebuilt" xml:id="suma.5.0.en-retail-guide">
  <prebuilt>
    <title>Retail Guide</title>
    <url format="html" href="/suma/5.0/en/suse-manager/retail/retail-overview.html"/>
    <url format="pdf" href="/suma/5.0/en/pdf/suse_manager_retail_guide.pdf"/>
    <descriptions>
      ...
    </descriptions>
  </prebuilt>
</deliverable>
```

### 3. Disambiguate IDs

*   **Where:** The `<xsl:template name="generate-external-link-id">` and its caller, `<xsl:template match="link" mode="external-link-deliverable">`.
*   **Change:** The ID generation logic needs to be more robust. Since a pure XSLT 1.0 solution for checking cross-file ID uniqueness is complex, a pragmatic approach is best:
    *   The primary ID can still be generated from the HTML URL, as it is the most common format.
    *   **To handle ID collisions:** When a link lacks an HTML URL or if the generated ID is known to be a duplicate (based on the 18 identified cases), append a unique part of the *first* URL's path to the ID to ensure uniqueness.
*   **Result:** This significantly reduces the chance of `xml:id` collisions, making the final output valid. A post-processing step could still be used to guarantee 100% uniqueness if needed, but this handles the vast majority of cases within the stylesheet itself.

This plan corrects the data loss, aligns the output with the schema, and resolves the critical ID collision issue, all with minimal, targeted changes to the existing stylesheet.
