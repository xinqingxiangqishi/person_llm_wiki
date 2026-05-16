"""Common helpers for the llm-interview-kit skills.

Keep this small and dependency-light: only stdlib + PyYAML.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Run: pip install pyyaml --break-system-packages", file=sys.stderr)
    sys.exit(1)


def kb_root() -> Path:
    """Resolve the knowledge base root.

    Priority:
      1. $LLM_KB_ROOT
      2. ./llm-kb relative to current working dir
      3. llm-kb relative to this file's grandparent (the kit root)
    """
    env = os.environ.get("LLM_KB_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    cwd_candidate = Path.cwd() / "llm-kb"
    if cwd_candidate.exists():
        return cwd_candidate.resolve()
    return (Path(__file__).resolve().parents[2] / "llm-kb").resolve()


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


@dataclass
class MdDoc:
    """A markdown doc with YAML frontmatter."""
    path: Path
    frontmatter: dict
    body: str

    @classmethod
    def load(cls, path: Path) -> "MdDoc":
        text = path.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        if not m:
            raise ValueError(f"No YAML frontmatter in {path}")
        fm = yaml.safe_load(m.group(1)) or {}
        return cls(path=path, frontmatter=fm, body=m.group(2))

    def save(self) -> None:
        fm_text = yaml.safe_dump(self.frontmatter, allow_unicode=True, sort_keys=False)
        out = f"---\n{fm_text}---\n{self.body}"
        self.path.write_text(out, encoding="utf-8")


def today_iso() -> str:
    return date.today().isoformat()


def slugify(text: str, max_len: int = 40) -> str:
    """Lowercase, ascii-safe, no spaces. Keeps Chinese chars intact for human readability."""
    text = text.strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9一-鿿\-]", "", text)
    return text[:max_len] or "untitled"


def next_question_id(kb: Path) -> str:
    """Find the next q_xxxx id by scanning existing question files."""
    qdir = kb / "questions"
    qdir.mkdir(parents=True, exist_ok=True)
    nums = []
    for p in qdir.glob("q_*.md"):
        m = re.match(r"q_(\d+)", p.stem)
        if m:
            nums.append(int(m.group(1)))
    n = (max(nums) + 1) if nums else 1
    return f"q_{n:04d}"


def next_frontier_id(kb: Path, slug: str) -> str:
    """Generate fr_<yyyy>_<slug>, appending _2/_3 on collision."""
    year = date.today().year
    base = f"fr_{year}_{slug}"
    fdir = kb / "frontier"
    fdir.mkdir(parents=True, exist_ok=True)
    if not (fdir / f"{base}.md").exists():
        return base
    n = 2
    while (fdir / f"{base}_{n}.md").exists():
        n += 1
    return f"{base}_{n}"


def next_wiki_id(kb: Path, slug: str) -> str:
    """Generate kn_<yyyy>_<slug>, appending _2/_3 on collision."""
    year = date.today().year
    base = f"kn_{year}_{slug}"
    wdir = kb / "wiki"
    wdir.mkdir(parents=True, exist_ok=True)
    if not (wdir / f"{base}.md").exists():
        return base
    n = 2
    while (wdir / f"{base}_{n}.md").exists():
        n += 1
    return f"{base}_{n}"


def load_all_wiki(kb: Path) -> list[MdDoc]:
    wdir = kb / "wiki"
    if not wdir.exists():
        return []
    return [MdDoc.load(p) for p in sorted(wdir.glob("*.md"))]


def load_all_frontier(kb: Path) -> list[MdDoc]:
    fdir = kb / "frontier"
    if not fdir.exists():
        return []
    return [MdDoc.load(p) for p in sorted(fdir.glob("*.md"))]


def load_all_questions(kb: Path) -> list[MdDoc]:
    qdir = kb / "questions"
    if not qdir.exists():
        return []
    return [MdDoc.load(p) for p in sorted(qdir.glob("*.md"))]


def load_all_interviews(kb: Path) -> list[tuple[Path, dict]]:
    """Returns (interview_dir, meta_dict) pairs."""
    out = []
    idir = kb / "interviews"
    if not idir.exists():
        return out
    for d in sorted(idir.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / "meta.yaml"
        if not meta_path.exists():
            continue
        with meta_path.open("r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
        out.append((d, meta))
    return out


def find_wiki_by_title_or_slug(kb: Path, hint: str) -> MdDoc | None:
    """Best-effort lookup of wiki entries by title or id slug."""
    hint_norm = hint.strip().lower()
    for doc in load_all_wiki(kb):
        title = str(doc.frontmatter.get("title", "")).strip().lower()
        kid = str(doc.frontmatter.get("id", "")).strip().lower()
        if hint_norm == title or hint_norm == kid:
            return doc
        if hint_norm in title or title in hint_norm:
            return doc
    return None


def find_frontier_by_title_or_slug(kb: Path, hint: str) -> MdDoc | None:
    """Best-effort lookup of frontier entries by title or id slug."""
    hint_norm = hint.strip().lower()
    for doc in load_all_frontier(kb):
        title = str(doc.frontmatter.get("title", "")).strip().lower()
        fid = str(doc.frontmatter.get("id", "")).strip().lower()
        if hint_norm == title or hint_norm == fid:
            return doc
        if hint_norm in title or title in hint_norm:
            return doc
    return None


def dedupe_keep_order(items: Iterable[Any]) -> list:
    seen = set()
    out = []
    for x in items:
        key = json.dumps(x, sort_keys=True) if not isinstance(x, (str, int, float)) else x
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


# ---------------------------------------------------------------------------
# Backward-compat aliases — interview-review scripts still import these names
# ---------------------------------------------------------------------------
def load_all_knowledge(kb: Path) -> list[MdDoc]:
    return load_all_wiki(kb)


def find_knowledge_by_title_or_slug(kb: Path, hint: str) -> MdDoc | None:
    return find_wiki_by_title_or_slug(kb, hint)
