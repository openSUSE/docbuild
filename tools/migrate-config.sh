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


# --- Help Function ---
usage() {
    # Using shell parameter expansion ${0##*/} instead of basename $0
    SCRIPT_NAME=${0##*/}
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS] [INPUT_FILE]

Options:
  -s, --schema FILE      Path to schema file (Default: ${SCHEMAFILE@Q})
  -o, --output FILE      Name of the output file (Default: ${OUTPUT@Q})
                         Use a trailing slash to mark it as directory,
                         otherwise it's just a prefix
  -d, --dir DIR          Output directory (Default: ${OUTDIR@Q})
  -x, --xinclude         Enable xinclude processing
  -h, --help             Show this help message

Arguments:
  INPUT_FILE             The full Docserv stitch file without any XIncludes

Example:
* Use mostly the defaults:
  $SCRIPT_NAME -x --schema custom.rnc docserv-stitch.xml

* Store
  $SCRIPT_NAME -x --dir "~/.config/docbuild/config.d/" docserv-stitch.xml
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
                "~/"*) OUTDIR="$HOME/${OUTDIR#\~/}" ;;
            esac
            shift 2
            ;;
        -x|--xinclude)
            USE_XINCLUDE=1
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
xsltproc ${USE_XINCLUDE:+--stringparam use.xincludes 1} \
         --stringparam schemafile "$SCHEMAFILE" \
         --stringparam outputfile "$OUTPUT" \
         --stringparam outputdir "$OUTDIR" \
         "$XSLT" "$INPUT"
