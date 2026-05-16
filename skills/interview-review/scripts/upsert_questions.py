#!/usr/bin/env python3
"""Upsert question cards from a JSON draft.

Reads a JSON array (schema in SKILL.md step 4), creates or updates question
markdown files, maintains bidirectional links with knowledge, and writes
questions.json into the interview directory.

This is where the "double-link consistency" rule lives. Claude doesn't touch YAML.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from common import (  # noqa: E402
    MdDoc, kb_root, next_question_id, today_iso,
    find_knowledge_by_title_or_slug, dedupe_keep_order,
)


def recompute_mastery(history: list[dict]) -> float:
    """Weighted average of last 3 ratings, normalized to 0-1."""
    if not history:
        return 0.0
    recent = history[-3:]
    weights = [0.25, 0.25, 0.5][-len(recent):]
    total_w = sum(weights)
    avg = sum(r.get("self_rating", 0) * w for r, w in zip(recent, weights)) / total_w
    return round(max(0.0, min(1.0, (avg - 1) / 4)), 2)


def create_question(kb: Path, iv_id: str, q: dict, missing: list[dict]) -> str:
    """Create a new question card. Returns the new q_id."""
    qid = next_question_id(kb)
    today = today_iso()

    # Resolve linked_knowledge_titles -> linked_knowledge ids
    linked_knowledge: list[str] = []
    for hint in q.get("linked_knowledge_titles") or []:
        kdoc = find_knowledge_by_title_or_slug(kb, hint)
        if kdoc is None:
            missing.append({"hint": hint, "from_question": qid})
            continue
        linked_knowledge.append(kdoc.frontmatter.get("id"))

    fm = {
        "id": qid,
        "question": q["question"],
        "topics": q.get("topics") or [],
        "asked_in": [iv_id],
        "my_answer_history": [{
            "date": today,
            "context": "real_interview",
            "summary": q.get("my_answer_summary", ""),
            "self_rating": int(q.get("self_rating", 3)),
        }],
        "better_answer": q.get("better_answer", ""),
        "gaps_to_fill": q.get("gaps_to_fill") or [],
        "linked_knowledge": linked_knowledge,
        "difficulty": int(q.get("difficulty", 3)),
        "mastery": 0.0,
        "tags": q.get("tags") or [],
        "created": today,
        "updated": today,
    }
    fm["mastery"] = recompute_mastery(fm["my_answer_history"])

    body = ""  # body is optional, frontmatter carries everything for now
    path = kb / "questions" / f"{qid}.md"
    fm_text = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{fm_text}---\n{body}", encoding="utf-8")

    # Write back-link into knowledge frontmatter
    for kid in linked_knowledge:
        kpath = kb / "wiki" / f"{kid}.md"
        if kpath.exists():
            kdoc = MdDoc.load(kpath)
            lq = kdoc.frontmatter.get("linked_questions") or []
            if qid not in lq:
                lq.append(qid)
                kdoc.frontmatter["linked_questions"] = lq
                kdoc.frontmatter["updated"] = today
                kdoc.save()

    return qid


def update_question(kb: Path, iv_id: str, q: dict, missing: list[dict]) -> str:
    """Append a new answer to an existing question, refresh links and mastery."""
    qid = q["reuse_id"]
    path = kb / "questions" / f"{qid}.md"
    if not path.exists():
        raise FileNotFoundError(f"reuse_id {qid} not found")
    doc = MdDoc.load(path)
    today = today_iso()

    asked_in = doc.frontmatter.get("asked_in") or []
    if iv_id not in asked_in:
        asked_in.append(iv_id)
        doc.frontmatter["asked_in"] = asked_in

    history = doc.frontmatter.get("my_answer_history") or []
    history.append({
        "date": today,
        "context": "real_interview",
        "summary": q.get("my_answer_summary", ""),
        "self_rating": int(q.get("self_rating", 3)),
    })
    doc.frontmatter["my_answer_history"] = history
    doc.frontmatter["mastery"] = recompute_mastery(history)

    # The reused question keeps its old better_answer unless the user passes a fresh one
    # that's longer/different. We append a "see also" note instead of overwriting,
    # to preserve learning trajectory.
    new_better = q.get("better_answer", "").strip()
    old_better = (doc.frontmatter.get("better_answer") or "").strip()
    if new_better and new_better != old_better:
        doc.frontmatter["better_answer"] = (
            old_better
            + f"\n\n---\n（{today} 复盘补充）\n"
            + new_better
        ) if old_better else new_better

    # gaps_to_fill: union, no duplicates
    new_gaps = list(doc.frontmatter.get("gaps_to_fill") or []) + list(q.get("gaps_to_fill") or [])
    doc.frontmatter["gaps_to_fill"] = dedupe_keep_order(new_gaps)

    # linked_knowledge: union, with title resolution
    existing_links = list(doc.frontmatter.get("linked_knowledge") or [])
    for hint in q.get("linked_knowledge_titles") or []:
        kdoc = find_knowledge_by_title_or_slug(kb, hint)
        if kdoc is None:
            missing.append({"hint": hint, "from_question": qid})
            continue
        kid = kdoc.frontmatter.get("id")
        if kid not in existing_links:
            existing_links.append(kid)
    doc.frontmatter["linked_knowledge"] = existing_links

    doc.frontmatter["updated"] = today
    doc.save()

    # Sync reverse links in knowledge
    for kid in existing_links:
        kpath = kb / "wiki" / f"{kid}.md"
        if not kpath.exists():
            continue
        kdoc = MdDoc.load(kpath)
        lq = kdoc.frontmatter.get("linked_questions") or []
        if qid not in lq:
            lq.append(qid)
            kdoc.frontmatter["linked_questions"] = lq
            kdoc.frontmatter["updated"] = today
            kdoc.save()

    return qid


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--interview", required=True, help="iv_id")
    p.add_argument("--questions-json", required=True, help="path to draft json")
    args = p.parse_args()

    kb = kb_root()
    iv_dir = kb / "interviews" / args.interview
    if not iv_dir.exists():
        print(f"ERROR: interview {args.interview} not found", file=sys.stderr)
        return 1

    drafts = json.loads(Path(args.questions_json).read_text(encoding="utf-8"))
    if not isinstance(drafts, list):
        print("ERROR: questions JSON must be a list", file=sys.stderr)
        return 1

    qids: list[str] = []
    missing: list[dict] = []
    for q in drafts:
        if q.get("reuse_id"):
            qids.append(update_question(kb, args.interview, q, missing))
        else:
            qids.append(create_question(kb, args.interview, q, missing))

    (iv_dir / "questions.json").write_text(
        json.dumps(qids, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if missing:
        (iv_dir / "missing_wiki.json").write_text(
            json.dumps(missing, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(json.dumps({
        "interview": args.interview,
        "question_ids": qids,
        "missing_wiki_count": len(missing),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
