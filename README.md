# nyra-tools

Shared Claude Code skills and tools for the nyra team — available to both Android and iOS developers.

## Available skills

| Skill | What it does |
|---|---|
| [`crosscheck`](skills/crosscheck/) | Cross-checks a feature between the Android and iOS repos, finds discrepancies, and generates an HTML report |

---

## Setup (one-time, ~1 minute)

```bash
git clone https://github.com/nyrahealth/nyra-tools ~/Work/nyra-tools
cd ~/Work/nyra-tools
./setup-claude-skills.sh
```

Then restart Claude. Done — `/crosscheck` is available in any project.

## Updating

When skills are updated, just pull and restart Claude:

```bash
cd ~/Work/nyra-tools && git pull
```

No reinstall needed — skills are symlinked directly from this repo.

---

## Using crosscheck

```
/crosscheck <feature> [--from android|ios] [--branch <branch>]
```

| Argument | Default | Meaning |
|---|---|---|
| `feature` | inferred from context | What to search for (e.g. `login`, `paywall`, `courses`) |
| `--from` | auto-detected from CWD | Which platform you are currently on |
| `--branch` | `main` | Branch to pull on the **other** repo |

**Examples:**

```bash
# Auto-detect your platform, compare login on both sides
/crosscheck login

# You're on Android, check how iOS implements the paywall
/crosscheck paywall --from android

# You're on iOS, check a specific Android branch
/crosscheck courses --from ios --branch feature/courses-v2
```

Claude will also invoke `crosscheck` automatically when you ask things like
*"how does iOS handle this?"* or *"is this consistent across platforms?"*.

### Report output

Reports are saved to `~/crosscheck-reports/<feature>_<timestamp>.html` and opened
automatically in your browser. Each report includes:

- Side-by-side architecture overview (Android vs iOS)
- Mermaid flowcharts for both platforms
- Color-coded findings: 🟢 parity · 🟡 minor difference · 🔴 discrepancy
- Recommendations for closing gaps

### If repo discovery fails

The skill auto-discovers the other repo from your current directory. If it can't find it,
set an environment variable in your shell profile:

```bash
# Android devs (if iOS repo is in an unusual location)
export CROSSCHECK_IOS_PATH=/path/to/nyra-ios

# iOS devs (if Android repo is in an unusual location)
export CROSSCHECK_ANDROID_PATH=/path/to/android
```

---

## Contributing a new skill

1. Create a folder under `skills/<skill-name>/` with a `SKILL.md` and any helper scripts
2. Open a PR — once merged, all team members get the skill on next `git pull`
