#!/bin/bash
# Script to generate self-signed SSL certificate

# Script directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Generate self-signed certificate valid for 365 days
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$DIR/key.pem" \
    -out "$DIR/cert.pem" \
    -subj "/C=US/ST=State/L=City/O=DNS Web Manager/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1"

echo "SSL certificate generated successfully!"
echo "  - Certificate: $DIR/cert.pem"
echo "  - Private key: $DIR/key.pem"
echo ""
echo "WARNING: This is a self-signed certificate for development."
echo "For production, use a valid certificate (Let's Encrypt, etc)."
