#!/usr/bin/env python3
"""Create a new frontier entry file with frontmatter template.

Claude calls this to allocate the fr_id and write the skeleton;
Claude then fills in the structured body content.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from common import kb_root, slugify, today_iso, next_frontier_id  # noqa: E402


BODY_TEMPLATE = """
## 一句话总结

<!-- TODO: 用一句话说清楚这篇的核心贡献和与已有工作的区别 -->

## 背景与动机

<!-- TODO: 这篇为什么要做，解决了什么问题，2-4 句 -->

## 核心方法

<!-- TODO: 主要技术创新，每个关键点一段，有公式写公式 -->

## 关键实验结论

<!-- TODO: 来自原文的具体数字，写明是哪个 benchmark，提升多少 -->

## 与相关工作的关系

<!-- TODO: 和哪几篇关联最紧密，区别在哪里 -->

## 待深入

<!-- TODO: 读完还没搞清楚的点，值得后续 deep-dive 的子问题 -->
"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True, help="short slug for the id, e.g. dapo or deepseek-r1")
    p.add_argument("--title", required=True)
    p.add_argument("--type", default="paper",
                   choices=["paper", "tech_report", "blog", "hot_topic_summary"])
    p.add_argument("--url", default="N/A")
    p.add_argument("--authors", default="")
    p.add_argument("--pub-date", default="", dest="pub_date")
    p.add_argument("--topics", default="", help="comma-separated topics")
    p.add_argument("--linked-wiki", default="", dest="linked_wiki",
                   help="comma-separated kn_ids already known to be related")
    args = p.parse_args()

    kb = kb_root()
    slug = slugify(args.slug, max_len=30)
    fr_id = next_frontier_id(kb, slug)
    today = today_iso()

    topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    linked_wiki = [k.strip() for k in args.linked_wiki.split(",") if k.strip()]

    fm: dict = {
        "id": fr_id,
        "title": args.title,
        "type": args.type,
        "url": args.url,
        "topics": topics or ["misc"],
        "status": "ingested",
        "linked_wiki": linked_wiki,
        "created": today,
        "updated": today,
    }
    if args.authors:
        fm["authors"] = args.authors
    if args.pub_date:
        fm["date"] = args.pub_date

    # Reorder for readability: id, title, type, url, authors, date, topics, status, linked_wiki, created, updated
    ordered_keys = ["id", "title", "type", "url", "authors", "date", "topics", "status",
                    "linked_wiki", "created", "updated"]
    fm_ordered = {k: fm[k] for k in ordered_keys if k in fm}

    fdir = kb / "frontier"
    fdir.mkdir(parents=True, exist_ok=True)
    path = fdir / f"{fr_id}.md"
    fm_text = yaml.safe_dump(fm_ordered, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{fm_text}---\n{BODY_TEMPLATE}", encoding="utf-8")

    print(fr_id)
    print(str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
