"""Bounded, content-free profiling of model/runtime behavior."""

from __future__ import annotations

import threading
from collections import Counter
from typing import Any


ALLOWED_SIGNALS = frozenset(
    {
        "provider_error",
        "invalid_tool_call",
        "response_not_text",
        "empty_response",
        "response_too_large",
        "repeated_lines",
    }
)
TASK_CATEGORIES = frozenset(
    {"conversation", "research", "coding", "file_ops", "automation", "tool_use", "other"}
)
TASK_OUTCOMES = frozenset({"success", "partial", "failure", "unverified"})


class ModelBehaviorProfiler:
    """Collect only bounded counters; task outcomes are recorded only when explicitly labelled."""

    def __init__(
        self,
        *,
        default_model_label: str = "configured model",
        max_models: int = 8,
    ) -> None:
        self._lock = threading.RLock()
        self._default_model_label = self._clean_model_label(default_model_label) or "configured model"
        self._max_models = max(1, min(int(max_models), 32))
        self._model_turns: Counter[str] = Counter()
        self._signals_by_model: dict[str, Counter[str]] = {}
        self._task_outcomes_by_model: dict[str, dict[str, Counter[str]]] = {}
        self._user_task_labels = 0

    @staticmethod
    def _clean_model_label(value: Any) -> str:
        if not isinstance(value, str):
            return ""
        cleaned = " ".join(value.strip().split())
        return cleaned[:80]

    def _resolve_model_locked(self, model_label: Any = None) -> str:
        label = self._clean_model_label(model_label) or self._default_model_label
        known = set(self._model_turns) | set(self._signals_by_model) | set(self._task_outcomes_by_model)
        if label in known or len(known) < self._max_models:
            return label
        return "other_model"

    def record_model_turn(self, model_label: Any = None) -> None:
        with self._lock:
            self._model_turns[self._resolve_model_locked(model_label)] += 1

    def record_signal(self, signal_code: str, *, model_label: Any = None) -> None:
        if signal_code not in ALLOWED_SIGNALS:
            raise ValueError(f"Unsupported profiler signal: {signal_code}")
        with self._lock:
            model = self._resolve_model_locked(model_label)
            self._signals_by_model.setdefault(model, Counter())[signal_code] += 1

    def record_task_outcome(
        self, category: str, outcome: str, *, model_label: Any = None
    ) -> None:
        category = category.strip().lower() if isinstance(category, str) else ""
        outcome = outcome.strip().lower() if isinstance(outcome, str) else ""
        if category not in TASK_CATEGORIES:
            raise ValueError(f"Unsupported task category: {category}")
        if outcome not in TASK_OUTCOMES:
            raise ValueError(f"Unsupported task outcome: {outcome}")
        with self._lock:
            model = self._resolve_model_locked(model_label)
            by_category = self._task_outcomes_by_model.setdefault(model, {})
            by_category.setdefault(category, Counter())[outcome] += 1
            self._user_task_labels += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            signals = {
                model: dict(counts)
                for model, counts in sorted(self._signals_by_model.items())
            }
            outcomes = {
                model: {
                    category: dict(counts)
                    for category, counts in sorted(by_category.items())
                }
                for model, by_category in sorted(self._task_outcomes_by_model.items())
            }
            return {
                "model_turns": dict(sorted(self._model_turns.items())),
                "signals_by_model": signals,
                "task_outcomes_by_model": outcomes,
                "user_task_labels": self._user_task_labels,
                "automatic_task_outcome_inference": False,
                "content_capture": False,
                "retention": "in-memory aggregate counters only; reset on plugin restart",
            }
