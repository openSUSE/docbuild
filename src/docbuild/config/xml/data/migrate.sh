#!/bin/sh

# --- Default Values ---
SCHEMAFILE="portal-config.rnc"
OUTPUT="portal-test.xml"
OUTDIR="./"

# Get the directory where the script is located using shell built-ins
# If $0 contains a slash, SCRIPT_DIR is the part before the last slash.
# Otherwise, we assume the current directory (.).
case "$0" in
    */*) SCRIPT_DIR="${0%/*}" ;;
    *)   SCRIPT_DIR="." ;;
esac

XSLT="$SCRIPT_DIR/convert-v6-to-v7.xsl"
INPUT="docserv-stitch-2026-04-27.xml"
USE_XINCLUDE=false


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
  -s, --schema FILE      Path to schema file (Default: $SCHEMAFILE)
  -o, --output FILE      Name of the output file (Default: $OUTPUT)
  -d, --dir DIR          Output directory (Default: $OUTDIR)
  -x, --xinclude         Enable xinclude processing
  -h, --help             Show this help message

Arguments:
  INPUT_FILE             The Docserv stitch file

Example:
  $SCRIPT_NAME -x --schema custom.rnc docserv-stitch.xml
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
            shift 2
            ;;
        -x|--xinclude)
            USE_XINCLUDE=true
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

# --- Prepare xsltproc Arguments ---
XINCLUDE_FLAGS=""
if [ "$USE_XINCLUDE" = true ]; then
    # --stringparam use.xincludes 1 passes the parameter to your XSLT logic
    # Note: You may also need to add the physical --xinclude flag here if xsltproc
    # needs to resolve the tags before passing them to the XSLT.
    XINCLUDE_FLAGS="--xinclude --stringparam use.xincludes 1"
fi

# --- Execution ---
# Note: Administrative privileges (sudo) may be required if writing to system-protected directories.
xsltproc $XINCLUDE_FLAGS \
         --stringparam schemafile "$SCHEMAFILE" \
         --stringparam outputfile "$OUTPUT" \
         --stringparam outputdir "$OUTDIR" \
         "$XSLT" "$INPUT"
