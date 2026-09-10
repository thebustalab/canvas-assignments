"""Payload-building tests for the push direction. Fully offline -- no network."""

import os
import tempfile

import pytest

from canvas_assignments import push
from canvas_assignments.columns import COLUMNS

TZ = "America/Chicago"


def row(**overrides):
    base = {col: "" for col in COLUMNS}
    base["name"] = "Problem set 1"
    base.update(overrides)
    return base


class TestTimeParsing:
    def test_local_datetime_becomes_utc(self):
        # 2026-09-04 is CDT (UTC-5), so 23:59 local -> 04:59 UTC the next day.
        assert push.to_utc_iso("2026-09-04 23:59", TZ) == "2026-09-05T04:59:00Z"

    def test_winter_date_uses_standard_time(self):
        # 2026-12-11 is CST (UTC-6), so 23:59 local -> 05:59 UTC the next day.
        assert push.to_utc_iso("2026-12-11 23:59", TZ) == "2026-12-12T05:59:00Z"

    def test_full_iso_passes_through(self):
        assert push.to_utc_iso("2026-09-05T04:59:00Z", TZ) == "2026-09-05T04:59:00Z"

    def test_bare_date_is_accepted(self):
        assert push.to_utc_iso("2026-09-05", TZ) == "2026-09-05T05:00:00Z"

    def test_unparseable_raises(self):
        with pytest.raises(ValueError):
            push.to_utc_iso("next tuesday", TZ)


class TestBuildPayload:
    def test_blank_cells_are_omitted(self):
        # The safety rule: a half-filled row touches only the fields it fills.
        payload = push.build_payload(row(points_possible="4"), ".", TZ)
        assert set(payload) == {"name", "points_possible"}
        assert "description" not in payload
        assert "submission_types" not in payload

    def test_only_the_dated_field_is_pushed(self):
        payload = push.build_payload(row(due_at="2026-09-04 23:59"), ".", TZ)
        assert set(payload) == {"name", "due_at"}

    def test_lists_split_on_semicolons(self):
        payload = push.build_payload(
            row(submission_types="online_upload;online_text_entry", allowed_extensions="pdf"),
            ".", TZ)
        assert payload["submission_types"] == ["online_upload", "online_text_entry"]
        assert payload["allowed_extensions"] == ["pdf"]

    def test_none_sentinel_clears_a_field(self):
        payload = push.build_payload(row(lock_at="NONE", allowed_extensions="NONE"), ".", TZ)
        assert payload["lock_at"] == ""
        assert payload["allowed_extensions"] == []

    def test_booleans_are_parsed(self):
        payload = push.build_payload(row(published="TRUE", omit_from_final_grade="no"), ".", TZ)
        assert payload["published"] is True
        assert payload["omit_from_final_grade"] is False

    def test_external_tool_attrs_are_nested(self):
        payload = push.build_payload(
            row(submission_types="external_tool",
                external_tool_url="https://tool.example.com/lti",
                external_tool_new_tab="TRUE"),
            ".", TZ)
        assert payload["external_tool_tag_attributes"] == {
            "url": "https://tool.example.com/lti", "new_tab": True}
        assert "external_tool_new_tab" not in payload

    def test_description_file_is_read_relative_to_the_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "desc.html"), "w", encoding="utf-8") as handle:
                handle.write("<p>Read chapter 3.</p>")
            payload = push.build_payload(row(description_file="desc.html"), tmp, TZ)
        assert payload["description"] == "<p>Read chapter 3.</p>"

    def test_description_file_wins_over_inline_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "desc.html"), "w", encoding="utf-8") as handle:
                handle.write("<p>from file</p>")
            payload = push.build_payload(
                row(description_file="desc.html", description="inline"), tmp, TZ)
        assert payload["description"] == "<p>from file</p>"

    def test_missing_description_file_raises(self):
        with pytest.raises(OSError):
            push.build_payload(row(description_file="nope.html"), ".", TZ)


class TestFlatten:
    def test_form_encoding_shapes(self):
        fields = push.flatten({
            "name": "x",
            "published": True,
            "submission_types": ["online_upload"],
            "external_tool_tag_attributes": {"url": "https://e", "new_tab": True},
        })
        assert ("assignment[name]", "x") in fields
        assert ("assignment[published]", "true") in fields
        assert ("assignment[submission_types][]", "online_upload") in fields
        assert ("assignment[external_tool_tag_attributes][url]", "https://e") in fields
        assert ("assignment[external_tool_tag_attributes][new_tab]", "true") in fields

    def test_empty_list_clears(self):
        assert push.flatten({"allowed_extensions": []}) == [("assignment[allowed_extensions][]", "")]


class TestReadRows:
    def _write(self, tmp, body):
        path = os.path.join(tmp, "a.csv")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        return path

    def test_nameless_rows_are_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "name,points_possible\nKeep,3\n,9\n")
            rows = push.read_rows(path)
        assert [r["name"] for r in rows] == ["Keep"]

    def test_only_filters_by_substring(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "name\nQuiz 1\nProblem set 1\nQuiz 2\n")
            rows = push.read_rows(path, only=["quiz"])
        assert [r["name"] for r in rows] == ["Quiz 1", "Quiz 2"]
