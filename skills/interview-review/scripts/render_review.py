#!/usr/bin/env python3
"""Render review.md for an interview.

Builds the deterministic parts: header, problem cards, gap summary.
Claude is expected to fill the marked sections at the top and bottom
(一句话总评 / 下次同公司应该准备) afterwards.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from common import kb_root, MdDoc  # noqa: E402


def render(iv_dir: Path, kb: Path) -> str:
    meta = yaml.safe_load((iv_dir / "meta.yaml").read_text(encoding="utf-8"))
    qids = json.loads((iv_dir / "questions.json").read_text(encoding="utf-8"))

    out = []
    out.append(f"# {meta['company']} {meta['round']} 复盘 — {meta['date']}\n")
    out.append(f"_岗位_: {meta['role']}  •  _时长_: {meta.get('duration_min', '?')} 分钟  •  _自评_: {meta.get('self_overall_rating', '?')}/5\n")
    if meta.get("interviewer_style"):
        out.append(f"_面试官风格_: {meta['interviewer_style']}\n")
    out.append("\n## 一句话总评\n")
    out.append("<!-- TODO Claude: 1-2 句话总评这场，写完删掉本注释 -->\n")

    out.append("\n## 问答清单\n")

    gap_collection: list[tuple[str, str]] = []  # (kid_or_qid, gap_text)

    for i, qid in enumerate(qids, 1):
        qpath = kb / "questions" / f"{qid}.md"
        qdoc = MdDoc.load(qpath)
        fm = qdoc.frontmatter

        latest = (fm.get("my_answer_history") or [])[-1]
        my_summary = (latest or {}).get("summary", "")
        rating = (latest or {}).get("self_rating", "?")
        linked_k = fm.get("linked_knowledge") or []

        out.append(f"\n### Q{i}. {fm.get('question', '?')}  [[{qid}]]\n")
        out.append(f"_topics_: {', '.join(fm.get('topics') or [])}  •  _自评_: {rating}/5  •  _难度_: {fm.get('difficulty', '?')}/5\n")
        out.append(f"\n**我当时的回答**\n\n{my_summary}\n")
        out.append(f"\n**更好的回答**\n\n{fm.get('better_answer', '')}\n")

        gaps = fm.get("gaps_to_fill") or []
        if gaps:
            out.append("\n**我没说到的点**\n")
            for g in gaps:
                out.append(f"- {g}")
                gap_collection.append((linked_k[0] if linked_k else qid, g))
            out.append("")

        if linked_k:
            out.append("\n**关联知识**: " + " ".join(f"[[{k}]]" for k in linked_k) + "\n")

    out.append("\n## 这场暴露的 gap\n")
    if gap_collection:
        out.append("（已通过 `propagate_gaps.py` 写入对应 wiki 条目）\n")
        for target, g in gap_collection:
            out.append(f"- `{target}`: {g}")
    else:
        out.append("无（要么你太强，要么抽得太浅）\n")

    # Surface missing knowledge if any
    missing_path = iv_dir / "missing_wiki.json"
    if missing_path.exists():
        missing = json.loads(missing_path.read_text(encoding="utf-8"))
        if missing:
            out.append("\n## 库里还没有的知识点\n")
            out.append("以下知识点在 questions 里被引用但 wiki/ 里还没有对应条目。建议用 frontier-ingest 或 wiki skill 补上：\n")
            for m in missing:
                out.append(f"- `{m['hint']}`  (引用自 {m['from_question']})")

    out.append("\n## 下次同公司应该准备\n")
    out.append("<!-- TODO Claude: 基于面试官风格和暴露的 gap，给 3-5 条具体建议，写完删掉本注释 -->\n")

    return "\n".join(out) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--interview", required=True)
    args = p.parse_args()

    kb = kb_root()
    iv_dir = kb / "interviews" / args.interview
    if not iv_dir.exists():
        print(f"ERROR: interview {args.interview} not found", file=sys.stderr)
        return 1

    text = render(iv_dir, kb)
    out_path = iv_dir / "review.md"
    out_path.write_text(text, encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
