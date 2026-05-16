#!/usr/bin/env python3
"""Build a mermaid mindmap from wiki and frontier entries.

Output: llm-kb/mindmap/mindmap.mmd  (mermaid source)
        llm-kb/mindmap/mindmap.md   (markdown wrapping the mermaid block)

Topology:
  root
    <topic>          ← wiki entries and frontier entries grouped by first topic
      kn_xxx: title  ← wiki entry
      fr_xxx: title  ← frontier entry (prefixed with [F])

Grouping key: the FIRST element of each entry's topics list.
This avoids the "post-training → post" split bug — no string splitting.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import kb_root  # noqa: E402


def main() -> int:
    kb = kb_root()
    idx_path = kb / "index" / "all.json"
    if not idx_path.exists():
        print("ERROR: run index.py first", file=sys.stderr)
        return 1
    idx = json.loads(idx_path.read_text(encoding="utf-8"))

    # top-level topic -> list of (node_id, display_label)
    tree: dict[str, list[tuple[str, str]]] = defaultdict(list)
    q_count: dict[str, int] = defaultdict(int)

    for k in idx.get("wiki", []):
        topics = k.get("topics") or ["misc"]
        top = topics[0]
        label = (k.get("title") or k["id"])[:50].replace("(", "[").replace(")", "]")
        tree[top].append((k["id"], label))

    for f in idx.get("frontier", []):
        topics = f.get("topics") or ["misc"]
        top = topics[0]
        label = ("[F] " + (f.get("title") or f["id"]))[:50].replace("(", "[").replace(")", "]")
        tree[top].append((f["id"], label))

    for q in idx.get("questions", []):
        for t in q.get("topics") or ["misc"]:
            q_count[t] += 1

    lines = ["mindmap", "  root((LLM KB))"]
    for top in sorted(tree):
        suffix = f" ({q_count[top]}q)" if q_count[top] else ""
        lines.append(f"    {top}{suffix}")
        for node_id, label in sorted(tree[top]):
            lines.append(f"      {node_id}: {label}")

    mm_dir = kb / "mindmap"
    mm_dir.mkdir(parents=True, exist_ok=True)
    mmd = "\n".join(lines) + "\n"
    (mm_dir / "mindmap.mmd").write_text(mmd, encoding="utf-8")
    (mm_dir / "mindmap.md").write_text(
        f"# Knowledge Mindmap\n\n```mermaid\n{mmd}```\n",
        encoding="utf-8",
    )
    print(f"mindmap built: {len(tree)} top-level topics")
    return 0


if __name__ == "__main__":
    sys.exit(main())
