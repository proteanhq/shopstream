#!/bin/bash
set -e

# Install app dependencies first (scalar-fastapi, etc.).
# This also installs Protean from the git lockfile.
echo "Installing application dependencies..."
poetry install --only main --no-root -q

# Then override Protean with the local editable mount (if present).
# This must run AFTER poetry install so the editable install takes precedence.
if [ -d "/protean" ]; then
    echo "Installing Protean from /protean (local development)..."
    pip install -e "/protean[postgresql,message-db,redis]" -q -q
else
    echo "Warning: /protean not mounted. Protean must be installed in the image."
fi

exec "$@"
