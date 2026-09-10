# canvas-assignments

Pull a Canvas course's assignments into a CSV. Edit the CSV. Push it back.

Rolling a course forward a year means changing forty due dates. Doing that
through the Canvas web interface is forty page loads, forty date pickers and
forty saves. This does it as one spreadsheet column and one command.

```bash
# Canvas -> CSV (read-only)
canvas-assignments pull course.csv --course-id 12345 --domain canvas.example.edu

# ... edit course.csv in a spreadsheet ...

# CSV -> Canvas (dry run: prints what it would do, writes nothing)
canvas-assignments push course.csv --course-id 12345 --domain canvas.example.edu

# ... read the dry run, then go live
canvas-assignments push course.csv --course-id 12345 --domain canvas.example.edu --apply
```

Both directions read the same column definition, so the round trip is lossless.

## The two rules that make it safe to re-run

These matter more than anything else here. A tool that writes back to a live
course can do real damage, and these are what stop it.

**A blank cell is never pushed.** Only the cells you actually fill are sent to
Canvas. A row filled in as far as its name and a new due date re-dates that
assignment and touches nothing else — the description, the points, the LTI
link all survive untouched. This is what lets you keep a half-empty CSV around
as a re-dating sheet, and what makes a re-run harmless.

To clear a field on purpose, write the literal word `NONE` in the cell. Erasing
something is thus always deliberate and never a side effect of an empty cell.

**An assignment with student submissions is skipped.** Before updating, the
push checks whether anyone has handed anything in. If they have, it says so and
moves on. Pass `--force` to override, once you have thought about it. This is
what stops a mid-semester re-run from disturbing work students have already
submitted.

On top of those: `push` is a dry run unless you pass `--apply`, and nothing in
this tool ever deletes anything.

## Install

```bash
pip install git+https://github.com/thebustalab/canvas-assignments.git
```

Python 3.9+. The only required dependency is `requests`. Install
`canvas-assignments[markdown]` if you want to write descriptions in Markdown.

## Auth

Make an API token in Canvas under **Account → Settings → New Access Token**,
then put it in your environment:

```bash
export CANVAS_TOKEN="…"
```

The tool reads `CANVAS_TOKEN`, or takes `--token`. It is never written to disk
and never hard-coded — treat it like a password, because it can do anything to
your courses that you can.

Your course id is the number in the course URL:
`https://canvas.example.edu/courses/`**`12345`**.

## The CSV

One row per assignment. See `example/course.csv` for a worked example.

| Column | Meaning |
|---|---|
| `canvas_id` | Existing assignment id. Blank → match on `name`, create if absent. |
| `name` | Assignment title, and the match key when `canvas_id` is blank. Required. |
| `assignment_group` | Group *name*; created if the course has no group by that name. |
| `points_possible` | Number. |
| `due_at`, `unlock_at`, `lock_at` | `YYYY-MM-DD HH:MM` in `--timezone`, or a full ISO string. |
| `published` | `TRUE` / `FALSE`. |
| `submission_types` | Semicolon-separated: `online_upload;online_text_entry;external_tool`… |
| `allowed_extensions` | Semicolon-separated, e.g. `pdf;docx`. |
| `external_tool_url` | LTI launch url, for `submission_types=external_tool`. |
| `external_tool_new_tab` | `TRUE` / `FALSE`. |
| `omit_from_final_grade` | `TRUE` / `FALSE`. |
| `description_file` | Path to an HTML or Markdown file, relative to the CSV. |
| `description` | Inline description, used when `description_file` is blank. |

Descriptions are long HTML, which spreadsheets handle badly, so `pull` writes
each one to its own file under `assignment_descriptions/` and puts the path in
`description_file`. Pass `--inline-descriptions` if you would rather have them
in the cell.

### Timezones

`--timezone` takes an IANA name (`America/Chicago`, `Europe/London`) and
defaults to `UTC`. It governs both directions: `pull` writes local times,
`push` reads them back and converts to UTC for Canvas. Daylight saving is
handled by the zone database, so a 23:59 deadline in September and one in
December both land at 23:59 local.

## Useful flags

| Flag | |
|---|---|
| `--apply` | On `push`: actually write. Without it you get a dry run. |
| `--force` | On `push`: update assignments that have student submissions. |
| `--only SUBSTR` | On `push`: only rows whose name contains this. Repeatable. |
| `--inline-descriptions` | On `pull`: descriptions in the CSV, not separate files. |
| `--descriptions-dir DIR` | On `pull`: where the description files go. |

## What it does not do

Assignments only — not pages, files, modules, or quiz questions. Classic
Quizzes and New Quizzes have their own APIs and are out of scope. It creates
and updates; it never deletes.

## Tests

```bash
pip install -e '.[test]'
pytest -q
```

Everything is offline. No test touches Canvas.

## Licence

MIT.
