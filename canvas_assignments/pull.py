"""Canvas -> CSV. Read-only: this direction never writes to Canvas."""

from __future__ import annotations

import csv
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from .api import auth_headers, course_base, fetch_all
from .columns import COLUMNS

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9 only
    ZoneInfo = None  # type: ignore


def to_local(value: Optional[str], tz_name: str) -> str:
    """Render a Canvas UTC timestamp as local 'YYYY-MM-DD HH:MM' for human editing."""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if ZoneInfo is None:  # pragma: no cover
        return value
    return dt.astimezone(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M")


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "assignment"


def assignment_to_row(item: Dict, group_names: Dict[int, str], tz_name: str) -> Dict[str, str]:
    """Turn one Canvas assignment into a CSV row (description handled by the caller)."""
    tool = item.get("external_tool_tag_attributes") or {}
    points = item.get("points_possible")
    return {
        "canvas_id": item.get("id") or "",
        "name": item.get("name") or "",
        "assignment_group": group_names.get(item.get("assignment_group_id"), ""),
        "points_possible": points if points is not None else "",
        "due_at": to_local(item.get("due_at"), tz_name),
        "unlock_at": to_local(item.get("unlock_at"), tz_name),
        "lock_at": to_local(item.get("lock_at"), tz_name),
        "published": "TRUE" if item.get("published") else "FALSE",
        "submission_types": ";".join(item.get("submission_types") or []),
        "allowed_extensions": ";".join(item.get("allowed_extensions") or []),
        "external_tool_url": tool.get("url") or "",
        "external_tool_new_tab": "TRUE" if tool.get("new_tab") else "",
        "omit_from_final_grade": "TRUE" if item.get("omit_from_final_grade") else "",
        "description_file": "",
        "description": "",
    }


def run(out_csv: str, course_id: str, domain: str, token: str, tz_name: str,
        descriptions_dir: Optional[str] = None, inline_descriptions: bool = False) -> int:
    headers = auth_headers(token)
    base = course_base(domain, course_id)

    group_names: Dict[int, str] = {
        g["id"]: (g.get("name") or "")
        for g in fetch_all(f"{base}/assignment_groups?per_page=100", headers)
    }
    assignments = fetch_all(f"{base}/assignments?per_page=100", headers)

    out_dir = os.path.dirname(os.path.abspath(out_csv))
    desc_dir = descriptions_dir or os.path.join(out_dir, "assignment_descriptions")
    if not inline_descriptions:
        os.makedirs(desc_dir, exist_ok=True)

    rows: List[Dict[str, str]] = []
    for item in sorted(assignments, key=lambda a: (a.get("name") or "")):
        row = assignment_to_row(item, group_names, tz_name)
        description = item.get("description") or ""
        if description and not inline_descriptions:
            # Descriptions are long HTML; a spreadsheet cell is the wrong home for
            # them, so each goes to its own file and the CSV carries the path.
            fname = f"{slugify(row['name'])}.html"
            with open(os.path.join(desc_dir, fname), "w", encoding="utf-8") as handle:
                handle.write(description)
            row["description_file"] = os.path.relpath(os.path.join(desc_dir, fname), out_dir)
        else:
            row["description"] = description
        rows.append(row)

    with open(out_csv, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} assignments to {out_csv}")
    if not inline_descriptions:
        print(f"Descriptions written to {desc_dir}/")
    return 0
