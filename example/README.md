# Example CSV

`course.csv` is a hand-written example of the format — a fake four-assignment
course, not an export from a real one. Use it to see the column layout, or as a
starting point if you are building a course from scratch rather than editing an
existing one.

Things it demonstrates:

- **A blank `canvas_id`** (the midterm proposal) — the row is matched on `name`,
  and created if no assignment by that name exists.
- **`assignment_group` by name** — `Projects` is created if the course has no
  group by that name.
- **Two ways to write a description** — a path in `description_file` (a
  relative path, resolved from the CSV's own directory) for anything long, or
  inline text in the `description` cell for a one-liner.
- **Semicolon-separated lists** — `pdf;docx` in `allowed_extensions`.
- **Mostly blank rows** — problem set 2 fills in only what it changes.

Dry-run it against a real course to see what it would do:

```bash
canvas-assignments push example/course.csv \
  --course-id 12345 --domain canvas.example.edu
```
