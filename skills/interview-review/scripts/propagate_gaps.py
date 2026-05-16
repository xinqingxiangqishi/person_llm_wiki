#!/usr/bin/env python3
"""Propagate gaps_to_fill from question cards into the linked knowledge entries.

This is the closure step. Without it, "this question wasn't answered well" stays
trapped on the question card and never tells the knowledge base what to fix.

For each question in this interview:
  - for each linked_knowledge kid:
      - merge question.gaps_to_fill into knowledge.gaps (dedupe)
      - add iv_id to knowledge.linked_from_interviews
      - if knowledge had gaps merged AND was 'reviewed', flip to 'needs_more'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from common import kb_root, MdDoc, today_iso, dedupe_keep_order  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--interview", required=True)
    args = p.parse_args()

    kb = kb_root()
    iv_dir = kb / "interviews" / args.interview
    if not iv_dir.exists():
        print(f"ERROR: interview {args.interview} not found", file=sys.stderr)
        return 1

    qids = json.loads((iv_dir / "questions.json").read_text(encoding="utf-8"))
    today = today_iso()
    summary: dict[str, list[str]] = {}  # kid -> list of new gaps appended

    for qid in qids:
        qdoc = MdDoc.load(kb / "questions" / f"{qid}.md")
        gaps = qdoc.frontmatter.get("gaps_to_fill") or []
        linked = qdoc.frontmatter.get("linked_knowledge") or []
        if not gaps or not linked:
            continue
        for kid in linked:
            kpath = kb / "wiki" / f"{kid}.md"
            if not kpath.exists():
                continue
            kdoc = MdDoc.load(kpath)
            existing_gaps = kdoc.frontmatter.get("gaps") or []
            merged = dedupe_keep_order(existing_gaps + gaps)
            added = [g for g in merged if g not in existing_gaps]
            if not added:
                continue
            kdoc.frontmatter["gaps"] = merged
            lfi = kdoc.frontmatter.get("linked_from_interviews") or []
            if args.interview not in lfi:
                lfi.append(args.interview)
            kdoc.frontmatter["linked_from_interviews"] = lfi
            if kdoc.frontmatter.get("status") == "reviewed":
                kdoc.frontmatter["status"] = "needs_more"
            kdoc.frontmatter["updated"] = today
            kdoc.save()
            summary.setdefault(kid, []).extend(added)

    if summary:
        print("propagated gaps:")
        for kid, added in summary.items():
            for g in added:
                print(f"  {kid}: {g}")
    else:
        print("no gaps to propagate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
