#!/bin/bash

# Generate a self-signed SSL/TLS certificate for localhost

CERT_DIR="$(dirname "$0")/certs"
mkdir -p "$CERT_DIR"

echo "Generating self-signed SSL certificate..."

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -subj "/C=AR/ST=BuenosAires/L=CABA/O=EDI2/CN=localhost"

echo "Certificate and private key generated in $CERT_DIR"
