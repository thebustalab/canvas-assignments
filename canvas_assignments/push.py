"""CSV -> Canvas. Creates and updates assignments; never deletes anything.

Two rules make this safe to re-run against a live course, and they are the
whole point of the tool:

1. **A blank cell is never pushed.** A row filled in only as far as its name and
   a new due date re-dates that assignment and touches nothing else -- the
   description, the points, the LTI link all survive. To clear a field on
   purpose, write the literal word ``NONE``.
2. **An assignment that already has student submissions is skipped**, unless
   ``--force``. This is what stops a mid-semester re-run from disturbing work
   students have already handed in.
"""

from __future__ import annotations

import csv
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

import requests

from .api import TIMEOUT, auth_headers, course_base, fetch_all
from .columns import CLEAR_SENTINEL, LIST_FIELDS, TIME_FIELDS

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9 only
    ZoneInfo = None  # type: ignore


def truthy(value: str) -> bool:
    return value.strip().lower() in {"true", "t", "yes", "y", "1"}


def to_utc_iso(value: str, tz_name: str) -> str:
    """'YYYY-MM-DD HH:MM' local -> Canvas UTC ISO. Full ISO strings pass through."""
    value = value.strip()
    if not value:
        return ""
    if value.endswith("Z") or re.search(r"[+-]\d{2}:\d{2}$", value):
        return value
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            naive = datetime.strptime(value, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Could not parse a date/time from {value!r}")
    if ZoneInfo is None:  # pragma: no cover
        return naive.isoformat()
    local = naive.replace(tzinfo=ZoneInfo(tz_name))
    return local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def markdown_to_html(text: str) -> str:
    """Convert Markdown if the optional package is installed; otherwise pass through."""
    try:
        import markdown  # type: ignore
    except ImportError:
        return text
    return markdown.markdown(text, extensions=["extra", "sane_lists"])


def build_payload(row: Dict[str, str], csv_dir: str, tz_name: str) -> Dict[str, object]:
    """Turn one CSV row into a Canvas assignment payload. Blank cells are omitted."""
    payload: Dict[str, object] = {}

    def cell(key: str) -> Optional[str]:
        raw = (row.get(key) or "").strip()
        return raw or None

    if cell("name"):
        payload["name"] = row["name"].strip()

    if cell("points_possible"):
        payload["points_possible"] = float(row["points_possible"])

    for field in TIME_FIELDS:
        value = cell(field)
        if value == CLEAR_SENTINEL:
            payload[field] = ""
        elif value:
            payload[field] = to_utc_iso(value, tz_name)

    # external_tool_new_tab is deliberately absent here -- it is folded into
    # external_tool_tag_attributes below, where Canvas expects it.
    for field in ("published", "omit_from_final_grade"):
        if cell(field):
            payload[field] = truthy(row[field])

    for field in LIST_FIELDS:
        value = cell(field)
        if value == CLEAR_SENTINEL:
            payload[field] = []
        elif value:
            payload[field] = [part.strip() for part in value.split(";") if part.strip()]

    if cell("external_tool_url"):
        payload["external_tool_tag_attributes"] = {
            "url": row["external_tool_url"].strip(),
            "new_tab": truthy(row.get("external_tool_new_tab") or "true"),
        }

    description = None
    if cell("description_file"):
        path = os.path.join(csv_dir, row["description_file"].strip())
        with open(path, "r", encoding="utf-8") as handle:
            description = handle.read()
        if path.lower().endswith((".md", ".markdown")):
            description = markdown_to_html(description)
    elif cell("description"):
        description = row["description"]
    if description is not None:
        payload["description"] = "" if description.strip() == CLEAR_SENTINEL else description

    return payload


def flatten(payload: Dict[str, object]) -> List[tuple]:
    """Canvas wants assignment[key] form-encoding, with [] for lists and nested LTI attrs."""
    fields: List[tuple] = []
    for key, value in payload.items():
        if isinstance(value, list):
            if not value:
                fields.append((f"assignment[{key}][]", ""))
            for item in value:
                fields.append((f"assignment[{key}][]", str(item)))
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                rendered = str(sub_value).lower() if isinstance(sub_value, bool) else str(sub_value)
                fields.append((f"assignment[{key}][{sub_key}]", rendered))
        elif isinstance(value, bool):
            fields.append((f"assignment[{key}]", "true" if value else "false"))
        else:
            fields.append((f"assignment[{key}]", str(value)))
    return fields


def read_rows(csv_path: str, only: Optional[List[str]] = None) -> List[Dict[str, str]]:
    """Read the CSV, dropping nameless rows and applying any --only filters."""
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if (row.get("name") or "").strip()]
    if only:
        rows = [r for r in rows if any(sub.lower() in r["name"].lower() for sub in only)]
    return rows


