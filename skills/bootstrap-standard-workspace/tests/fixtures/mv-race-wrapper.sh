#!/bin/sh
set -eu

# 仅在第一次 mv 前创建竞态目标，用于验证创建脚本不会误报成功。
if [ ! -e "$BOOTSTRAP_RACE_MARKER" ]; then
    : > "$BOOTSTRAP_RACE_MARKER"
    mkdir "$BOOTSTRAP_RACE_TARGET"
fi

exec "$BOOTSTRAP_REAL_MV" "$@"
