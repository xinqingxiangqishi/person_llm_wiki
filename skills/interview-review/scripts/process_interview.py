#!/usr/bin/env python3
"""process_interview.py — single-call interview processor.

Replaces: new_interview.py + upsert_questions.py + render_review.py + propagate_gaps.py

Input:  --json <path>   path to interview_draft.json produced by Claude
Output: iv_id, review.md path, stats (printed to stdout as JSON)

JSON schema (all fields):
{
  "meta": {
    "company": str,
    "role": str,
    "round": str,
    "date": str,           // YYYY-MM-DD, defaults to today
    "duration_min": int,
    "self_overall_rating": int,   // 1-5
    "interviewer_style": str      // optional
  },
  "cleaned_transcript": str,
  "overall_rating": float,        // 1-5, can be .5
  "overall_comment": str,
  "next_prep": [str],
  "questions": [
    {
      "reuse_id": str,             // "" or null = new question
      "question": str,
      "topics": [str],
      "my_answer_summary": str,
      "self_rating": int,          // 1-5
      "highlights": str,
      "weaknesses": str,
      "improvement": str,
      "better_answer": str,
      "gaps_to_fill": [str],
      "linked_wiki_titles": [str]  // resolved to kn_ids by script
    }
  ]
}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from common import (  # noqa: E402
    kb_root, slugify, today_iso, next_question_id,
    find_wiki_by_title_or_slug, MdDoc, dedupe_keep_order,
)


# ---------------------------------------------------------------------------
# Mastery
# ---------------------------------------------------------------------------

def recompute_mastery(history: list[dict]) -> float:
    if not history:
        return 0.0
    recent = history[-3:]
    weights = [0.25, 0.25, 0.5][-len(recent):]
    total_w = sum(weights)
    avg = sum(r.get("self_rating", 0) * w for r, w in zip(recent, weights)) / total_w
    return round(max(0.0, min(1.0, (avg - 1) / 4)), 2)


# ---------------------------------------------------------------------------
# Interview directory
# ---------------------------------------------------------------------------

def make_iv_id(kb: Path, company: str, date_str: str) -> tuple[str, Path]:
    interviews_dir = kb / "interviews"
    interviews_dir.mkdir(parents=True, exist_ok=True)
    parts = date_str.split("-")
    yyyy, mm = parts[0], parts[1] if len(parts) > 1 else "01"
    slug = slugify(company, max_len=20)
    base = f"iv_{yyyy}_{mm}_{slug}"
    existing = [d.name for d in interviews_dir.iterdir() if d.is_dir() and d.name.startswith(base)]
    nums = []
    for name in existing:
        m = re.match(re.escape(base) + r"_(\d+)$", name)
        if m:
            nums.append(int(m.group(1)))
    n = (max(nums) + 1) if nums else 1
    iv_id = f"{base}_{n}"
    return iv_id, interviews_dir / iv_id


# ---------------------------------------------------------------------------
# Question cards
# ---------------------------------------------------------------------------

def upsert_question(kb: Path, iv_id: str, q: dict, missing_wiki: list[dict]) -> str:
    today = today_iso()
    # Resolve linked_wiki_titles -> kn_ids
    linked_knowledge: list[str] = []
    for hint in q.get("linked_wiki_titles") or []:
        doc = find_wiki_by_title_or_slug(kb, hint)
        if doc is None:
            missing_wiki.append({"hint": hint})
        else:
            kid = doc.frontmatter.get("id")
            if kid and kid not in linked_knowledge:
                linked_knowledge.append(kid)

    answer_entry = {
        "date": today,
        "context": "real_interview",
        "summary": q.get("my_answer_summary", ""),
        "self_rating": int(q.get("self_rating", 3)),
    }

    reuse_id = q.get("reuse_id", "")
    if reuse_id:
        # Update existing question card
        qpath = kb / "questions" / f"{reuse_id}.md"
        if not qpath.exists():
            print(f"WARNING: reuse_id {reuse_id} not found, creating new instead", file=sys.stderr)
            reuse_id = ""
        else:
            doc = MdDoc.load(qpath)
            asked_in = doc.frontmatter.get("asked_in") or []
            if iv_id not in asked_in:
                asked_in.append(iv_id)
            doc.frontmatter["asked_in"] = asked_in

            history = doc.frontmatter.get("my_answer_history") or []
            history.append(answer_entry)
            doc.frontmatter["my_answer_history"] = history
            doc.frontmatter["mastery"] = recompute_mastery(history)

            new_better = (q.get("better_answer") or "").strip()
            old_better = (doc.frontmatter.get("better_answer") or "").strip()
            if new_better and new_better != old_better:
                doc.frontmatter["better_answer"] = (
                    old_better + f"\n\n---\n（{today} 复盘补充）\n" + new_better
                ) if old_better else new_better

            new_gaps = dedupe_keep_order(
                list(doc.frontmatter.get("gaps_to_fill") or []) + list(q.get("gaps_to_fill") or [])
            )
            doc.frontmatter["gaps_to_fill"] = new_gaps

            existing_links = list(doc.frontmatter.get("linked_knowledge") or [])
            for kid in linked_knowledge:
                if kid not in existing_links:
                    existing_links.append(kid)
            doc.frontmatter["linked_knowledge"] = existing_links
            doc.frontmatter["updated"] = today
            doc.save()
            _sync_wiki_backlinks(kb, reuse_id, existing_links, today)
            return reuse_id

    if not reuse_id:
        # Create new question card
        qid = next_question_id(kb)
        fm = {
            "id": qid,
            "question": q["question"],
            "topics": q.get("topics") or [],
            "asked_in": [iv_id],
            "my_answer_history": [answer_entry],
            "better_answer": q.get("better_answer", ""),
            "gaps_to_fill": q.get("gaps_to_fill") or [],
            "linked_knowledge": linked_knowledge,
            "mastery": 0.0,
        }
        fm["mastery"] = recompute_mastery(fm["my_answer_history"])
        qpath = kb / "questions" / f"{qid}.md"
        qpath.parent.mkdir(parents=True, exist_ok=True)
        fm_text = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
        qpath.write_text(f"---\n{fm_text}---\n", encoding="utf-8")
        _sync_wiki_backlinks(kb, qid, linked_knowledge, today)
        return qid

    return ""  # unreachable


def _sync_wiki_backlinks(kb: Path, qid: str, linked_knowledge: list[str], today: str) -> None:
    for kid in linked_knowledge:
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


# ---------------------------------------------------------------------------
# Gap propagation
# ---------------------------------------------------------------------------

def propagate_gaps(kb: Path, iv_id: str, qids: list[str], today: str) -> list[tuple[str, str]]:
    """Push gaps_to_fill from question cards into linked wiki entries."""
    propagated: list[tuple[str, str]] = []
    for qid in qids:
        qpath = kb / "questions" / f"{qid}.md"
        if not qpath.exists():
            continue
        qdoc = MdDoc.load(qpath)
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
            if iv_id not in lfi:
                lfi.append(iv_id)
            kdoc.frontmatter["linked_from_interviews"] = lfi
            if kdoc.frontmatter.get("status") == "reviewed":
                kdoc.frontmatter["status"] = "needs_more"
            kdoc.frontmatter["updated"] = today
            kdoc.save()
            for g in added:
                propagated.append((kid, g))
    return propagated


# ---------------------------------------------------------------------------
# review.md renderer
# ---------------------------------------------------------------------------

def render_review(iv_id: str, meta: dict, questions: list[dict], qids: list[str],
                  overall_rating: float, overall_comment: str,
                  next_prep: list[str], propagated: list[tuple[str, str]],
                  missing_wiki: list[dict], kb: Path) -> str:
    out = []
    out.append(f"# {meta['company']} {meta['round']} 复盘 — {meta.get('date', today_iso())}\n")
    out.append(
        f"_岗位_: {meta['role']}  •  _时长_: {meta.get('duration_min', '?')} 分钟"
        f"  •  _自评_: {meta.get('self_overall_rating', '?')}/5\n"
    )
    if meta.get("interviewer_style"):
        out.append(f"_面试官风格_: {meta['interviewer_style']}\n")

    out.append("\n## 总体评价\n")
    out.append(f"**评分**：{overall_rating}/5\n")
    out.append(f"{overall_comment}\n")
    if next_prep:
        out.append("\n**下次重点准备**：\n")
        for item in next_prep:
            out.append(f"- {item}")
    out.append("\n---\n")

    out.append("\n## 问题逐题复盘\n")
    for i, (q, qid) in enumerate(zip(questions, qids), 1):
        rating = q.get("self_rating", "?")
        out.append(f"\n### Q{i}. {q['question']}  [[{qid}]]\n")
        out.append(f"_topics_: {', '.join(q.get('topics') or [])}  •  _自评_: {rating}/5\n")
        out.append(f"\n**我的回答**\n\n{q.get('my_answer_summary', '')}\n")
        out.append(
            f"\n**评分**：{rating}/5  "
            f"✅ 亮点：{q.get('highlights', '')}  "
            f"❌ 不足：{q.get('weaknesses', '')}\n"
        )
        if q.get("improvement"):
            out.append(f"\n**改进方向**\n\n{q['improvement']}\n")
        if q.get("better_answer"):
            out.append(f"\n**参考回答要点**\n\n{q['better_answer']}\n")
        out.append("\n---\n")

    out.append("\n## 这场暴露的 Gap\n")
    if propagated:
        out.append("| 知识点 | Gap | 状态 |\n|---|---|---|\n")
        for kid, gap in propagated:
            out.append(f"| `{kid}` | {gap} | 已写入 wiki |\n")
    else:
        out.append("无（或相关 wiki 条目还未建立）\n")

    if missing_wiki:
        out.append("\n## 库里还没有的知识点\n")
        out.append("以下知识点在题目里被引用但 wiki/ 里还没有对应条目，建议用 wiki skill 补上：\n")
        seen = set()
        for m in missing_wiki:
            hint = m.get("hint", "")
            if hint not in seen:
                out.append(f"- `{hint}`")
                seen.add(hint)

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", required=True, dest="json_path", help="path to interview_draft.json")
    args = p.parse_args()

    draft_path = Path(args.json_path)
    if not draft_path.exists():
        print(f"ERROR: {draft_path} not found", file=sys.stderr)
        return 1

    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    kb = kb_root()
    today = today_iso()

    meta = draft["meta"]
    date_str = meta.get("date") or today
    meta["date"] = date_str

    iv_id, iv_dir = make_iv_id(kb, meta["company"], date_str)
    iv_dir.mkdir(parents=True, exist_ok=True)

    # Write meta.yaml
    meta_out = {k: meta[k] for k in
                ["company", "role", "round", "date", "duration_min",
                 "self_overall_rating"] if k in meta}
    meta_out["id"] = iv_id
    meta_out["outcome"] = "pending"
    if meta.get("interviewer_style"):
        meta_out["interviewer_style"] = meta["interviewer_style"]
    meta_out["created"] = today
    (iv_dir / "meta.yaml").write_text(
        yaml.safe_dump(meta_out, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    # Write raw.md (cleaned transcript)
    cleaned = draft.get("cleaned_transcript", "")
    (iv_dir / "raw.md").write_text(cleaned, encoding="utf-8")

    # Upsert question cards
    questions = draft.get("questions") or []
    qids: list[str] = []
    missing_wiki: list[dict] = []
    new_count = 0
    reuse_count = 0

    for q in questions:
        was_reuse = bool(q.get("reuse_id"))
        qid = upsert_question(kb, iv_id, q, missing_wiki)
        if qid:
            qids.append(qid)
            if was_reuse:
                reuse_count += 1
            else:
                new_count += 1

    # Write questions.json
    (iv_dir / "questions.json").write_text(
        json.dumps(qids, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Propagate gaps to wiki
    propagated = propagate_gaps(kb, iv_id, qids, today)

    # Render review.md
    review_text = render_review(
        iv_id, meta, questions, qids,
        overall_rating=draft.get("overall_rating", 3),
        overall_comment=draft.get("overall_comment", ""),
        next_prep=draft.get("next_prep") or [],
        propagated=propagated,
        missing_wiki=missing_wiki,
        kb=kb,
    )
    review_path = iv_dir / "review.md"
    review_path.write_text(review_text, encoding="utf-8")

    # Output summary
    top_gaps = propagated[:3]
    result = {
        "iv_id": iv_id,
        "review_path": str(review_path),
        "questions_new": new_count,
        "questions_reused": reuse_count,
        "gaps_propagated": len(propagated),
        "top_gaps": [f"{kid}: {g}" for kid, g in top_gaps],
        "missing_wiki": [m["hint"] for m in missing_wiki],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
