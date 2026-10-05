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
INPUT=""
USE_XINCLUDE=""


if ! command -v xsltproc >/dev/null 2>&1; then
    echo "Error: 'xsltproc' is required but not installed." >&2
    exit 1
fi

if ! command -v realpath >/dev/null 2>&1; then
    echo "Error: 'realpath' is required but not installed." >&2
    exit 1
fi


CREATE_LINK=0

# --- Help Function ---
usage() {
    # Using shell parameter expansion ${0##*/} instead of basename $0
    SCRIPT_NAME=${0##*/}
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS] [INPUT_FILE]

Options:
  -s, --schema FILE      Path to schema file (Default: ${SCHEMAFILE@Q})
  -o, --output FILE      Name of the output file (Default: ${OUTPUT@Q})
  -d, --dir DIR          Output directory (Default: ${OUTDIR@Q})
                         Use a trailing slash to mark it as directory,
                         otherwise it's just a prefix and it might get
                         unexpected results!
  -x, --xinclude         Enable xinclude processing
  -L, --with-link        Create a symlink to the portal-config.rnc in OUTDIR
      --without-link     Do not create a symlink (Default)
  -h, --help             Show this help message

Arguments:
  INPUT_FILE             The full Docserv stitch file without any XIncludes

Example:
* Use mostly the defaults:
  $SCRIPT_NAME -x --schema custom.rnc docserv-stitch.xml

* Store in the user's directory:
  $SCRIPT_NAME -x --dir "~/.config/docbuild/config.d/" docserv-stitch.xml

* Store in a single file:
  $SCRIPT_NAME --dir /tmp/test/ --output portal-config.xml docserv-stitch.xml
EOF
    exit 0
}

# --- Manual Argument Parsing ---
while [ $# -gt 0 ]; do
    case "$1" in
        -s|--schema)
            SCHEMAFILE="$2"
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
        -x|--xinclude)
            USE_XINCLUDE=1
            shift
            ;;
        -L|--with-link)
            CREATE_LINK=1
            shift
            ;;
        --without-link)
            CREATE_LINK=0
            shift
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

# --- Execution ---
# Note: Administrative privileges (sudo) may be required if writing to system-protected directories.
mkdir -p "$OUTDIR"
xsltproc ${USE_XINCLUDE:+--stringparam use.xincludes 1} \
         --stringparam schemafile "$SCHEMAFILE" \
         --stringparam outputfile "$OUTPUT" \
         --stringparam outputdir "$OUTDIR" \
         "$XSLT" "$INPUT"

# --- Create Symlink ---
if [ "$CREATE_LINK" -eq 1 ]; then
    # The -r option creates a relative symlink
    # The -f option removes any existing destination file
    RNC_PATH=$(realpath "$SCRIPT_DIR/../src/docbuild/config/xml/data/portal-config.rnc")
    ln -srf "$RNC_PATH" "$OUTDIR"
fi
