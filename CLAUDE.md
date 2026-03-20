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
| GET | `/api/tickets/<id>` | JSON ticket detail |
| PATCH | `/api/tickets/<id>/status` | Update ticket status (JSON API) |

### API Usage

**Get a ticket:**
```bash
curl http://localhost:5000/api/tickets/1
```

**Update ticket status:**
```bash
curl -X PATCH http://localhost:5000/api/tickets/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "In Progress"}'
```

Valid status values: `Open`, `In Progress`, `Pending`, `Closed`.

API responses use HTTP `404` for unknown ticket IDs and `400` for invalid/missing fields. Flask 3.x serializes returned dicts as `application/json` automatically — no `jsonify()` needed.

### Validation
Server-side only, in `validate_ticket()` in `app.py`. On failure, re-render the form with `errors` dict and `form_data=request.form` to preserve user input.

### Severity Levels
Defined in `SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]`. Used in validation, templates, and CSS badge classes (`.badge-Low`, `.badge-Medium`, etc.).

### Status
Defined in `STATUS_LEVELS = ["Open", "In Progress", "Pending", "Closed"]`. Defaults to `"Open"` on ticket submission. CSS badge classes use hyphens for spaces (e.g. `.badge-In-Progress`).

### Pagination
20 tickets per page (`PER_PAGE = 20`). Controlled by `?page=N` query param in `/tickets`.

## Accessibility

The UI adheres to strict WCAG 2.1 AA standards throughout all templates:

- **Semantic HTML:** `<main>`, `<nav>`, `<header>`, `<footer>` landmarks used consistently; `lang="en"` on `<html>`
- **ARIA labels & roles:** All forms have `aria-label`; nav menus use `role="menu"` / `role="menuitem"` with `aria-haspopup`, `aria-expanded`, and `aria-controls`; flash messages use `role="status"` with `aria-live="polite"`
- **Form accessibility:** Every input has an associated `<label for="...">`, `aria-required="true"`, and on validation failure: `aria-invalid="true"` + `aria-describedby` pointing to the inline error element (`role="alert"`)
- **Sortable table headers:** `<th scope="col" aria-sort="ascending|descending|none">` with decorative sort arrows marked `aria-hidden="true"`
- **Pagination:** Full `<nav aria-label="Pagination navigation">` with per-link `aria-label` (e.g. "Go to page 3") and `aria-current="page"` on the active page
- **Decorative elements:** Icons and visual-only characters use `aria-hidden="true"`; screen-reader-only text uses `.sr-only` class
- **Keyboard navigation:** Dropdown menu implements keyboard arrow-key navigation and focus management; `tabindex="-1"` used on hidden menu items
- **Badge labels:** Severity and status badges include `aria-label="Severity: Critical"` / `aria-label="Status: In Progress"` for screen readers

## Dependencies
- `flask>=3.0` — only direct dependency; SQLite is part of the Python standard library

## Git
- `.venv/`, `tickets.db`, and `__pycache__/` are gitignored — never commit these
- Remote: `git@github.com:uchicago-its-linux/hackathon.git`
