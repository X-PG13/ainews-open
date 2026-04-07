import json
import logging
import unittest

from ainews.logging_utils import JsonFormatter, configure_logging


class LoggingUtilsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        root = logging.getLogger()
        self._level = root.level
        self._handlers = list(root.handlers)

    def tearDown(self) -> None:
        root = logging.getLogger()
        root.handlers = self._handlers
        root.setLevel(self._level)

    def test_json_formatter_serializes_known_fields(self) -> None:
        record = logging.LogRecord(
            name="ainews.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="hello",
            args=(),
            exc_info=None,
        )
        record.event = "unit.test"
        record.request_id = "req-123"
        record.status_code = 200

        payload = json.loads(JsonFormatter().format(record))

        self.assertEqual(payload["message"], "hello")
        self.assertEqual(payload["event"], "unit.test")
        self.assertEqual(payload["request_id"], "req-123")
        self.assertEqual(payload["status_code"], 200)

    def test_configure_logging_switches_formatter_and_level(self) -> None:
        configure_logging(level="DEBUG", log_format="json", force=True)

        root = logging.getLogger()

        self.assertEqual(root.level, logging.DEBUG)
        self.assertIsInstance(root.handlers[0].formatter, JsonFormatter)


if __name__ == "__main__":
    unittest.main()
