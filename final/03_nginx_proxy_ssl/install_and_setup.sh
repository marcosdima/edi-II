#!/bin/bash

# Setup script for Nginx Reverse Proxy with SSL

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root."
    echo "Usage: sudo ./install_and_setup.sh"
    exit 1
fi

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install Nginx package if not already installed
if ! command -v nginx &> /dev/null; then
    echo "Nginx not found. Installing Nginx..."
    apt update && apt install -y nginx
fi

# Ensure SSL certificates exist
if [ ! -f "$BASE_DIR/certs/server.crt" ]; then
    echo "Generating certificates..."
    "$BASE_DIR/generate_cert.sh"
fi

# Copy certificates to system Nginx directory
echo "Deploying SSL certificates to /etc/nginx/ssl/..."
mkdir -p /etc/nginx/ssl
cp "$BASE_DIR/certs/server.crt" /etc/nginx/ssl/
cp "$BASE_DIR/certs/server.key" /etc/nginx/ssl/
chmod 600 /etc/nginx/ssl/server.key

# Deploy virtual host configuration
echo "Configuring Nginx reverse proxy..."
cp "$BASE_DIR/nginx_reverse_proxy.conf" /etc/nginx/sites-available/reverse_proxy.conf
ln -sf /etc/nginx/sites-available/reverse_proxy.conf /etc/nginx/sites-enabled/reverse_proxy.conf

# Disable default site to prevent port conflicts
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
echo "Testing Nginx configuration syntax..."
nginx -t

if [ $? -eq 0 ]; then
    systemctl restart nginx
    echo "Nginx successfully configured and restarted."
    echo "Ready for demonstration."
else
    echo "Configuration test failed. Please check errors above."
    exit 1
fi
