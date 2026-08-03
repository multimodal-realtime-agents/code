import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROXY_DIR = Path(__file__).resolve().parents[1] / "backend" / "proxy"
sys.path.insert(0, str(PROXY_DIR))

from config import load_settings  # noqa: E402
from proxy import create_live_config  # noqa: E402


class LiveConfigTests(unittest.TestCase):
    def test_function_declarations_use_sdk_parameters_field(self):
        config = create_live_config()
        payload = config.model_dump(exclude_none=True, by_alias=True, mode="json")
        declarations = payload["tools"][0]["functionDeclarations"]

        self.assertGreaterEqual(len(declarations), 2)
        for declaration in declarations:
            self.assertIn("parameters", declaration)
            self.assertNotIn("parametersJsonSchema", declaration)
            self.assertEqual(declaration["parameters"]["type"], "OBJECT")

    def test_proxy_default_max_size_accepts_visual_context_frames(self):
        with patch.dict("os.environ", {"CHAPTER4_PROXY_MAX_SIZE": ""}):
            settings = load_settings()

        self.assertGreaterEqual(settings.proxy_max_size, 8 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
