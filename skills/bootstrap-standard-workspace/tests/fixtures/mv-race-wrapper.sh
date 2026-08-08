#!/bin/sh
set -eu

# Create the raced target only before the first mv to ensure creation cannot report false success.
if [ ! -e "$BOOTSTRAP_RACE_MARKER" ]; then
    : > "$BOOTSTRAP_RACE_MARKER"
    mkdir "$BOOTSTRAP_RACE_TARGET"
fi

exec "$BOOTSTRAP_REAL_MV" "$@"
