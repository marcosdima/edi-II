#!/bin/bash

# Generates a GPG key pair without passphrase for automated signing

echo "Generating test GPG key for automated signing demo..."

gpg --batch --generate-key <<EOF
%no-protection
Key-Type: RSA
Key-Length: 2048
Subkey-Type: RSA
Subkey-Length: 2048
Name-Real: EDI II Demo User
Name-Email: edi2@example.com
Expire-Date: 0
EOF

echo "Key generation completed."
gpg --list-secret-keys
