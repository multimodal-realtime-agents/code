import base64
import unittest

from mcp.types import ImageContent

import stock_server


class StockServerTests(unittest.TestCase):
    def test_normalize_ticker_strips_suffix_and_noise(self):
        self.assertEqual(stock_server.normalize_ticker(" nvda.us "), "NVDA")
        self.assertEqual(stock_server.normalize_ticker("msft!!!"), "MSFT")

    def test_normalize_ticker_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            stock_server.normalize_ticker(" !!! ")

    def test_stock_price_returns_deterministic_quote(self):
        quote = stock_server.get_stock_price("aapl")

        self.assertEqual(quote["symbol"], "AAPL")
        self.assertEqual(quote["name"], "Apple Inc.")
        self.assertEqual(quote["currency"], "USD")
        self.assertEqual(quote["source"], "deterministic-sample")

    def test_unknown_ticker_is_explicitly_unavailable(self):
        quote = stock_server.get_stock_price("XYZ")

        self.assertEqual(quote["symbol"], "XYZ")
        self.assertIsNone(quote["price"])
        self.assertEqual(quote["source"], "deterministic-sample-unavailable")
        self.assertIn("rather than inventing a price", quote["warning"])

    def test_company_info_resource_uses_static_metadata(self):
        info = stock_server.get_company_info("msft")

        self.assertIn("Microsoft Corp. (MSFT)", info)
        self.assertIn("Technology", info)

    def test_stock_chart_returns_valid_png_image_content(self):
        chart = stock_server.get_stock_chart("GOOGL")

        self.assertIsInstance(chart, ImageContent)
        self.assertEqual(chart.type, "image")
        self.assertEqual(chart.mimeType, "image/png")
        payload = base64.b64decode(chart.data, validate=True)
        self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
