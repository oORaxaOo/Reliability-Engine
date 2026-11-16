"""Privacy-bounded publisher for Reliability Engine operational metadata."""
from __future__ import annotations

import json
from pathlib import Path
import socket
from typing import Any, Mapping
from uuid import uuid4

_MAX_MESSAGE_BYTES = 64 * 1024
_ALLOWED_OBSERVATIONS = frozenset({"provider_error", "tool_call_blocked", "response_anomaly"})
_ALLOWED_ANOMALIES = frozenset({
    "response_not_text", "empty_response", "response_too_large", "repeated_lines",
})


def _send(socket_path: str | Path | None, event_type: str, payload: dict[str, Any]) -> bool:
    if not isinstance(socket_path, (str, Path)) or not str(socket_path).strip():
        return False
    path = Path(socket_path).expanduser()
    if not path.is_absolute():
        return False
    message = {
        "event_id": str(uuid4()),
        "engine_id": "reliability",
        "event_type": event_type,
        "payload": payload,
    }
    try:
        encoded = json.dumps(message, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > _MAX_MESSAGE_BYTES:
            return False
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(0.15)
            client.connect(str(path))
            client.sendall(encoded + b"\n")
            response = client.makefile("rb").readline(1024)
        return json.loads(response.decode("utf-8")).get("ok") is True
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def publish_observation(
    socket_path: str | Path | None,
    *,
    kind: str,
    count: int = 1,
    anomaly_codes: tuple[str, ...] | list[str] = (),
) -> bool:
    """Publish one mechanical observation without request or response content."""
    if kind not in _ALLOWED_OBSERVATIONS:
        return False
    if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 1_000_000:
        return False
    codes = list(anomaly_codes)
    if len(codes) > 4 or any(code not in _ALLOWED_ANOMALIES for code in codes):
        return False
    if (kind == "response_anomaly") != bool(codes):
        return False
    return _send(
        socket_path,
        "reliability.runtime_observation",
        {"kind": kind, "count": count, "anomaly_codes": codes},
    )


def publish_runtime_snapshot(
    socket_path: str | Path | None,
    monitor_snapshot: Mapping[str, Any],
    profiler_snapshot: Mapping[str, Any],
) -> bool:
    """Publish aggregate counters only; deliberately omit model/tool labels and content."""
    try:
        response_anomalies = monitor_snapshot["response_anomalies"]
        model_turns = profiler_snapshot["model_turns"]
        payload = {
            "api_requests": monitor_snapshot["api_requests"],
            "api_successes": monitor_snapshot["api_successes"],
            "api_errors": monitor_snapshot["api_errors"],
            "tool_calls": monitor_snapshot["tool_calls"],
            "tool_blocks": monitor_snapshot["tool_blocks"],
            "anomaly_count": sum(response_anomalies.values()),
            "context_pressure": monitor_snapshot["context_pressure"],
            "context_warning_events": monitor_snapshot["context_warning_events"],
            "context_critical_events": monitor_snapshot["context_critical_events"],
            "model_turns": sum(model_turns.values()),
            "user_task_labels": profiler_snapshot["user_task_labels"],
        }
        return _send(socket_path, "reliability.runtime_snapshot", payload)
    except (KeyError, TypeError, ValueError):
        return False


__all__ = ["publish_observation", "publish_runtime_snapshot"]
