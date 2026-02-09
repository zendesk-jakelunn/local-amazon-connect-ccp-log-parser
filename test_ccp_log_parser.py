"""
Unit tests for CCP Log Parser

Run tests with: python -m pytest test_ccp_log_parser.py
or: python -m unittest test_ccp_log_parser.py
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime
from ccp_log_parser import CCPLogParser, list_log_files, display_file_menu


class TestCCPLogParser(unittest.TestCase):
    """Test cases for CCPLogParser class"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()

    def _create_test_log_file(self, filename: str, log_data: list) -> Path:
        """Helper method to create a test log file"""
        log_file = self.test_dir / filename
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f)
        return log_file

    def test_init(self):
        """Test parser initialization"""
        log_file = self.test_dir / "test.txt"
        parser = CCPLogParser(log_file)

        self.assertEqual(parser.log_file_path, log_file)
        self.assertEqual(len(parser.logs), 0)
        self.assertEqual(len(parser.skew_metrics), 0)
        self.assertEqual(len(parser.snapshots), 0)
        self.assertEqual(len(parser.parse_errors), 0)

    def test_parse_valid_log_file(self):
        """Test parsing a valid log file"""
        test_data = [
            {
                "time": "2025-01-01T12:00:00.000Z",
                "level": "INFO",
                "component": "ccp",
                "text": "Test log entry",
                "line": 1
            },
            {
                "time": "2025-01-01T12:00:01.000Z",
                "level": "WARN",
                "component": "SharedWorker",
                "text": "Warning message",
                "line": 2
            }
        ]

        log_file = self._create_test_log_file("valid_log.txt", test_data)
        parser = CCPLogParser(log_file)
        parser.parse_log_file()

        self.assertEqual(len(parser.logs), 2)
        self.assertEqual(parser.logs[0]['level'], 'INFO')
        self.assertEqual(parser.logs[1]['component'], 'SharedWorker')

    def test_parse_empty_log_file(self):
        """Test parsing an empty log array"""
        log_file = self._create_test_log_file("empty_log.txt", [])
        parser = CCPLogParser(log_file)
        parser.parse_log_file()

        self.assertEqual(len(parser.logs), 0)
        self.assertEqual(len(parser.parse_errors), 0)

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON"""
        log_file = self.test_dir / "invalid.txt"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("This is not JSON")

        parser = CCPLogParser(log_file)
        parser.parse_log_file()

        self.assertEqual(len(parser.logs), 0)

    def test_extract_skew_metric(self):
        """Test skew metric extraction"""
        test_data = [
            {
                "time": "2025-01-01T12:00:00.000Z",
                "level": "INFO",
                "component": "ccp",
                "text": "Test with skew",
                "serverTimestamp": 1000,
                "clientTimestamp": 1100,
                "line": 1
            }
        ]

        log_file = self._create_test_log_file("skew_log.txt", test_data)
        parser = CCPLogParser(log_file)
        parser.parse_log_file()

        self.assertEqual(len(parser.skew_metrics), 1)
        self.assertEqual(parser.skew_metrics[0]['skew_ms'], 100)

    def test_snapshot_detection(self):
        """Test snapshot entry detection"""
        test_data = [
            {
                "time": "2025-01-01T12:00:00.000Z",
                "level": "INFO",
                "component": "ccp",
                "text": "Agent snapshot captured",
                "line": 1
            }
        ]

        log_file = self._create_test_log_file("snapshot_log.txt", test_data)
        parser = CCPLogParser(log_file)
        parser.parse_log_file()

        self.assertEqual(len(parser.snapshots), 1)

    def test_generate_readable_output(self):
        """Test readable output generation"""
        test_data = [
            {
                "time": "2025-01-01T12:00:00.000Z",
                "level": "INFO",
                "component": "ccp",
                "text": "Test entry",
                "line": 1
            }
        ]

        log_file = self._create_test_log_file("output_test.txt", test_data)
        parser = CCPLogParser(log_file)
        parser.parse_log_file()

        output_file = self.test_dir / "test_output.txt"
        result = parser.generate_readable_output(str(output_file))

        self.assertTrue(output_file.exists())
        self.assertEqual(result, str(output_file))

    def test_generate_html_output(self):
        """Test HTML output generation"""
        test_data = [
            {
                "time": "2025-01-01T12:00:00.000Z",
                "level": "INFO",
                "component": "ccp",
                "text": "Test entry",
                "line": 1
            }
        ]

        log_file = self._create_test_log_file("html_test.txt", test_data)
        parser = CCPLogParser(log_file)
        parser.parse_log_file()

        output_file = self.test_dir / "test_output.html"
        result = parser.generate_html_output(str(output_file))

        self.assertTrue(output_file.exists())
        self.assertEqual(result, str(output_file))


class TestListLogFiles(unittest.TestCase):
    """Test cases for list_log_files function"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()

    def test_list_txt_and_log_files(self):
        """Test listing .txt and .log files"""
        (self.test_dir / "test1.txt").touch()
        (self.test_dir / "test2.log").touch()
        (self.test_dir / "test3.json").touch()  # Should be ignored

        files = list_log_files(self.test_dir)

        self.assertEqual(len(files), 2)
        self.assertTrue(any(f.name == "test1.txt" for f in files))
        self.assertTrue(any(f.name == "test2.log" for f in files))

    def test_list_nonexistent_directory(self):
        """Test listing files from non-existent directory"""
        fake_dir = self.test_dir / "nonexistent"
        files = list_log_files(fake_dir)

        self.assertEqual(len(files), 0)

    def test_list_empty_directory(self):
        """Test listing files from empty directory"""
        files = list_log_files(self.test_dir)

        self.assertEqual(len(files), 0)


if __name__ == '__main__':
    unittest.main()
