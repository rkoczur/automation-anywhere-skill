#!/usr/bin/env python3
"""
render_report.py
----------------

Fill assets/analysis_report_template.html from a JSON analysis payload and
write a finished, self-contained HTML review. Used by the code-analysis
workflow in A360_ANALYSIS_GUIDE.md §6 so every review comes out identical in
layout and styling — you supply the data, the template supplies the design.

Usage
-----
    python render_report.py payload.json                     # -> <automation>_review.html
    python render_report.py payload.json -o review.html      # custom output path
    python render_report.py payload.json --template t.html   # custom template
    python render_report.py payload.json --quiet             # no stdout summary

The payload shape is documented in A360_ANALYSIS_GUIDE.md §6.1. In short you
supply the raw analysis facts (score, counts, metric numbers, findings,
catalogue, fixes, positives); this script derives everything cosmetic:

* SCORE_COLOR from the score band (§5.3),
* MI/duplication/violation meter bands from their thresholds,
* severity/status icon glyphs and text labels from their keys,

then expands the `<!-- REPEAT: name -->` blocks and substitutes the {{TOKENS}}.
Values are HTML-escaped. If any {{TOKEN}} is left unfilled the script exits
non-zero and names it, so a typo in the payload fails loudly instead of
shipping a broken report.
"""

from __future__ import annotations
import argparse
import html
import json
import os
import re
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Derivations — the cosmetic decisions the payload should NOT have to make
# ---------------------------------------------------------------------------

def score_color(score: float) -> str:
    """Score band -> CSS color variable name (see A360_ANALYSIS_GUIDE.md §5.3)."""
    if score >= 90:
        return "good"
    if score >= 75:
        return "accent"
    if score >= 60:
        return "warning"
    if score >= 40:
        return "serious"
    return "critical"


def mi_band(mi: float) -> str:
    """Maintainability index -> meter band. Higher is better."""
    if mi >= 85:
        return "good"
    if mi >= 65:
        return "moderate"
    if mi >= 40:
        return "poor"
    return "bad"


def duplication_band(ratio: float) -> str:
    """Duplication % -> meter band. Lower is better."""
    if ratio < 5:
        return "good"
    if ratio <= 15:
        return "poor"
    return "bad"


def violation_band(ratio: float) -> str:
    """Violation-line ratio % -> meter band. Lower is better."""
    if ratio < 5:
        return "good"
    if ratio <= 25:
        return "poor"
    return "bad"


# Severity key -> (icon glyph, human label). Matches the summary-tile glyphs.
SEVERITY = {
    "blocker": ("■", "Blocker"),
    "major":   ("▲", "Major"),
    "minor":   ("◆", "Minor"),
    "info":    ("●", "Info"),
    "pass":    ("✓", "Pass"),
}

# Catalogue status key -> (icon glyph, human label, badge severity key).
# 'pass' reuses the outlined pass badge; 'fail' borrows the blocker fill so a
# failing rule reads hot; 'na' is a quiet info badge.
STATUS = {
    "pass": ("✓", "Pass", "pass"),
    "fail": ("✕", "Fail", "blocker"),
    "na":   ("–", "N/A", "info"),
}


# ---------------------------------------------------------------------------
# Template plumbing
# ---------------------------------------------------------------------------

REPEAT_RE = re.compile(
    r"[ \t]*<!-- REPEAT: (?P<name>[\w]+) -->\r?\n(?P<body>.*?)[ \t]*<!-- /REPEAT -->\r?\n?",
    re.DOTALL,
)
TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def esc(v: Any) -> str:
    """HTML-escape a scalar for safe insertion into element text/attributes."""
    return html.escape("" if v is None else str(v), quote=True)


def fill_tokens(fragment: str, values: dict[str, Any]) -> str:
    """Substitute {{TOKEN}} in a fragment. Unknown tokens are left intact so
    the final unfilled-token scan can report them."""
    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key in values:
            return esc(values[key])
        return m.group(0)
    return TOKEN_RE.sub(repl, fragment)


def expand_repeats(template: str, rows: dict[str, list[dict[str, Any]]]) -> str:
    """Replace each `<!-- REPEAT: name -->…<!-- /REPEAT -->` block with one
    filled copy of its body per row in rows[name] (empty list -> block removed)."""
    def repl(m: re.Match) -> str:
        name = m.group("name")
        body = m.group("body")
        items = rows.get(name, [])
        return "".join(fill_tokens(body, item) for item in items)
    return REPEAT_RE.sub(repl, template)


# ---------------------------------------------------------------------------
# Payload -> token/rows mapping
# ---------------------------------------------------------------------------

