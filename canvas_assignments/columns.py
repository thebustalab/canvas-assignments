"""The CSV contract shared by the pull and push directions.

Both directions import this module, so the round trip is lossless by
construction: there is one definition of the column order, not two that have to
be kept in step.
"""

from __future__ import annotations

#: Column order of the assignments CSV, written by ``pull`` and read by ``push``.
COLUMNS = [
    "canvas_id",
    "name",
    "assignment_group",
    "points_possible",
    "due_at",
    "unlock_at",
    "lock_at",
    "published",
    "submission_types",
    "allowed_extensions",
    "external_tool_url",
    "external_tool_new_tab",
    "omit_from_final_grade",
    "description_file",
    "description",
]

#: Columns holding a date/time, written in local time for human editing.
TIME_FIELDS = ("due_at", "unlock_at", "lock_at")

#: Columns holding a semicolon-separated list.
LIST_FIELDS = ("submission_types", "allowed_extensions")

#: Columns holding TRUE/FALSE.
BOOL_FIELDS = ("published", "external_tool_new_tab", "omit_from_final_grade")

#: Write this literal in a cell to clear the field. A *blank* cell means
#: "leave whatever Canvas already has" — see the README's safety rules.
CLEAR_SENTINEL = "NONE"
