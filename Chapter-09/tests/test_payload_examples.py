import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from a2a_client.image_handler import (
    extract_files,
    inline_file_artifact,
    save_inline_files,
    url_file_artifact,
)


class PayloadExampleTests(unittest.TestCase):
    def test_extracts_inline_file_artifact(self):
        artifact = inline_file_artifact("example.txt", b"hello", "text/plain")
        files = extract_files(artifact)

        self.assertEqual(files[0].filename, "example.txt")
        self.assertEqual(files[0].media_type, "text/plain")
        self.assertEqual(files[0].data, b"hello")

    def test_extracts_url_file_artifact(self):
        artifact = url_file_artifact("example.txt", "https://example.com/example.txt", "text/plain")
        files = extract_files(artifact)

        self.assertEqual(files[0].filename, "example.txt")
        self.assertEqual(files[0].media_type, "text/plain")
        self.assertEqual(files[0].url, "https://example.com/example.txt")

    def test_save_inline_files_sanitizes_filename(self):
        artifact = inline_file_artifact(r"..\unsafe path/report?.txt", b"hello", "text/plain")

        with TemporaryDirectory() as temp_dir:
            saved_paths = save_inline_files(artifact, Path(temp_dir))

            self.assertEqual(saved_paths[0].name, "received_report_.txt")
            self.assertEqual(saved_paths[0].read_bytes(), b"hello")


if __name__ == "__main__":
    unittest.main()
