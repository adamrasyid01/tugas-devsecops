import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import emit_event, normalize_request_id


class CommonTests(unittest.TestCase):
    def test_valid_request_id_is_preserved(self):
        value = "REQ-20261027-ABCDEFGH"
        self.assertEqual(normalize_request_id(value), value)

    def test_invalid_request_id_is_replaced(self):
        value = normalize_request_id("bad value with spaces")
        self.assertTrue(value.startswith("REQ-"))
        self.assertNotIn(" ", value)

    def test_sensitive_fields_are_redacted(self):
        output = io.StringIO()
        with redirect_stdout(output):
            emit_event(
                "test-service",
                "INFO",
                "test_event",
                "REQ-TEST-12345678",
                password="do-not-log",
                nested={"authorization": "Bearer example", "safe": "ok"},
            )
        record = json.loads(output.getvalue())
        self.assertEqual(record["password"], "[REDACTED]")
        self.assertEqual(record["nested"]["authorization"], "[REDACTED]")
        self.assertEqual(record["nested"]["safe"], "ok")
        self.assertNotIn("do-not-log", output.getvalue())


if __name__ == "__main__":
    unittest.main()
