import unittest

from a2a_math_agent.math_agent_ch6.tools import add, divide, multiply, subtract


class MathToolTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add([1, 2, 3]), 6)
        self.assertEqual(add([]), 0)

    def test_subtract(self):
        self.assertEqual(subtract([10, 2, 5]), 3)
        self.assertEqual(subtract([]), 0)

    def test_multiply(self):
        self.assertEqual(multiply([2, 3, 4]), 24)
        self.assertEqual(multiply([]), 1)

    def test_divide(self):
        self.assertEqual(divide([10, 2, 5]), 1.0)
        self.assertEqual(divide([]), 0.0)
        with self.assertRaises(ZeroDivisionError):
            divide([10, 0])


if __name__ == "__main__":
    unittest.main()
