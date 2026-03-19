#!/usr/bin/env python3
"""
find_repo.py — Locates the counterpart repo (Android or iOS) without hardcoded paths.

Usage:
    python3 find_repo.py --current-platform android --cwd /path/to/android/repo
    python3 find_repo.py --current-platform ios --cwd /path/to/ios/repo

Exit codes:
    0  — success, prints the resolved path to stdout
    1  — not found, prints an error message to stderr
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Platform markers
# ---------------------------------------------------------------------------

ANDROID_MARKERS = ["build.gradle", "gradlew", "build.gradle.kts"]
# Package.swift (SPM), *.xcodeproj (Xcode project dir), or *.xcworkspace
IOS_MARKERS = ["Package.swift"]
IOS_GLOB_MARKERS = ["*.xcodeproj", "*.xcworkspace"]

# Common repo directory names to probe (for the *other* platform)
ANDROID_DIR_CANDIDATES = ["android", "Android", "android-app", "nyra-android"]
IOS_DIR_CANDIDATES = ["ios", "iOS", "nyra-ios", "ios-app", "nyra-ios-app"]


def has_markers(path: Path, markers: list[str], glob_markers: list[str] | None = None) -> bool:
    """Return True if any marker file exists directly in path, or any glob matches."""
    if any((path / m).exists() for m in markers):
        return True
    if glob_markers:
        for pattern in glob_markers:
            if any(path.glob(pattern)):
                return True
    return False


def find_git_root(start: Path) -> Path | None:
    """Walk up from start until we find a .git directory."""
    current = start.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def resolve_other_repo(current_platform: str, cwd: Path) -> Path | None:
    """
    Try to locate the other platform's repo using several strategies, in order:

    1. Environment variable override (CROSSCHECK_IOS_PATH / CROSSCHECK_ANDROID_PATH)
    2. Named candidate subdirectories under the same parent as the current git root
    3. Any sibling directory containing the other platform's markers
    """
    other_platform = "ios" if current_platform == "android" else "android"
    candidates = IOS_DIR_CANDIDATES if other_platform == "ios" else ANDROID_DIR_CANDIDATES
    is_other_repo = is_ios_repo if other_platform == "ios" else is_android_repo

    # --- Strategy 1: env var ---
    env_key = f"CROSSCHECK_{other_platform.upper()}_PATH"
    env_val = os.environ.get(env_key)
    if env_val:
        p = Path(env_val).expanduser().resolve()
        if p.is_dir():
            return p
        print(f"Warning: {env_key}={env_val} is set but directory does not exist.", file=sys.stderr)

    # --- Find current git root ---
    git_root = find_git_root(cwd)
    if git_root is None:
        print("Warning: could not find git root from CWD, using CWD as base.", file=sys.stderr)
        git_root = cwd.resolve()

    # Search from parent and grandparent of git root
    search_bases = [git_root.parent, git_root.parent.parent]

    # --- Strategy 2: named candidates ---
    for base in search_bases:
        for name in candidates:
            candidate = base / name
            if candidate.is_dir() and is_other_repo(candidate):
                return candidate

    # --- Strategy 3: any sibling (or sibling's child) with platform markers ---
    for base in search_bases:
        try:
            siblings = [p for p in base.iterdir() if p.is_dir() and p != git_root]
        except PermissionError:
            continue
        # Direct siblings first
        for sibling in sorted(siblings):
            if is_other_repo(sibling):
                return sibling
        # One level deeper (e.g. iOS/nyra-ios when base is ~/Work/Workspace)
        for sibling in sorted(siblings):
            try:
                for child in sorted(sibling.iterdir()):
                    if child.is_dir() and is_other_repo(child):
                        return child
            except PermissionError:
                continue

    return None


def is_ios_repo(path: Path) -> bool:
    return has_markers(path, IOS_MARKERS, IOS_GLOB_MARKERS)


def is_android_repo(path: Path) -> bool:
    return has_markers(path, ANDROID_MARKERS)


def detect_platform(cwd: Path) -> str | None:
    """Detect current platform from CWD markers."""
    git_root = find_git_root(cwd)
    for p in ([cwd] if not git_root else [cwd, git_root]):
        if is_android_repo(p):
            return "android"
        if is_ios_repo(p):
            return "ios"
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Locate the counterpart platform repo.")
    parser.add_argument("--current-platform", choices=["android", "ios"],
                        help="Platform you are on. If omitted, auto-detected from --cwd.")
    parser.add_argument("--cwd", required=True,
                        help="Current working directory (the repo you are in).")
    args = parser.parse_args()

    cwd = Path(args.cwd).expanduser().resolve()

    platform = args.current_platform
    if not platform:
        platform = detect_platform(cwd)
        if not platform:
            print(
                "ERROR: Could not detect current platform from CWD.\n"
                "Pass --current-platform android or --current-platform ios.",
                file=sys.stderr,
            )
            sys.exit(1)

    other = resolve_other_repo(platform, cwd)

    if other is None:
        other_platform = "ios" if platform == "android" else "android"
        env_key = f"CROSSCHECK_{other_platform.upper()}_PATH"
        print(
            f"ERROR: Could not find the {other_platform.upper()} repo.\n"
            f"Options:\n"
            f"  1. Set {env_key}=/path/to/repo in your shell environment\n"
            f"  2. Pass --other-repo <path> to the skill invocation",
            file=sys.stderr,
        )
        sys.exit(1)

    print(str(other))


if __name__ == "__main__":
    main()
