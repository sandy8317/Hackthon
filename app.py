import sqlite3
import csv
from io import StringIO
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, redirect, url_for, flash, g, Response

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

DATABASE = "tickets.db"
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]
STATUS_LEVELS = ["Open", "In Progress", "Pending", "Closed"]
PER_PAGE = 20

# Whitelist of sortable columns; values are SQL expressions
SORT_COLUMNS = {
    "id": "id",
    "customer_name": "customer_name",
    "url": "url",
    "severity": "CASE severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END",
    "status": "CASE status WHEN 'Open' THEN 1 WHEN 'In Progress' THEN 2 WHEN 'Pending' THEN 3 ELSE 4 END",
    "problem_time": "problem_time",
    "submitted_at": "submitted_at",
}
DASHBOARD_LIMIT = 15


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource("schema.sql") as f:
            db.executescript(f.read().decode("utf8"))
        db.commit()


def validate_ticket(form):
    errors = {}

    customer_name = form.get("customer_name", "").strip()
    if not customer_name:
        errors["customer_name"] = "Name is required."
    elif len(customer_name) > 120:
        errors["customer_name"] = "Name must be 120 characters or fewer."

    email = form.get("email", "").strip()
    if not email:
        errors["email"] = "Email is required."
    elif "@" not in email or "." not in email:
        errors["email"] = "Enter a valid email address."
    elif len(email) > 200:
        errors["email"] = "Email must be 200 characters or fewer."

    url = form.get("url", "").strip()
    if not url:
        errors["url"] = "Website URL is required."
    elif len(url) > 500:
        errors["url"] = "URL must be 500 characters or fewer."

    severity = form.get("severity", "")
    if severity not in SEVERITY_LEVELS:
        errors["severity"] = "Select a valid severity level."

    problem_time = form.get("problem_time", "").strip()
    if not problem_time:
        errors["problem_time"] = "Problem time is required."
    else:
        try:
            datetime.strptime(problem_time, "%Y-%m-%d")
        except ValueError:
            errors["problem_time"] = "Enter a valid date."

    description = form.get("description", "").strip()
    if not description:
        errors["description"] = "Description is required."
    elif len(description) > 5000:
        errors["description"] = "Description must be 5000 characters or fewer."

    return errors


@app.route("/", methods=["GET", "POST"])
def submit():
    if request.method == "POST":
        errors = validate_ticket(request.form)
        if errors:
            return render_template(
                "submit.html",
                errors=errors,
                form_data=request.form,
                severity_levels=SEVERITY_LEVELS,
            )

        db = get_db()
        chicago_tz = ZoneInfo("America/Chicago")
        chicago_time = datetime.now(chicago_tz).strftime("%Y-%m-%dT%H:%M:%S")
        cursor = db.execute(
            "INSERT INTO tickets (customer_name, email, url, severity, problem_time, description, submitted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                request.form.get("customer_name", "").strip(),
                request.form.get("email", "").strip(),
                request.form.get("url", "").strip(),
                request.form.get("severity", ""),
                request.form.get("problem_time", "").strip(),
                request.form.get("description", "").strip(),
                chicago_time,
            ),
        )
        db.commit()
        ticket_id = cursor.lastrowid
        return redirect(url_for("submit_success", ticket_id=ticket_id))

    return render_template(
        "submit.html", errors={}, form_data={}, severity_levels=SEVERITY_LEVELS
    )


@app.route("/success/<int:ticket_id>")
def submit_success(ticket_id):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        return redirect(url_for("submit"))
    return render_template("submit_success.html", ticket=ticket)


@app.route("/tickets")
def ticket_list():
    db = get_db()
    page = request.args.get("page", 1, type=int)
    severity_filter = request.args.get("severity", "")
    search_query = request.args.get("q", "").strip()
    sort = request.args.get("sort", "submitted_at")
    order = request.args.get("order", "desc")

    if sort not in SORT_COLUMNS:
        sort = "submitted_at"
    if order not in ("asc", "desc"):
        order = "desc"

    conditions = []
    params = []

    if severity_filter and severity_filter in SEVERITY_LEVELS:
        conditions.append("severity = ?")
        params.append(severity_filter)
    else:
        severity_filter = ""

    if search_query:
        conditions.append("(customer_name LIKE ? OR email LIKE ? OR url LIKE ? OR description LIKE ?)")
        like = f"%{search_query}%"
        params.extend([like, like, like, like])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    order_sql = "ASC" if order == "asc" else "DESC"
    sort_expr = SORT_COLUMNS[sort]

    total = db.execute(f"SELECT COUNT(*) FROM tickets {where}", params).fetchone()[0]
    tickets = db.execute(
        f"SELECT * FROM tickets {where} ORDER BY {sort_expr} {order_sql} LIMIT ? OFFSET ?",
        params + [PER_PAGE, (page - 1) * PER_PAGE],
    ).fetchall()

    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    return render_template(
        "ticket_list.html",
        tickets=tickets,
        page=page,
        total_pages=total_pages,
        total=total,
        per_page=PER_PAGE,
        severity_filter=severity_filter,
        search_query=search_query,
        sort=sort,
        order=order,
        severity_levels=SEVERITY_LEVELS,
        status_levels=STATUS_LEVELS,
    )


