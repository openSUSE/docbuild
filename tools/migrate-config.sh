#!/bin/sh

# --- Default Values ---
SCHEMAFILE="portal-config.rnc"
OUTPUT="portal.xml"
OUTDIR="output/"

# Get the directory where the script is located using shell built-ins
# If $0 contains a slash, SCRIPT_DIR is the part before the last slash.
# Otherwise, we assume the current directory (.).
case "$0" in
    */*) SCRIPT_DIR="${0%/*}" ;;
    *)   SCRIPT_DIR="." ;;
esac

XSLT="$SCRIPT_DIR/../src/docbuild/config/xml/data/convert-v6-to-v7.xsl"
DEFAULT_SCHEMA="$SCRIPT_DIR/../src/docbuild/config/xml/data/portal-config.rnc"
INPUT=""
USE_XINCLUDE=1
SCHEMA_GIVEN=""


for cmd in realpath xmlstarlet xmllint xsltproc ; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "Error: '$cmd' is required but not installed." >&2
      exit 1
  fi
done

SCHEMA_MODE=copy

# --- Help Function ---
usage() {
    # Using shell parameter expansion ${0##*/} instead of basename $0
    SCRIPT_NAME=${0##*/}
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS] [DOCSERV_STITCHFILE|CONFIGD_DIR]

Output options:
  -d, --dir DIR          Output directory (Default: ${OUTDIR@Q})
                         Use a trailing slash to mark it as directory,
                         otherwise it's just a prefix and it might get
                         unexpected results!
  -o, --output FILE      Name of the output file (Default: ${OUTPUT@Q})
  -X, --with-xinclude    Enable xinclude processing (Default)
      --without-xinclude Disable xinclude processing

Schema options:
  -s, --schema FILE      Schema file (RNC or RNG) (Default: ${SCHEMAFILE@Q})
                         With copy/link, FILE must exist; if not given,
                         the schema from this repository is used.
                         With none, FILE is used as-is in the
                         <?xml-model?> PI (can be a URL).
                         Schemas using include/external are unsupported.
  -S, --schema-mode MODE How to provide the schema in OUTDIR:
                         copy  - copy the file (Default)
                         link  - create an absolute symlink
                         none  - do nothing

General options:
  -h, --help             Show this help message

Arguments:
  DOCSERV_STITCHFILE     The full Docserv stitch file without any XIncludes
                         usually located at /tmp/docserv-stitch-YYYY-MM-DD.xml
  CONFIGD_DIR            A Docserv config directory (like config.d/);
                         a stitch file is created from it first

Example:
* Use the defaults (cr)
  $SCRIPT_NAME docserv-stitch.xml

* Store in the user's directory:
  $SCRIPT_NAME --dir "~/.config/docbuild/config.d/" docserv-stitch.xml

* Store in a single file:
  $SCRIPT_NAME --without-xinclude --dir /tmp/test/ --output portal-config.xml docserv-stitch.xml

* Create the stitchfile from a Docserv config directory:
  $SCRIPT_NAME config.d/
EOF

    exit 0
}

# --- Manual Argument Parsing ---
while [ $# -gt 0 ]; do
    case "$1" in
        -s|--schema)
            SCHEMAFILE="$2"
            SCHEMA_GIVEN=1
            shift 2
            ;;
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        -d|--dir)
            OUTDIR="$2"
            # Expand a leading ~ (quoted "~/..." is not expanded by the shell)
            case "$OUTDIR" in
                "~") OUTDIR="$HOME" ;;
                \~/*) OUTDIR="$HOME/${OUTDIR#\~/}" ;;
            esac
            shift 2
            ;;
        -X|--with-xinclude)
            USE_XINCLUDE=1
            shift
            ;;
        --without-xinclude)
            USE_XINCLUDE=""
            shift
            ;;
        -S|--schema-mode)
            SCHEMA_MODE="$2"
            case "$SCHEMA_MODE" in
                copy|link|none) ;;
                *)
                    echo "Error: Invalid schema mode '$SCHEMA_MODE', expected 'copy', 'link', or 'none'." >&2
                    exit 1
                    ;;
            esac
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        -*)
            echo "Error: Unknown option $1"
            usage
            ;;
        *)
            # This is assumed to be the input file
            INPUT="$1"
            shift
            ;;
    esac
done

if [ -z "$INPUT" ]; then
    echo "Error: No input Docserv stitchfile specified." >&2
    usage
fi

# --- Create stitchfile from a Docserv config directory ---
if [ -d "$INPUT" ]; then
    CONFIGDIR="${INPUT%/}"
    set -- "$CONFIGDIR"/*.xml
    if [ ! -e "$1" ]; then
        echo "Error: No XML files found in directory '$CONFIGDIR'." >&2
        exit 1
    fi

    if [ ! -f "$CONFIGDIR/_categories.xml" ]; then
        echo "Error: '$CONFIGDIR/_categories.xml' not found." >&2
        exit 1
    fi

    ROOT=$(xmlstarlet sel -t -v 'name(/*)' "$1" 2>/dev/null)
    case "$ROOT" in
        product|categories) ;;
        *)
            echo "Error: '$1' has root element '${ROOT}', expected 'product' or 'categories'." >&2
            exit 1
            ;;
    esac


    STITCHFILE="/tmp/docserv-stitch-$(date --iso-8601).xml"
    {
        printf '<?xml version="1.0" encoding="UTF-8"?>\n<docservconfig>\n'
        xmllint --xpath "/*" "$CONFIGDIR/_categories.xml" &&
        xmllint --xinclude --xpath "/*" "$CONFIGDIR"/[a-z]*.xml &&
        printf '</docservconfig>\n'
    } > "$STITCHFILE" || {
        echo "Error: Failed to create stitchfile '$STITCHFILE'." >&2
        exit 1
    }
    echo "Created stitchfile '$STITCHFILE'."
    INPUT="$STITCHFILE"
fi

# --- Resolve Schema ---
if [ "$SCHEMA_MODE" != none ]; then
    if [ -f "$SCHEMAFILE" ]; then
        SCHEMA_SRC=$(realpath "$SCHEMAFILE")
    elif [ -z "$SCHEMA_GIVEN" ]; then
        SCHEMA_SRC=$(realpath "$DEFAULT_SCHEMA")
    else
        echo "Error: Schema file '$SCHEMAFILE' not found." >&2
        exit 1
    fi
    # The schema ends up next to the main file, so the PI only needs its name
    SCHEMAFILE="${SCHEMAFILE##*/}"
fi

# --- Execution ---
# Note: Administrative privileges (sudo) may be required if writing to system-protected directories.
mkdir -p "$OUTDIR"
xsltproc ${USE_XINCLUDE:+--stringparam use.xincludes 1} \
         --stringparam schemafile "$SCHEMAFILE" \
         --stringparam outputfile "$OUTPUT" \
         --stringparam outputdir "$OUTDIR" \
         "$XSLT" "$INPUT"

# --- Provide Schema ---
if [ "$SCHEMA_MODE" != none ]; then
    SCHEMA_DEST="${OUTDIR%/}/$SCHEMAFILE"
    # Never replace the source with a copy or link to itself
    if [ ! -L "$SCHEMA_DEST" ] && [ "$SCHEMA_DEST" -ef "$SCHEMA_SRC" ]; then
        :
    elif [ "$SCHEMA_MODE" = copy ]; then
        # Replace a leftover symlink instead of writing through it
        cp --remove-destination "$SCHEMA_SRC" "$SCHEMA_DEST"
    else
        ln -sf "$SCHEMA_SRC" "$SCHEMA_DEST"
    fi
fi
