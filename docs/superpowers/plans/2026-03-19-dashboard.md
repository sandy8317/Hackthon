# Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/dashboard` staff landing page with ticket metric summary cards and an inline-editable urgent tickets table.

**Architecture:** New `GET /dashboard` route in `app.py` runs 5 DB queries and renders `templates/dashboard.html`. The existing `POST /tickets/<id>/status` route is extended with a `next` redirect parameter. No new files except the template — all changes are additive or small modifications.

**Tech Stack:** Python 3, Flask 3, SQLite (sqlite3.Row), Jinja2, plain CSS

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `app.py` | Modify | Add `dashboard()` route; extend `update_status()` with `next` redirect |
| `templates/dashboard.html` | Create | New dashboard template |
| `templates/base.html` | Modify | Add "Dashboard" nav link |
| `static/style.css` | Modify | Add `.stat-row` and `.stat-card` styles |
| `tests/test_dashboard.py` | Create | Pytest tests for both backend changes |

---

## Task 1: Set up test infrastructure

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Add pytest to requirements.txt**

Append `pytest` to `requirements.txt` so it reads:
```
flask>=3.0
pytest
```

- [ ] **Step 2: Install it**

```bash
.venv/bin/pip install pytest
```

Expected: `Successfully installed pytest-...`

- [ ] **Step 3: Create tests package**

Create `tests/__init__.py` as an empty file.

- [ ] **Step 4: Create conftest.py with a Flask test client fixture**

Create `tests/conftest.py`:

```python
import pytest
import tempfile
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app as flask_app


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    flask_app.app.config["TESTING"] = True
    flask_app.DATABASE = db_path

    with flask_app.app.app_context():
        flask_app.init_db()

    with flask_app.app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client_with_tickets(client):
    """Client with a few seeded tickets for realistic tests."""
    with flask_app.app.app_context():
        db = flask_app.get_db()
        db.executemany(
            "INSERT INTO tickets (customer_name, email, url, severity, problem_time, description, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("Alice", "alice@example.com", "http://a.com", "Critical", "2026-03-19", "Site down", "Open"),
                ("Bob",   "bob@example.com",   "http://b.com", "High",     "2026-03-18", "Slow load", "In Progress"),
                ("Carol", "carol@example.com", "http://c.com", "Low",      "2026-03-17", "Typo",      "Closed"),
            ],
        )
        db.commit()
    return client
```

- [ ] **Step 5: Verify fixture works**

```bash
.venv/bin/python -m pytest tests/ -v --collect-only
```

Expected: `no tests ran` (0 collected, no errors)

---

## Task 2: Dashboard route — backend

**Files:**
- Create: `tests/test_dashboard.py`
- Modify: `app.py`

- [ ] **Step 1: Write failing tests for the dashboard route**

Create `tests/test_dashboard.py`:

```python
def test_dashboard_empty_db_returns_200(client):
    """Dashboard loads on an empty database without crashing."""
    response = client.get("/dashboard")
    assert response.status_code == 200


def test_dashboard_shows_all_status_cards(client):
    """/dashboard renders a card for every status level, even with 0 tickets."""
    response = client.get("/dashboard")
    body = response.data.decode()
    for status in ["Open", "In Progress", "Pending", "Closed"]:
        assert status in body, f"Expected status '{status}' in dashboard"


def test_dashboard_shows_all_severity_cards(client):
    """/dashboard renders a card for every severity level, even with 0 tickets."""
    response = client.get("/dashboard")
    body = response.data.decode()
    for severity in ["Low", "Medium", "High", "Critical"]:
        assert severity in body, f"Expected severity '{severity}' in dashboard"


def test_dashboard_shows_urgent_tickets(client_with_tickets):
    """Unresolved tickets appear in the dashboard table."""
    response = client_with_tickets.get("/dashboard")
    body = response.data.decode()
    assert "Alice" in body   # Critical, Open — should appear
    assert "Bob" in body     # High, In Progress — should appear
    assert "Carol" not in body  # Closed — must NOT appear


def test_dashboard_orders_by_severity(client_with_tickets):
    """Critical tickets appear before High tickets in the dashboard."""
    response = client_with_tickets.get("/dashboard")
    body = response.data.decode()
    assert body.index("Alice") < body.index("Bob")
```

- [ ] **Step 2: Run tests — expect all to fail**

```bash
.venv/bin/python -m pytest tests/test_dashboard.py -v
```

Expected: 5 FAILED (404 or template not found errors)

- [ ] **Step 3: Add the `dashboard()` route to app.py**

In `app.py`, add this route **before** the `if __name__ == "__main__":` block:

