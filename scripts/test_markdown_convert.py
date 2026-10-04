#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("markdown_convert.py")
SPEC = importlib.util.spec_from_file_location("markdown_convert", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class MarkdownConvertTests(unittest.TestCase):
    def test_html_writes_expected_markup_and_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "notes.md"
            source.write_text("# Hello\n\nThis is **bold** and `code`.\n\n> [!NOTE]\n> Alert note", encoding="utf-8")
            output = MODULE.convert_markdown(source, "html")
            self.assertEqual(output, Path(temp_dir, "notes.html").resolve())
            content = output.read_text(encoding="utf-8")
            self.assertIn("Hello</h1>", content)
            self.assertIn("<strong>bold</strong>", content)
            self.assertIn("<code>code</code>", content)
            self.assertIn("callout-note", content)

    def test_custom_output_path_is_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "notes.md"
            destination = Path(temp_dir) / "exports" / "notes.html"
            source.write_text("hello", encoding="utf-8")
            output = MODULE.convert_markdown(source, "html", destination)
            self.assertEqual(output, destination.resolve())
            self.assertTrue(destination.is_file())

    def test_non_markdown_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "notes.txt"
            source.write_text("hello", encoding="utf-8")
            with self.assertRaises(ValueError):
                MODULE.convert_markdown(source, "html")

    def test_codespan_with_underscores_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "notes.md"
            source.write_text("Test `my_var_name` and __bold text__ and `another_code`.", encoding="utf-8")
            output = MODULE.convert_markdown(source, "html")
            content = output.read_text(encoding="utf-8")
            self.assertIn("<code>my_var_name</code>", content)
            self.assertIn("<strong>bold text</strong>", content)
            self.assertIn("<code>another_code</code>", content)


if __name__ == "__main__":
    unittest.main()
