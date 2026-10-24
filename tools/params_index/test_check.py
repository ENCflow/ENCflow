#!/usr/bin/env python3
"""tools/params_index/check.py の単体テスト(標準ライブラリのみ)"""
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
  namelist /save_info/ save_version, nx
end module
"""
SRC_B = """\
  namelist /list_b/ ba, &
       & aa
  namelist /list_b/ ba, &
       & aa
"""


def write(root: Path, name: str, body: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def repo(rows_ja, rows_en=None, count=None, guide_count=None, pages=None):
    root = Path(tempfile.mkdtemp())
    write(root, "src/list_a.f90", SRC)
    write(root, "src/m_b.f90", SRC_B)
    n = count if count is not None else len(rows_ja)
    g = guide_count if guide_count is not None else len(rows_ja)
    write(root, check.INDEX_JA, f"# 索引\n\n(アルファベット順、全 {n} 項目)。\n\n| a | b | c |\n|---|---|---|\n" + "\n".join(rows_ja) + "\n")
    write(root, check.INDEX_EN, f"# Index\n\n(alphabetical, all\n{n} entries).\n\n| a | b | c |\n|---|---|---|\n" + "\n".join(rows_en or rows_ja) + "\n")
    write(root, check.GUIDE_JA, f"- 索引 — 全 {g} パラメータの名前→章の逆引き\n")
    write(root, check.GUIDE_EN, f"- index -- reverse lookup from all {g} parameter names\n")
    for name, body in (pages or {"a.md": "aa ab ac ba", "b.md": "ba aa"}).items():
        write(root, f"docs/users_guide/{name}", body)
        write(root, f"docs/en/users_guide/{name}", body)
    return root


ROWS = ["| aa | &list_a | [A](a.md) |", "| aa | &list_b | [B](b.md) |", "| ab | &list_a | [A](a.md) |",
        "| ac | &list_a | [A](a.md)(注) |", "| ba | &list_b | [B](b.md) |"]


class NamelistTest(unittest.TestCase):
    def test_continuation_comment_and_exclusion(self):
        groups = check.namelists(repo(ROWS))
        self.assertEqual(groups, {"list_a": ["aa", "ab", "ac"], "list_b": ["ba", "aa"]})


class CheckTest(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(check.check(repo(ROWS)), [])

    def test_missing_extra_duplicate(self):
        rows = ["| aa | &list_a | [A](a.md) |", "| aa | &list_a | [A](a.md) |", "| ab | &list_a | [A](a.md) |",
                "| ac | &list_a | [A](a.md) |", "| ba | &list_b | [B](b.md) |", "| zz | &list_b | [B](b.md) |"]
        issues = check.check(repo(rows, pages={"a.md": "aa ab ac", "b.md": "ba zz"}))
        self.assertTrue(any("duplicate row aa (&list_a)" in i for i in issues))
        self.assertTrue(any("missing aa (&list_b)" in i for i in issues))
        self.assertTrue(any("extra row zz (&list_b)" in i for i in issues))

    def test_order(self):
        rows = ROWS[:2] + [ROWS[3], ROWS[2], ROWS[4]]
        issues = check.check(repo(rows))
        self.assertEqual([i for i in issues if "out of order" in i],
                         [f"{check.INDEX_JA}:10: out of order: ab (&list_a) after ac (&list_a)"])

    def test_english_mirror_differs(self):
        en = ROWS[:4] + ["| ba | &list_b | [B](a.md) |"]
        issues = check.check(repo(ROWS, rows_en=en))
        self.assertEqual(len(issues), 1)
        self.assertIn("differs from", issues[0])

    def test_counts(self):
        issues = check.check(repo(ROWS, count=6, guide_count=4))
        self.assertEqual(len(issues), 4)
        self.assertTrue(all("states" in i for i in issues))

    def test_page_mentions_and_shorthand(self):
        pages = {"a.md": "a* の既定、ab(_c) の文字列版", "b.md": "b*、aa"}
        issues = check.check(repo(ROWS, pages=pages))
        self.assertEqual(issues, [])
        page = "dt、tt のすべてに `_c` 版があります。bc_eta_w/e/n/s"
        for name in ("dt_c", "tt_c", "bc_eta_n"):
            self.assertTrue(check.mentions(page, name), name)
        self.assertFalse(check.mentions(page, "dx_c"))
        self.assertFalse(check.mentions("dt_file", "dt"))

    def test_page_missing(self):
        issues = check.check(repo(ROWS, pages={"a.md": "aa ab ac ba"}))
        self.assertTrue(any("chapter page missing" in i for i in issues))
        self.assertTrue(any("b.md: does not mention" not in i for i in issues))


if __name__ == "__main__":
    unittest.main()
