import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import app as flask_app


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
