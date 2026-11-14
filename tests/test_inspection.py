import unittest

from reliability_engine.inspection import inspect_response


class ResponseInspectionTests(unittest.TestCase):
    def test_clean_response(self):
        self.assertTrue(inspect_response("A normal response.").clean)

    def test_empty_response_is_flagged(self):
        self.assertIn("empty_response", inspect_response("  ").anomaly_codes)

    def test_oversized_response_is_flagged(self):
        self.assertIn("response_too_large", inspect_response("12345", max_chars=4).anomaly_codes)

    def test_repeated_long_lines_are_flagged(self):
        text = "This is a repeated diagnostic line.\nThis is a repeated diagnostic line.\nThis is a repeated diagnostic line."
        self.assertIn("repeated_lines", inspect_response(text).anomaly_codes)

    def test_non_text_is_flagged(self):
        self.assertIn("response_not_text", inspect_response(None).anomaly_codes)


if __name__ == "__main__":
    unittest.main()
