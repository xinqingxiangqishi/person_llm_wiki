#!/usr/bin/env python3
"""Update metadata fields of an existing wiki entry.

Handles: status changes, gap clearing, source addition.
Claude handles body edits directly; this script only touches frontmatter.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from common import kb_root, MdDoc, today_iso  # noqa: E402

VALID_STATUSES = {"stub", "draft", "reviewed", "needs_more"}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--id", required=True, dest="kn_id", help="wiki entry id, e.g. kn_2026_grpo")
    p.add_argument("--status", default="", help="new status value")
    p.add_argument("--clear-gap", default="", dest="clear_gap",
                   help="exact gap text to remove from gaps list")
    p.add_argument("--add-source-url", default="", dest="add_source_url")
    p.add_argument("--add-source-kind", default="other", dest="add_source_kind",
                   choices=["paper", "blog", "doc", "repo", "other"])
    p.add_argument("--add-source-citation", default="", dest="add_source_citation")
    args = p.parse_args()

    kb = kb_root()
    path = kb / "wiki" / f"{args.kn_id}.md"
    if not path.exists():
        print(f"ERROR: wiki entry {args.kn_id} not found", file=sys.stderr)
        return 1

    doc = MdDoc.load(path)
    fm = doc.frontmatter
    today = today_iso()
    changed = False

    if args.status:
        if args.status not in VALID_STATUSES:
            print(f"ERROR: unknown status '{args.status}'. Valid: {VALID_STATUSES}", file=sys.stderr)
            return 1
        fm["status"] = args.status
        changed = True
        print(f"status -> {args.status}")

    if args.clear_gap:
        gaps = fm.get("gaps") or []
        before = len(gaps)
        gaps = [g for g in gaps if g != args.clear_gap]
        if len(gaps) < before:
            fm["gaps"] = gaps
            changed = True
            print(f"cleared gap: {args.clear_gap}")
            if not gaps and fm.get("status") == "needs_more":
                print("NOTE: gaps cleared and status is needs_more. "
                      "Consider running with --status reviewed if you are satisfied.")
        else:
            print(f"WARNING: gap not found: '{args.clear_gap}'", file=sys.stderr)
            print(f"  existing gaps: {gaps}", file=sys.stderr)

    if args.add_source_url:
        sources = fm.get("sources") or []
        new_src: dict = {"kind": args.add_source_kind, "url": args.add_source_url}
        if args.add_source_citation:
            new_src["citation"] = args.add_source_citation
        # Avoid duplicates by url
        if not any(s.get("url") == args.add_source_url for s in sources):
            sources.append(new_src)
            fm["sources"] = sources
            changed = True
            print(f"added source: {args.add_source_url}")
        else:
            print(f"source already present: {args.add_source_url}")

    if changed:
        fm["updated"] = today
        doc.save()
        print(f"saved: {path}")
    else:
        print("no changes made")

    return 0


if __name__ == "__main__":
    sys.exit(main())
