#!/bin/sh
set -e

CERT_DIR="/etc/nginx/ssl"
mkdir -p "$CERT_DIR"

# Generate 2048-bit private key and self-signed certificate if they do not exist
if [ ! -f "$CERT_DIR/server.key" ] || [ ! -f "$CERT_DIR/server.crt" ]; then
    echo "Generating self-signed SSL/TLS certificates for localhost..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$CERT_DIR/server.key" \
        -out "$CERT_DIR/server.crt" \
        -subj "/C=AR/ST=BuenosAires/L=Lujan/O=EdiII/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
    
    chmod 600 "$CERT_DIR/server.key"
    chmod 644 "$CERT_DIR/server.crt"
    echo "Certificates generated successfully at $CERT_DIR."
else
    echo "SSL certificates already exist at $CERT_DIR."
fi
