# rnc2html Extension

This directory contains documentation for the `rnc2html` extension.

## Usage

See [index.rst](index.rst) for usage instructions and configuration details.

## Example Schema

An example RELAX NG XML schema is provided in [book.rng](book.rng). This schema demonstrates how to use `db:refpurpose` annotations for documentation extraction.

### Testing the Example

To test the extension with this example:

1. Add `book.rng` to your `conf.py` configuration:

   ```python
   rnc_html_files = ["extensions/rnc2html/docs/book.rng"]
   ```

2. Run the documentation build.
