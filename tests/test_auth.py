"""Tests for authentication: JWT token exchange and protected routes."""


class TestTokenExchange:
    def test_exchange_valid_admin_token(self, client):
        response = client.post("/api/auth/token", json={"static_token": "test-admin-token"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in_minutes"] > 0

    def test_exchange_valid_counter_token(self, client):
        response = client.post("/api/auth/token", json={"static_token": "test-counter-token"})
        assert response.status_code == 200

    def test_exchange_invalid_token_returns_401(self, client):
        response = client.post("/api/auth/token", json={"static_token": "not-a-real-token"})
        assert response.status_code == 401

    def test_jwt_from_exchange_is_usable(self, client):
        """A JWT obtained from token exchange must work on protected endpoints."""
        token_resp = client.post("/api/auth/token", json={"static_token": "test-counter-token"})
        jwt = token_resp.json()["access_token"]

        response = client.get("/api/counters", headers={"Authorization": f"Bearer {jwt}"})
        assert response.status_code == 200


class TestProtectedRoutes:
    def test_counters_without_auth_returns_401(self, client):
        response = client.get("/api/counters")
        assert response.status_code == 401

    def test_counters_with_wrong_token_returns_401(self, client):
        response = client.get("/api/counters", headers={"Authorization": "Bearer bad-token"})
        assert response.status_code == 401

    def test_counters_with_admin_token_returns_200(self, client, admin_headers):
        response = client.get("/api/counters", headers=admin_headers)
        assert response.status_code == 200
