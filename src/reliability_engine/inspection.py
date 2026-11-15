"""Non-invasive inspection of final model responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResponseInspection:
    anomaly_codes: tuple[str, ...] = ()

    @property
    def clean(self) -> bool:
        return not self.anomaly_codes


def inspect_response(response: Any, *, max_chars: int = 100_000) -> ResponseInspection:
    """Flag simple mechanical anomalies without rewriting or judging the response."""
    codes: list[str] = []
    if not isinstance(response, str):
        return ResponseInspection(("response_not_text",))
    if not response.strip():
        codes.append("empty_response")
    if len(response) > max_chars:
        codes.append("response_too_large")

    longest_run = 0
    current_line = None
    current_run = 0
    for raw_line in response.splitlines():
        line = raw_line.strip()
        if len(line) < 12:
            current_line, current_run = None, 0
            continue
        if line == current_line:
            current_run += 1
        else:
            current_line, current_run = line, 1
        longest_run = max(longest_run, current_run)
    if longest_run >= 3:
        codes.append("repeated_lines")
    return ResponseInspection(tuple(codes))
