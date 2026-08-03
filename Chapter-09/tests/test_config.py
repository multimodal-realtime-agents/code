import os
import unittest
from unittest.mock import patch

from chapter9_support.config import has_google_credentials


class ConfigTests(unittest.TestCase):
    def test_google_api_key_enables_model_backed_examples(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=True):
            self.assertTrue(has_google_credentials())

    def test_gemini_api_key_alone_is_not_documented_credential_path(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            self.assertFalse(has_google_credentials())

    def test_vertex_ai_environment_enables_model_backed_examples(self):
        env = {
            "GOOGLE_GENAI_USE_VERTEXAI": "1",
            "GOOGLE_CLOUD_PROJECT": "example-project",
            "GOOGLE_CLOUD_LOCATION": "us-central1",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(has_google_credentials())


if __name__ == "__main__":
    unittest.main()
