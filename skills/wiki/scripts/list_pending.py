#!/usr/bin/env python3
"""List wiki entries that need attention: status=needs_more or non-empty gaps.

Output is JSON consumed by Claude to present to the user.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from common import kb_root, load_all_wiki  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--topic", default="", help="filter by topic (partial match)")
    p.add_argument("--status", default="",
                   help="filter by status (needs_more, draft, stub). Empty = all pending.")
    p.add_argument("--min-gaps", type=int, default=0,
                   help="only show entries with at least this many gaps")
    args = p.parse_args()

    kb = kb_root()
    all_wiki = load_all_wiki(kb)

    pending = []
    for doc in all_wiki:
        fm = doc.frontmatter
        status = fm.get("status", "stub")
        gaps = fm.get("gaps") or []

        # Filter by status
        if args.status:
            if status != args.status:
                continue
        else:
            # Default: show anything that needs attention
            if status not in {"needs_more", "stub", "draft"} and not gaps:
                continue

        # Filter by topic
        if args.topic:
            topics = fm.get("topics") or []
            if not any(args.topic.lower() in t.lower() for t in topics):
                continue

        # Filter by min gaps
        if len(gaps) < args.min_gaps:
            continue

        pending.append({
            "id": fm.get("id"),
            "title": fm.get("title"),
            "type": fm.get("type"),
            "topics": fm.get("topics") or [],
            "status": status,
            "gap_count": len(gaps),
            "gaps": gaps,
            "linked_frontier_count": len(fm.get("linked_frontier") or []),
            "linked_questions_count": len(fm.get("linked_questions") or []),
            "updated": fm.get("updated"),
            "path": str(doc.path.relative_to(kb)),
        })

    # Sort: needs_more first, then by gap count desc
    status_order = {"needs_more": 0, "stub": 1, "draft": 2}
    pending.sort(key=lambda x: (status_order.get(x["status"], 9), -x["gap_count"]))

    # Group by first topic for display
    by_topic: dict[str, list] = defaultdict(list)
    for entry in pending:
        top = (entry["topics"] or ["misc"])[0]
        by_topic[top].append(entry)

    result = {
        "total": len(pending),
        "by_topic": dict(by_topic),
        "all": pending,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