def run(csv_path: str, course_id: str, domain: str, token: str, tz_name: str,
        apply: bool = False, force: bool = False, only: Optional[List[str]] = None) -> int:
    headers = auth_headers(token)
    base = course_base(domain, course_id)
    csv_dir = os.path.dirname(os.path.abspath(csv_path))

    rows = read_rows(csv_path, only)
    if not rows:
        print("No rows to process.")
        return 0

    existing = fetch_all(f"{base}/assignments?per_page=100", headers)
    by_id = {a["id"]: a for a in existing}
    by_name = {(a.get("name") or "").strip(): a for a in existing}

    groups: Dict[str, int] = {
        (g.get("name") or "").strip(): g["id"]
        for g in fetch_all(f"{base}/assignment_groups?per_page=100", headers)
    }

    mode = "APPLY" if apply else "DRY RUN"
    print(f"=== {mode}: {len(rows)} row(s) against course {course_id} ===\n")

    created = updated = skipped = 0
    for row in rows:
        name = row["name"].strip()
        target = None
        if (row.get("canvas_id") or "").strip():
            target = by_id.get(int(row["canvas_id"].strip()))
        if target is None:
            target = by_name.get(name)

        try:
            payload = build_payload(row, csv_dir, tz_name)
        except (ValueError, OSError) as exc:
            print(f"  !! {name}: {exc}")
            skipped += 1
            continue

        group_name = (row.get("assignment_group") or "").strip()
        if group_name:
            group_id = groups.get(group_name)
            if group_id is None:
                if apply:
                    resp = requests.post(f"{base}/assignment_groups", headers=headers,
                                         data={"name": group_name}, timeout=TIMEOUT)
                    resp.raise_for_status()
                    group_id = resp.json()["id"]
                    groups[group_name] = group_id
                    print(f"  + created assignment group {group_name!r}")
                else:
                    print(f"  + would create assignment group {group_name!r}")
            if group_id is not None:
                payload["assignment_group_id"] = group_id

        touched = ", ".join(sorted(payload.keys()))

        if target is None:
            print(f"  + CREATE  {name}\n      fields: {touched}")
            created += 1
            if apply:
                resp = requests.post(f"{base}/assignments", headers=headers,
                                     data=flatten(payload), timeout=TIMEOUT)
                resp.raise_for_status()
                print(f"      -> id {resp.json().get('id')}")
            continue

        if target.get("has_submitted_submissions") and not force:
            print(f"  ~ SKIP    {name} (id {target['id']}) -- has student submissions; "
                  f"re-run with --force to update anyway")
            skipped += 1
            continue

        print(f"  * UPDATE  {name} (id {target['id']})\n      fields: {touched}")
        updated += 1
        if apply:
            resp = requests.put(f"{base}/assignments/{target['id']}", headers=headers,
                                data=flatten(payload), timeout=TIMEOUT)
            resp.raise_for_status()

    print(f"\n{created} to create, {updated} to update, {skipped} skipped.")
    if not apply:
        print("Dry run -- nothing was written. Re-run with --apply to go live.")
    return 0
