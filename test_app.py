import unittest
import requests
import uuid

BASE_URL = "http://localhost:8001/api"


class TestQueueManagementSystem(unittest.TestCase):

    def create_ticket(self):
        payload = {
            "id_number": f"EP{uuid.uuid4().hex[:6]}",
            "full_name": "Tesfaye Getachew",
            "service_type": "land_registration",
            "phone_number": "+251911234567",
        }
        response = requests.post(f"{BASE_URL}/tickets", json=payload)
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_create_ticket(self):
        ticket = self.create_ticket()
        self.assertIn("ticket_number", ticket)

    def test_call_next_ticket(self):
        self.create_ticket()
        counter_id = 1
        response = requests.post(f"{BASE_URL}/counters/{counter_id}/call-next")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(
            "ticket_number" in payload or payload.get("message") == "No tickets waiting",
            f"Unexpected response payload: {payload}",
        )

    def test_get_queue_status(self):
        response = requests.get(f"{BASE_URL}/display/queue-status")
        self.assertEqual(response.status_code, 200)
        self.assertIn("waiting_count", response.json())


if __name__ == "__main__":
    unittest.main()
