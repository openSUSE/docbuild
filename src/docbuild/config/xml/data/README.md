# Portal Configuration

This directory contains:

* A RELAX NG schema. It's the successor of the previous Docserv
  product schema.
* An example `config.d` directory.

## File structure

The `config.d` directory contains several subdirectories

```text
config.d/
├── categories/
│   ├── [... more languages ...]
│   ├── de-de.xml
│   └── en-us.xml
├── cloudnative/  # product 1
│   ├── [... similar to sles/... ]
│   └── cloudnative.xml
├── portal.xml    # <-- Main file
└── sles/         # product 2
    ├── desc
    │   ├── [... more languages ...]
    │   ├── descriptions.xml   # <-- includes all the other
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
* `sles/desc/`: contains all language specific
* `sles/docsets/`: contains all docsets of a product.
  Depending on the complexity of the product, this may not always be
  needed. For SLES, it would probably useful.

## Additional Sources

https://confluence.suse.com/x/0QB5e