@app.route("/tickets/<int:ticket_id>")
def ticket_detail(ticket_id):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        flash("Ticket not found.", "error")
        return redirect(url_for("ticket_list"))

    # Format submitted_at timestamp for Chicago time display
    chicago_tz = ZoneInfo("America/Chicago")
    submitted_dt = datetime.fromisoformat(ticket["submitted_at"])
    if submitted_dt.tzinfo is None:
        submitted_dt = submitted_dt.replace(tzinfo=ZoneInfo("UTC"))
    chicago_dt = submitted_dt.astimezone(chicago_tz)
    formatted_time = chicago_dt.strftime("%Y-%m-%d %I:%M %p %Z")

    return render_template("ticket_detail.html", ticket=ticket,
                           submitted_at_formatted=formatted_time,
                           status_levels=STATUS_LEVELS, severity_levels=SEVERITY_LEVELS)


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


def build_report_query(filters):
    """Build SQL query based on report filters"""
    conditions = []
    params = []

    # Handle preset report types
    if filters["report_type"] == "open":
        # Open Tickets: Status is Open or In Progress
        conditions.append("status IN ('Open', 'In Progress')")
    elif filters["report_type"] == "high_priority":
        # High Priority: Critical and High severity
        conditions.append("severity IN ('Critical', 'High')")
    elif filters["report_type"] == "edu":
        # .edu Websites
        conditions.append("(LOWER(url) LIKE '%.edu' OR LOWER(url) LIKE '%.edu/%' OR LOWER(url) LIKE '%.edu?%')")
    elif filters["report_type"] == "recent":
        # Recent: Last 30 days
        conditions.append("DATE(submitted_at) >= DATE('now', '-30 days')")
    elif filters["report_type"] == "pending":
        # Pending Review: Status is Pending
        conditions.append("status = 'Pending'")
    elif filters["report_type"] == "closed_week":
        # Closed This Week: Status is Closed, submitted in last 7 days
        conditions.append("status = 'Closed'")
        conditions.append("DATE(submitted_at) >= DATE('now', '-7 days')")
    elif filters["report_type"] == "all_tickets":
        # All Tickets: No filter, everything
        pass  # No conditions needed
    elif filters["report_type"] == "custom":
        # Custom: Apply user-defined filters
        if filters["url_contains"]:
            conditions.append("LOWER(url) LIKE ?")
            params.append(f"%{filters['url_contains'].lower()}%")

        # Severity filter (only for custom)
        if filters["severity"]:
            placeholders = ",".join("?" * len(filters["severity"]))
            conditions.append(f"severity IN ({placeholders})")
            params.extend(filters["severity"])

        # Status filter (only for custom)
        if filters["status"]:
            placeholders = ",".join("?" * len(filters["status"]))
            conditions.append(f"status IN ({placeholders})")
            params.extend(filters["status"])

    # Apply date filters for staff (always) and managers (custom only)
    is_manager = filters.get("user_role") == "manager"
    is_custom = filters["report_type"] == "custom"

    # Staff can always use date filters; managers only on custom reports
    if not is_manager or is_custom:
        if filters["date_from"]:
            conditions.append("DATE(submitted_at) >= ?")
            params.append(filters["date_from"])
        if filters["date_to"]:
            conditions.append("DATE(submitted_at) <= ?")
            params.append(filters["date_to"])

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, params


@app.route("/reports/edu", methods=["GET", "POST"])
def report_edu():
    db = get_db()

    # Track if report has been generated
    report_generated = request.method == "POST"

    # Default filters
    filters = {
        "user_role": request.form.get("user_role", "staff") if request.method == "POST" else "staff",
        "report_type": request.form.get("report_type", "open") if request.method == "POST" else "open",
        "severity": request.form.getlist("severity") if request.method == "POST" else [],
        "status": request.form.getlist("status") if request.method == "POST" else [],
        "date_from": request.form.get("date_from", "").strip() if request.method == "POST" else "",
        "date_to": request.form.get("date_to", "").strip() if request.method == "POST" else "",
        "url_contains": request.form.get("url_contains", "").strip() if request.method == "POST" else "",
    }

    tickets = []
    severity_counts = {s: 0 for s in SEVERITY_LEVELS}
    status_counts = {s: 0 for s in STATUS_LEVELS}
    report_title = ""

    # Only run query if report has been generated
    if report_generated:
        # Build query
        where_clause, params = build_report_query(filters)

        tickets = db.execute(
            f"SELECT * FROM tickets WHERE {where_clause} "
            "ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, submitted_at DESC",
            params
        ).fetchall()

        # Calculate statistics
        for t in tickets:
            if t["severity"] in severity_counts:
                severity_counts[t["severity"]] += 1
            if t["status"] in status_counts:
                status_counts[t["status"]] += 1

        # Determine report title based on report type
        if filters["report_type"] == "open":
            report_title = "My Open Tickets" if filters["user_role"] == "staff" else "Open Tickets"
        elif filters["report_type"] == "high_priority":
            report_title = "High Priority Tickets"
        elif filters["report_type"] == "edu":
            report_title = ".edu Website Issues"
        elif filters["report_type"] == "recent":
            report_title = "Recent Activity (Last 30 Days)"
        elif filters["report_type"] == "pending":
            report_title = "Pending Review"
        elif filters["report_type"] == "closed_week":
            report_title = "Closed This Week"
        elif filters["report_type"] == "all_tickets":
            report_title = "All Tickets"
        elif filters["report_type"] == "custom":
            report_title = "Custom Report"

    return render_template(
        "report_edu.html",
        tickets=tickets,
        severity_counts=severity_counts,
        status_counts=status_counts,
        severity_levels=SEVERITY_LEVELS,
        status_levels=STATUS_LEVELS,
        filters=filters,
        report_title=report_title,
        report_generated=report_generated,
    )


