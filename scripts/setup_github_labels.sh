#!/usr/bin/env bash
# Create or update GitHub labels used by PM/Frontend/Backend/QA Grok Bots.
# Requires: gh auth, jq
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABELS_FILE="${LABELS_FILE:-$ROOT/.github/labels.yml}"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi
if [[ ! -f "$LABELS_FILE" ]]; then
  echo "Labels file not found: $LABELS_FILE" >&2
  exit 1
fi

echo "Applying labels from $LABELS_FILE"

python3 - <<'PY' "$LABELS_FILE"
import re, subprocess, sys, pathlib

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
# Minimal YAML list parser for our flat label file (no nested structures).
entries = []
current = None
for raw in text.splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("- name:"):
        if current:
            entries.append(current)
        name = line.split(":", 1)[1].strip().strip('"').strip("'")
        current = {"name": name, "color": "", "description": ""}
    elif current is not None and line.startswith("color:"):
        current["color"] = line.split(":", 1)[1].strip().strip('"').strip("'")
    elif current is not None and line.startswith("description:"):
        current["description"] = line.split(":", 1)[1].strip().strip('"').strip("'")
if current:
    entries.append(current)

for e in entries:
    name = e["name"]
    color = e["color"]
    desc = e["description"]
    # Prefer update; create on failure.
    upd = subprocess.run(
        ["gh", "label", "edit", name, "--color", color, "--description", desc],
        capture_output=True,
        text=True,
    )
    if upd.returncode == 0:
        print(f"updated: {name}")
        continue
    cre = subprocess.run(
        ["gh", "label", "create", name, "--color", color, "--description", desc],
        capture_output=True,
        text=True,
    )
    if cre.returncode == 0:
        print(f"created: {name}")
    else:
        print(f"FAILED: {name}\n{upd.stderr or ''}{cre.stderr or ''}", file=sys.stderr)
        sys.exit(1)

print(f"Done ({len(entries)} labels).")
PY