```python
@app.route("/dashboard")
def dashboard():
    db = get_db()

    status_counts = {s: 0 for s in STATUS_LEVELS}
    for row in db.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status").fetchall():
        status_counts[row["status"]] = row["count"]

    severity_counts = {s: 0 for s in SEVERITY_LEVELS}
    for row in db.execute("SELECT severity, COUNT(*) as count FROM tickets GROUP BY severity").fetchall():
        severity_counts[row["severity"]] = row["count"]

    today_count = db.execute(
        "SELECT COUNT(*) FROM tickets WHERE DATE(submitted_at) = DATE('now')"
    ).fetchone()[0]

    week_count = db.execute(
        "SELECT COUNT(*) FROM tickets WHERE DATETIME(submitted_at) >= DATETIME('now', '-7 days')"
    ).fetchone()[0]

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

The tests will remain failing until the template exists (Task 4). That's expected.

- [ ] **Step 4: Commit backend route**

```bash
git add app.py tests/conftest.py tests/__init__.py tests/test_dashboard.py requirements.txt
git commit -m "feat: add /dashboard route with stats and urgent ticket queries"
```

---

## Task 3: Extend update_status with next redirect

**Files:**
- Modify: `tests/test_dashboard.py`
- Modify: `app.py`

- [ ] **Step 1: Add failing tests for the `next` redirect behaviour**

Append to `tests/test_dashboard.py`:

```python
def test_update_status_redirects_to_dashboard_when_next_is_dashboard(client_with_tickets):
    """Successful status update with next=dashboard redirects back to /dashboard."""
    # Get the first non-closed ticket id (Alice = id 1)
    with flask_app.app.app_context():
        db = flask_app.get_db()
        ticket = db.execute("SELECT id FROM tickets WHERE status != 'Closed' LIMIT 1").fetchone()
        ticket_id = ticket["id"]

    response = client_with_tickets.post(
        f"/tickets/{ticket_id}/status",
        data={"status": "Pending", "next": "dashboard"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_update_status_without_next_still_redirects_to_detail(client_with_tickets):
    """Status update without next field still redirects to ticket_detail (existing behaviour)."""
    with flask_app.app.app_context():
        db = flask_app.get_db()
        ticket = db.execute("SELECT id FROM tickets WHERE status != 'Closed' LIMIT 1").fetchone()
        ticket_id = ticket["id"]

    response = client_with_tickets.post(
        f"/tickets/{ticket_id}/status",
        data={"status": "Pending"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert f"/tickets/{ticket_id}" in response.headers["Location"]
```

Add the following import block at the **very top** of `tests/test_dashboard.py` (before all test functions):

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import app as flask_app
```

- [ ] **Step 2: Run new tests — expect them to fail**

```bash
.venv/bin/python -m pytest tests/test_dashboard.py::test_update_status_redirects_to_dashboard_when_next_is_dashboard tests/test_dashboard.py::test_update_status_without_next_still_redirects_to_detail -v
```

Expected: FAILED (redirect goes to ticket_detail, not dashboard)

- [ ] **Step 3: Modify `update_status` in app.py**

Find the existing `update_status` function (currently around line 168). Replace it with:

```python
@app.route("/tickets/<int:ticket_id>/status", methods=["POST"])
def update_status(ticket_id):
    db = get_db()
    ticket = db.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        flash("Ticket not found.", "error")
        return redirect(url_for("ticket_list"))
    next_page = request.form.get("next", "")
    new_status = request.form.get("status", "")
    if new_status not in STATUS_LEVELS:
        flash("Invalid status.", "error")
        if next_page == "dashboard":
            return redirect(url_for("dashboard"))
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    db.execute("UPDATE tickets SET status = ? WHERE id = ?", (new_status, ticket_id))
    db.commit()
    flash(f"Status updated to {new_status}.", "success")
    if next_page == "dashboard":
        return redirect(url_for("dashboard"))
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))
```

- [ ] **Step 4: Run the two new tests — expect them to pass**

```bash
.venv/bin/python -m pytest tests/test_dashboard.py::test_update_status_redirects_to_dashboard_when_next_is_dashboard tests/test_dashboard.py::test_update_status_without_next_still_redirects_to_detail -v
```

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_dashboard.py
git commit -m "feat: extend update_status to redirect back to dashboard when next=dashboard"
```

---

## Task 4: Create dashboard.html template

**Files:**
- Create: `templates/dashboard.html`

- [ ] **Step 1: Create the template**

Create `templates/dashboard.html`:

```html
{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}

{% block content %}
<h1>Dashboard</h1>

<div class="stat-row">
    <div class="stat-card">
        <div class="stat-label">Today</div>
        <div class="stat-number">{{ today_count }}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Last 7 Days</div>
        <div class="stat-number">{{ week_count }}</div>
    </div>
    {% for s in status_levels %}
    <div class="stat-card">
        <div class="stat-label">{{ s }}</div>
        <div class="stat-number">{{ status_counts[s] }}</div>
    </div>
    {% endfor %}
    {% for s in severity_levels %}
    <div class="stat-card">
        <div class="stat-label">{{ s }}</div>
        <div class="stat-number">{{ severity_counts[s] }}</div>
    </div>
    {% endfor %}
</div>

<div class="card" style="margin-top: 1.5rem;">
    <h2>Open &amp; In-Progress Tickets</h2>

    {% if tickets %}
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Customer</th>
                <th>Website</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Problem Time</th>
                <th>Submitted</th>
            </tr>
        </thead>
        <tbody>
            {% for ticket in tickets %}
            <tr>
                <td><a href="{{ url_for('ticket_detail', ticket_id=ticket.id) }}">#{{ ticket.id }}</a></td>
                <td>{{ ticket.customer_name }}</td>
                <td style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ ticket.url }}</td>
                <td><span class="badge badge-{{ ticket.severity }}">{{ ticket.severity }}</span></td>
                <td>
                    <form method="POST" action="{{ url_for('update_status', ticket_id=ticket.id) }}">
                        <input type="hidden" name="next" value="dashboard">
                        <select name="status" style="width:auto; padding:0.3rem 0.5rem; font-size:0.88rem;">
                            {% for s in status_levels %}
                            <option value="{{ s }}" {% if ticket.status == s %}selected{% endif %}>{{ s }}</option>
                            {% endfor %}
                        </select>
                        <button type="submit" class="btn btn-primary" style="padding:0.3rem 0.65rem; font-size:0.85rem; margin-left:0.35rem;">Save</button>
                    </form>
                </td>
                <td>{{ ticket.problem_time }}</td>
                <td>{{ ticket.submitted_at }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p style="color:#777; padding:1rem 0;">No open tickets.</p>
    {% endif %}
</div>

<div style="margin-top: 1.25rem;">
    <a href="{{ url_for('ticket_list') }}" class="btn btn-secondary">View all tickets</a>
</div>
{% endblock %}
```

- [ ] **Step 2: Run the full dashboard test suite — expect all 5 original tests to now pass**

```bash
.venv/bin/python -m pytest tests/test_dashboard.py -v
```

Expected: 7 PASSED (5 dashboard + 2 update_status)

- [ ] **Step 3: Commit**

```bash
git add templates/dashboard.html
git commit -m "feat: add dashboard.html template"
```

---

## Task 5: Add nav link and CSS styles

**Files:**
- Modify: `templates/base.html`
- Modify: `static/style.css`

- [ ] **Step 1: Add Dashboard link to base.html nav**

In `templates/base.html`, find line 14:
```html
            <a href="{{ url_for('ticket_list') }}">View Tickets</a>
```

Replace with:
```html
            <a href="{{ url_for('dashboard') }}">Dashboard</a>
            <a href="{{ url_for('ticket_list') }}">View Tickets</a>
```

- [ ] **Step 2: Add stat card CSS to style.css**

Append to the end of `static/style.css`:

```css
/* Dashboard stat cards */
.stat-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
}

.stat-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 0.9rem 1.25rem;
    min-width: 110px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    text-align: center;
}

.stat-card .stat-number {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1a3a5c;
    line-height: 1.2;
}

.stat-card .stat-label {
    font-size: 0.78rem;
    color: #777;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.25rem;
}
```

- [ ] **Step 3: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: 7 PASSED, 0 failed

- [ ] **Step 4: Commit**

```bash
git add templates/base.html static/style.css
git commit -m "feat: add Dashboard nav link and stat card styles"
```

---

## Task 6: Manual smoke test

- [ ] **Step 1: Start the app**

```bash
.venv/bin/python app.py
```

Expected: `Running on http://127.0.0.1:5000`

- [ ] **Step 2: Verify dashboard loads**

Open `http://127.0.0.1:5000/dashboard` in a browser.

Confirm:
- Stat cards appear for all 4 statuses and 4 severities (showing 0 if DB is empty)
- "Today" and "Last 7 Days" cards appear
- "No open tickets." message shows when DB is empty
- "View all tickets" button is visible

- [ ] **Step 3: Submit a test ticket and verify it appears**

Go to `http://127.0.0.1:5000/`, submit a ticket with severity "Critical".
Return to `/dashboard` and confirm:
- The Critical severity card shows count 1
- The ticket appears in the urgent tickets table
- The status dropdown shows "Open" pre-selected

- [ ] **Step 4: Test inline status update**

Change the status dropdown to "In Progress" and click Save.
Confirm:
- You are redirected back to `/dashboard` (not the detail page)
- A flash message "Status updated to In Progress." appears
- The ticket now shows "In Progress" in the dropdown

- [ ] **Step 5: Verify ticket_detail still works**

Go to `/tickets`, click a ticket, change its status from the detail page.
Confirm you are redirected to the ticket detail page (not dashboard) — existing behaviour unchanged.
