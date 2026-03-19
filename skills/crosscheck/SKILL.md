---
name: crosscheck
description: >
  Cross-checks a feature between the Android and iOS repos, surfacing discrepancies,
  missing behavior, or parity gaps. Use proactively when implementing or reviewing a
  feature to verify cross-platform parity, when unsure how the other platform implemented
  something, or when the user asks about iOS/Android differences. Invoked explicitly with
  "/crosscheck FEATURE [--from android|ios] [--branch BRANCH]". Auto-trigger whenever
  the user asks "how does [platform] do X", "check [platform]", "is this consistent
  across platforms", or you notice something that might differ between Android and iOS.
---

# crosscheck

Compares a feature between the Android (Kotlin/Jetpack Compose) and iOS (Swift/SwiftUI)
repos and produces a styled HTML report with side-by-side analysis and Mermaid flowcharts.
Works from either repo — usable by both Android and iOS developers.

## Invocation

```
/crosscheck <feature> [--from android|ios] [--branch <branch>]
```

| Argument | Default | Meaning |
|---|---|---|
| `feature` | inferred from context | Keyword to search (e.g. `login`, `paywall`, `task-dismissal`) |
| `--from` | auto-detected from CWD | Which platform you are currently on |
| `--branch` | `main` | Branch to pull on the **other** repo |

**Examples:**
- `/crosscheck login` — auto-detects your platform, compares login on both sides
- `/crosscheck login --from android` — explicit; you're on Android, checking iOS main
- `/crosscheck paywall --from ios --branch feature/paywall-v2` — iOS dev checking Android branch
- `/crosscheck registration --branch hotfix/email-validation` — check a hotfix branch

## Workflow

### 1. Parse invocation

Extract `feature`, `--from`, and `--branch` from the command or surrounding conversation context.
If `feature` is not provided, infer it from what is currently being discussed.

### 2. Detect current platform (if --from not given)

Check CWD for platform markers:
- `build.gradle` or `gradlew` present → **Android**
- `Package.swift` or `*.xcodeproj` present → **iOS**
- Neither found → stop and ask the user to pass `--from android` or `--from ios`

### 3. Find the other repo

Run the discovery script to locate the counterpart repo:

```bash
python3 ~/.claude/skills/crosscheck/scripts/find_repo.py \
  --current-platform <android|ios> \
  --cwd <current working directory>
```

The script walks from the current git root upward, then scans sibling directories for the
other platform's markers. It also checks `CROSSCHECK_IOS_PATH` / `CROSSCHECK_ANDROID_PATH`
env vars as an override. See `scripts/find_repo.py` for the full resolution order.

If the repo cannot be found, the script exits with a clear error message — show it to the
user and stop.

### 4. Sync the other repo

```bash
cd <other_repo_path>
git fetch origin
git checkout <branch>   # defaults to main
git pull origin <branch>
```

If the branch doesn't exist, fall back to `main` and note this in the report.

### 5. Search both repos

**Current repo** — use files already in conversation context, or search:
```bash
# Kotlin (Android)
grep -rl "<feature>" <android_root>/app/src/main/java --include="*.kt" | head -20

# Swift (iOS)
grep -rl "<feature>" <ios_root> --include="*.swift" | head -20
```

Also search by filename:
```bash
find <repo_root> -name "*<Feature>*" \( -name "*.kt" -o -name "*.swift" \) | head -15
```

Prioritise: ViewModels → Views/Screens → Services/Repositories → Models.
Read up to 6 most relevant files per platform.

### 6. Analyse and compare

For each platform extract:
- **Architecture** — how state flows (ViewModel → UI)
- **Key data models**
- **API / service calls**
- **Error handling** — which error cases are covered
- **Edge cases**
- **Navigation flow**

Classify each finding:
- 🟢 **Parity** — same behavior on both platforms
- 🟡 **Minor difference** — different impl, equivalent outcome
- 🔴 **Discrepancy** — meaningful gap, missing feature, or missing error handling

### 7. Generate HTML report

```bash
python3 ~/.claude/skills/crosscheck/scripts/generate_report.py \
  --feature "<keyword>" \
  --current-platform <android|ios> \
  --current-files "<comma-separated paths>" \
  --other-files "<comma-separated paths>" \
  --analysis-json '<json>' \
  --branch "<branch>" \
  --output-dir ~/crosscheck-reports
```

The script saves to `~/crosscheck-reports/<feature>_<timestamp>.html` and opens it.

Pass `--analysis-json` with this shape:

```json
{
  "summary": "One-sentence summary",
  "android": {
    "architecture": "...",
    "key_files": ["path/File.kt"],
    "flow_steps": ["Step 1", "Step 2"],
    "error_handling": "...",
    "notes": "..."
  },
  "ios": {
    "architecture": "...",
    "key_files": ["path/File.swift"],
    "flow_steps": ["Step 1", "Step 2"],
    "error_handling": "...",
    "notes": "..."
  },
  "findings": [
    {
      "status": "green|yellow|red",
      "title": "Short title",
      "description": "What differs and why it matters",
      "android_detail": "What Android does",
      "ios_detail": "What iOS does"
    }
  ],
  "recommendation": "What to do to close any gaps"
}
```

### 8. Summary inline

After the report opens, give a brief inline summary:
- Files checked per platform
- Green / yellow / red finding counts
- Most important discrepancy (if any)
- Path to saved report

## Tips

- If `feature` matches too many files (>30 results), narrow it — e.g. `loginviewmodel` or
  search within a specific module path.
- Android exercise codes (b1, y2…) often have no iOS counterpart by the same name — search
  by the human-readable name instead (e.g. `speechrecording`, `wordmatch`).
- iOS modules may have their own `Package.swift` — treat each top-level directory as a
  potential module.
- If a colleague's repo lives in an unusual path, they can set `CROSSCHECK_IOS_PATH` or
  `CROSSCHECK_ANDROID_PATH` in their shell environment to skip discovery.
