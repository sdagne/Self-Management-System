"""Tests for health and root endpoints."""
import pytest


class TestRootEndpoint:
    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_contains_version(self, client):
        data = response = client.get("/")
        assert "version" in response.json()

    def test_root_contains_status(self, client):
        data = client.get("/").json()
        assert data["status"] == "operational"


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_status_field(self, client):
        data = client.get("/health").json()
        assert "status" in data

    def test_health_has_checks(self, client):
        data = client.get("/health").json()
        assert "checks" in data
        assert "database" in data["checks"]

    def test_health_reports_db_ok(self, client):
        data = client.get("/health").json()
        assert data["checks"]["database"] == "ok"

    def test_health_has_timestamp(self, client):
        data = client.get("/health").json()
        assert "timestamp" in data


class TestStatusEndpoint:
    def test_status_returns_online(self, client):
        response = client.get("/status")
        assert response.status_code == 200
        assert response.json()["server"] == "online"