def build_rows(payload: dict) -> dict[str, list[dict[str, Any]]]:
    metric_rows = [
        {
            "BOT_NAME": m.get("bot", ""),
            "BOT_LINES": m.get("lines", ""),
            "BOT_CC": m.get("cc", ""),
            "BOT_HALSTEAD_V": m.get("halstead_v", ""),
            "BOT_MI": m.get("mi", ""),
            "BOT_DUPLICATION": m.get("duplication", ""),
            "BOT_TECH_MIX": m.get("tech_mix", ""),
        }
        for m in payload.get("metrics", [])
    ]

    finding_rows = []
    for f in payload.get("findings", []):
        sev = f.get("severity", "info")
        icon, label = SEVERITY.get(sev, SEVERITY["info"])
        finding_rows.append({
            "RULE_ID": f.get("rule_id", ""),
            "RULE_NAME": f.get("rule_name", ""),
            "SEV_KEY": sev,
            "SEV_ICON": icon,
            "SEV_LABEL": label,
            "FINDING_COUNT": f.get("count", ""),
            "FINDING_LOCATIONS": f.get("locations", ""),
            "FINDING_MESSAGE": f.get("message", ""),
        })

    catalogue_rows = []
    for r in payload.get("catalogue", []):
        sev = r.get("severity", "info")
        sev_icon, sev_label = SEVERITY.get(sev, SEVERITY["info"])
        status = r.get("status", "na")
        st_icon, st_label, st_badge = STATUS.get(status, STATUS["na"])
        catalogue_rows.append({
            "RULE_ID": r.get("rule_id", ""),
            "RULE_NAME": r.get("rule_name", ""),
            "SEV_KEY": sev,
            "SEV_ICON": sev_icon,
            "SEV_LABEL": sev_label,
            "RULE_THRESHOLD": r.get("threshold", ""),
            "STATUS_KEY": st_badge,
            "STATUS_ICON": st_icon,
            "STATUS_LABEL": st_label,
            "RULE_COUNT": r.get("count", 0),
        })

    fix_items = [{"FIX_TEXT": t} for t in payload.get("fixes", [])]
    positive_items = [{"POSITIVE_TEXT": t} for t in payload.get("positives", [])]

    return {
        "metric_row": metric_rows,
        "finding_row": finding_rows,
        "catalogue_row": catalogue_rows,
        "fix_item": fix_items,
        "positive_item": positive_items,
    }


def build_tokens(payload: dict) -> dict[str, Any]:
    counts = payload.get("counts", {}) or {}
    score = payload.get("score", 0)
    mi = payload.get("mi", 0)
    dup = payload.get("duplication_ratio", 0)
    viol = payload.get("violation_line_ratio", 0)
    metrics = payload.get("metrics", []) or []

    return {
        "AUTOMATION_NAME": payload.get("automation_name", ""),
        "REVIEW_DATE": payload.get("review_date", ""),
        "SCORE": score,
        "SCORE_COLOR": score_color(score),
        "VERDICT_BAND": payload.get("verdict_band", ""),
        "THRESHOLD_PROFILE": payload.get("threshold_profile", ""),
        "BOTS_ANALYZED_COUNT": payload.get("bots_analyzed_count", len(metrics)),
        "BOTS_ANALYZED_LIST": payload.get("bots_analyzed_list", ""),
        "TOTAL_AUTOMATION_SIZE": payload.get("total_automation_size", ""),
        "CONFIG_OVERRIDES": payload.get("config_overrides", "none"),
        "COUNT_BLOCKER": counts.get("blocker", 0),
        "COUNT_MAJOR": counts.get("major", 0),
        "COUNT_MINOR": counts.get("minor", 0),
        "COUNT_INFO": counts.get("info", 0),
        "VIOLATION_LINE_RATIO": viol,
        "VIOLATION_BAND": violation_band(viol),
        "MI": mi,
        "MI_BAND": mi_band(mi),
        "DUPLICATION_RATIO": dup,
        "DUPLICATION_BAND": duplication_band(dup),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render(template: str, payload: dict) -> str:
    html_out = expand_repeats(template, build_rows(payload))
    html_out = fill_tokens(html_out, build_tokens(payload))
    return html_out


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Render an A360 analysis HTML report from a JSON payload.")
    ap.add_argument("payload", help="Path to the analysis payload .json")
    ap.add_argument("-o", "--output", help="Output HTML path (default: <automation_name>_review.html)")
    ap.add_argument("--template", default=os.path.join(here, "analysis_report_template.html"),
                    help="Template path (default: analysis_report_template.html next to this script)")
    ap.add_argument("--quiet", action="store_true", help="Do not print a summary to stdout")
    args = ap.parse_args(argv)

    with open(args.payload, encoding="utf-8") as fh:
        payload = json.load(fh)
    with open(args.template, encoding="utf-8") as fh:
        template = fh.read()

    html_out = render(template, payload)

    # Fail loud: any {{TOKEN}} still present means a value was missing.
    leftover = sorted(set(TOKEN_RE.findall(html_out)))
    if leftover:
        sys.stderr.write(
            "[render_report] ERROR: unfilled tokens remain — check the payload keys:\n  "
            + ", ".join(leftover) + "\n"
        )
        return 2

    out_path = args.output
    if not out_path:
        base = payload.get("automation_name") or os.path.splitext(os.path.basename(args.payload))[0]
        safe = re.sub(r"[^\w.-]+", "_", str(base)).strip("_") or "review"
        out_path = f"{safe}_review.html"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html_out)

    if not args.quiet:
        n_find = len(payload.get("findings", []))
        n_cat = len(payload.get("catalogue", []))
        sys.stdout.write(
            f"[render_report] wrote {out_path} — score {payload.get('score','?')}/100, "
            f"{n_find} finding(s), {n_cat} catalogue row(s)\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
