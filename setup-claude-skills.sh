#!/bin/bash
# Sets up nyra Claude skills by symlinking them into the Claude Mac app's skills directory
# and registering them in the skills manifest.
# Run once after cloning nyra-tools.

set -e

NYRA_TOOLS_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_PLUGIN_BASE="$HOME/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin"

# Find the skills manifest — it's nested under two UUIDs
MANIFEST=$(find "$SKILLS_PLUGIN_BASE" -name "manifest.json" -maxdepth 4 2>/dev/null | head -1)

if [ -z "$MANIFEST" ]; then
  echo "❌ Could not find Claude skills manifest."
  echo "   Make sure the Claude Mac app has been opened at least once."
  exit 1
fi

SKILLS_DIR="$(dirname "$MANIFEST")/skills"
mkdir -p "$SKILLS_DIR"

install_skill() {
  local SKILL_ID="$1"
  local SKILL_SRC="$NYRA_TOOLS_DIR/skills/$SKILL_ID"

  if [ ! -d "$SKILL_SRC" ]; then
    echo "⚠️  Skill source not found: $SKILL_SRC — skipping."
    return
  fi

  # Symlink skill files
  ln -sf "$SKILL_SRC" "$SKILLS_DIR/$SKILL_ID"
  echo "🔗 Symlinked $SKILL_ID → $SKILL_SRC"

  # Register in manifest via Python
  python3 - "$MANIFEST" "$SKILL_ID" "$SKILL_SRC/SKILL.md" <<'PYEOF'
import json, sys, re

manifest_path, skill_id, skill_md_path = sys.argv[1], sys.argv[2], sys.argv[3]

# Extract description from SKILL.md frontmatter
description = ""
try:
    content = open(skill_md_path).read()
    match = re.search(r'^description:\s*[>|]?\s*\n((?:[ \t]+.+\n)+)', content, re.MULTILINE)
    if match:
        description = re.sub(r'\s+', ' ', match.group(1)).strip()
except Exception:
    pass

with open(manifest_path) as f:
    data = json.load(f)

data['skills'] = [s for s in data['skills'] if s['skillId'] != skill_id]
data['skills'].append({
    "skillId": skill_id,
    "name": skill_id,
    "description": description,
    "creatorType": "user",
    "updatedAt": "2026-03-19T00:00:00.000000Z",
    "enabled": True
})

with open(manifest_path, 'w') as f:
    json.dump(data, f, indent=2)
PYEOF

  echo "✅ Registered $SKILL_ID in manifest"
}

# Install all skills found in the skills/ directory
for skill_dir in "$NYRA_TOOLS_DIR/skills"/*/; do
  install_skill "$(basename "$skill_dir")"
done

echo ""
echo "✅ Done. Restart Claude to activate the skills."
