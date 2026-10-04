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

    def test_latex_and_fmath_formula_html_conversion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            md_text = """# Formula Tests
Inline TeX: $E = mc^2$ and LaTeX: \\( \\alpha + \\beta = 1 \\).
Currency isolation: Item is $50 and shipping is $10.

Block $$:
$$
\\int_0^1 x^2 dx = \\frac{1}{3}
$$

Bracket block:
\\[
\\sum_{i=1}^n i = \\frac{n(n+1)}{2}
\\]

Environment:
\\begin{align}
a &= b + c \\\\
x &= y + z
\\end{align}

Fenced latex:
```latex
\\mathbf{F} = m\\mathbf{a}
```

Fenced fmath:
```fmath-formula
\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1
```

HTML fmath tags:
<fmath>\\sqrt{x^2 + y^2}</fmath>
<fmath-formula>\\cos(\\theta)</fmath-formula>
<div class="fmath-formula">\\nabla \\cdot \\mathbf{E} = \\rho</div>
"""
            source = Path(temp_dir) / "math.md"
            source.write_text(md_text, encoding="utf-8")
            output = MODULE.convert_markdown(source, "html")
            content = output.read_text(encoding="utf-8")

            self.assertIn("katex", content)
            self.assertIn("fmath-formula", content)
            self.assertIn("katex-display", content)
            self.assertIn("katex-inline", content)
            self.assertIn("Item is $50 and shipping is $10.", content)

    def test_latex_and_fmath_formula_docx_conversion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "math.md"
            source.write_text("# Math\n\n$E = mc^2$\n\n<fmath>\\frac{a}{b}</fmath>\n", encoding="utf-8")
            output = MODULE.convert_markdown(source, "docx")
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()

