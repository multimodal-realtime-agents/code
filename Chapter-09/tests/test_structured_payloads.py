import unittest

from google.protobuf.json_format import MessageToDict

from a2a_client.structured_payloads import (
    expense_message,
    extract_data_parts,
    structured_message,
    validate_expense_fields,
)


class StructuredPayloadTests(unittest.TestCase):
    def test_structured_message_serializes_data_part(self):
        message = structured_message(
            {
                "date": "2026-06-30",
                "amount": 42.5,
                "currency": "USD",
                "purpose": "Client meeting",
            },
            message_id="message-1",
            context_id="context-1",
        )

        message_json = MessageToDict(message)

        self.assertEqual(message_json["messageId"], "message-1")
        self.assertEqual(message_json["parts"][0]["data"]["currency"], "USD")
        self.assertEqual(message_json["parts"][0]["data"]["amount"], 42.5)

    def test_extract_data_parts_returns_structured_payloads(self):
        message = structured_message(
            {"date": "2026-06-30", "currency": "USD"},
            message_id="message-1",
            context_id="context-1",
        )

        self.assertEqual(
            extract_data_parts(message),
            [{"currency": "USD", "date": "2026-06-30"}],
        )

    def test_validate_expense_fields_accepts_expected_schema(self):
        self.assertEqual(
            validate_expense_fields(
                {
                    "date": "2026-06-30",
                    "amount": 42.5,
                    "currency": "USD",
                    "purpose": "Client meeting",
                    "extra": "ignored by this contract",
                }
            ),
            {
                "date": "2026-06-30",
                "amount": 42.5,
                "currency": "USD",
                "purpose": "Client meeting",
            },
        )

    def test_validate_expense_fields_rejects_bad_currency(self):
        with self.assertRaisesRegex(ValueError, "three-letter uppercase"):
            validate_expense_fields(
                {
                    "date": "2026-06-30",
                    "amount": 42.5,
                    "currency": "usd",
                    "purpose": "Client meeting",
                }
            )

    def test_validate_expense_fields_rejects_bad_date(self):
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            validate_expense_fields(
                {
                    "date": "2026-02-31",
                    "amount": 42.5,
                    "currency": "USD",
                    "purpose": "Client meeting",
                }
            )

    def test_validate_expense_fields_rejects_empty_purpose(self):
        with self.assertRaisesRegex(ValueError, "required"):
            validate_expense_fields(
                {
                    "date": "2026-06-30",
                    "amount": 42.5,
                    "currency": "USD",
                    "purpose": " ",
                }
            )

    def test_expense_message_validates_before_serializing(self):
        with self.assertRaisesRegex(ValueError, "positive number"):
            expense_message(
                {
                    "date": "2026-06-30",
                    "amount": -1,
                    "currency": "USD",
                    "purpose": "Client meeting",
                },
                message_id="message-1",
                context_id="context-1",
            )


if __name__ == "__main__":
    unittest.main()
