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


def test_update_status_redirects_to_dashboard_when_next_is_dashboard(client_with_tickets):
    """Successful status update with next=dashboard redirects back to /dashboard."""
    response = client_with_tickets.post(
        "/tickets/1/status",
        data={"status": "Pending", "next": "dashboard"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_update_status_without_next_still_redirects_to_detail(client_with_tickets):
    """Status update without next field still redirects to ticket_detail (existing behaviour)."""
    response = client_with_tickets.post(
        "/tickets/1/status",
        data={"status": "Pending"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/tickets/1" in response.headers["Location"]
