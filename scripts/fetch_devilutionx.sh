#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readarray -t LOCK < <(python - "$ROOT/upstream.lock.toml" <<'PY'
import sys, tomllib
with open(sys.argv[1], 'rb') as f:
    v=tomllib.load(f)['devilutionx']
print(v['repository'])
print(v['commit'])
PY
)
REPOSITORY="${LOCK[0]}"
COMMIT="${LOCK[1]}"
TARGET="$ROOT/third_party/DevilutionX"
if [[ ! -d "$TARGET/.git" ]]; then
  git clone --filter=blob:none --no-checkout "$REPOSITORY" "$TARGET"
fi
git -C "$TARGET" fetch --depth=1 origin "$COMMIT"
git -C "$TARGET" checkout --detach "$COMMIT"
ACTUAL="$(git -C "$TARGET" rev-parse HEAD)"
[[ "$ACTUAL" == "$COMMIT" ]] || { echo "revision mismatch: $ACTUAL" >&2; exit 1; }
echo "DevilutionX pinned at $ACTUAL"
echo "No Diablo MPQ/assets were downloaded by this script. Read upstream LICENSE.md before use."
