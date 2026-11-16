import json
import socket
import socketserver
import threading

from reliability_engine.kie_events import publish_observation, publish_runtime_snapshot


class _CaptureServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True


def _capture(tmp_path, callback):
    path = tmp_path / "kie.sock"
    received = []

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            received.append(json.loads(self.rfile.readline(65537)))
            self.wfile.write(b'{"ok":true}\n')
            self.wfile.flush()

    server = _CaptureServer(str(path), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert callback(path) is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    return received[0]


def test_runtime_observation_contains_only_allowlisted_codes(tmp_path):
    event = _capture(
        tmp_path,
        lambda path: publish_observation(
            path, kind="response_anomaly", anomaly_codes=("repeated_lines",)
        ),
    )
    assert event["event_type"] == "reliability.runtime_observation"
    assert event["payload"] == {
        "kind": "response_anomaly", "count": 1, "anomaly_codes": ["repeated_lines"]
    }
    assert "response" not in json.dumps(event["payload"])


def test_runtime_snapshot_omits_model_names_and_tool_names(tmp_path):
    event = _capture(
        tmp_path,
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
        ),
    )
    assert event["event_type"] == "reliability.runtime_snapshot"
    assert event["payload"]["model_turns"] == 9
    assert event["payload"]["anomaly_count"] == 2
    assert "private-model-label" not in json.dumps(event)
    assert "private_tool" not in json.dumps(event)
    assert "task_outcomes_by_model" not in json.dumps(event)


def test_unknown_observation_and_unavailable_socket_fail_open(tmp_path):
    assert publish_observation(tmp_path / "missing.sock", kind="unknown") is False
    assert publish_observation(None, kind="tool_call_blocked") is False


def test_raw_anomaly_values_are_rejected(tmp_path):
    assert publish_observation(
        tmp_path / "missing.sock", kind="response_anomaly", anomaly_codes=("raw response",)
    ) is False
