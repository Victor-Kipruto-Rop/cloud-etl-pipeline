import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil
import os
from pathlib import Path
import sqlite3
import pandas as pd
from sqlalchemy import create_engine
import runpy

from src.config import DatabaseConfig, PipelineConfig, get_config, reload_config
from src.health import HealthChecker
from src.migrations import MigrationManager
from src.pipeline import PipelineStats, process_file, run
from src.transform.transform_data import transform, handle_missing_values, normalize_columns
from src.extract.extract_data import DataExtractor, ExtractionError
from src.api import app, schedule_pipeline_job, create_app


class TestConfigCoverage(unittest.TestCase):
    def setUp(self):
        self.orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)

    def test_database_config_validation(self):
        os.environ['POSTGRES_USER'] = 'user'
        os.environ['POSTGRES_PASSWORD'] = 'pass'
        os.environ['POSTGRES_HOST'] = 'localhost'
        os.environ['POSTGRES_DB'] = 'db'
        config = DatabaseConfig()
        self.assertTrue(config.validate())
        self.assertIn('postgresql://', config.get_connection_string())

    def test_pipeline_config_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ['RAW_DATA_DIR'] = tmpdir + '/raw'
            os.environ['PROCESSED_DATA_DIR'] = tmpdir + '/processed'
            os.environ['LOG_DIR'] = tmpdir + '/logs'
            cfg = PipelineConfig()
            self.assertTrue(cfg.validate())
            self.assertTrue(cfg.raw_data_dir.exists())
            self.assertTrue(cfg.processed_data_dir.exists())
            self.assertTrue(cfg.log_dir.exists())

    def test_reload_config(self):
        os.environ['POSTGRES_DB'] = 'another_db'
        cfg2 = reload_config()
        self.assertEqual(cfg2.database.database, os.getenv('POSTGRES_DB'))


class TestHealthCoverage(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.patcher = patch('src.health.get_config')
        self.mock_get_config = self.patcher.start()
        config = MagicMock()
        config.database.get_connection_string.return_value = 'sqlite:///:memory:'
        config.pipeline.raw_data_dir = Path(self.tempdir) / 'raw'
        config.pipeline.processed_data_dir = Path(self.tempdir) / 'processed'
        config.pipeline.log_dir = Path(self.tempdir) / 'logs'
        self.mock_get_config.return_value = config
        os.makedirs(config.pipeline.raw_data_dir, exist_ok=True)
        os.makedirs(config.pipeline.processed_data_dir, exist_ok=True)
        os.makedirs(config.pipeline.log_dir, exist_ok=True)

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.tempdir)

    def test_check_database_healthy(self):
        checker = HealthChecker()
        result = checker.check_database()
        self.assertEqual(result['status'], 'healthy')

    def test_check_file_system(self):
        checker = HealthChecker()
        result = checker.check_file_system()
        self.assertEqual(result['status'], 'healthy')
        self.assertIn('raw_data', result['directories'])

    def test_check_dependencies(self):
        checker = HealthChecker()
        result = checker.check_dependencies()
        self.assertEqual(result['status'], 'healthy')
        self.assertIn('pandas', result['dependencies'])

    def test_run_all_checks(self):
        checker = HealthChecker()
        overall = checker.run_all_checks()
        self.assertIn('overall_status', overall)
        self.assertIn('checks', overall)

    def test_status_report(self):
        checker = HealthChecker()
        checker.check_dependencies()
        report = checker.get_status_report()
        self.assertIn('Health Check Report', report)


