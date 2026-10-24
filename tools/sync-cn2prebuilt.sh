#!/bin/bash
#
# ==============================================================================
# Script Overview & Execution Steps:
# 1. Resolve the script's working directory dynamically without subshells.
# 2. Initialize default configuration variables (destination, config dir, etc.).
# 3. Parse command-line arguments (-h, --from-file, --dest, --config-dir).
# 4. Determine the file list source:
#    a. If a static file is provided via --from-file, validate and use it.
#    b. If not, parse Cloudnative XML configs using xmlstarlet, strip any
#       empty lines with sed, and save the paths to a temporary file.
# 5. Ensure the local destination directory exists (creates it if missing).
# 6. Execute rsync to securely pull the exact file list from the remote server.
# ==============================================================================
#
# 1. Resolve default script directory
SCRIPT_DIR="${BASH_SOURCE[0]%/*}"
if [[ "$SCRIPT_DIR" == "${BASH_SOURCE[0]}" ]]; then
    SCRIPT_DIR="."
fi

# 2. Define default configuration variables
LOCAL_DEST_DIR="prebuilt"
FILE_LIST=""
CONFIG_DIR="${HOME}/.config/docbuild/config.d/cloudnative"
REMOTE_BASE_DIR="/data/docserv2/external-builds/external-tree/en-us/"
REMOTE_HOST="docserv"


# 3. Define the Help Function using a HERE document
show_help() {
    cat <<EOF
Usage: ${0##*/} [OPTIONS]
Synchronize specific files from the remote documentation server using rsync.

Options:
  -h, --help               Display this help message and exit.
      --from-file FILE     Specify a custom file containing the list of files to sync.
                           (Overrides dynamic XML config extraction)
      --dest DIR           Specify the local destination directory.
                           (Default: ${LOCAL_DEST_DIR@Q})
      --config-dir DIR     Directory containing Cloudnative XML config files.
                           (Default: ${CONFIG_DIR@Q})

Example:
  ${0##*/} --config-dir /alternate/config/path --dest custom_build_dir
EOF
}

# 4. Parse Command-Line Arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        --from-file)
            if [[ -n "$2" && "$2" != -* ]]; then
                FILE_LIST="$2"
                shift 2
            else
                echo "Error: --from-file requires a valid file path as an argument." >&2
                exit 1
            fi
            ;;
        --dest)
            if [[ -n "$2" && "$2" != -* ]]; then
                LOCAL_DEST_DIR="$2"
                shift 2
            else
                echo "Error: --dest requires a valid directory path as an argument." >&2
                exit 1
            fi
            ;;
        --config-dir)
            if [[ -n "$2" && "$2" != -* ]]; then
                CONFIG_DIR="$2"
                shift 2
            else
                echo "Error: --config-dir requires a valid directory path as an argument." >&2
                exit 1
            fi
            ;;
        *)
            echo "Error: Unknown option '$1'" >&2
            show_help >&2
            exit 1
            ;;
    esac
done

# 5. Determine Sync Source (File vs. Config Extraction)
SYNC_LIST=""
TMP_FILE_LIST=""

if [[ -n "$FILE_LIST" ]]; then
    # User provided a static file
    if [[ ! -f "$FILE_LIST" ]]; then
        echo "Error: The file list '$FILE_LIST' does not exist or is not readable." >&2
        exit 1
    fi
    SYNC_LIST="$FILE_LIST"
    echo "Using static file list: $SYNC_LIST"
else
    # User did not provide a static file, extract dynamically from XML
    if ! command -v xmlstarlet &> /dev/null; then
        echo "Error: 'xmlstarlet' is required but not installed." >&2
        echo "Please install it before running this script." >&2
        exit 1
    fi

    if [[ ! -d "$CONFIG_DIR" ]]; then
        echo "Error: Configuration directory '$CONFIG_DIR' not found." >&2
        exit 1
    fi

    echo "Extracting file list from XML configs in: $CONFIG_DIR..."

    # Securely create a temporary file
    TMP_FILE_LIST=$(mktemp)

    # Ensure the temporary file is deleted when the script exits (success or fail)
    trap 'rm -f "$TMP_FILE_LIST" "$RSYNC_ERR_LOG"' EXIT

    # Execute xmlstarlet against all XML files, pipe to sed to remove empty lines, and save to tmp file
    xmlstarlet sel -t -v "/docset/resources/locale[@lang='en-us']//url[@format='html']/@href" -n "$CONFIG_DIR"/*.xml | sed '/^[[:space:]]*$/d' > "$TMP_FILE_LIST"

    # Verify that we actually extracted something
    if [[ ! -s "$TMP_FILE_LIST" ]]; then
        echo "Error: No files were extracted from the XML configs. Check your XPath or XML structure." >&2
        exit 1
    fi

    SYNC_LIST="$TMP_FILE_LIST"
fi

# 6. Execute rsync
echo "Destination directory: $LOCAL_DEST_DIR"

mkdir -p "$LOCAL_DEST_DIR" || { echo "Error: Failed to create destination directory." >&2; exit 1; }

# Define a temporary file to hold the rsync errors
RSYNC_ERR_LOG=$(mktemp /tmp/rsync_errors.XXXXXX)

echo "Starting synchronization..."
rsync -avzL --files-from="$SYNC_LIST" "${REMOTE_HOST}:${REMOTE_BASE_DIR}" "$LOCAL_DEST_DIR" 2> "$RSYNC_ERR_LOG" || true

# Check if the log file has contents (meaning errors occurred)
if [ -s "$RSYNC_ERR_LOG" ]; then
    echo ""
    echo "========================================="
    echo "       RSYNC ERROR SUMMARY"
    echo "========================================="

    # Extract just the file paths that were missing
    MISSING_FILES=$(grep "failed: No such file or directory" "$RSYNC_ERR_LOG" | awk -F '"' '{print $2}')

    if [ -n "$MISSING_FILES" ]; then
        echo "The following files were missing from the source:"
        echo "$MISSING_FILES" | sed 's/^/ - /'
    fi

    # Optional: Print any other unexpected errors that aren't "No such file"
    OTHER_ERRS=$(grep -v "failed: No such file or directory" "$RSYNC_ERR_LOG")
    if [ -n "$OTHER_ERRS" ]; then
        echo -e "\nOther errors encountered:"
        echo "$OTHER_ERRS"
    fi
    echo "========================================="
fi



echo "Synchronization complete."
