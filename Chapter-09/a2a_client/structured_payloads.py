"""Build and read structured A2A data parts.

The A2A protobuf model exposes structured payloads through Part.data, which is
serialized as the wire field "data". A UI can render forms from its own schema,
but the protocol-level exchange should still be tested as a data part.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from a2a.types import Message, Part, Role
from google.protobuf import struct_pb2
from google.protobuf.json_format import MessageToDict


def data_part(fields: Mapping[str, Any]) -> Part:
    value = struct_pb2.Value()
    value.struct_value.update(dict(fields))
    return Part(data=value)


def structured_message(
    fields: Mapping[str, Any],
    *,
    message_id: str,
    context_id: str,
) -> Message:
    return Message(
        role=Role.ROLE_USER,
        message_id=message_id,
        context_id=context_id,
        parts=[data_part(fields)],
    )


def expense_message(
    fields: Mapping[str, Any],
    *,
    message_id: str,
    context_id: str,
) -> Message:
    return structured_message(
        validate_expense_fields(fields),
        message_id=message_id,
        context_id=context_id,
    )


def extract_data_parts(message: Message) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    for part in message.parts:
        if part.HasField("data"):
            extracted.append(MessageToDict(part)["data"])
    return extracted


def validate_expense_fields(fields: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the schema this chapter's structured payload example expects."""
    required = ("date", "amount", "currency", "purpose")
    missing = [name for name in required if name not in fields]
    if missing:
        raise ValueError(f"Missing required expense fields: {', '.join(missing)}")

    expense_date = fields["date"]
    if not isinstance(expense_date, str):
        raise ValueError("Expense date must be YYYY-MM-DD.")
    try:
        date.fromisoformat(expense_date)
    except ValueError:
        raise ValueError("Expense date must be YYYY-MM-DD.")

    amount = fields["amount"]
    if (
        not isinstance(amount, (int, float))
        or isinstance(amount, bool)
        or amount <= 0
    ):
        raise ValueError("Expense amount must be a positive number.")

    currency = fields["currency"]
    if (
        not isinstance(currency, str)
        or len(currency) != 3
        or not currency.isupper()
    ):
        raise ValueError("Expense currency must be a three-letter uppercase code.")

    purpose = fields["purpose"]
    if not isinstance(purpose, str) or not purpose.strip():
        raise ValueError("Expense purpose is required.")

    return {name: fields[name] for name in required}