@app.route("/reports/edu/export", methods=["POST"])
def report_edu_export():
    db = get_db()

    # Get filters from form
    filters = {
        "user_role": request.form.get("user_role", "staff"),
        "report_type": request.form.get("report_type", "open"),
        "severity": request.form.getlist("severity"),
        "status": request.form.getlist("status"),
        "date_from": request.form.get("date_from", "").strip(),
        "date_to": request.form.get("date_to", "").strip(),
        "url_contains": request.form.get("url_contains", "").strip(),
    }

    # Build query using same logic as report view
    where_clause, params = build_report_query(filters)

    tickets = db.execute(
        f"SELECT * FROM tickets WHERE {where_clause} "
        "ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, submitted_at DESC",
        params
    ).fetchall()

    # Create CSV
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "Ticket ID",
        "Customer Name",
        "Email",
        "Website URL",
        "Severity",
        "Status",
        "Problem Date",
        "Description",
        "Submitted At"
    ])

    # Write data rows
    for ticket in tickets:
        writer.writerow([
            ticket["id"],
            ticket["customer_name"],
            ticket["email"],
            ticket["url"],
            ticket["severity"],
            ticket["status"],
            ticket["problem_time"],
            ticket["description"],
            ticket["submitted_at"]
        ])

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ticket_report_{timestamp}.csv"

    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/dashboard")
def dashboard():
    db = get_db()

    status_counts = {s: 0 for s in STATUS_LEVELS}
    for row in db.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status").fetchall():
        if row["status"] in status_counts:
            status_counts[row["status"]] = row["count"]

    severity_counts = {s: 0 for s in SEVERITY_LEVELS}
    for row in db.execute("SELECT severity, COUNT(*) as count FROM tickets GROUP BY severity").fetchall():
        if row["severity"] in severity_counts:
            severity_counts[row["severity"]] = row["count"]

    today_count = db.execute(
        "SELECT COUNT(*) FROM tickets WHERE DATETIME(submitted_at) >= DATETIME('now', 'start of day')"
    ).fetchone()[0]

    week_count = db.execute(
        "SELECT COUNT(*) FROM tickets WHERE DATETIME(submitted_at) >= DATETIME('now', '-7 days')"
    ).fetchone()[0]

    tickets = db.execute(
        "SELECT * FROM tickets WHERE status != 'Closed' "
        "ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 "
        "WHEN 'Medium' THEN 3 ELSE 4 END, submitted_at DESC LIMIT ?",
        (DASHBOARD_LIMIT,),
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


@app.route("/api/tickets/<int:ticket_id>")
def api_get_ticket(ticket_id):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        return {"error": "Ticket not found"}, 404
    return {
        "id": ticket["id"],
        "customer_name": ticket["customer_name"],
        "email": ticket["email"],
        "url": ticket["url"],
        "severity": ticket["severity"],
        "status": ticket["status"],
        "problem_time": ticket["problem_time"],
        "description": ticket["description"],
        "submitted_at": ticket["submitted_at"],
    }


@app.route("/api/tickets/<int:ticket_id>/status", methods=["PATCH"])
def api_update_ticket_status(ticket_id):
    db = get_db()
    ticket = db.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        return {"error": "Ticket not found"}, 404
    data = request.get_json(silent=True)
    if not data or "status" not in data:
        return {"error": "Missing 'status' field in request body"}, 400
    new_status = data["status"]
    if new_status not in STATUS_LEVELS:
        return {"error": f"Invalid status. Must be one of: {', '.join(STATUS_LEVELS)}"}, 400
    db.execute("UPDATE tickets SET status = ? WHERE id = ?", (new_status, ticket_id))
    db.commit()
    return {"id": ticket_id, "status": new_status}


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
