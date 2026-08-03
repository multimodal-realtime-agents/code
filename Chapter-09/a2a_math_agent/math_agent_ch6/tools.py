"""Arithmetic tools adapted from the Chapter 6 Math Agent."""

from __future__ import annotations


def add(numbers: list[int]) -> int:
    """Calculate the sum of a list of integers."""
    return sum(numbers)


def subtract(numbers: list[int]) -> int:
    """Subtract numbers in a list sequentially from left to right."""
    if not numbers:
        return 0
    result = numbers[0]
    for number in numbers[1:]:
        result -= number
    return result


def multiply(numbers: list[int]) -> int:
    """Calculate the product of a list of integers."""
    product = 1
    for number in numbers:
        product *= number
    return product


def divide(numbers: list[int]) -> float:
    """Divide numbers in a list sequentially from left to right."""
    if not numbers:
        return 0.0
    if 0 in numbers[1:]:
        raise ZeroDivisionError("Cannot divide by zero.")
    result = float(numbers[0])
    for number in numbers[1:]:
        result /= number
    return result
