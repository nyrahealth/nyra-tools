#!/usr/bin/env python3
"""
generate_report.py — Produces a styled HTML cross-platform comparison report.

Usage:
    python3 generate_report.py \
        --feature "login" \
        --current-platform android \
        --current-files "path/a.kt,path/b.kt" \
        --other-files "path/a.swift,path/b.swift" \
        --analysis-json '{"summary": "...", "android": {...}, "ios": {...}, "findings": [...]}' \
        --branch main \
        --output-dir ~/crosscheck-reports
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CrossCheck: {feature}</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    :root {{
      --green: #22c55e; --green-bg: #f0fdf4; --green-border: #bbf7d0;
      --yellow: #f59e0b; --yellow-bg: #fffbeb; --yellow-border: #fde68a;
      --red: #ef4444; --red-bg: #fef2f2; --red-border: #fecaca;
      --android: #3ddc84; --ios: #007aff;
      --bg: #f8fafc; --card: #fff; --text: #0f172a; --muted: #64748b;
      --border: #e2e8f0; --radius: 12px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: var(--bg); color: var(--text); line-height: 1.6; }}
    header {{ background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
              color: #fff; padding: 32px 40px; }}
    header h1 {{ font-size: 1.6rem; font-weight: 700; margin-bottom: 4px; }}
    header .meta {{ opacity: .7; font-size: .85rem; }}
    .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px;
              font-size: .75rem; font-weight: 600; margin-left: 8px; }}
    .badge-android {{ background: var(--android); color: #000; }}
    .badge-ios {{ background: var(--ios); color: #fff; }}
    .badge-current {{ outline: 2px solid #fff; }}
    main {{ max-width: 1200px; margin: 32px auto; padding: 0 24px 64px; }}
    .summary-card {{ background: var(--card); border: 1px solid var(--border);
                     border-radius: var(--radius); padding: 20px 24px; margin-bottom: 28px; }}
    .summary-card p {{ color: var(--muted); }}
    .scoreboard {{ display: flex; gap: 16px; margin-bottom: 28px; flex-wrap: wrap; }}
    .score {{ flex: 1; min-width: 120px; background: var(--card);
              border: 1px solid var(--border); border-radius: var(--radius);
              padding: 16px; text-align: center; }}
    .score .num {{ font-size: 2rem; font-weight: 700; }}
    .score .label {{ font-size: .8rem; color: var(--muted); text-transform: uppercase;
                     letter-spacing: .05em; }}
    .score.green .num {{ color: var(--green); }}
    .score.yellow .num {{ color: var(--yellow); }}
    .score.red .num {{ color: var(--red); }}
    h2 {{ font-size: 1.1rem; font-weight: 600; margin: 32px 0 14px;
          padding-bottom: 8px; border-bottom: 1px solid var(--border); }}
    .platforms {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
                  margin-bottom: 28px; }}
    @media (max-width: 700px) {{ .platforms {{ grid-template-columns: 1fr; }} }}
    .platform-card {{ background: var(--card); border: 1px solid var(--border);
                      border-radius: var(--radius); overflow: hidden; }}
    .platform-card .header {{ padding: 12px 18px; font-weight: 600; font-size: .9rem;
                               display: flex; align-items: center; gap: 8px; }}
    .platform-card.android .header {{ background: #f0fdf4; border-bottom: 2px solid var(--android); }}
    .platform-card.ios .header {{ background: #eff6ff; border-bottom: 2px solid var(--ios); }}
    .platform-card .body {{ padding: 16px 18px; font-size: .88rem; }}
    .platform-card .body dl {{ display: grid; grid-template-columns: auto 1fr; gap: 6px 16px; }}
    .platform-card .body dt {{ font-weight: 600; color: var(--muted); white-space: nowrap; }}
    .platform-card .body dd {{ color: var(--text); }}
    .platform-card .files {{ padding: 10px 18px; background: #f8fafc;
                              border-top: 1px solid var(--border);
                              font-size: .78rem; color: var(--muted); font-family: monospace; }}
    .findings {{ display: flex; flex-direction: column; gap: 14px; }}
    .finding {{ border-radius: var(--radius); overflow: hidden;
                border: 1px solid var(--border); }}
    .finding.green {{ border-color: var(--green-border); background: var(--green-bg); }}
    .finding.yellow {{ border-color: var(--yellow-border); background: var(--yellow-bg); }}
    .finding.red {{ border-color: var(--red-border); background: var(--red-bg); }}
    .finding .ftop {{ display: flex; align-items: center; gap: 10px;
                      padding: 12px 18px; font-weight: 600; }}
    .finding .fdesc {{ padding: 0 18px 10px; font-size: .88rem; color: var(--text); }}
    .finding .fdetails {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0;
                           border-top: 1px solid rgba(0,0,0,.07); }}
    .finding .fdetail {{ padding: 10px 18px; font-size: .82rem; }}
    .finding .fdetail:first-child {{ border-right: 1px solid rgba(0,0,0,.07); }}
    .finding .fdetail strong {{ display: block; margin-bottom: 3px;
                                font-size: .75rem; text-transform: uppercase;
                                letter-spacing: .04em; color: var(--muted); }}
    .mermaid-wrap {{ background: var(--card); border: 1px solid var(--border);
                     border-radius: var(--radius); padding: 24px; margin-bottom: 20px; }}
    .mermaid-wrap h3 {{ font-size: .95rem; font-weight: 600; margin-bottom: 16px;
                        color: var(--muted); }}
    .flows {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 28px; }}
    @media (max-width: 700px) {{ .flows {{ grid-template-columns: 1fr; }} }}
    .rec-card {{ background: #fafafa; border: 1px solid var(--border);
                 border-left: 4px solid #6366f1; border-radius: var(--radius);
                 padding: 16px 20px; margin-top: 32px; font-size: .9rem; }}
    .rec-card strong {{ display: block; margin-bottom: 6px; color: #6366f1; }}
    footer {{ text-align: center; padding: 20px; font-size: .8rem; color: var(--muted); }}
  </style>
</head>
<body>
<header>
  <h1>CrossCheck: {feature}
    <span class="badge badge-android{current_android_class}">🤖 Android</span>
    <span class="badge badge-ios{current_ios_class}">🍎 iOS</span>
  </h1>
  <div class="meta">Generated {timestamp} &nbsp;·&nbsp; Branch: {branch}
    &nbsp;·&nbsp; From: {from_platform}</div>
</header>

<main>
  <div class="summary-card">
    <p>{summary}</p>
  </div>

  <div class="scoreboard">
    <div class="score green"><div class="num">{count_green}</div><div class="label">✓ Parity</div></div>
    <div class="score yellow"><div class="num">{count_yellow}</div><div class="label">~ Minor diff</div></div>
    <div class="score red"><div class="num">{count_red}</div><div class="label">✗ Discrepancy</div></div>
    <div class="score"><div class="num">{files_current}</div><div class="label">{current_label} files</div></div>
    <div class="score"><div class="num">{files_other}</div><div class="label">{other_label} files</div></div>
  </div>

  <h2>Architecture overview</h2>
  <div class="platforms">
    <div class="platform-card android">
      <div class="header">🤖 Android</div>
      <div class="body">
        <dl>
          <dt>Pattern</dt><dd>{android_arch}</dd>
          <dt>Error handling</dt><dd>{android_errors}</dd>
        </dl>
        {android_notes_html}
      </div>
      <div class="files">{android_files_html}</div>
    </div>
    <div class="platform-card ios">
      <div class="header">🍎 iOS</div>
      <div class="body">
        <dl>
          <dt>Pattern</dt><dd>{ios_arch}</dd>
          <dt>Error handling</dt><dd>{ios_errors}</dd>
        </dl>
        {ios_notes_html}
      </div>
      <div class="files">{ios_files_html}</div>
    </div>
  </div>

  <h2>Feature flow</h2>
  <div class="flows">
    <div class="mermaid-wrap">
      <h3>🤖 Android flow</h3>
      <div class="mermaid">
flowchart TD
{android_mermaid}
      </div>
    </div>
    <div class="mermaid-wrap">
      <h3>🍎 iOS flow</h3>
      <div class="mermaid">
flowchart TD
{ios_mermaid}
      </div>
    </div>
  </div>

  <h2>Findings ({total_findings})</h2>
  <div class="findings">
{findings_html}
  </div>

  {recommendation_html}
</main>

<footer>crosscheck · nyra · {timestamp}</footer>

<script>mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});</script>
</body>
</html>
"""

