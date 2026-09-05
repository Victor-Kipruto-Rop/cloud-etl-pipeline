import os
import time
import unittest

from src.orchestration import PipelineOrchestrator
from src.secrets import SecretManager


class TestProductionOrchestration(unittest.TestCase):
    def setUp(self):
        self.original_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_secret_manager_reads_environment(self):
        os.environ["APP_SECRET"] = "super-secret-value"
        manager = SecretManager()

        self.assertEqual(manager.get_secret("APP_SECRET"), "super-secret-value")
        self.assertEqual(
            manager.get_secret("APP_SECRET_MISSING", default="fallback-value"),
            "fallback-value",
        )

    def test_orchestrator_tracks_job_status(self):
        orchestrator = PipelineOrchestrator()

        job_id = orchestrator.start_job(
            "demo-job",
            lambda: {"status": "ok", "rows": 3},
            timeout=5,
        )

        self.assertTrue(job_id)

        deadline = time.time() + 5
        while time.time() < deadline:
            status = orchestrator.get_job_status(job_id)
            if status["status"] == "completed":
                break
            time.sleep(0.05)

        final_status = orchestrator.get_job_status(job_id)
        self.assertEqual(final_status["status"], "completed")
        self.assertEqual(final_status["result"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
