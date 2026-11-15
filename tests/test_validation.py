import math
import unittest

from reliability_engine.validation import ToolCallValidator, ValidationLimits


class ToolCallValidatorTests(unittest.TestCase):
    def test_accepts_normal_json_arguments(self):
        result = ToolCallValidator().validate("terminal", {"command": "python -m unittest", "timeout": 10})
        self.assertTrue(result.valid)
        self.assertEqual(result.issues, ())

    def test_rejects_non_object_arguments(self):
        result = ToolCallValidator().validate("terminal", ["echo", "hi"])
        self.assertFalse(result.valid)
        self.assertEqual(result.issues[0].code, "invalid_args_type")

    def test_rejects_non_finite_numbers(self):
        result = ToolCallValidator().validate("test", {"value": math.nan})
        self.assertIn("non_finite_number", {issue.code for issue in result.issues})

    def test_rejects_null_byte(self):
        result = ToolCallValidator().validate("test", {"value": "bad\x00value"})
        self.assertIn("nul_character", {issue.code for issue in result.issues})

    def test_rejects_excessive_nesting(self):
        value = {"a": {"b": {"c": 1}}}
        validator = ToolCallValidator(ValidationLimits(max_depth=1))
        result = validator.validate("test", value)
        self.assertIn("max_depth", {issue.code for issue in result.issues})

    def test_rejects_too_many_items(self):
        validator = ToolCallValidator(ValidationLimits(max_items=2))
        result = validator.validate("test", {"a": 1, "b": 2, "c": 3})
        self.assertIn("too_many_items", {issue.code for issue in result.issues})

    def test_rejects_long_strings(self):
        validator = ToolCallValidator(ValidationLimits(max_string_chars=4))
        result = validator.validate("test", {"a": "12345"})
        self.assertIn("string_too_long", {issue.code for issue in result.issues})

    def test_rejects_large_serialized_arguments(self):
        validator = ToolCallValidator(ValidationLimits(max_args_bytes=10))
        result = validator.validate("test", {"value": "abcdefgh"})
        self.assertIn("args_too_large", {issue.code for issue in result.issues})

    def test_rejects_invalid_tool_name(self):
        result = ToolCallValidator().validate("", {})
        self.assertIn("invalid_tool_name", {issue.code for issue in result.issues})


if __name__ == "__main__":
    unittest.main()
