#!/usr/bin/env python3
"""Create a new wiki entry with frontmatter template.

Claude calls this to allocate the kn_id and write the frontmatter skeleton;
Claude then fills in the body content via direct file edit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from common import kb_root, slugify, today_iso, next_wiki_id  # noqa: E402


BODY_TEMPLATE = """
## 一句话总结

<!-- TODO: 一句话说清楚这个概念是什么 -->

## 核心内容

<!-- TODO: 关键机制、原理、使用场景 -->

## 与相关概念的对比

<!-- TODO: 和最相关的 1-3 个概念的区别，这是最有价值的部分 -->

## 来源说明

<!-- TODO: 主要参考来源，或写"基于面试复盘整理" -->
"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True, help="short slug, e.g. grpo or rl-alignment")
    p.add_argument("--title", required=True)
    p.add_argument("--type", default="concept",
                   choices=["concept", "method", "framework", "tool", "other"])
    p.add_argument("--topics", default="", help="comma-separated; first one is mindmap grouping key")
    p.add_argument("--source-url", default="", dest="source_url")
    p.add_argument("--source-kind", default="", dest="source_kind",
                   choices=["paper", "blog", "doc", "repo", "other", ""])
    p.add_argument("--source-citation", default="", dest="source_citation")
    p.add_argument("--status", default="stub",
                   choices=["stub", "draft", "reviewed", "needs_more"])
    args = p.parse_args()

    kb = kb_root()
    slug = slugify(args.slug, max_len=30)
    kn_id = next_wiki_id(kb, slug)
    today = today_iso()

    topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    sources: list[dict] = []
    if args.source_url:
        src: dict = {"kind": args.source_kind or "other", "url": args.source_url}
        if args.source_citation:
            src["citation"] = args.source_citation
        sources.append(src)

    fm: dict = {
        "id": kn_id,
        "title": args.title,
        "type": args.type,
        "topics": topics or ["misc"],
        "status": args.status,
        "linked_questions": [],
        "linked_frontier": [],
        "linked_from_interviews": [],
        "gaps": [],
        "created": today,
        "updated": today,
    }
    if sources:
        fm["sources"] = sources

    # Put sources before gaps for readability
    ordered_keys = ["id", "title", "type", "topics", "status",
                    "linked_questions", "linked_frontier", "linked_from_interviews",
                    "sources", "gaps", "created", "updated"]
    fm_ordered = {k: fm[k] for k in ordered_keys if k in fm}

    wdir = kb / "wiki"
    wdir.mkdir(parents=True, exist_ok=True)
    path = wdir / f"{kn_id}.md"
    fm_text = yaml.safe_dump(fm_ordered, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{fm_text}---\n{BODY_TEMPLATE}", encoding="utf-8")

    print(kn_id)
    print(str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
