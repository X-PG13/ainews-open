import unittest

from ainews.telemetry import OperationTracker


class TelemetryTestCase(unittest.TestCase):
    def test_tracker_records_operation_and_failure_category(self) -> None:
        tracker = OperationTracker()

        token = tracker.start("pipeline", context={"region": "all"})
        record = tracker.finish(
            token,
            status="partial_error",
            metrics={"total_articles": 12},
            error_category="timeout",
        )
        snapshot = tracker.snapshot()

        self.assertEqual(record["name"], "pipeline")
        self.assertEqual(record["status"], "partial_error")
        self.assertGreaterEqual(record["duration_ms"], 0)
        self.assertEqual(snapshot["operations"]["pipeline"]["context"]["region"], "all")
        self.assertEqual(snapshot["failure_categories"]["timeout"], 1)


if __name__ == "__main__":
    unittest.main()