FINDING_TEMPLATE = """\
    <div class="finding {status_class}">
      <div class="ftop"><span class="icon">{icon}</span>{title}</div>
      <div class="fdesc">{description}</div>
      <div class="fdetails">
        <div class="fdetail"><strong>Android</strong>{android_detail}</div>
        <div class="fdetail"><strong>iOS</strong>{ios_detail}</div>
      </div>
    </div>"""

STATUS_META = {
    "green":  ("green",  "🟢"),
    "yellow": ("yellow", "🟡"),
    "red":    ("red",    "🔴"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def steps_to_mermaid(steps: list[str]) -> str:
    if not steps:
        return "    A[No steps provided]"
    lines = []
    node_ids = [f"N{i}" for i in range(len(steps))]
    for nid, step in zip(node_ids, steps):
        label = step.replace('"', "'")
        lines.append(f'    {nid}["{label}"]')
    for i in range(len(node_ids) - 1):
        lines.append(f"    {node_ids[i]} --> {node_ids[i+1]}")
    return "\n".join(lines)


def short_path(p: str) -> str:
    return p.replace(str(Path.home()), "~")


def html_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_report(feature: str, current_platform: str,
                 current_files: list[str], other_files: list[str],
                 analysis: dict, branch: str, output_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{feature.replace(' ', '_')}_{ts}.html"

    other_platform = "ios" if current_platform == "android" else "android"
    current_label = current_platform.upper()
    other_label = other_platform.upper()

    android = analysis.get("android", {})
    ios = analysis.get("ios", {})
    findings = analysis.get("findings", [])

    count = {"green": 0, "yellow": 0, "red": 0}
    for f in findings:
        s = f.get("status", "yellow")
        count[s] = count.get(s, 0) + 1

    findings_html_parts = []
    for f in findings:
        status = f.get("status", "yellow")
        cls, icon = STATUS_META.get(status, ("yellow", "🟡"))
        findings_html_parts.append(FINDING_TEMPLATE.format(
            status_class=cls,
            icon=icon,
            title=html_escape(f.get("title", "")),
            description=html_escape(f.get("description", "")),
            android_detail=html_escape(f.get("android_detail", "—")),
            ios_detail=html_escape(f.get("ios_detail", "—")),
        ))

    def notes_html(notes: str) -> str:
        if not notes:
            return ""
        return f'<p style="margin-top:10px;color:var(--muted);font-size:.85rem">{html_escape(notes)}</p>'

    def files_html(paths: list[str]) -> str:
        return "<br>".join(short_path(p) for p in paths) or "—"

    rec = analysis.get("recommendation", "")
    rec_html = (f'<div class="rec-card"><strong>Recommendation</strong>'
                f'{html_escape(rec)}</div>') if rec else ""

    # Files for current vs other
    files_current = len(current_files)
    files_other = len(other_files)
    android_files = current_files if current_platform == "android" else other_files
    ios_files = current_files if current_platform == "ios" else other_files

    html = TEMPLATE.format(
        feature=html_escape(feature),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        branch=html_escape(branch),
        from_platform=html_escape(current_label),
        current_label=current_label,
        other_label=other_label,
        # Outline badge for whichever is "current"
        current_android_class=" badge-current" if current_platform == "android" else "",
        current_ios_class=" badge-current" if current_platform == "ios" else "",
        summary=html_escape(analysis.get("summary", "")),
        count_green=count["green"],
        count_yellow=count["yellow"],
        count_red=count["red"],
        files_current=files_current,
        files_other=files_other,
        android_arch=html_escape(android.get("architecture", "—")),
        android_errors=html_escape(android.get("error_handling", "—")),
        android_notes_html=notes_html(android.get("notes", "")),
        android_files_html=files_html(android.get("key_files", android_files)),
        ios_arch=html_escape(ios.get("architecture", "—")),
        ios_errors=html_escape(ios.get("error_handling", "—")),
        ios_notes_html=notes_html(ios.get("notes", "")),
        ios_files_html=files_html(ios.get("key_files", ios_files)),
        android_mermaid=steps_to_mermaid(android.get("flow_steps", [])),
        ios_mermaid=steps_to_mermaid(ios.get("flow_steps", [])),
        findings_html="\n".join(findings_html_parts) if findings_html_parts
                      else '    <p style="color:var(--muted)">No findings.</p>',
        total_findings=len(findings),
        recommendation_html=rec_html,
    )

    out_path.write_text(html, encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate a cross-platform comparison report.")
    parser.add_argument("--feature", required=True)
    parser.add_argument("--current-platform", choices=["android", "ios"], required=True)
    parser.add_argument("--current-files", default="")
    parser.add_argument("--other-files", default="")
    parser.add_argument("--analysis-json", required=True)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--output-dir", default=str(Path.home() / "crosscheck-reports"))
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    current_files = [f.strip() for f in args.current_files.split(",") if f.strip()]
    other_files = [f.strip() for f in args.other_files.split(",") if f.strip()]

    try:
        analysis = json.loads(args.analysis_json)
    except json.JSONDecodeError as e:
        print(f"Error: invalid --analysis-json: {e}", file=sys.stderr)
        sys.exit(1)

    out_path = build_report(
        feature=args.feature,
        current_platform=args.current_platform,
        current_files=current_files,
        other_files=other_files,
        analysis=analysis,
        branch=args.branch,
        output_dir=Path(args.output_dir).expanduser(),
    )

    print(f"Report saved: {out_path}")

    if not args.no_open:
        subprocess.run(["open", str(out_path)], check=False)


if __name__ == "__main__":
    main()
