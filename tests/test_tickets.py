"""Tests for ticket lifecycle: create, retrieve, duplicate prevention."""

import uuid

import pytest


def unique_payload(service_type="immigration"):
    """Generate a payload with a unique ID to avoid duplicate-ticket errors."""
    return {
        "id_number": f"ETH-{uuid.uuid4().hex[:8]}",
        "full_name": "Tesfaye Bekele",
        "service_type": service_type,
        "phone_number": "+251911234567",
    }


class TestCreateTicket:
    def test_create_ticket_returns_201(self, client):
        response = client.post("/api/tickets", json=unique_payload())
        assert response.status_code == 201

    def test_create_ticket_has_ticket_number(self, client):
        response = client.post("/api/tickets", json=unique_payload())
        data = response.json()
        assert "ticket_number" in data
        assert len(data["ticket_number"]) > 0

    def test_create_ticket_has_queue_position(self, client):
        response = client.post("/api/tickets", json=unique_payload())
        data = response.json()
        assert data["queue_position"] >= 1

    def test_create_ticket_status_is_waiting(self, client):
        response = client.post("/api/tickets", json=unique_payload())
        assert response.json()["status"] == "waiting"

    def test_create_ticket_has_expiry(self, client):
        response = client.post("/api/tickets", json=unique_payload())
        assert "expires_at" in response.json()

    def test_create_ticket_has_qr_code(self, client):
        response = client.post("/api/tickets", json=unique_payload())
        assert response.json().get("qr_code") is not None

    def test_duplicate_ticket_returns_400(self, client):
        """Same ID number cannot have two active tickets."""
        payload = unique_payload()
        client.post("/api/tickets", json=payload)  # first ticket
        response = client.post("/api/tickets", json=payload)  # duplicate
        assert response.status_code == 400
        assert "active ticket" in response.json()["detail"].lower()

    def test_invalid_service_type_returns_422(self, client):
        payload = unique_payload()
        payload["service_type"] = "invalid_service_xyz"
        response = client.post("/api/tickets", json=payload)
        assert response.status_code == 422

    def test_missing_full_name_returns_422(self, client):
        payload = {"id_number": "ETH-TEST-999", "service_type": "immigration"}
        response = client.post("/api/tickets", json=payload)
        assert response.status_code == 422


class TestGetTicket:
    def test_get_existing_ticket(self, client):
        create_resp = client.post("/api/tickets", json=unique_payload())
        ticket_number = create_resp.json()["ticket_number"]

        response = client.get(f"/api/tickets/{ticket_number}")
        assert response.status_code == 200
        assert response.json()["ticket_number"] == ticket_number

    def test_get_nonexistent_ticket_returns_404(self, client):
        response = client.get("/api/tickets/XX-999")
        assert response.status_code == 404


class TestQueueDisplay:
    def test_queue_status_accessible_without_auth(self, client):
        response = client.get("/api/display/queue-status")
        assert response.status_code == 200

    def test_queue_status_has_waiting_count(self, client):
        data = client.get("/api/display/queue-status").json()
        assert "waiting_count" in data

    def test_waiting_tickets_endpoint(self, client):
        response = client.get("/api/display/waiting-tickets")
        assert response.status_code == 200
        data = response.json()
        assert "total_waiting" in data
        assert "tickets" in data
