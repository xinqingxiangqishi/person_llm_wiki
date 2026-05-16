#!/usr/bin/env python3
"""Validate kb invariants across wiki, frontier, questions, and interviews.

Exits non-zero on any error. Run after every skill writes files.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (  # noqa: E402
    kb_root, load_all_wiki, load_all_frontier, load_all_questions, load_all_interviews,
)


def main() -> int:
    kb = kb_root()
    errors: list[str] = []
    warnings: list[str] = []

    wiki = load_all_wiki(kb)
    frontier = load_all_frontier(kb)
    questions = load_all_questions(kb)
    interviews = load_all_interviews(kb)

    w_by_id = {d.frontmatter.get("id"): d for d in wiki}
    f_by_id = {d.frontmatter.get("id"): d for d in frontier}
    q_by_id = {d.frontmatter.get("id"): d for d in questions}
    iv_by_id = {meta.get("id"): (d, meta) for d, meta in interviews}

    # --- Wiki schema ---
    for d in wiki:
        fm = d.frontmatter
        for req in ("id", "title", "type", "topics", "status"):
            if not fm.get(req):
                errors.append(f"wiki/{d.path.name}: missing field '{req}'")
        if fm.get("status") not in {"stub", "draft", "reviewed", "needs_more", None}:
            warnings.append(f"wiki/{d.path.name}: unknown status '{fm.get('status')}'")

    # --- Frontier schema ---
    for d in frontier:
        fm = d.frontmatter
        for req in ("id", "title", "type", "topics"):
            if not fm.get(req):
                errors.append(f"frontier/{d.path.name}: missing field '{req}'")
        if fm.get("status") not in {"ingested", "needs_review", "archived", None}:
            warnings.append(f"frontier/{d.path.name}: unknown status '{fm.get('status')}'")

    # --- Question schema ---
    for d in questions:
        fm = d.frontmatter
        for req in ("id", "question", "topics", "better_answer"):
            if not fm.get(req):
                errors.append(f"questions/{d.path.name}: missing field '{req}'")

    # --- Cross-link: question.linked_knowledge <-> wiki.linked_questions ---
    for d in questions:
        qid = d.frontmatter.get("id")
        for kid in d.frontmatter.get("linked_knowledge", []) or []:
            wdoc = w_by_id.get(kid)
            if wdoc is None:
                errors.append(f"{qid}: linked_knowledge '{kid}' not in wiki/")
                continue
            back = wdoc.frontmatter.get("linked_questions", []) or []
            if qid not in back:
                errors.append(f"{qid} -> {kid}: missing reverse link in wiki.linked_questions")

    for d in wiki:
        kid = d.frontmatter.get("id")
        for qid in d.frontmatter.get("linked_questions", []) or []:
            qdoc = q_by_id.get(qid)
            if qdoc is None:
                errors.append(f"{kid}: linked_questions '{qid}' not in questions/")
                continue
            back = qdoc.frontmatter.get("linked_knowledge", []) or []
            if kid not in back:
                errors.append(f"{kid} -> {qid}: missing reverse link in question.linked_knowledge")

    # --- Cross-link: frontier.linked_wiki <-> wiki.linked_frontier ---
    for d in frontier:
        fid = d.frontmatter.get("id")
        for kid in d.frontmatter.get("linked_wiki", []) or []:
            wdoc = w_by_id.get(kid)
            if wdoc is None:
                errors.append(f"{fid}: linked_wiki '{kid}' not in wiki/")
                continue
            back = wdoc.frontmatter.get("linked_frontier", []) or []
            if fid not in back:
                errors.append(f"{fid} -> {kid}: missing reverse link in wiki.linked_frontier")

    for d in wiki:
        kid = d.frontmatter.get("id")
        for fid in d.frontmatter.get("linked_frontier", []) or []:
            fdoc = f_by_id.get(fid)
            if fdoc is None:
                errors.append(f"{kid}: linked_frontier '{fid}' not in frontier/")
                continue
            back = fdoc.frontmatter.get("linked_wiki", []) or []
            if kid not in back:
                errors.append(f"{kid} -> {fid}: missing reverse link in frontier.linked_wiki")

    # --- Cross-link: question.asked_in <-> interview/questions.json ---
    for iv_id, (iv_dir, _) in iv_by_id.items():
        qjson_path = iv_dir / "questions.json"
        if not qjson_path.exists():
            warnings.append(f"interviews/{iv_id}: no questions.json yet")
            continue
        try:
            iv_qs = json.loads(qjson_path.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"interviews/{iv_id}/questions.json: invalid json: {e}")
            continue
        for qid in iv_qs:
            qdoc = q_by_id.get(qid)
            if qdoc is None:
                errors.append(f"interviews/{iv_id} references unknown question {qid}")
                continue
            if iv_id not in (qdoc.frontmatter.get("asked_in", []) or []):
                errors.append(f"{qid} should list {iv_id} in asked_in")

    for d in questions:
        qid = d.frontmatter.get("id")
        for iv_id in d.frontmatter.get("asked_in", []) or []:
            if iv_id not in iv_by_id:
                errors.append(f"{qid}: asked_in references unknown interview {iv_id}")

    # --- Source warnings ---
    for d in wiki:
        fm = d.frontmatter
        if fm.get("status") in {"reviewed", "needs_more"} and not (fm.get("sources") or []):
            warnings.append(f"{fm.get('id')}: status={fm.get('status')} but no sources")

    # Report
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(
        f"OK  ({len(wiki)} wiki, {len(frontier)} frontier, "
        f"{len(questions)} questions, {len(interviews)} interviews)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
