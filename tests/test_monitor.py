import unittest

from reliability_engine.monitor import ReliabilityMonitor


class ReliabilityMonitorTests(unittest.TestCase):
    def test_context_pressure_is_disabled_without_an_explicit_budget(self):
        monitor = ReliabilityMonitor()
        monitor.api_request_started(approx_input_tokens=10_000)
        snapshot = monitor.snapshot()
        self.assertEqual(snapshot["context_budget_tokens"], None)
        self.assertEqual(snapshot["context_pressure"], "disabled")

    def test_configured_context_pressure_waits_for_first_valid_sample(self):
        monitor = ReliabilityMonitor(context_budget_tokens=65_536)
        self.assertEqual(monitor.snapshot()["context_pressure"], "waiting")
        monitor.api_request_started(approx_input_tokens=True)
        self.assertEqual(monitor.snapshot()["context_pressure"], "waiting")
        monitor.api_request_started(approx_input_tokens=10_000)
        self.assertEqual(monitor.snapshot()["context_pressure"], "normal")

    def test_context_pressure_warns_and_escalates_against_configured_budget(self):
        monitor = ReliabilityMonitor(context_budget_tokens=10_000)
        monitor.api_request_started(approx_input_tokens=7_500)
        monitor.api_request_started(approx_input_tokens=9_000)
        snapshot = monitor.snapshot()
        self.assertEqual(snapshot["context_pressure"], "critical")
        self.assertEqual(snapshot["context_warning_events"], 1)
        self.assertEqual(snapshot["context_critical_events"], 1)
        self.assertEqual(snapshot["max_context_utilization"], 0.9)

    def test_context_pressure_counts_transitions_not_repeated_requests(self):
        monitor = ReliabilityMonitor(context_budget_tokens=10_000)
        monitor.api_request_started(approx_input_tokens=9_000)
        monitor.api_request_started(approx_input_tokens=9_200)
        monitor.api_request_started(approx_input_tokens=9_500)
        self.assertEqual(monitor.snapshot()["context_critical_events"], 1)

        monitor.api_request_started(approx_input_tokens=7_500)
        monitor.api_request_started(approx_input_tokens=7_800)
        self.assertEqual(monitor.snapshot()["context_warning_events"], 1)

        monitor.api_request_started(approx_input_tokens=9_100)
        self.assertEqual(monitor.snapshot()["context_critical_events"], 2)

    def test_context_metrics_ignore_invalid_token_estimates(self):
        monitor = ReliabilityMonitor(context_budget_tokens=10_000)
        monitor.api_request_started(approx_input_tokens=-1)
        monitor.api_request_started(approx_input_tokens=True)
        snapshot = monitor.snapshot()
        self.assertEqual(snapshot["context_pressure"], "waiting")
        self.assertEqual(snapshot["context_warning_events"], 0)

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
        self.assertEqual(snapshot["average_api_latency_ms"], 25.0)
        self.assertEqual(snapshot["average_tool_latency_ms"], 10.0)
        self.assertEqual(snapshot["response_anomalies"]["repeated_lines"], 1)
        self.assertFalse(snapshot["content_capture"])
        self.assertNotIn("prompt", snapshot)
        self.assertNotIn("response", snapshot)


if __name__ == "__main__":
    unittest.main()
