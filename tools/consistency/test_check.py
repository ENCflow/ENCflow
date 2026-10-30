#!/usr/bin/env python3
"""tools/consistency/check.py の単体テスト(標準ライブラリのみ)"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check  # noqa: E402

SRC = """\
module list_a
  namelist /list_a/ aa, &   ! コメント
                    ab, ac
  namelist /list_b/ ba
  namelist /save_info/ save_version
end module
"""

SAMPLE = """\
! 設定例
&list_a
  ! 説明文の式 E = mc2 は代入として読まない
  aa = 1            ! 有効な行
  !ab = 2.5         ! コメントアウトした例
  !ac(1:2,1) = 0, 1
/
&list_a_2
  aa = 3
/
&list_b
  !ba = 'x.txt'
/
"""


def write(root: Path, name: str, body: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def samples_repo(ja=SAMPLE, en=None):
    root = Path(tempfile.mkdtemp())
    write(root, "src/list_a.f90", SRC)
    write(root, "examples/List_samples/list_a.txt", ja)
    write(root, "examples/List_samples/en/list_a.txt", en if en is not None else ja.replace("説明文", "prose"))
    return root


README_JA = """\
| ディレクトリ | 内容 | 機能 | 検証 |
|---|---|---|---|
| **区分** | | | |
| [a/](a/) | ケース a | 機能 | ref・解析 |
| [b/](b/) | ケース b | 機能 | 解析 |
| Scripts/ | 共通 | — | — |
"""
README_EN = """\
| Directory | Contents | Features | Verification |
|---|---|---|---|
| [a/](a/en/README.md) | case a | feature | ref, analytic |
| [b/](b/en/README.md) | case b | feature | analytic |
"""


def tests_repo(ja=README_JA, en=README_EN, dirs=("a", "b"), refs=("a",)):
    root = Path(tempfile.mkdtemp())
    for d in list(dirs) + ["Scripts"]:
        (root / "test" / d).mkdir(parents=True, exist_ok=True)
    for d in refs:
        (root / "test" / d / "reference").mkdir(parents=True, exist_ok=True)
    write(root, "test/README.md", ja)
    write(root, "test/README.en.md", en)
    return root


class SamplesTest(unittest.TestCase):
    def test_clean(self):
        errors, notes = check.check_samples(samples_repo())
        self.assertEqual(errors, [])

    def test_parse_variant_and_prose(self):
        root = samples_repo()
        items = check.sample_assignments(root / "examples/List_samples/list_a.txt", check.namelists(root))
        self.assertEqual([(g, n, i, v, a) for _no, g, n, i, v, a in items],
                         [("list_a", "aa", "", "1", True), ("list_a", "ab", "", "2.5", False),
                          ("list_a", "ac", "(1:2,1)", "0, 1", False), ("list_a", "aa", "", "3", True),
                          ("list_b", "ba", "", "'x.txt'", False)])

    def test_unknown_name_and_group(self):
        bad = SAMPLE.replace("!ab = 2.5", "!ad = 2.5").replace("&list_b", "&list_z")
        errors, _ = check.check_samples(samples_repo(bad, bad))
        self.assertTrue(any("ad is not declared in namelist /list_a/" in e for e in errors))
        self.assertTrue(any("&list_z is not a namelist group" in e for e in errors))

    def test_ja_en_differ(self):
        errors, _ = check.check_samples(samples_repo(en=SAMPLE.replace("!ab = 2.5", "!ab = 3.5")))
        self.assertTrue(any("sequence of assignments" in e and "item 2" in e for e in errors))
        errors, _ = check.check_samples(samples_repo(en=SAMPLE.replace("  !ac(1:2,1) = 0, 1\n", "")))
        self.assertTrue(any("sequence of assignments" in e for e in errors))
        errors, _ = check.check_samples(samples_repo(en=SAMPLE.replace("  aa = 1 ", "  !aa = 1")))
        self.assertTrue(any("sequence of assignments" in e for e in errors))

    def test_absent_parameters_are_info_only(self):
        errors, notes = check.check_samples(samples_repo(SAMPLE.replace("  !ba = 'x.txt'\n", ""),
                                                         SAMPLE.replace("  !ba = 'x.txt'\n", "")))
        self.assertEqual(errors, [])
        self.assertTrue(any("1 of 4 parameters appear in no settings example (list_b 1)" in n for n in notes))


class TestsTest(unittest.TestCase):
    def test_clean(self):
        errors, _ = check.check_tests(tests_repo())
        self.assertEqual(errors, [])

    def test_missing_and_extra_rows(self):
        errors, _ = check.check_tests(tests_repo(dirs=("a", "b", "c")))
        self.assertTrue(any("test/c/ is not listed" in e for e in errors))
        errors, _ = check.check_tests(tests_repo(dirs=("a",)))
        self.assertTrue(any("b/ is listed but test/b/ does not exist" in e for e in errors))

    def test_duplicate_and_en_order(self):
        dup = README_JA.replace("| [b/](b/)", "| [a/](a/) | 重複 | 機能 | ref |\n| [b/](b/)")
        errors, _ = check.check_tests(tests_repo(ja=dup))
        self.assertTrue(any("a/ is listed 2 times" in e for e in errors))
        swapped = "\n".join(README_EN.split("\n")[:2] + [README_EN.split("\n")[3], README_EN.split("\n")[2]]) + "\n"
        errors, _ = check.check_tests(tests_repo(en=swapped))
        self.assertTrue(any("differs from test/README.md from row 1" in e for e in errors))

    def test_ref_column(self):
        errors, _ = check.check_tests(tests_repo(refs=("a", "b")))
        self.assertTrue(any("b/ has reference/ but the verification column does not say ref" in e for e in errors))
        errors, _ = check.check_tests(tests_repo(refs=()))
        self.assertTrue(any("a/ says ref but has no reference/" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
