#!/bin/sh

# Get the directory where the script is located using shell built-ins
case "$0" in
    */*) SCRIPT_DIR="${0%/*}" ;;
    *)   SCRIPT_DIR="." ;;
esac

# --- Default Values ---
SCHEMAFILE="$SCRIPT_DIR/portal-config.rnc"
USE_XINCLUDE=false
DISABLE_ID_CHECK=false
INPUT=""

if ! command -v jing >/dev/null 2>&1; then
    echo "Error: 'jing' is required but not installed." >&2
    exit 1
fi

# --- Help Function ---
usage() {
    SCRIPT_NAME=${0##*/}
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS] <INPUT_FILE>

Options:
  -s, --schema FILE      Path to RNC/RNG schema file (Default: $SCHEMAFILE)
  -x, --xinclude         Enable XInclude processing
  -i, --id               Disable checking of ID/IDREF/IDREFS
  -h, --help             Show this help message

Arguments:
  INPUT_FILE             The main Portal XML file to validate


Example:
  $SCRIPT_NAME -x --id config.d/portal.xml
EOF
    exit 0
}

# --- Manual Argument Parsing ---
if [ $# -eq 0 ]; then usage; fi

while [ $# -gt 0 ]; do
    case "$1" in
        -s|--schema)
            SCHEMAFILE="$2"
            shift 2
            ;;
        -x|--xinclude)
            USE_XINCLUDE=true
            shift
            ;;
        -i|--id)
            DISABLE_ID_CHECK=true
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
            INPUT="$1"
            shift
            ;;
    esac
done

if [ -z "$INPUT" ]; then
    echo "Error: No input XML file specified."
    usage
fi

# --- Prepare Jing Arguments ---
JING_FLAGS=""
XINCLUDE_PROP="-Dorg.apache.xerces.xni.parser.XMLParserConfiguration=org.apache.xerces.parsers.XIncludeParserConfiguration"

# Detect if the schema is in compact syntax (.rnc)
case "$SCHEMAFILE" in
    *.rnc)
        JING_FLAGS="$JING_FLAGS -c"
        ;;
esac

if [ "$DISABLE_ID_CHECK" = true ]; then
    JING_FLAGS="$JING_FLAGS -i"
fi


# --- Execution ---
echo "Validating $INPUT against $SCHEMAFILE..."

if [ "$USE_XINCLUDE" = true ]; then
    # We set ADDITIONAL_FLAGS (openSUSE), JAVA_OPTS (Fedora)
    # and JAVA_ARGS (Debian/Ubuntu) to ensure the XInclude parser
    # configuration is picked up regardless of the wrapper.
    ADDITIONAL_FLAGS="$XINCLUDE_PROP" JAVA_OPTS="$XINCLUDE_PROP" JAVA_ARGS="$XINCLUDE_PROP" jing $JING_FLAGS "$SCHEMAFILE" "$INPUT"
else
    jing $JING_FLAGS "$SCHEMAFILE" "$INPUT"
fi

# Check the exit status of jing
if [ $? -eq 0 ]; then
    echo "Validation successful."
else
    echo "Validation failed."
    exit 1
fi
