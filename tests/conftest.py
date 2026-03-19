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
