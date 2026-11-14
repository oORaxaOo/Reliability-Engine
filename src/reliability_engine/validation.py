"""Deterministic structural validation for model-generated tool arguments."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationLimits:
    max_args_bytes: int = 32_768
    max_depth: int = 12
    max_items: int = 512
    max_string_chars: int = 16_384
    max_issues: int = 5


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def summary(self) -> str:
        return "; ".join(issue.message for issue in self.issues)


class ToolCallValidator:
    """Check the JSON envelope and size/complexity bounds of a tool call.

    This deliberately does not duplicate Hermes' per-tool schema validation or
    decide whether a requested action is semantically safe or appropriate.
    """

    def __init__(self, limits: ValidationLimits | None = None) -> None:
        self.limits = limits or ValidationLimits()

    def validate(self, tool_name: Any, args: Any) -> ValidationResult:
        issues: list[ValidationIssue] = []

        def add(code: str, message: str) -> None:
            if len(issues) < self.limits.max_issues:
                issues.append(ValidationIssue(code, message))

        if not isinstance(tool_name, str) or not tool_name.strip() or len(tool_name) > 128:
            add("invalid_tool_name", "Tool name is missing or invalid.")
        if not isinstance(args, dict):
            add("invalid_args_type", "Tool arguments must be a JSON object.")
            return ValidationResult(False, tuple(issues))

        item_count = 0

        def visit(value: Any, path: str, depth: int) -> None:
            nonlocal item_count
            if len(issues) >= self.limits.max_issues:
                return
            if depth > self.limits.max_depth:
                add("max_depth", f"Arguments exceed the maximum nesting depth at {path}.")
                return
            if value is None or isinstance(value, (bool, int)):
                return
            if isinstance(value, float):
                if not math.isfinite(value):
                    add("non_finite_number", f"Non-finite number at {path}.")
                return
            if isinstance(value, str):
                if len(value) > self.limits.max_string_chars:
                    add("string_too_long", f"String at {path} exceeds the configured character limit.")
                if "\x00" in value:
                    add("nul_character", f"String at {path} contains a null character.")
                return
            if isinstance(value, list):
                item_count += len(value)
                if item_count > self.limits.max_items:
                    add("too_many_items", "Arguments contain too many nested items.")
                    return
                for index, child in enumerate(value):
                    visit(child, f"{path}[{index}]", depth + 1)
                    if len(issues) >= self.limits.max_issues:
                        return
                return
            if isinstance(value, dict):
                item_count += len(value)
                if item_count > self.limits.max_items:
                    add("too_many_items", "Arguments contain too many nested items.")
                    return
                for key, child in value.items():
                    if not isinstance(key, str):
                        add("non_string_key", f"Object at {path} contains a non-string key.")
                        continue
                    if len(key) > self.limits.max_string_chars or "\x00" in key:
                        add("invalid_key", f"Object at {path} contains an invalid key.")
                        continue
                    visit(child, f"{path}.{key}", depth + 1)
                    if len(issues) >= self.limits.max_issues:
                        return
                return
            add("non_json_value", f"Arguments contain a non-JSON value at {path}.")

        visit(args, "args", 0)
        if issues:
            return ValidationResult(False, tuple(issues))

        try:
            encoded = json.dumps(
                args, ensure_ascii=False, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
            add("serialization_error", "Arguments cannot be safely serialized as JSON.")
            return ValidationResult(False, tuple(issues))

        if len(encoded) > self.limits.max_args_bytes:
            add("args_too_large", "Tool arguments exceed the configured byte limit.")
        return ValidationResult(not issues, tuple(issues))
