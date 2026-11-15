"""Privacy-conscious, in-memory runtime metrics (no prompts, outputs, or tool args stored)."""

from __future__ import annotations

import threading
import time
from collections import Counter, deque
from statistics import fmean
from typing import Any


class ReliabilityMonitor:
    def __init__(self, *, sample_limit: int = 100, context_budget_tokens: int | None = None) -> None:
        self._lock = threading.RLock()
        self._started = time.monotonic()
        self._api_requests = 0
        self._api_successes = 0
        self._api_errors = 0
        self._tool_calls = 0
        self._tool_blocks = 0
        self._response_anomalies: Counter[str] = Counter()
        self._error_types: Counter[str] = Counter()
        self._tool_names: Counter[str] = Counter()
        self._api_latencies: deque[float] = deque(maxlen=sample_limit)
        self._tool_latencies: deque[float] = deque(maxlen=sample_limit)
        self._input_token_estimates: deque[int] = deque(maxlen=sample_limit)
        self._max_input_tokens = 0
        self._context_budget_tokens = (
            context_budget_tokens
            if isinstance(context_budget_tokens, int)
            and not isinstance(context_budget_tokens, bool)
            and context_budget_tokens >= 1024
            else None
        )
        self._context_warning_events = 0
        self._context_critical_events = 0
        self._max_context_utilization = 0.0
        self._context_pressure = "disabled"

    def api_request_started(self, *, approx_input_tokens: Any = None) -> None:
        with self._lock:
            self._api_requests += 1
            if (
                isinstance(approx_input_tokens, int)
                and not isinstance(approx_input_tokens, bool)
                and approx_input_tokens >= 0
            ):
                self._input_token_estimates.append(approx_input_tokens)
                self._max_input_tokens = max(self._max_input_tokens, approx_input_tokens)
                if self._context_budget_tokens:
                    utilization = approx_input_tokens / self._context_budget_tokens
                    self._max_context_utilization = max(self._max_context_utilization, utilization)
                    if utilization >= 0.90:
                        self._context_pressure = "critical"
                        self._context_critical_events += 1
                    elif utilization >= 0.75:
                        self._context_pressure = "warning"
                        self._context_warning_events += 1
                    else:
                        self._context_pressure = "normal"

    def api_request_succeeded(self, *, duration_ms: Any = None) -> None:
        with self._lock:
            self._api_successes += 1
            if (
                isinstance(duration_ms, (int, float))
                and not isinstance(duration_ms, bool)
                and duration_ms >= 0
            ):
                self._api_latencies.append(float(duration_ms))

    def api_request_failed(self, *, error_type: Any = None) -> None:
        name = str(error_type or "unknown")[:80]
        with self._lock:
            self._api_errors += 1
            self._error_types[name] += 1

    def tool_call_completed(self, *, tool_name: Any = None, duration_ms: Any = None) -> None:
        name = str(tool_name or "unknown")[:80]
        with self._lock:
            self._tool_calls += 1
            self._tool_names[name] += 1
            if (
                isinstance(duration_ms, (int, float))
                and not isinstance(duration_ms, bool)
                and duration_ms >= 0
            ):
                self._tool_latencies.append(float(duration_ms))

    def tool_call_blocked(self) -> None:
        with self._lock:
            self._tool_blocks += 1

    def response_inspected(self, anomaly_codes: tuple[str, ...]) -> None:
        with self._lock:
            self._response_anomalies.update(anomaly_codes)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            api_latencies = list(self._api_latencies)
            tool_latencies = list(self._tool_latencies)
            token_samples = list(self._input_token_estimates)
            return {
                "uptime_seconds": round(time.monotonic() - self._started, 1),
                "api_requests": self._api_requests,
                "api_successes": self._api_successes,
                "api_errors": self._api_errors,
                "tool_calls": self._tool_calls,
                "tool_blocks": self._tool_blocks,
                "response_anomalies": dict(self._response_anomalies),
                "api_error_types": dict(self._error_types),
                "tool_calls_by_name": dict(self._tool_names),
                "average_api_latency_ms": round(fmean(api_latencies), 1) if api_latencies else None,
                "average_tool_latency_ms": round(fmean(tool_latencies), 1) if tool_latencies else None,
                "average_input_tokens": round(fmean(token_samples), 1) if token_samples else None,
                "max_input_tokens": self._max_input_tokens,
                "context_budget_tokens": self._context_budget_tokens,
                "context_pressure": self._context_pressure,
                "context_warning_events": self._context_warning_events,
                "context_critical_events": self._context_critical_events,
                "max_context_utilization": round(self._max_context_utilization, 4),
                "metrics_retention": "in-memory; reset when the plugin process restarts",
                "content_capture": False,
            }
