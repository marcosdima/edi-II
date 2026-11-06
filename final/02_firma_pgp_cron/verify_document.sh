#!/bin/bash

# Simple Signature Verification Script

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$BASE_DIR/Firmados"

# Check if file name argument was provided
if [ -z "$1" ]; then
    echo "Usage: $0 <filename>"
    echo "Example: $0 document.txt"
    exit 1
fi

FILE="$OUTPUT_DIR/$1"
SIG="$OUTPUT_DIR/$1.asc"

# Verify that both the file and its signature exist
if [ ! -f "$FILE" ] || [ ! -f "$SIG" ]; then
    echo "Error: File '$1' or signature '$1.asc' not found in $OUTPUT_DIR"
    exit 1
fi

echo "Verifying signature for $1..."
gpg --verify "$SIG" "$FILE" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[VALID]${NC} The signature is authentic and the document has not been modified."
else
    echo -e "${RED}[INVALID]${NC} Signature check failed! The document has been modified or signature is invalid."
fi
