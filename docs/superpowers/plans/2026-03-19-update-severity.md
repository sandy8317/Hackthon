# Update Ticket Severity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow staff to update a ticket's severity from both the ticket detail page and the dashboard inline table.

**Architecture:** New `POST /tickets/<id>/severity` route in `app.py` mirrors `update_status` exactly. `ticket_detail` route is updated to pass `severity_levels`. `ticket_detail.html` gets a new "Update Severity" card. `dashboard.html`'s read-only severity column becomes an inline edit form.

**Tech Stack:** Python 3, Flask 3, SQLite (sqlite3.Row), Jinja2

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `app.py` | Modify | Add `update_severity()` route; pass `severity_levels` in `ticket_detail` route |
| `templates/ticket_detail.html` | Modify | Add "Update Severity" form card below existing "Update Status" card |
| `templates/dashboard.html` | Modify | Replace read-only severity badge column with inline edit form |
| `tests/test_severity.py` | Create | Tests for `update_severity` route |

---

## Task 1: Backend — update_severity route

**Files:**
- Create: `tests/test_severity.py`
- Modify: `app.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_severity.py`:

```python
def test_update_severity_success_redirects_to_detail(client_with_tickets):
    """Successful severity update redirects to ticket detail by default."""
    response = client_with_tickets.post(
        "/tickets/1/severity",
        data={"severity": "High"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/tickets/1" in response.headers["Location"]


def test_update_severity_persists_change(client_with_tickets):
    """Severity is actually updated in the database."""
    client_with_tickets.post("/tickets/1/severity", data={"severity": "Low"})
    response = client_with_tickets.get("/tickets/1")
    assert b"Low" in response.data


def test_update_severity_redirects_to_dashboard_when_next_is_dashboard(client_with_tickets):
    """next=dashboard redirects back to dashboard."""
    response = client_with_tickets.post(
        "/tickets/1/severity",
        data={"severity": "Medium", "next": "dashboard"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_update_severity_invalid_value_rejected(client_with_tickets):
    """An invalid severity value is rejected with a flash message."""
    response = client_with_tickets.post(
        "/tickets/1/severity",
        data={"severity": "Extreme"},
        follow_redirects=True,
    )
    assert b"Invalid severity" in response.data


def test_update_severity_nonexistent_ticket_redirects_to_list(client):
    """Posting to a non-existent ticket redirects to ticket list."""
    response = client.post(
        "/tickets/9999/severity",
        data={"severity": "High"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/tickets" in response.headers["Location"]
    assert "9999" not in response.headers["Location"]
```

- [ ] **Step 2: Run tests — expect all to fail**

```bash
.venv/Scripts/python -m pytest tests/test_severity.py -v
```

