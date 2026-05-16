#!/usr/bin/env python3
"""Search the question bank for similar existing questions.

Uses cheap heuristics (token overlap + topic match). No embeddings — that's a v2 thing.
Returns top-3 as JSON for Claude to judge whether to reuse.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from common import kb_root, load_all_questions  # noqa: E402


def tokenize(s: str) -> set[str]:
    """Crude bilingual tokenizer: ascii words + single CJK chars + bigrams."""
    s = s.lower()
    tokens = set(re.findall(r"[a-z0-9]+", s))
    cjk = re.findall(r"[\u4e00-\u9fff]", s)
    tokens.update(cjk)
    # CJK bigrams
    for i in range(len(cjk) - 1):
        tokens.add(cjk[i] + cjk[i + 1])
    # drop tiny noise
    return {t for t in tokens if len(t) >= 1}


def score(query_tokens: set[str], q_text: str, q_topics: list[str], query_topics: list[str]) -> float:
    qt = tokenize(q_text)
    if not qt or not query_tokens:
        return 0.0
    overlap = len(query_tokens & qt) / max(len(query_tokens | qt), 1)
    topic_bonus = 0.0
    if query_topics:
        common = set(query_topics) & set(q_topics or [])
        topic_bonus = 0.2 * (len(common) / len(set(query_topics) | set(q_topics or [])))
    return overlap + topic_bonus


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True)
    p.add_argument("--topics", default="")
    p.add_argument("--top", type=int, default=3)
    p.add_argument("--threshold", type=float, default=0.15)
    args = p.parse_args()

    kb = kb_root()
    query_tokens = tokenize(args.query)
    query_topics = [t.strip() for t in args.topics.split(",") if t.strip()]

    candidates = []
    for d in load_all_questions(kb):
        fm = d.frontmatter
        s = score(query_tokens, fm.get("question", ""), fm.get("topics") or [], query_topics)
        if s >= args.threshold:
            candidates.append({
                "id": fm.get("id"),
                "question": fm.get("question"),
                "topics": fm.get("topics") or [],
                "score": round(s, 3),
                "mastery": fm.get("mastery", 0),
                "asked_in_count": len(fm.get("asked_in") or []),
            })
    candidates.sort(key=lambda x: x["score"], reverse=True)
    print(json.dumps(candidates[: args.top], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
