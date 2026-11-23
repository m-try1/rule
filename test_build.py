import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import build


class ConvertRuleTests(unittest.TestCase):
    def test_drops_surge_only_and_keeps_no_resolve(self):
        self.assertEqual(
            build.convert_rule("domain,example.com,extended-matching", "t:1"),
            "DOMAIN,example.com",
        )
        self.assertEqual(
            build.convert_rule("ip-cidr,1.2.3.0/24,pre-matching,no-resolve", "t:2"),
            "IP-CIDR,1.2.3.0/24,no-resolve",
        )

    def test_option_case_insensitivity(self):
        self.assertEqual(
            build.convert_rule("DOMAIN,example.com,EXTENDED-MATCHING", "t:3"),
            "DOMAIN,example.com",
        )
        self.assertEqual(
            build.convert_rule("IP-CIDR,10.0.0.0/8,No-Resolve", "t:4"),
            "IP-CIDR,10.0.0.0/8,no-resolve",
        )

    def test_rejects_empty_payload(self):
        with self.assertRaises(ValueError):
            build.convert_rule("DOMAIN,,extended-matching", "t:5")
        with self.assertRaises(ValueError):
            build.convert_rule("DOMAIN", "t:6")

    def test_rejects_unknown_type_and_option(self):
        with self.assertRaises(ValueError):
            build.convert_rule("URL-REGEX,^https://example\\.com", "t:7")
        with self.assertRaises(ValueError):
            build.convert_rule("DOMAIN,example.com,bogus-option", "t:8")


class ConvertLineAndBuildOneTests(unittest.TestCase):
    def test_commented_rule_and_prose_comment_safety(self):
        self.assertEqual(
            build.convert_line("# IP-CIDR,1.2.3.4/32,pre-matching,no-resolve", 1, "t"),
            "#  - IP-CIDR,1.2.3.4/32,no-resolve",
        )
        self.assertEqual(
            build.convert_line("# DOMAIN, note with comma, extra text", 2, "t"),
            "# DOMAIN, note with comma, extra text",
        )

    def test_leading_blank_lines_before_preamble(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "Sample.list"
            src.write_text(
                "\n\n# NAME: IgnoredName\n# Type:DOMAIN\n\nDOMAIN,a.example\n",
                encoding="utf-8",
            )
            rendered = build.build_one(src)
        expected = (
            "# NAME: Sample\n"
            "# Type:DOMAIN\n"
            "# Generated from Surge/Sample.list by build.py -- DO NOT EDIT\n"
            "\n"
            "payload:\n"
            "  - DOMAIN,a.example\n"
        )
        self.assertEqual(rendered, expected)


class CliTests(unittest.TestCase):
    def test_check_passes_on_repo(self):
        self.assertEqual(build.main(["--check"]), 0)

    def test_check_detects_stale_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_dir = root / "Surge"
            out_dir = root / "Clash"
            src_dir.mkdir()
            out_dir.mkdir()
            (src_dir / "Demo.list").write_text("# NAME: Demo\n\nDOMAIN,example.com\n", encoding="utf-8")

            orig_src, orig_out, orig_root = build.SRC_DIR, build.OUT_DIR, build.ROOT
            try:
                build.SRC_DIR, build.OUT_DIR, build.ROOT = src_dir, out_dir, root
                self.assertEqual(build.main(["--check"]), 1)
                self.assertEqual(build.main([]), 0)
                self.assertEqual(build.main(["--check"]), 0)
                (out_dir / "Demo.yaml").write_text("stale\n", encoding="utf-8")
                self.assertEqual(build.main(["--check"]), 1)
            finally:
                build.SRC_DIR, build.OUT_DIR, build.ROOT = orig_src, orig_out, orig_root

    def test_unknown_flag_exits_2(self):
        proc = subprocess.run(
            [sys.executable, "-B", str(Path(build.__file__).resolve()), "--bogus"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unrecognized arguments", proc.stderr)


if __name__ == "__main__":
    unittest.main()