class TestMigrationsCoverage(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.engine = create_engine('sqlite:///:memory:')
        self.manager = MigrationManager(self.engine, Path(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_create_migration_and_apply(self):
        version = self.manager.create_migration('create_test', 'CREATE TABLE test (id INTEGER);')
        self.assertTrue(Path(self.manager.migrations_dir / f"{version}.sql").exists())
        self.manager.apply_migrations()
        applied = self.manager._get_applied_migrations()
        self.assertIn(version, applied)
        self.manager.status()
        self.manager.rollback(steps=1)

    def test_get_applied_migrations_empty(self):
        self.assertEqual(self.manager._get_applied_migrations(), set())


class TestPipelineCoverage(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.raw_dir = Path(self.tempdir.name) / 'data' / 'raw'
        self.proc_dir = Path(self.tempdir.name) / 'data' / 'processed'
        self.raw_dir.mkdir(parents=True)
        self.proc_dir.mkdir(parents=True)
        self.csv_file = self.raw_dir / 'sample.csv'
        pd.DataFrame({'A': [1, 2], 'B': [3, 4]}).to_csv(self.csv_file, index=False)
        self.patcher_raw = patch('src.pipeline.RAW_DIR', self.raw_dir)
        self.patcher_proc = patch('src.pipeline.PROCESSED_DIR', self.proc_dir)
        self.patcher_env = patch.dict(os.environ, {}, clear=True)
        self.patcher_raw.start()
        self.patcher_proc.start()
        self.patcher_env.start()

    def tearDown(self):
        self.patcher_raw.stop()
        self.patcher_proc.stop()
        self.patcher_env.stop()
        self.tempdir.cleanup()

    def test_run_with_no_csv_files(self):
        # remove existing file to test no files branch
        self.csv_file.unlink()
        self.assertTrue(run())

    def test_process_file_success(self):
        stats = PipelineStats()
        success = process_file(self.csv_file, stats, max_retries=1)
        self.assertTrue(success)
        self.assertEqual(stats.files_processed, 1)
        self.assertEqual(stats.rows_transformed, 2)
        self.assertEqual(stats.rows_extracted, 2)

    @patch('src.pipeline.extract_csv', side_effect=ExtractionError('fail'))
    def test_process_file_failure(self, *_): 
        stats = PipelineStats()
        result = process_file(self.csv_file, stats, max_retries=1)
        self.assertFalse(result)
        self.assertEqual(stats.files_failed, 1)


class TestTransformCoverage(unittest.TestCase):
    def test_transform_fill_mean_and_convert(self):
        df = pd.DataFrame({'num': ['1', None, '3'], 'name': ['x', 'y', 'z']})
        transformed = transform(df, normalize_cols=True, remove_dups=False, handle_missing='fill_mean', convert_types=True)
        self.assertEqual(list(transformed.columns), ['num', 'name'])
        self.assertTrue(pd.api.types.is_numeric_dtype(transformed['num']))

    def test_normalize_columns(self):
        df = pd.DataFrame({'A B': [1], 'C-D': [2]})
        result = normalize_columns(df)
        self.assertEqual(list(result.columns), ['a_b', 'c_d'])

    def test_handle_missing_values_drop_any(self):
        df = pd.DataFrame({'a': [1, None], 'b': [None, None]})
        result, removed = handle_missing_values(df, strategy='drop_any')
        self.assertEqual(removed, 2)

    def test_transform_invalid_df(self):
        with self.assertRaises(Exception):
            transform('not a df')


class TestExtractCoverage(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.tempdir.name) / 'huge.csv'
        df = pd.DataFrame({'a': range(10)})
        df.to_csv(self.csv_path, index=False)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_extract_chunked(self):
        extractor = DataExtractor()
        with patch('pathlib.Path.is_file', return_value=True), patch('pathlib.Path.stat') as mock_stat, patch('pandas.read_csv') as mock_read:
            mock_stat.return_value = MagicMock(st_size=60 * 1024 * 1024, st_mode=0o100644)
            mock_read.return_value = [pd.DataFrame({'a': [1]}), pd.DataFrame({'a': [2]})]
            result = extractor.extract_csv(self.csv_path, chunksize=1)
            self.assertEqual(len(result), 2)

    def test_extract_errors(self):
        extractor = DataExtractor()
        with patch.object(extractor, 'validate_file', side_effect=ExtractionError('missing')):
            with self.assertRaises(ExtractionError):
                extractor.extract_csv(self.csv_path)


class TestAPICoverage(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    @patch('src.api.HealthChecker')
    def test_health_endpoint(self, MockHealth):
        instance = MockHealth.return_value
        instance.run_all_checks.return_value = {'overall_status': 'healthy', 'checks': {}}
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)

    @patch('src.api.run_pipeline')
    def test_trigger_pipeline_endpoints(self, mock_run_pipeline):
        resp = self.client.post('/api/v1/pipeline/run', json={'dry_run': True})
        self.assertEqual(resp.json['status'], 'success')
        mock_run_pipeline.return_value = {'ok': True}
        resp2 = self.client.post('/api/v1/pipeline/run', json={})
        self.assertEqual(resp2.status_code, 200)

    @patch('src.api.get_config')
    def test_pipeline_config_and_status(self, mock_config):
        config = MagicMock()
        config.pipeline.raw_data_dir = Path('raw')
        config.pipeline.processed_data_dir = Path('processed')
        config.pipeline.log_dir = Path('logs')
        config.pipeline.chunk_size = 100
        config.pipeline.max_retries = 3
        config.database.host = 'localhost'
        config.database.port = 5432
        config.database.database = 'etl_db'
        config.database.get_connection_string.return_value = 'sqlite:///:memory:'
        mock_config.return_value = config
        resp = self.client.get('/api/v1/pipeline/status')
        self.assertEqual(resp.status_code, 200)
        resp2 = self.client.get('/api/v1/pipeline/config')
        self.assertEqual(resp2.status_code, 200)

    def test_schedule_and_not_found(self):
        resp = self.client.post('/api/v1/scheduler/schedule', json={'interval': 'daily'})
        self.assertEqual(resp.status_code, 200)
        resp2 = self.client.post('/api/v1/scheduler/stop')
        self.assertEqual(resp2.status_code, 200)
        resp3 = self.client.get('/not-a-route')
        self.assertEqual(resp3.status_code, 404)

    def test_schedule_pipeline_job(self):
        schedule_pipeline_job('hourly')
        schedule_pipeline_job('daily')
        schedule_pipeline_job('weekly')


if __name__ == '__main__':
    unittest.main()
