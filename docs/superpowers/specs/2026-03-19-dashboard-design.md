# Dashboard Design Spec

**Date:** 2026-03-19
**Status:** Approved

## Overview

Add a `/dashboard` route as the new staff landing page. It provides a summary of ticket metrics and a triage view of recent/urgent tickets with inline status updates. The existing `/tickets` route remains unchanged and is linked from the dashboard.

## Route

`GET /dashboard` — new route in `app.py`, renders `templates/dashboard.html`.

## Page Sections

### 1. Stats Row

Three groups of stat cards:

- **By status:** Open, In Progress, Pending, Closed (counts) — always show all four cards, even if count is 0
- **By severity:** Low, Medium, High, Critical (counts) — always show all four cards, even if count is 0
- **Time-based:** Tickets submitted today, tickets submitted in the last 7 days (rolling 168-hour window)

### 2. Recent / Urgent Tickets Table

Shows up to 15 tickets: unresolved tickets (status != 'Closed') ordered by severity (Critical first, then High, Medium, Low), then by `submitted_at` DESC.

Columns: ID, Customer, Website, Severity, Status (inline dropdown), Problem Time, Submitted.

`submitted_at` is stored as ISO text (`2026-03-19T14:30:00`); display as-is in the table (same convention as `ticket_list.html`).

Inline status update: each row has a `<form method="POST" action="/tickets/<id>/status">` with a `<select name="status">` pre-selected to the ticket's current status, a hidden `<input name="next" value="dashboard">`, and a `<button type="submit" class="btn btn-primary">Save</button>` (consistent with `ticket_detail.html`). Note: `<form>` elements inside `<td>` cells are re-parsed by browsers per HTML5 rules but work correctly in all modern browsers — this is the accepted pattern here.

If there are no unresolved tickets, show: `<p style="color:#777; padding:1rem 0;">No open tickets.</p>` (same styling as `ticket_list.html` empty state).

### 3. Footer Link

A "View all tickets" link styled as `class="btn btn-secondary"` pointing to `/tickets`.

## Backend Changes

### New `/dashboard` route

```python
@app.route("/dashboard")
def dashboard():
    db = get_db()

    # Status counts — pre-populate all levels with 0 so template never gets a missing key
    status_counts = {s: 0 for s in STATUS_LEVELS}
    for row in db.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status").fetchall():
        status_counts[row['status']] = row['count']

    # Severity counts — pre-populate all levels with 0
    severity_counts = {s: 0 for s in SEVERITY_LEVELS}
    for row in db.execute("SELECT severity, COUNT(*) as count FROM tickets GROUP BY severity").fetchall():
        severity_counts[row['severity']] = row['count']

    # Today's count (submitted_at and DATE('now') are both UTC — consistent)
    today_count = db.execute(
        "SELECT COUNT(*) FROM tickets WHERE DATE(submitted_at) = DATE('now')"
    ).fetchone()[0]

    # This week's count — rolling 168-hour window ending now (UTC).
    # DATETIME(submitted_at) normalises the stored T-separated ISO text to space-separated
    # form before comparison, avoiding a fragile cross-format string comparison.
    week_count = db.execute(
        "SELECT COUNT(*) FROM tickets WHERE DATETIME(submitted_at) >= DATETIME('now', '-7 days')"
    ).fetchone()[0]

    # Recent/urgent tickets: unresolved, ordered by severity then recency
    tickets = db.execute(
        "SELECT * FROM tickets WHERE status != 'Closed' "
        "ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 "
        "WHEN 'Medium' THEN 3 ELSE 4 END, submitted_at DESC LIMIT 15"
    ).fetchall()

    return render_template(
        "dashboard.html",
        status_counts=status_counts,
        severity_counts=severity_counts,
        today_count=today_count,
        week_count=week_count,
        tickets=tickets,
        status_levels=STATUS_LEVELS,
        severity_levels=SEVERITY_LEVELS,
    )
```

### Modified `update_status` route

Add a `next_page = request.form.get('next', '')` lookup. Apply it to all three branches:

| Branch | Current redirect | New redirect |
|--------|-----------------|--------------|
| `ticket is None` | `url_for('ticket_list')` | unchanged — always `ticket_list` |
| invalid status | `url_for('ticket_detail', ticket_id=ticket_id)` | `url_for('dashboard')` if `next_page == 'dashboard'`, else `ticket_detail` |
| success | `url_for('ticket_detail', ticket_id=ticket_id)` | `url_for('dashboard')` if `next_page == 'dashboard'`, else `ticket_detail` |

`ticket_detail.html` requires no changes — it does not pass a `next` field, so `next_page` will be empty and behaviour is unchanged.

Flash messages (`"Status updated to X."` / `"Invalid status."`) continue to fire as before; `base.html` renders them on both `ticket_detail` and `dashboard`.

### Navigation

Add a "Dashboard" link to `base.html` nav, pointing to `url_for('dashboard')`.

## Template Context (`dashboard.html`)

| Variable | Type | Description |
|----------|------|-------------|
| `status_counts` | dict | `{status: count}` for all STATUS_LEVELS, 0-filled |
| `severity_counts` | dict | `{severity: count}` for all SEVERITY_LEVELS, 0-filled |
| `today_count` | int | Tickets submitted today (UTC) |
| `week_count` | int | Tickets submitted in last 7 days (rolling 168-hour window) |
| `tickets` | list of sqlite3.Row | Up to 15 recent/urgent unresolved tickets |
| `status_levels` | list | `STATUS_LEVELS` — iterate for stat cards and dropdown options |
| `severity_levels` | list | `SEVERITY_LEVELS` — iterate for stat cards |

Use `status_levels` and `severity_levels` to iterate cards in defined order (not dict key order).

## Template Structure (`dashboard.html`)

```html
{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}

{% block content %}
<h1>Dashboard</h1>

<!-- Stats row -->
<div class="stat-row">
  <!-- status cards, severity cards, today/week cards -->
</div>

<!-- Recent/urgent tickets -->
<div class="card">
  <h2>...</h2>
  <table>...</table>  <!-- or empty-state message -->
</div>

<!-- Footer link -->
<a href="..." class="btn btn-secondary">View all tickets</a>
{% endblock %}
```

## CSS (`static/style.css`)

Add styles for the stat card layout. Use these class names:

- `.stat-row` — flex container for all stat cards, wraps on small screens
- `.stat-card` — individual card: border, padding, min-width; number prominent, label below

Existing badge classes (`.badge-Low`, `.badge-Critical`, `.badge-In-Progress`, etc.) work as-is for the table.

## Files Changed

| File | Change |
|------|--------|
| `app.py` | Add `dashboard()` route; modify `update_status()` to handle `next=dashboard` |
| `templates/dashboard.html` | New template |
| `templates/base.html` | Add Dashboard nav link |
| `static/style.css` | Add `.stat-row` and `.stat-card` styles |

## Out of Scope

- Authentication / staff-only access
- Pagination on the dashboard ticket table (capped at 15 rows; full list is at `/tickets`)
- Charts or graphs
- Real-time updates
