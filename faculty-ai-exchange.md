---
title: Editing a Canvas course as a spreadsheet
summary: Pull every assignment in a Canvas course into a CSV, edit the dates in a spreadsheet, and push them back in one command instead of forty page loads.
faculty: Dr. Lucas Busta
department: Chemistry and Biochemistry, University of Minnesota Duluth
department_id: chemistry-and-biochemistry
audience: Faculty who maintain their own Canvas courses and roll them forward each term
use_case: Course administration
tools:
  - Claude Code
  - Canvas LMS REST API
tags:
  - Teaching
  - Course administration
  - Canvas LMS
  - CSV
  - Python
image: /assets/images/canvas-assignments.jpg
repository_url: https://github.com/thebustalab/canvas-assignments
---

## What faculty used it for

Rolling a course forward to a new term means changing every due date in it. In the Canvas web interface that is one page load, one date picker, and one save per assignment, many times over, with no way to see the whole schedule at once and no way to check your work afterwards except by clicking through it all again. This tool turns that click fest into a spreadsheet. One command pulls every assignment in a course into a CSV (name, group, points, due/unlock/lock dates, submission types, published state, description). You sort by date, see the whole term's layout in one view, drag the dates forward, and push the file back.

The AI assistant did the work that makes this sort of tool tedious to write by hand: reading the Canvas API docs, handling pagination, getting the form-encoding right for nested LTI attributes, and converting local times to UTC correctly across a daylight-saving boundary.

## Why it was useful

The time saving provided by this tool is real, but not out of the ordinary. The part of this tool that is worth passing on is the safety design. Part way through a semester, a course is not a blank slate. Students have submitted work, the gradebook is live, and a careless bulk write can do damage that is tedious or impossible to undo. Two rules emerged from thinking about that, and both are worth stealing from this tool for whatever you build:

**A blank cell is never pushed.** Only the cells you actually fill get sent. A row filled in as far as its name and a new due date re-dates that assignment and touches nothing else: the description, the points, and the LTI link all survive. This is what makes the tool re-runnable: you can keep a half-empty CSV around as a re-dating sheet without it silently blanking everything you left out (e.g. assignment content, questions, etc.). To clear a field on purpose you write the literal word `NONE`, so erasing is always deliberate and never a side effect of an empty cell.

**An assignment with student submissions is skipped.** Before updating anything, the tool checks whether work has been handed in, and if it has, it says so and moves on. `--force` overrides it, in case that is needed.

On top of those: the push is a dry run unless you pass `--apply`, and nothing in the tool ever deletes anything. The dry run prints exactly which fields it would touch on which assignments, which is also the fastest way to catch a spreadsheet mistake before it reaches your students.

The general lesson is that with an AI assistant the code is the cheap part. It will happily write you a bulk-update script in a few minutes. Deciding what the script should refuse to do is the part that needs a human who knows what a half-graded course looks like in week nine. This tool also frees up faculty time (i.e. less time managing Canvas) which can then be repurposed for improving course materials, assignment design, and so forth.

## Materials to adapt

- **The tool**: <https://github.com/thebustalab/canvas-assignments>. Python 3.9+, MIT licensed, one dependency. `pip install git+https://github.com/thebustalab/canvas-assignments.git`
- **A Canvas API token**, from Account → Settings → New Access Token, in the `CANVAS_TOKEN` environment variable. Treat it like your Canvas password: a user access token is not scoped to a course or to this tool, but grants the whole API as you — every course, the gradebook, your files and your inbox — so anyone holding it can read student data you have access to. Pass it by environment variable rather than on the command line, where it would land in your shell history.
- **Your course id**, the number in the course URL.
- **An example CSV** is in `example/` in the repo: a fake four-assignment course showing the column layout, so you can see the format without touching a real course.
- **Nothing institution-specific.** Your Canvas hostname and timezone are command-line flags. It should work against any Canvas instance.