Expected: 5 FAILED (404 — route doesn't exist yet)

- [ ] **Step 3: Add update_severity route and fix ticket_detail route in app.py**

**3a. Add `update_severity` route** — insert it directly after the `update_status` function (around line 189), before `if __name__ == "__main__":`:

```python
@app.route("/tickets/<int:ticket_id>/severity", methods=["POST"])
def update_severity(ticket_id):
    db = get_db()
    ticket = db.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        flash("Ticket not found.", "error")
        return redirect(url_for("ticket_list"))
    next_page = request.form.get("next", "")
    new_severity = request.form.get("severity", "")
    if new_severity not in SEVERITY_LEVELS:
        flash("Invalid severity.", "error")
        if next_page == "dashboard":
            return redirect(url_for("dashboard"))
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    db.execute("UPDATE tickets SET severity = ? WHERE id = ?", (new_severity, ticket_id))
    db.commit()
    flash(f"Severity updated to {new_severity}.", "success")
    if next_page == "dashboard":
        return redirect(url_for("dashboard"))
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))
```

**3b. Fix `ticket_detail` route** — find the existing `ticket_detail` function (around line 158). Change the final `return render_template` call from:

```python
    return render_template("ticket_detail.html", ticket=ticket, status_levels=STATUS_LEVELS)
```

to:

```python
    return render_template("ticket_detail.html", ticket=ticket,
                           status_levels=STATUS_LEVELS, severity_levels=SEVERITY_LEVELS)
```

- [ ] **Step 4: Run tests — expect all to pass**

```bash
.venv/Scripts/python -m pytest tests/test_severity.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
.venv/Scripts/python -m pytest tests/ -v
```

Expected: 12 PASSED (7 existing + 5 new)

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_severity.py
git commit -m "feat: add update_severity route and pass severity_levels to ticket_detail"
```

---

## Task 2: ticket_detail.html — severity update form

**Files:**
- Modify: `templates/ticket_detail.html`

- [ ] **Step 1: Add the Update Severity card**

In `templates/ticket_detail.html`, find the closing `</div>` of the "Update Status" card (currently the last card, ending at line 51). Add a new card directly after it, before `{% endblock %}`:

```html
<div class="card" style="margin-top:1.25rem;">
    <h2>Update Severity</h2>
    <form method="post" action="{{ url_for('update_severity', ticket_id=ticket.id) }}" style="display:flex; align-items:center; gap:0.75rem; flex-wrap:wrap;">
        <select name="severity">
            {% for s in severity_levels %}
                <option value="{{ s }}" {% if ticket.severity == s %}selected{% endif %}>{{ s }}</option>
            {% endfor %}
        </select>
        <button type="submit" class="btn btn-primary">Save Severity</button>
    </form>
</div>
```

The full file after the change should end with:

```html
<div class="card" style="margin-top:1.25rem;">
    <h2>Update Status</h2>
    <form method="post" action="{{ url_for('update_status', ticket_id=ticket.id) }}" style="display:flex; align-items:center; gap:0.75rem; flex-wrap:wrap;">
        <select name="status">
            {% for s in status_levels %}
                <option value="{{ s }}" {% if ticket.status == s %}selected{% endif %}>{{ s }}</option>
            {% endfor %}
        </select>
        <button type="submit" class="btn btn-primary">Save Status</button>
    </form>
</div>

<div class="card" style="margin-top:1.25rem;">
    <h2>Update Severity</h2>
    <form method="post" action="{{ url_for('update_severity', ticket_id=ticket.id) }}" style="display:flex; align-items:center; gap:0.75rem; flex-wrap:wrap;">
        <select name="severity">
            {% for s in severity_levels %}
                <option value="{{ s }}" {% if ticket.severity == s %}selected{% endif %}>{{ s }}</option>
            {% endfor %}
        </select>
        <button type="submit" class="btn btn-primary">Save Severity</button>
    </form>
</div>
{% endblock %}
```

- [ ] **Step 2: Run full test suite**

```bash
.venv/Scripts/python -m pytest tests/ -v
```

Expected: 12 PASSED

- [ ] **Step 3: Commit**

```bash
git add templates/ticket_detail.html
git commit -m "feat: add Update Severity form to ticket detail page"
```

---

## Task 3: dashboard.html — inline severity editing

**Files:**
- Modify: `templates/dashboard.html`

- [ ] **Step 1: Replace read-only severity badge column with inline edit form**

In `templates/dashboard.html`, find the `<th>Severity</th>` table header and the corresponding `<td>` cell in the row loop.

**Replace the header:**
```html
                <th>Severity</th>
```
(Keep it the same — the column header text stays "Severity", no change needed.)

**Replace the severity `<td>` cell.** Currently it looks like this (the existing badge cell from before dashboard was built — now it should be the inline form):

Find:
```html
                <td><span class="badge badge-{{ ticket.severity }}">{{ ticket.severity }}</span></td>
```

Replace with:
```html
                <td>
                    <form method="POST" action="{{ url_for('update_severity', ticket_id=ticket.id) }}"
                          style="display:flex; align-items:center; gap:0.35rem; flex-wrap:wrap;">
                        <input type="hidden" name="next" value="dashboard">
                        <span class="badge badge-{{ ticket.severity }}">{{ ticket.severity }}</span>
                        <select name="severity" style="width:auto; padding:0.3rem 0.5rem; font-size:0.88rem;">
                            {% for s in severity_levels %}
                            <option value="{{ s }}" {% if ticket.severity == s %}selected{% endif %}>{{ s }}</option>
                            {% endfor %}
                        </select>
                        <button type="submit" class="btn btn-primary"
                                style="padding:0.3rem 0.65rem; font-size:0.85rem; margin-left:0.35rem;">Save</button>
                    </form>
                </td>
```

Note: `severity_levels` is already passed to `dashboard.html` by the `dashboard()` route — no backend change needed.

- [ ] **Step 2: Run full test suite**

```bash
.venv/Scripts/python -m pytest tests/ -v
```

Expected: 12 PASSED

- [ ] **Step 3: Commit**

```bash
git add templates/dashboard.html
git commit -m "feat: add inline severity editing to dashboard table"
```

---

## Task 4: Manual smoke test

- [ ] **Step 1: Start the app (if not already running)**

```bash
.venv/Scripts/python app.py
```

Expected: `Running on http://127.0.0.1:5000`

- [ ] **Step 2: Submit a test ticket**

Go to `http://127.0.0.1:5000/`, submit a ticket with severity "Low".

- [ ] **Step 3: Verify severity update on ticket detail page**

Go to `/tickets`, click the ticket. Confirm:
- "Update Severity" card is visible below "Update Status"
- Dropdown shows "Low" pre-selected
- Change to "Critical", click "Save Severity"
- Flash message "Severity updated to Critical." appears
- Severity badge in the page header updates to "Critical"

- [ ] **Step 4: Verify severity update on dashboard**

Go to `/dashboard`. Confirm:
- Severity column shows badge + dropdown + Save button for each unresolved ticket
- Change severity for a ticket, click Save
- Redirected back to dashboard
- Flash message appears
- Badge and dropdown reflect the new severity
