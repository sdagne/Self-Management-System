"""Tests for counter management endpoints."""

import pytest


def counter_payload(number: int):
    return {
        "counter_number": number,
        "counter_name": f"Counter {number}",
        "service_types": ["immigration", "passport_renewal"],
        "staff_name": "Almaz Tadesse",
    }


class TestCreateCounter:
    def test_create_counter_returns_200(self, client, admin_headers):
        response = client.post("/api/counters", json=counter_payload(901), headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["counter_number"] == 901

    def test_create_duplicate_counter_returns_400(self, client, admin_headers):
        client.post("/api/counters", json=counter_payload(902), headers=admin_headers)
        response = client.post("/api/counters", json=counter_payload(902), headers=admin_headers)
        assert response.status_code == 400

    def test_create_counter_without_auth_returns_401(self, client):
        response = client.post("/api/counters", json=counter_payload(903))
        assert response.status_code == 401


class TestListCounters:
    def test_list_counters_returns_list(self, client, admin_headers):
        response = client.get("/api/counters", headers=admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestCallNextTicket:
    def test_call_next_with_no_tickets(self, client, admin_headers):
        """Call-next on an empty queue should return a graceful message."""
        # Create a counter for a service that has no tickets
        client.post(
            "/api/counters",
            json={
                "counter_number": 999,
                "counter_name": "Empty Counter",
                "service_types": ["health_services"],
                "staff_name": "Test Staff",
            },
            headers=admin_headers,
        )
        # Find the counter id
        counters = client.get("/api/counters", headers=admin_headers).json()
        counter = next((c for c in counters if c["counter_number"] == 999), None)
        assert counter is not None

        response = client.post(f"/api/counters/{counter['id']}/call-next", headers=admin_headers)
        assert response.status_code == 200
        assert "No tickets waiting" in response.json().get("message", "")


class TestStatistics:
    def test_statistics_returns_200(self, client, admin_headers):
        response = client.get("/api/statistics", headers=admin_headers)
        assert response.status_code == 200

    def test_statistics_has_required_fields(self, client, admin_headers):
        data = client.get("/api/statistics", headers=admin_headers).json()
        assert "total_tickets_today" in data
        assert "total_served_today" in data
        assert "total_waiting" in data
        assert "active_counters" in data
