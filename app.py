import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, g

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

DATABASE = "tickets.db"
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]
STATUS_LEVELS = ["Open", "In Progress", "Pending", "Closed"]
PER_PAGE = 20
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
        cursor = db.execute(
            "INSERT INTO tickets (customer_name, email, url, severity, problem_time, description) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                request.form.get("customer_name", "").strip(),
                request.form.get("email", "").strip(),
                request.form.get("url", "").strip(),
                request.form.get("severity", ""),
                request.form.get("problem_time", "").strip(),
                request.form.get("description", "").strip(),
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

    if severity_filter and severity_filter in SEVERITY_LEVELS:
        total = db.execute(
            "SELECT COUNT(*) FROM tickets WHERE severity = ?", (severity_filter,)
        ).fetchone()[0]
        tickets = db.execute(
            "SELECT * FROM tickets WHERE severity = ? ORDER BY submitted_at DESC LIMIT ? OFFSET ?",
            (severity_filter, PER_PAGE, (page - 1) * PER_PAGE),
        ).fetchall()
    else:
        severity_filter = ""
        total = db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        tickets = db.execute(
            "SELECT * FROM tickets ORDER BY submitted_at DESC LIMIT ? OFFSET ?",
            (PER_PAGE, (page - 1) * PER_PAGE),
        ).fetchall()

    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    return render_template(
        "ticket_list.html",
        tickets=tickets,
        page=page,
        total_pages=total_pages,
        severity_filter=severity_filter,
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
    return render_template("ticket_detail.html", ticket=ticket,
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


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
