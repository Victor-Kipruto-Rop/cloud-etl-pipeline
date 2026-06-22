import unittest
from unittest.mock import patch, MagicMock
import json

from src.api import create_app


class TestAPIModule(unittest.TestCase):
    def setUp(self):
        self.app = create_app().test_client()

    @patch('src.api.HealthChecker')
    def test_health_endpoint(self, MockHealth):
        instance = MockHealth.return_value
        instance.run_all_checks.return_value = {'overall_status': 'healthy', 'checks': {}}

        resp = self.app.get('/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('overall_status', data)

    @patch('src.api.run_pipeline')
    def test_trigger_pipeline_dry_run_and_run(self, mock_run_pipeline):
        # dry run
        resp = self.app.post('/api/v1/pipeline/run', json={'dry_run': True})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'success')

        # actual run
        mock_run_pipeline.return_value = {'processed': 42}
        resp2 = self.app.post('/api/v1/pipeline/run', json={})
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertEqual(data2['status'], 'success')
        self.assertIn('result', data2)


if __name__ == '__main__':
    unittest.main()
