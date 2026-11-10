#!/usr/bin/env python3
"""tools/consistency/check.py の単体テスト(標準ライブラリのみ)"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


GUIDE_TOC = """\
# ガイド

- [骨格](#骨格)
- [時刻](users_guide/time.md) — 説明 <details><summary>解説(2 件)</summary>
  - [入門](users_guide/courant.md) — 説明
  - [方針](users_guide/policy.md) — 説明
  </details>
- [構造物](users_guide/structure.md) <details><summary>解説(1 件)</summary>
  - [水理則](users_guide/hydraulics.md) — 説明
  </details>
- [索引](users_guide/params_index.md)

---

- [本文の箇条書き](users_guide/time.md)
  - [目次ではない](users_guide/other.md)
"""

TUTORIAL_TABLE = """\
本文

| 分野(章ページ) | 詳説ページ |
|---|---|
| [時刻](users_guide/time.md) | [入門](users_guide/courant.md)(入門)、[方針](users_guide/policy.md) |
| [構造物](users_guide/structure.md)・[境界](users_guide/boundary.md) | [水理則](users_guide/hydraulics.md) |

本文
"""


def guide_repo(table=TUTORIAL_TABLE, toc=GUIDE_TOC):
    root = Path(tempfile.mkdtemp())
    write(root, "docs/users_guide.md", toc)
    write(root, "docs/en/users_guide.md", toc)
    write(root, "docs/tutorial.md", table)
    write(root, "docs/en/tutorial.md", table.replace("| 分野(章ページ) | 詳説ページ |",
                                                    "| Field (chapter page) | Explanation pages |"))
    return root


class GuideTest(unittest.TestCase):
    def test_clean_and_toc_ends_at_rule(self):
        # 水平線より後の字下げの箇条書き(other.md)は目次に数えない
        root = guide_repo()
        self.assertEqual(check.guide_explanations(root / "docs/users_guide.md"),
                         {"users_guide/courant.md": "users_guide/time.md",
                          "users_guide/policy.md": "users_guide/time.md",
                          "users_guide/hydraulics.md": "users_guide/structure.md"})
        self.assertEqual(check.check_guide(root)[0], [])

    def test_missing_extra_duplicate_and_wrong_row(self):
        bad = (TUTORIAL_TABLE.replace("、[方針](users_guide/policy.md)", "、[他](users_guide/other.md)")
               .replace("[水理則](users_guide/hydraulics.md) |", "[水理則](users_guide/hydraulics.md)、[入門](users_guide/courant.md) |"))
        errors, _ = check.check_guide(guide_repo(bad))
        self.assertTrue(any("policy.md (under users_guide/time.md" in e and "missing" in e for e in errors))
        self.assertTrue(any("other.md is not an explanation page" in e for e in errors))
        self.assertTrue(any("courant.md is listed 2 times" in e for e in errors))
        self.assertTrue(any("courant.md is under users_guide/time.md" in e and "left column" in e for e in errors))
        self.assertEqual(len([e for e in errors if e.startswith("docs/en/tutorial.md")]), 4)

    def test_table_not_found(self):
        errors, _ = check.check_guide(guide_repo(TUTORIAL_TABLE.replace("詳説ページ |", "解説 |")))
        self.assertTrue(any("docs/tutorial.md: the table" in e and "was not found" in e for e in errors))


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

    def test_removed_parameter_is_reported(self):
        # 廃止して検出だけ残す名前は宣言に数えず、設定例に書かれていたら誤り(未宣言とは別の文言)
        with mock.patch.object(check, "REMOVED", {("list_a", "ab")}):
            root = samples_repo()
            self.assertEqual(check.namelists(root)["list_a"], {"aa", "ac"})
            errors, _ = check.check_samples(root)
            self.assertTrue(any("ab was removed from namelist /list_a/" in e for e in errors))
            self.assertFalse(any("ab is not declared" in e for e in errors))
            errors, _ = check.check_samples(samples_repo(SAMPLE.replace("  !ab = 2.5         ! コメントアウトした例\n", ""),
                                                         SAMPLE.replace("  !ab = 2.5         ! コメントアウトした例\n", "")))
            self.assertEqual(errors, [])

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
