#!/bin/bash

# Automatic Document Signing Script using GPG

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Determine base directory to ensure reliable paths under CRON
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT_DIR="$BASE_DIR/ParaFirmar"
OUTPUT_DIR="$BASE_DIR/Firmados"
LOG_FILE="$BASE_DIR/Logs/signing.log"

# Ensure required directories exist
mkdir -p "$INPUT_DIR" "$OUTPUT_DIR" "$BASE_DIR/Logs"

# Check if there are any files pending signature
FILES=("$INPUT_DIR"/*)
if [ ! -e "${FILES[0]}" ]; then
    echo "No files found in $INPUT_DIR to sign."
    exit 0
fi

# Process each file found in the input folder
for FILE in "${FILES[@]}"; do
    if [ -f "$FILE" ]; then
        FILENAME=$(basename "$FILE")

        # Generate detached ASCII-armored signature
        gpg --batch --yes --armor --detach-sign -o "$OUTPUT_DIR/$FILENAME.asc" "$FILE"

        if [ $? -eq 0 ]; then
            # Move original file to the signed folder
            mv "$FILE" "$OUTPUT_DIR/"

            # Log operation
            TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
            echo "$TIMESTAMP | SIGNED | $FILENAME" >> "$LOG_FILE"
            echo -e "${GREEN}[OK]${NC} Successfully signed: $FILENAME"
        else
            TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
            echo "$TIMESTAMP | ERROR  | Failed to sign $FILENAME" >> "$LOG_FILE"
            echo -e "${RED}[ERROR]${NC} Failed to sign: $FILENAME"
        fi
    fi
done
