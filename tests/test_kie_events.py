import json
import socketserver
import tempfile
import threading
import unittest
from pathlib import Path

from reliability_engine.kie_events import publish_observation, publish_runtime_snapshot


class _CaptureServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True


class KIEEventPublisherTests(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)
        self.socket_path = self.root / "kie.sock"

    def _capture(self, callback):
        received = []

        class Handler(socketserver.StreamRequestHandler):
            def handle(inner_self):
                received.append(json.loads(inner_self.rfile.readline(65537)))
                inner_self.wfile.write(b'{"ok":true}\n')
                inner_self.wfile.flush()

        server = _CaptureServer(str(self.socket_path), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            self.assertTrue(callback(self.socket_path))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        return received[0]

    def test_runtime_observation_contains_only_allowlisted_codes(self):
        event = self._capture(
            lambda path: publish_observation(
                path, kind="response_anomaly", anomaly_codes=("repeated_lines",)
            )
        )
        self.assertEqual(event["event_type"], "reliability.runtime_observation")
        self.assertEqual(event["payload"], {
            "kind": "response_anomaly",
            "count": 1,
            "anomaly_codes": ["repeated_lines"],
        })

    def test_runtime_snapshot_omits_model_names_and_tool_names(self):
        event = self._capture(
            lambda path: publish_runtime_snapshot(
                path,
                {
                    "api_requests": 4, "api_successes": 3, "api_errors": 1,
                    "tool_calls": 2, "tool_blocks": 5,
                    "response_anomalies": {"repeated_lines": 2},
                    "context_pressure": "warning",
                    "context_warning_events": 1, "context_critical_events": 0,
                    "tool_calls_by_name": {"private_tool": 12},
                },
                {
                    "model_turns": {"private-model-label": 9},
                    "user_task_labels": 2,
                    "task_outcomes_by_model": {"private-model-label": {"coding": {"success": 1}}},
                },
            )
        )
        self.assertEqual(event["event_type"], "reliability.runtime_snapshot")
        self.assertEqual(event["payload"]["model_turns"], 9)
        self.assertEqual(event["payload"]["anomaly_count"], 2)
        self.assertNotIn("private-model-label", json.dumps(event))
        self.assertNotIn("private_tool", json.dumps(event))
        self.assertNotIn("task_outcomes_by_model", json.dumps(event))

    def test_unknown_observation_and_unavailable_socket_fail_open(self):
        self.assertFalse(publish_observation(self.root / "missing.sock", kind="unknown"))
        self.assertFalse(publish_observation(None, kind="tool_call_blocked"))

    def test_raw_anomaly_values_are_rejected(self):
        self.assertFalse(
            publish_observation(
                self.root / "missing.sock",
                kind="response_anomaly",
                anomaly_codes=("raw response",),
            )
        )


if __name__ == "__main__":
    unittest.main()
