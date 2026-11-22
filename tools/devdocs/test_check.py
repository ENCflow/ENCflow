#!/usr/bin/env python3
"""tools/devdocs/check.py の単体テスト(標準ライブラリのみ)"""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check  # noqa: E402

INDEX = """\
# 目次

本文は [developer/001.md](developer/001.md) から。

## 0. 基本方針(policy.md へ移した)

[policy.md](policy.md) にある。

## テーマ別の索引

- 現行: [§2.1](developer/002.md)

## 全節の一覧

- [§1](developer/001.md) 一つ目
- [§2](developer/002.md) 二つ目(日付)
"""
SEC1 = "## 1. 一つ目\n\n本文。[式](a (b)) と [x](…) はリンクではない。\n"
SEC2 = "## 2. 二つ目(日付)\n\n### 2.1 小節\n\n#### 2.1.1 下位\n\n### 見出しに番号のない小節\n"


def write(root: Path, name: str, body) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(body, bytes):
        path.write_bytes(body)
    else:
        path.write_text(body, encoding="utf-8")


def repo(index=INDEX, sections=None, extra=None):
    root = Path(tempfile.mkdtemp())
    write(root, "docs/developer.md", index)
    write(root, "docs/policy.md", "# 方針\n")
    write(root, "docs/developer/README.md", "# 本文\n")
    for name, body in (sections if sections is not None else {"001.md": SEC1, "002.md": SEC2}).items():
        write(root, f"docs/developer/{name}", body)
    for name, body in (extra or {}).items():
        write(root, name, body)
    return root


class IndexTests(unittest.TestCase):
    def test_clean(self):
        errors, _ = check.check_index(repo())
        self.assertEqual(errors, [])

    def test_unlisted_and_mistitled_sections(self):
        index = INDEX.replace("- [§2](developer/002.md) 二つ目(日付)\n", "")
        errors, _ = check.check_index(repo(index=index))
        self.assertTrue(any("§2" in e and "not listed" in e for e in errors), errors)
        index = INDEX.replace("二つ目(日付)\n", "二つ目\n")
        errors, _ = check.check_index(repo(index=index))
        self.assertTrue(any("title of §2 differs" in e for e in errors), errors)

    def test_order_and_wrong_file(self):
        index = INDEX.replace("- [§1](developer/001.md) 一つ目\n- [§2](developer/002.md) 二つ目(日付)\n",
                              "- [§2](developer/002.md) 二つ目(日付)\n- [§1](developer/001.md) 一つ目\n")
        errors, _ = check.check_index(repo(index=index))
        self.assertTrue(any("in order" in e for e in errors), errors)
        index = INDEX.replace("[§2](developer/002.md)", "[§2](developer/001.md)")
        errors, _ = check.check_index(repo(index=index))
        self.assertTrue(any("§2 links to developer/001.md" in e for e in errors), errors)

    def test_gap_and_stray_file(self):
        errors, _ = check.check_index(repo(sections={"001.md": SEC1, "003.md": "## 3. 三つ目\n"},
                                           extra={"docs/developer/notes.md": "x\n"}))
        self.assertTrue(any("without gaps" in e and "[2]" in e for e in errors), errors)
        self.assertTrue(any("notes.md" in e for e in errors), errors)

    def test_section_written_in_the_index(self):
        errors, _ = check.check_index(repo(index=INDEX + "\n## 3. 新しい節\n"))
        self.assertTrue(any("§3 must not be written in the index" in e for e in errors), errors)

    def test_bad_first_line_second_section_and_foreign_subsection(self):
        sections = {"001.md": "# 一つ目\n", "002.md": SEC2 + "\n### 1.5 迷い込んだ小節\n\n## 3. 次の節\n"}
        errors, _ = check.check_index(repo(sections=sections))
        self.assertTrue(any("001.md:1" in e for e in errors), errors)
        self.assertTrue(any("subsection of §1 inside §2" in e for e in errors), errors)
        self.assertTrue(any("second '## '" in e for e in errors), errors)

    def test_missing_local_link_but_not_prose(self):
        errors, _ = check.check_index(repo(sections={"001.md": SEC1 + "[図](../figs/none.png)\n",
                                                      "002.md": SEC2}))
        self.assertEqual([e for e in errors if "missing local link" in e],
                         ["docs/developer/001.md:4: missing local link: ../figs/none.png"])


class CiteTests(unittest.TestCase):
    def test_resolved_across_lines_and_comments(self):
        src = ("! 説明は developer.md\n  ! §2.1 にある\n# developer.md の §2.1.1\n"
               "[developer.md](developer.md) §2\n**developer.md §0**・developer.md §0-5\n")
        errors, notes = check.check_cites(repo(extra={"src/a.f90": src}))
        self.assertEqual(errors, [])
        self.assertIn("5 citation(s) checked", notes[0])

    def test_missing_section_and_subsection(self):
        src = "developer.md §3 と developer.md §2.2 と developer.md §2.1.2 と developer.md §2.10\n"
        errors, _ = check.check_cites(repo(extra={"docs/x.md": src}))
        self.assertEqual(len(errors), 4, errors)
        self.assertTrue(errors[0].startswith("docs/x.md:1: developer.md §3: no section"), errors)

    def test_binary_and_own_directory_are_skipped(self):
        errors, _ = check.check_cites(repo(extra={"data/a.bin": b"\xff\xfedeveloper.md \xa73",
                                                  "tools/devdocs/sample.md": "developer.md §9\n"}))
        self.assertEqual(errors, [])


class SizeTests(unittest.TestCase):
    def test_limit_and_soft_limit(self):
        big = "x" * (check.LIMIT_KB * 1024 + 1)
        soft = "## 3. 大きい節\n" + "y" * (check.SOFT_KB * 1024 + 1)
        errors, notes = check.check_size(repo(extra={"docs/big.md": big, "docs/developer/003.md": soft}))
        self.assertEqual(len(errors), 1)
        self.assertIn("docs/big.md", errors[0])
        self.assertTrue(any("003.md" in n for n in notes), notes)


class MainTests(unittest.TestCase):
    def test_exit_status(self):
        root = repo()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check.main(["--root", str(root)]), 0)
            write(root, "docs/developer/003.md", "## 3. 載っていない節\n")
            self.assertEqual(check.main(["--root", str(root), "index"]), 1)


if __name__ == "__main__":
    unittest.main()
