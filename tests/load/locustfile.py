"""
Load Testing Suite — Queue Management System
Run locally:  locust -f tests/load/locustfile.py --host=http://localhost:8001
CI (headless): locust -f tests/load/locustfile.py --host=$HOST \
                      --headless -u 100 -r 10 --run-time 60s \
                      --csv=reports/load --html=reports/load-report.html
"""

import random
import string
from locust import HttpUser, TaskSet, task, between, events

# ─── Helpers ────────────────────────────────────────────────────────────────────────


def random_id() -> str:
    """Generate a random Ethiopian-style ID number for load tests."""
    return "ET" + "".join(random.choices(string.digits, k=8))


def random_name() -> str:
    names = [
        "Abebe Kebede",
        "Tigist Haile",
        "Dawit Solomon",
        "Hana Tesfaye",
        "Yohannes Girma",
        "Selam Bekele",
        "Bereket Alemu",
        "Mekdes Tadesse",
        "Fiker Worku",
        "Eyob Mekonnen",
        "Rahel Gebre",
        "Natnael Desalegn",
    ]
    return random.choice(names)


SERVICE_TYPES = [
    "kebele_id",
    "birth_certificate",
    "passport_renewal",
    "business_license",
    "driver_license_renewal",
    "vehicle_registration",
    "tax_service",
    "land_registration",
    "visa_services",
    "fayda_id",
]

ADMIN_TOKEN = "test-admin-token"
COUNTER_TOKEN = "test-counter-token"
DISPLAY_TOKEN = "test-display-token"


# ─── Task Sets ──────────────────────────────────────────────────────────────────────


class PublicKioskTasks(TaskSet):
    """Simulates a self-service kiosk: citizens checking status and creating tickets."""

    def on_start(self):
        """Log in and get a JWT on session start."""
        resp = self.client.post(
            "/api/auth/token",
            json={"token": DISPLAY_TOKEN},
            name="/api/auth/token [display]",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
        else:
            self.token = DISPLAY_TOKEN

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def health_check(self):
        self.client.get("/health", name="/health")

    @task(4)
    def get_queue_status(self):
        self.client.get("/api/queue/status", headers=self._auth_headers(), name="/api/queue/status")

    @task(3)
    def create_ticket(self):
        payload = {
            "id_number": random_id(),
            "full_name": random_name(),
            "service_type": random.choice(SERVICE_TYPES),
        }
        with self.client.post(
            "/api/tickets",
            json=payload,
            headers=self._auth_headers(),
            name="/api/tickets [POST]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201, 409):  # 409 = duplicate ticket, expected
                resp.success()

    @task(3)
    def get_ticket_status(self):
        # Use a plausible ticket number pattern
        ticket_num = f"BC-{random.randint(1, 200):03d}"
        self.client.get(
            f"/api/tickets/{ticket_num}",
            headers=self._auth_headers(),
            name="/api/tickets/[ticket_number]",
        )

    @task(2)
    def list_counters(self):
        self.client.get("/api/counters", headers=self._auth_headers(), name="/api/counters")

    @task(1)
    def get_metrics(self):
        self.client.get("/metrics", name="/metrics")


class CounterStaffTasks(TaskSet):
    """Simulates a counter operator: calling, serving, completing tickets."""

    def on_start(self):
        resp = self.client.post(
            "/api/auth/token",
            json={"token": COUNTER_TOKEN},
            name="/api/auth/token [counter]",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
        else:
            self.token = COUNTER_TOKEN
        self.counter_number = random.randint(1, 5)

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def get_queue_status(self):
        self.client.get(
            "/api/queue/status", headers=self._auth_headers(), name="/api/queue/status [counter]"
        )

    @task(3)
    def call_next_ticket(self):
        with self.client.post(
            f"/api/counters/{self.counter_number}/call-next",
            headers=self._auth_headers(),
            name="/api/counters/[n]/call-next",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):  # 404 = no waiting tickets
                resp.success()

    @task(2)
    def complete_ticket(self):
        ticket_num = f"BC-{random.randint(1, 100):03d}"
        with self.client.patch(
            f"/api/tickets/{ticket_num}/complete",
            headers=self._auth_headers(),
            name="/api/tickets/[n]/complete",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()

    @task(1)
    def get_statistics(self):
        self.client.get("/api/statistics", headers=self._auth_headers(), name="/api/statistics")


class AdminTasks(TaskSet):
    """Simulates admin operations: counters, statistics, configuration."""

    def on_start(self):
        resp = self.client.post(
            "/api/auth/token",
            json={"token": ADMIN_TOKEN},
            name="/api/auth/token [admin]",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
        else:
            self.token = ADMIN_TOKEN

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(4)
    def get_statistics(self):
        self.client.get(
            "/api/statistics", headers=self._auth_headers(), name="/api/statistics [admin]"
        )

    @task(3)
    def list_counters(self):
        self.client.get("/api/counters", headers=self._auth_headers(), name="/api/counters [admin]")

    @task(2)
    def get_queue_status(self):
        self.client.get(
            "/api/queue/status", headers=self._auth_headers(), name="/api/queue/status [admin]"
        )

    @task(1)
    def get_audit_logs(self):
        self.client.get(
            "/api/audit-logs?limit=50", headers=self._auth_headers(), name="/api/audit-logs"
        )


# ─── User Classes ────────────────────────────────────────────────────────────────────


class KioskUser(HttpUser):
    """Citizen / kiosk user — majority of traffic."""

    tasks = [PublicKioskTasks]
    weight = 7
    wait_time = between(1, 3)


class CounterUser(HttpUser):
    """Counter staff — moderate traffic."""

    tasks = [CounterStaffTasks]
    weight = 2
    wait_time = between(2, 5)


class AdminUser(HttpUser):
    """Admin — low traffic."""

    tasks = [AdminTasks]
    weight = 1
    wait_time = between(5, 15)


# ─── Thresholds & CI Failure Hooks ──────────────────────────────────────────────────


@events.quitting.add_listener
def assert_thresholds(environment, **kwargs):
    """
    Fail the CI job if performance thresholds are breached.
    Thresholds (configurable via env vars in CI):
      - p95 response time  < 500 ms
      - failure rate       < 1%
    """
    stats = environment.stats.total
    if stats.num_requests == 0:
        return

    failure_rate = stats.num_failures / stats.num_requests * 100
    p95 = stats.get_response_time_percentile(0.95) or 0

    print("\n📊 Load Test Summary:")
    print(f"   Total Requests : {stats.num_requests}")
    print(f"   Failures       : {stats.num_failures} ({failure_rate:.2f}%)")
    print(f"   Avg RPS        : {stats.current_rps:.1f}")
    print(f"   p95 Latency    : {p95:.0f} ms")
    print(f"   p99 Latency    : {stats.get_response_time_percentile(0.99) or 0:.0f} ms")

    breaches = []
    if p95 > 500:
        breaches.append(f"p95 latency {p95:.0f}ms exceeds 500ms threshold")
    if failure_rate > 1.0:
        breaches.append(f"failure rate {failure_rate:.2f}% exceeds 1% threshold")

    if breaches:
        print("\n❌ Performance thresholds BREACHED:")
        for b in breaches:
            print(f"   - {b}")
        environment.process_exit_code = 1
    else:
        print("\n✅ All performance thresholds passed")
