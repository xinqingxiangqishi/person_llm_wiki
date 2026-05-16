#!/usr/bin/env python3
"""Maintain bidirectional links between a frontier entry and wiki entries.

Run after new_frontier.py (or any time the linked_wiki list changes).
Idempotent: safe to run multiple times.

For each kn_id:
  - Adds fr_id to wiki.linked_frontier (if not already there)
  - Adds kn_id to frontier.linked_wiki (if not already there)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from common import kb_root, MdDoc, today_iso  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--frontier", required=True, help="fr_id to link from")
    p.add_argument("--wiki", required=True,
                   help="comma-separated kn_ids to link to (can be empty string to just validate)")
    args = p.parse_args()

    kb = kb_root()
    fr_id = args.frontier
    kn_ids = [k.strip() for k in args.wiki.split(",") if k.strip()]

    fr_path = kb / "frontier" / f"{fr_id}.md"
    if not fr_path.exists():
        print(f"ERROR: frontier entry {fr_id} not found at {fr_path}", file=sys.stderr)
        return 1

    today = today_iso()
    errors: list[str] = []
    linked_ok: list[str] = []

    for kn_id in kn_ids:
        kn_path = kb / "wiki" / f"{kn_id}.md"
        if not kn_path.exists():
            errors.append(f"wiki entry {kn_id} not found — skipping link")
            continue

        # Update wiki entry: add fr_id to linked_frontier
        wdoc = MdDoc.load(kn_path)
        lf = wdoc.frontmatter.get("linked_frontier") or []
        if fr_id not in lf:
            lf.append(fr_id)
            wdoc.frontmatter["linked_frontier"] = lf
            wdoc.frontmatter["updated"] = today
            wdoc.save()

        # Update frontier entry: add kn_id to linked_wiki
        fdoc = MdDoc.load(fr_path)
        lw = fdoc.frontmatter.get("linked_wiki") or []
        if kn_id not in lw:
            lw.append(kn_id)
            fdoc.frontmatter["linked_wiki"] = lw
            fdoc.frontmatter["updated"] = today
            fdoc.save()

        linked_ok.append(kn_id)

    if linked_ok:
        print(f"linked {fr_id} <-> {', '.join(linked_ok)}")
    if errors:
        for e in errors:
            print(f"WARNING: {e}", file=sys.stderr)

    return 1 if errors and not linked_ok else 0


if __name__ == "__main__":
    sys.exit(main())
