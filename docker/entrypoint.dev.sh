#!/bin/bash
set -e

# Install Protean from mounted volume first so the path dependency resolves.
if [ -d "/protean" ]; then
    echo "Installing Protean from /protean (local development)..."
    pip install -e "/protean[postgresql,message-db,redis]" -q -q
else
    echo "Warning: /protean not mounted. Protean must be installed in the image."
fi

# Install remaining app dependencies (scalar-fastapi, etc.).
# Protean path dep (../protean → /protean) resolves since we're in /app.
echo "Installing application dependencies..."
poetry install --only main --no-root -q

exec "$@"
