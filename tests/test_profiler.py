import unittest

from reliability_engine.profiler import ModelBehaviorProfiler


class ModelBehaviorProfilerTests(unittest.TestCase):
    def test_model_turns_are_counted_without_inspecting_response_text(self):
        profiler = ModelBehaviorProfiler(default_model_label="Gemma E4B Q4 Uncensored")
        profiler.record_model_turn()
        profiler.record_model_turn("Gemma E4B Q4 Uncensored")

        snapshot = profiler.snapshot()
        self.assertEqual(snapshot["model_turns"], {"Gemma E4B Q4 Uncensored": 2})
        self.assertEqual(snapshot["signals_by_model"], {})
        self.assertFalse(snapshot["content_capture"])

    def test_only_allowlisted_technical_signals_are_recorded(self):
        profiler = ModelBehaviorProfiler(default_model_label="Gemma E4B Q4 Uncensored")
        profiler.record_signal("provider_error")
        profiler.record_signal("invalid_tool_call")
        profiler.record_signal("repeated_lines")

        signals = profiler.snapshot()["signals_by_model"]["Gemma E4B Q4 Uncensored"]
        self.assertEqual(signals, {
            "provider_error": 1,
            "invalid_tool_call": 1,
            "repeated_lines": 1,
        })

    def test_task_outcomes_require_explicit_user_labels(self):
        profiler = ModelBehaviorProfiler(default_model_label="Gemma E4B Q4 Uncensored")
        profiler.record_task_outcome("research", "success")
        profiler.record_task_outcome("coding", "partial")
        profiler.record_task_outcome("research", "failure")

        outcomes = profiler.snapshot()["task_outcomes_by_model"]["Gemma E4B Q4 Uncensored"]
        self.assertEqual(outcomes["research"], {"success": 1, "failure": 1})
        self.assertEqual(outcomes["coding"], {"partial": 1})
        self.assertFalse(profiler.snapshot()["automatic_task_outcome_inference"])

    def test_unknown_signal_category_and_outcome_are_rejected(self):
        profiler = ModelBehaviorProfiler()
        with self.assertRaises(ValueError):
            profiler.record_signal("profanity_detected")
        with self.assertRaises(ValueError):
            profiler.record_task_outcome("uncensored_style", "success")
        with self.assertRaises(ValueError):
            profiler.record_task_outcome("research", "unsafe")

    def test_model_labels_and_model_count_are_bounded(self):
        profiler = ModelBehaviorProfiler(default_model_label="Gemma", max_models=2)
        profiler.record_model_turn("Model A")
        profiler.record_model_turn("Model B")
        profiler.record_model_turn("Model C")
        snapshot = profiler.snapshot()
        self.assertIn("other_model", snapshot["model_turns"])
        self.assertLessEqual(len(snapshot["model_turns"]), 3)


if __name__ == "__main__":
    unittest.main()
