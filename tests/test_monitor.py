import unittest

from reliability_engine.monitor import ReliabilityMonitor


class ReliabilityMonitorTests(unittest.TestCase):
    def test_aggregates_metrics_without_content(self):
        monitor = ReliabilityMonitor()
        monitor.api_request_started(approx_input_tokens=123)
        monitor.api_request_succeeded(duration_ms=25.0)
        monitor.api_request_failed(error_type="TimeoutError")
        monitor.tool_call_completed(tool_name="terminal", duration_ms=10.0)
        monitor.tool_call_blocked()
        monitor.response_inspected(("repeated_lines",))

        snapshot = monitor.snapshot()
        self.assertEqual(snapshot["api_requests"], 1)
        self.assertEqual(snapshot["api_successes"], 1)
        self.assertEqual(snapshot["api_errors"], 1)
        self.assertEqual(snapshot["tool_calls"], 1)
        self.assertEqual(snapshot["tool_blocks"], 1)
        self.assertEqual(snapshot["max_input_tokens"], 123)
        self.assertEqual(snapshot["response_anomalies"]["repeated_lines"], 1)
        self.assertFalse(snapshot["content_capture"])
        self.assertNotIn("prompt", snapshot)
        self.assertNotIn("response", snapshot)


if __name__ == "__main__":
    unittest.main()
