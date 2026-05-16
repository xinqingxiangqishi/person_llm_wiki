#!/usr/bin/env python3
"""Rebuild llm-kb/index/all.json from all markdown frontmatter.

Idempotent, fast, dependency-light. Run after every write operation.
Covers: wiki entries, frontier entries, questions, interviews.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (  # noqa: E402
    kb_root, load_all_wiki, load_all_frontier, load_all_questions, load_all_interviews,
)


def main() -> int:
    kb = kb_root()
    if not kb.exists():
        print(f"ERROR: kb root not found: {kb}", file=sys.stderr)
        return 1

    topics_idx: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"wiki": [], "frontier": [], "questions": []}
    )

    # Wiki entries
    wiki = []
    for doc in load_all_wiki(kb):
        fm = doc.frontmatter
        entry = {
            "id": fm.get("id"),
            "title": fm.get("title"),
            "type": fm.get("type"),
            "topics": fm.get("topics", []),
            "status": fm.get("status", "draft"),
            "gap_count": len(fm.get("gaps", []) or []),
            "linked_questions": fm.get("linked_questions", []) or [],
            "linked_frontier": fm.get("linked_frontier", []) or [],
            "path": str(doc.path.relative_to(kb)),
            "updated": fm.get("updated"),
        }
        wiki.append(entry)
        for t in entry["topics"]:
            topics_idx[t]["wiki"].append(entry["id"])

    # Frontier entries
    frontier = []
    for doc in load_all_frontier(kb):
        fm = doc.frontmatter
        entry = {
            "id": fm.get("id"),
            "title": fm.get("title"),
            "type": fm.get("type"),
            "topics": fm.get("topics", []),
            "status": fm.get("status", "ingested"),
            "linked_wiki": fm.get("linked_wiki", []) or [],
            "url": fm.get("url"),
            "date": str(fm.get("date", "")),
            "path": str(doc.path.relative_to(kb)),
            "updated": fm.get("updated"),
        }
        frontier.append(entry)
        for t in entry["topics"]:
            topics_idx[t]["frontier"].append(entry["id"])

    # Questions
    questions = []
    for doc in load_all_questions(kb):
        fm = doc.frontmatter
        entry = {
            "id": fm.get("id"),
            "question": fm.get("question"),
            "topics": fm.get("topics", []),
            "mastery": fm.get("mastery", 0),
            "difficulty": fm.get("difficulty"),
            "asked_in": fm.get("asked_in", []) or [],
            "linked_knowledge": fm.get("linked_knowledge", []) or [],
            "answer_count": len(fm.get("my_answer_history", []) or []),
            "path": str(doc.path.relative_to(kb)),
            "updated": fm.get("updated"),
        }
        questions.append(entry)
        for t in entry["topics"]:
            topics_idx[t]["questions"].append(entry["id"])

    # Interviews
    interviews = []
    for d, meta in load_all_interviews(kb):
        interviews.append({
            "id": meta.get("id"),
            "company": meta.get("company"),
            "role": meta.get("role"),
            "round": meta.get("round"),
            "date": str(meta.get("date", "")),
            "outcome": meta.get("outcome", "pending"),
            "self_overall_rating": meta.get("self_overall_rating"),
            "path": str(d.relative_to(kb)),
        })

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kb_root": str(kb),
        "wiki": wiki,
        "frontier": frontier,
        "questions": questions,
        "interviews": interviews,
        "topics": dict(topics_idx),
        "stats": {
            "wiki_total": len(wiki),
            "wiki_with_gaps": sum(1 for k in wiki if k["gap_count"] > 0),
            "frontier_total": len(frontier),
            "questions_total": len(questions),
            "questions_low_mastery": sum(1 for q in questions if (q["mastery"] or 0) < 0.5),
            "interviews_total": len(interviews),
        },
    }

    idx_dir = kb / "index"
    idx_dir.mkdir(parents=True, exist_ok=True)
    (idx_dir / "all.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"index rebuilt: {out['stats']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
