"""Row-building tests for the pull direction. Fully offline -- no network."""

from canvas_assignments import pull
from canvas_assignments.columns import COLUMNS

TZ = "America/Chicago"


def test_utc_timestamp_renders_as_local():
    assert pull.to_local("2026-09-05T04:59:00Z", TZ) == "2026-09-04 23:59"


def test_empty_timestamp_stays_empty():
    assert pull.to_local(None, TZ) == ""
    assert pull.to_local("", TZ) == ""


def test_unparseable_timestamp_passes_through():
    assert pull.to_local("not a date", TZ) == "not a date"


def test_slugify_makes_a_safe_filename():
    assert pull.slugify("Problem Set 1: Kinetics!") == "problem_set_1_kinetics"
    assert pull.slugify("***") == "assignment"


def test_assignment_to_row_covers_every_column():
    item = {
        "id": 7,
        "name": "Problem set 1",
        "assignment_group_id": 2,
        "points_possible": 10,
        "due_at": "2026-09-05T04:59:00Z",
        "published": True,
        "submission_types": ["online_upload"],
        "allowed_extensions": ["pdf"],
        "external_tool_tag_attributes": {"url": "https://tool.example.com/lti", "new_tab": True},
    }
    row = pull.assignment_to_row(item, {2: "Problem sets"}, TZ)
    assert set(row) == set(COLUMNS)
    assert row["assignment_group"] == "Problem sets"
    assert row["due_at"] == "2026-09-04 23:59"
    assert row["published"] == "TRUE"
    assert row["submission_types"] == "online_upload"
    assert row["external_tool_url"] == "https://tool.example.com/lti"


def test_round_trip_of_a_dated_row_is_stable():
    """pull -> push -> pull must not drift the timestamp."""
    from canvas_assignments import push
    row = pull.assignment_to_row({"id": 1, "name": "x", "due_at": "2026-09-05T04:59:00Z"}, {}, TZ)
    assert push.to_utc_iso(row["due_at"], TZ) == "2026-09-05T04:59:00Z"
