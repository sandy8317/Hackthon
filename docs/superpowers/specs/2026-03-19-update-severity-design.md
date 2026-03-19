# Update Ticket Severity Design Spec

**Date:** 2026-03-19
**Status:** Approved

## Overview

Add the ability for staff to update a ticket's severity. Editable from two places: the ticket detail page and inline on the dashboard table. Modeled exactly on the existing `update_status` pattern.

## Route

`POST /tickets/<id>/severity` — new route in `app.py`, mirrors `update_status`.

### Logic

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

### Redirect branches

| Branch | Redirect |
|--------|----------|
| `ticket is None` | Always `ticket_list` |
| Invalid severity | `dashboard` if `next == "dashboard"`, else `ticket_detail` |
| Success | `dashboard` if `next == "dashboard"`, else `ticket_detail` |

Flash messages: `"Ticket not found."` / `"Invalid severity."` / `"Severity updated to {x}."` rendered by `base.html` on both `ticket_detail` and `dashboard`.

## Modified `ticket_detail` Route

Pass `severity_levels=SEVERITY_LEVELS` to the template (currently missing):

```python
return render_template("ticket_detail.html", ticket=ticket,
                       status_levels=STATUS_LEVELS, severity_levels=SEVERITY_LEVELS)
```

## Template Changes

### `templates/ticket_detail.html`

Add a severity update form below (or alongside) the existing status form. Structure:

```html
<form method="POST" action="{{ url_for('update_severity', ticket_id=ticket.id) }}">
    <span class="badge badge-{{ ticket.severity }}">{{ ticket.severity }}</span>
    <select name="severity">
        {% for s in severity_levels %}
        <option value="{{ s }}" {% if ticket.severity == s %}selected{% endif %}>{{ s }}</option>
        {% endfor %}
    </select>
    <button type="submit" class="btn btn-primary">Save Severity</button>
</form>
```

`ticket_detail.html` does not pass a `next` field — absent `next` falls through to `ticket_detail` redirect (existing behaviour, no change needed).

### `templates/dashboard.html`

Replace the read-only severity badge column with an inline edit form, same pattern as the status column:

- Add `<th>Severity</th>` column header (replaces the old read-only header)
- Each row: form POSTing to `update_severity`, hidden `next=dashboard`, `<select name="severity">` pre-selected to `ticket.severity`, Save button
- Show current severity badge above/beside the select (same as status column treatment)

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

`severity_levels` is already passed to `dashboard.html` by the `dashboard()` route — no backend change needed for the dashboard template.

## Files Changed

| File | Change |
|------|--------|
| `app.py` | Add `update_severity()` route; pass `severity_levels` in `ticket_detail` route |
| `templates/ticket_detail.html` | Add severity update form |
| `templates/dashboard.html` | Replace read-only severity badge with inline edit form |

## Out of Scope

- Changing severity at ticket submission time (already supported)
- Audit log / history of severity changes
- Bulk severity updates
