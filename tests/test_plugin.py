import unittest
from unittest.mock import Mock, patch
import sys
import types

from reliability_engine.plugin import register


class FakeContext:
    def __init__(self, settings=None):
        self.hooks = {}
        self.commands = {}
        self.prompt_sections = {}
        self.settings = settings or {}

    def get_config(self, key, default=None):
        return self.settings.get(key, default)

    def register_hook(self, name, callback, **kwargs):
        self.hooks[name] = callback

    def register_command(self, name, handler, **kwargs):
        self.commands[name] = handler

    def register_system_prompt_section(self, section_id, content, **kwargs):
        self.prompt_sections[section_id] = content


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.ctx = FakeContext()
        register(self.ctx)

    def test_publishes_aggregate_snapshot_to_kie_at_session_end(self):
        publisher = Mock()
        fake_kie = types.ModuleType("kie")
        fake_kie.__path__ = []
        fake_publisher_module = types.ModuleType("kie.publisher")
        fake_publisher_module.publish_reliability_snapshot = publisher
        with patch.dict(sys.modules, {"kie": fake_kie, "kie.publisher": fake_publisher_module}):
            ctx = FakeContext({"kie_database": "/tmp/kie-reliability-test.sqlite3"})
            register(ctx)
            ctx.hooks["pre_api_request"](approx_input_tokens=1234)
            ctx.hooks["post_api_request"](api_duration=0.1)
            ctx.hooks["post_llm_call"](assistant_response="Private response text", session_id="private-session")
            ctx.hooks["on_session_end"](session_id="private-session")

        publisher.assert_called_once()
        args, kwargs = publisher.call_args
        self.assertEqual(args[0], "/tmp/kie-reliability-test.sqlite3")
        self.assertEqual(args[1]["api_requests"], 1)
        self.assertEqual(args[1]["api_successes"], 1)
        self.assertEqual(args[1]["max_input_tokens"], 1234)
        self.assertEqual(args[2]["model_turns"], {})
        serialized = repr(args[1:]) + repr(kwargs)
        self.assertNotIn("Private response text", serialized)
        self.assertNotIn("private-session", serialized)

    def test_kie_publication_failure_does_not_break_session_end(self):
        publisher = Mock(side_effect=OSError("database unavailable"))
        fake_kie = types.ModuleType("kie")
        fake_kie.__path__ = []
        fake_publisher_module = types.ModuleType("kie.publisher")
        fake_publisher_module.publish_reliability_snapshot = publisher
        with patch.dict(sys.modules, {"kie": fake_kie, "kie.publisher": fake_publisher_module}):
            ctx = FakeContext({"kie_database": "/tmp/kie-reliability-test.sqlite3"})
            register(ctx)
            ctx.hooks["on_session_end"](session_id="s-safe")
        publisher.assert_called_once()

    def test_relative_kie_path_does_not_enable_publisher(self):
        ctx = FakeContext({"kie_database": "relative/kie.sqlite3"})
        register(ctx)
        self.assertNotIn("on_session_end", ctx.hooks)

    def test_registers_expected_hermes_hooks_and_status_command(self):
        self.assertIn("pre_tool_call", self.ctx.hooks)
        self.assertIn("post_llm_call", self.ctx.hooks)
        self.assertIn("api_request_error", self.ctx.hooks)
        self.assertIn("pre_auxiliary_call", self.ctx.hooks)
        self.assertIn("post_auxiliary_call", self.ctx.hooks)
        self.assertIn("reliability", self.ctx.commands)
        self.assertIn("reliability.core", self.ctx.prompt_sections)

    def test_valid_tool_call_passes(self):
        result = self.ctx.hooks["pre_tool_call"](
            tool_name="terminal", args={"command": "pwd"}, task_id="t1", session_id="s1"
        )
        self.assertIsNone(result)

    def test_invalid_tool_call_is_blocked_and_profiled_as_technical_signal(self):
        result = self.ctx.hooks["pre_tool_call"](
            tool_name="terminal", args={"command": "bad\x00command"}, task_id="t1", session_id="s1"
        )
        self.assertEqual(result["action"], "block")
        self.assertIn("null character", result["message"])
        profile = self.ctx.commands["reliability"]("profile")
        self.assertIn('"invalid_tool_call": 1', profile)

    def test_repeated_invalid_calls_trigger_session_guard(self):
        callback = self.ctx.hooks["pre_tool_call"]
        first = callback(tool_name="terminal", args={"x": "a\x00"}, session_id="s2")
        second = callback(tool_name="terminal", args={"x": "a\x00"}, session_id="s2")
        third = callback(tool_name="terminal", args={"x": "a\x00"}, session_id="s2")
        fourth = callback(tool_name="terminal", args={"x": "still\x00bad"}, session_id="s2")
        corrected = callback(tool_name="terminal", args={"x": "ok"}, session_id="s2")
        self.assertEqual(first["action"], "block")
        self.assertEqual(second["action"], "block")
        self.assertIn("limit", third["message"])
        self.assertIn("still blocking", fourth["message"])
        self.assertIsNone(corrected)

    def test_status_command_reports_privacy_and_counters(self):
        report = self.ctx.commands["reliability"]("")
        self.assertIn("RELIABILITY ENGINE STATUS", report)
        self.assertIn("Captured prompts, model responses, and tool arguments: no", report)
        self.assertIn("budget: 65536 tokens", report)

    def test_profiler_does_not_flag_uncensored_or_blunt_style(self):
        self.ctx.hooks["post_llm_call"](
            assistant_response="An uncensored answer can use blunt wording without being a technical failure.",
            session_id="s4",
            model="Gemma E4B Q4 Uncensored",
        )
        report = self.ctx.commands["reliability"]("profile")
        self.assertIn("Gemma E4B Q4 Uncensored: 1", report)
        self.assertIn("No technical signals observed", report)
        self.assertIn("Profanity/style moderation or uncensored-language scoring: none", report)

    def test_task_outcome_requires_an_explicit_command_label(self):
        self.ctx.hooks["post_llm_call"](
            assistant_response="Completed a research summary.", session_id="s5"
        )
        result = self.ctx.commands["reliability"]("label research success")
        self.assertIn("Recorded explicit task label: research = success", result)
        report = self.ctx.commands["reliability"]("profile")
        self.assertIn('"success": 1', report)
        self.assertIn("Automatic task-outcome inference: no", report)

    def test_context_budget_defaults_to_configured_65k(self):
        self.ctx.hooks["pre_api_request"](approx_input_tokens=60_000)
        report = self.ctx.commands["reliability"]("")
        self.assertIn("Context pressure: critical (budget: 65536 tokens)", report)

    def test_turn_completion_clears_invalid_call_guard(self):
        callback = self.ctx.hooks["pre_tool_call"]
        for _ in range(3):
            callback(tool_name="terminal", args={"x": "a\x00"}, session_id="s3")
        self.ctx.hooks["post_llm_call"](assistant_response="Done", session_id="s3")
        result = callback(tool_name="terminal", args={"x": "ok"}, session_id="s3")
        self.assertIsNone(result)

    def test_api_hooks_feed_privacy_safe_metrics(self):
        self.ctx.hooks["pre_api_request"](approx_input_tokens=500)
        self.ctx.hooks["post_api_request"](api_duration=0.25)
        self.ctx.hooks["api_request_error"](error_type="TimeoutError", error_message="private text")
        report = self.ctx.commands["reliability"]("")
        self.assertIn("LLM requests: 1 (success: 1, errors: 1)", report)
        self.assertIn("Average API latency: 250.0 ms", report)
        self.assertNotIn("private text", report)


if __name__ == "__main__":
    unittest.main()
