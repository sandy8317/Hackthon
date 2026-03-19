# CLAUDE.md

## Project Overview
Web hosting customer support ticketing system. Customers submit tickets for website problems; staff view and manage them.

**Stack:** Python + Flask + SQLite (no ORM)

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The database (`tickets.db`) is created automatically on first run via `init_db()`.

## Running the App
Always use the project venv:
```bash
.venv/bin/python app.py
```

## Project Structure
```
app.py               # All routes, DB helpers, validation logic
schema.sql           # SQLite DDL — edit this to change the schema
requirements.txt     # Python dependencies
static/style.css     # All styles
templates/
  base.html          # Shared layout (nav, flash messages, footer)
  submit.html        # Customer ticket submission form
  submit_success.html
  ticket_list.html   # Paginated staff view with severity filter
  ticket_detail.html
```

## Key Conventions

### Database
- Use `get_db()` / `close_db()` via Flask `g` — never open raw connections in routes
- `sqlite3.Row` row factory is set — access columns by name in templates
- Schema changes go in `schema.sql`; call `init_db()` to apply

### Routes
| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/` | Customer ticket submission |
| GET | `/success/<id>` | Post-submit confirmation (POST-Redirect-GET) |
| GET | `/tickets` | Staff list — supports `?page=N&severity=X` |
| GET | `/tickets/<id>` | Staff detail view |

### Validation
Server-side only, in `validate_ticket()` in `app.py`. On failure, re-render the form with `errors` dict and `form_data=request.form` to preserve user input.

### Severity Levels
Defined in `SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]`. Used in validation, templates, and CSS badge classes (`.badge-Low`, `.badge-Medium`, etc.).

### Status
Defined in `STATUS_LEVELS = ["Open", "In Progress", "Pending", "Closed"]`. Defaults to `"Open"` on ticket submission. CSS badge classes use hyphens for spaces (e.g. `.badge-In-Progress`).

### Pagination
20 tickets per page (`PER_PAGE = 20`). Controlled by `?page=N` query param in `/tickets`.

## Dependencies
- `flask>=3.0` — only direct dependency; SQLite is part of the Python standard library

## Git
- `.venv/`, `tickets.db`, and `__pycache__/` are gitignored — never commit these
- Remote: `git@github.com:uchicago-its-linux/hackathon.git`
