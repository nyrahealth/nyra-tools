#!/bin/bash
# Sets up nyra Claude skills by symlinking them into ~/.claude/skills/
# Run once after cloning nyra-tools. Safe to re-run.

set -e

NYRA_TOOLS_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"

mkdir -p "$CLAUDE_SKILLS_DIR"

for skill_dir in "$NYRA_TOOLS_DIR/skills"/*/; do
  SKILL_ID="$(basename "$skill_dir")"
  ln -sf "$skill_dir" "$CLAUDE_SKILLS_DIR/$SKILL_ID"
  echo "🔗 Linked $SKILL_ID → $skill_dir"
done

echo ""
echo "✅ Done. Restart Claude to activate the skills."
