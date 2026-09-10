"""Command-line entry point: ``canvas-assignments pull`` and ``canvas-assignments push``."""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__

EPILOG = """\
the round trip:

  canvas-assignments pull  course.csv --course-id 12345 --domain canvas.example.edu
  (edit course.csv, and the HTML files in assignment_descriptions/, by hand)
  canvas-assignments push  course.csv --course-id 12345 --domain canvas.example.edu
  canvas-assignments push  course.csv --course-id 12345 --domain canvas.example.edu --apply

push is a dry run until you pass --apply. A blank cell is never pushed; write the
literal word NONE to clear a field. Assignments with student submissions are
skipped unless you pass --force.

Auth: set CANVAS_TOKEN in your environment, or pass --token.
"""


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--course-id", required=True, help="numeric Canvas course id")
    parser.add_argument("--domain", required=True,
                        help="your Canvas hostname, e.g. canvas.example.edu")
    parser.add_argument("--token", default=os.environ.get("CANVAS_TOKEN"),
                        help="Canvas API token (default: $CANVAS_TOKEN)")
    parser.add_argument("--timezone", default="UTC",
                        help="timezone the date columns are written and read in "
                             "(IANA name, e.g. America/Chicago; default UTC)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="canvas-assignments",
        description="Round-trip Canvas LMS assignments through a CSV.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version",
                        version=f"canvas-assignments {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    pull = sub.add_parser("pull", help="Canvas -> CSV (read-only)")
    pull.add_argument("csv_path", help="path to write the assignments CSV to")
    _add_common(pull)
    pull.add_argument("--descriptions-dir", default=None,
                      help="directory for per-assignment description HTML "
                           "(default: <csv dir>/assignment_descriptions)")
    pull.add_argument("--inline-descriptions", action="store_true",
                      help="put description HTML in the CSV cell instead of separate files")

    push = sub.add_parser("push", help="CSV -> Canvas (dry run unless --apply)")
    push.add_argument("csv_path", help="the assignments CSV to read")
    _add_common(push)
    push.add_argument("--apply", action="store_true", help="actually write to Canvas")
    push.add_argument("--force", action="store_true",
                      help="update even assignments that already have student submissions")
    push.add_argument("--only", action="append", default=[],
                      help="only process rows whose name contains this string (repeatable)")

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if not args.token:
        print("Set CANVAS_TOKEN in your environment, or pass --token.", file=sys.stderr)
        return 2

    if args.command == "pull":
        from .pull import run
        return run(args.csv_path, args.course_id, args.domain, args.token, args.timezone,
                   descriptions_dir=args.descriptions_dir,
                   inline_descriptions=args.inline_descriptions)

    from .push import run
    return run(args.csv_path, args.course_id, args.domain, args.token, args.timezone,
               apply=args.apply, force=args.force, only=args.only)


if __name__ == "__main__":
    raise SystemExit(main())
