#!/usr/bin/env python3
"""Create a new interview directory with meta.yaml."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from common import kb_root, slugify, today_iso  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--company", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--round", required=True)
    p.add_argument("--date", default=today_iso())
    p.add_argument("--duration", type=int, default=60)
    p.add_argument("--rating", type=int, default=3)
    p.add_argument("--interviewer-style", default="")
    args = p.parse_args()

    kb = kb_root()
    iv_root = kb / "interviews"
    iv_root.mkdir(parents=True, exist_ok=True)

    # id = iv_<yyyy>_<mm>_<company-slug>_<n>
    yyyy, mm, _ = args.date.split("-")
    company_slug = slugify(args.company)
    base = f"iv_{yyyy}_{mm}_{company_slug}"
    # find next number suffix
    existing = [d.name for d in iv_root.iterdir() if d.is_dir() and d.name.startswith(base)]
    nums = []
    for name in existing:
        m = re.match(re.escape(base) + r"_(\d+)$", name)
        if m:
            nums.append(int(m.group(1)))
    n = (max(nums) + 1) if nums else 1
    iv_id = f"{base}_{n}"

    iv_dir = iv_root / iv_id
    iv_dir.mkdir()

    meta = {
        "id": iv_id,
        "company": args.company,
        "role": args.role,
        "round": args.round,
        "date": args.date,
        "duration_min": args.duration,
        "interviewer_style": args.interviewer_style,
        "outcome": "pending",
        "self_overall_rating": args.rating,
        "created": today_iso(),
    }
    (iv_dir / "meta.yaml").write_text(
        yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (iv_dir / "raw.md").write_text("", encoding="utf-8")  # will be filled by caller

    print(iv_id)
    print(str(iv_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
