import unittest

from research_coordinator.source_records import format_source_records, validate_source_record


class SourceRecordTests(unittest.TestCase):
    def test_validate_source_record_accepts_complete_record(self):
        record = validate_source_record(
            {
                "source_url": "https://example.com/a2a",
                "title": "A2A protocol overview",
                "retrieved_at": "2026-06-30T10:00:00Z",
                "claim": "A2A uses Agent Cards for discovery.",
                "confidence": "Medium",
            }
        )

        self.assertEqual(record["confidence"], "medium")
        self.assertEqual(record["source_url"], "https://example.com/a2a")

    def test_validate_source_record_rejects_missing_source_url(self):
        with self.assertRaisesRegex(ValueError, "source_url"):
            validate_source_record(
                {
                    "title": "A2A protocol overview",
                    "retrieved_at": "2026-06-30T10:00:00Z",
                    "claim": "A2A uses Agent Cards for discovery.",
                    "confidence": "medium",
                }
            )

    def test_format_source_records_requires_at_least_one_record(self):
        with self.assertRaisesRegex(ValueError, "At least one source record"):
            format_source_records([])

    def test_format_source_records_preserves_evidence_fields(self):
        formatted = format_source_records(
            [
                {
                    "source_url": "https://example.com/a2a",
                    "title": "A2A protocol overview",
                    "retrieved_at": "2026-06-30T10:00:00Z",
                    "claim": "A2A uses Agent Cards for discovery.",
                    "confidence": "high",
                }
            ]
        )

        self.assertIn("URL: https://example.com/a2a", formatted)
        self.assertIn("Confidence: high", formatted)
        self.assertIn("Claim: A2A uses Agent Cards for discovery.", formatted)


if __name__ == "__main__":
    unittest.main()
