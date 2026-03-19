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
    assert b"badge-Low" in response.data
    assert b"badge-Critical" not in response.data


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
