import os
import unittest
from unittest.mock import patch
from server import create_app

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = create_app().test_client()

    def test_release_and_health(self):
        with patch.dict(os.environ, {"APP_VERSION": "test-release"}):
            self.assertEqual(self.client.get("/").json["version"], "test-release")
        for route in ("/healthz", "/readyz"):
            self.assertEqual(self.client.get(route).status_code, 200)

    def test_bounded_work_and_validation(self):
        self.assertEqual(self.client.get("/work?delay_ms=0").json["result"], "completed")
        for value in ("-1", "2001", "nope"):
            self.assertEqual(self.client.get("/work?delay_ms=" + value).status_code, 400)

    def test_canary_failure_keeps_readiness_healthy(self):
        with patch.dict(os.environ, {"APP_FAIL_WORK": "true"}):
            self.assertEqual(self.client.get("/work?delay_ms=0").status_code, 500)
            self.assertEqual(self.client.get("/readyz").status_code, 200)
        self.assertEqual(self.client.get("/work?delay_ms=0").status_code, 200)

    def test_error_is_observed(self):
        self.assertEqual(self.client.get("/error").status_code, 500)
        metrics = self.client.get("/metrics").text
        self.assertIn('portfolio_requests_total{route="/error",status="500"}', metrics)

    def test_unknown_routes_have_bounded_metric_cardinality(self):
        self.client.get("/random-id-123")
        metrics = self.client.get("/metrics").text
        self.assertIn('route="unmatched"', metrics)
        self.assertNotIn("random-id-123", metrics)

if __name__ == "__main__":
    unittest.main()
