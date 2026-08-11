#!/usr/bin/env python3
"""Lightweight heuristic scan for likely customer-facing hardcoded English in JSX.

Usage:
  python scripts/audit_hardcoded_strings.py
  python scripts/audit_hardcoded_strings.py --json

This is intentionally imperfect — it flags JSX text / string literals that look
like English UI copy and are not obvious t() / className / testid usage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "src"
SKIP_DIRS = {"node_modules", "ui", "__tests__", "constants"}
# Match >Text here< or quoted multi-word Title Case / sentence-like strings
TEXT_BETWEEN_TAGS = re.compile(r">\s*([A-Za-z][^<{]{2,80}?)\s*<")
QUOTED = re.compile(r"""(?<!t\()(?<!defaultValue:\s)(["'])([A-Z][a-z]+(?:\s+[A-Za-z']+){1,8})\1""")
ALLOW = re.compile(
    r"^(data-testid|className|http|https|bg-|text-|border-|from-|to-|via-|sm:|md:|lg:|"
    r"flex|grid|hidden|absolute|relative|px-|py-|gap-|rounded|shadow|outline|"
    r"Assistify|Copilot|CRM|API|JSON|PDF|DOCX|EUR|USD|UTC)$",
    re.I,
)

def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return True
    if path.name.endswith(".test.js") or path.name.endswith(".test.jsx"):
        return True
    return False

def scan(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings = []
    for i, line in enumerate(text.splitlines(), 1):
        if "t(" in line and "defaultValue" not in line and '"' not in line[line.find("t("):line.find("t(")+40] if "t(" in line else True:
            # still check but skip pure className lines
            pass
        if "className=" in line and ">" not in line:
            continue
        if "data-testid" in line or "console." in line:
            continue
        for m in TEXT_BETWEEN_TAGS.finditer(line):
            s = m.group(1).strip()
            if ALLOW.match(s) or "{" in s or s.startswith("{") or len(s) < 3:
                continue
            if re.search(r"[a-z]{3,}", s) and " " in s or (s[0].isupper() and len(s) > 4):
                findings.append({"file": str(path.relative_to(ROOT.parent.parent)), "line": i, "text": s, "kind": "jsx-text"})
        for m in QUOTED.finditer(line):
            s = m.group(2).strip()
            if ALLOW.match(s) or s.lower() in {"new", "edit", "save", "cancel"}:
                # still flag multi-word
                pass
            if " " not in s:
                continue
            if any(x in line for x in ("t(", "defaultValue", "toast.", "placeholder=", "aria-label", "title=")):
                # may still be hardcoded — keep if not clearly t("...")
                if 't("' in line or "t('" in line:
                    continue
            findings.append({"file": str(path.relative_to(ROOT.parent.parent)), "line": i, "text": s, "kind": "quoted"})
    # de-dupe
    seen = set()
    out = []
    for f in findings:
        key = (f["file"], f["line"], f["text"])
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()
    all_findings = []
    for path in sorted(ROOT.rglob("*.jsx")):
        if should_skip(path):
            continue
        all_findings.extend(scan(path))
    for path in sorted(ROOT.rglob("*.js")):
        if should_skip(path) or path.name.endswith(".config.js"):
            continue
        if "i18n" in path.parts and path.name.endswith(".js") and path.name != "errors.js":
            continue
        all_findings.extend(scan(path))
    all_findings = all_findings[: args.limit]
    if args.json:
        print(json.dumps({"count": len(all_findings), "findings": all_findings}, indent=2))
    else:
        print(f"Hardcoded string candidates: {len(all_findings)} (heuristic)\n")
        for f in all_findings:
            print(f"{f['file']}:{f['line']}: [{f['kind']}] {f['text']}")
        print("\nClassify manually: technical/internal | test-only | proper-noun | follow-up")
    return 0

if __name__ == "__main__":
    sys.exit(main())
