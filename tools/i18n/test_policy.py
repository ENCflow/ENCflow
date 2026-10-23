"""2026-10-23 の導入時に加えた判定(散文の除外・脚注・Notebook・範囲・構成・刻印・Git 日付)。"""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import check


class ProseTests(unittest.TestCase):
    def test_prose_after_value_is_not_an_example(self):
        self.assertIsNone(check.disabled_assignment("! gw_psif = 0 を使うこと)。"))
        self.assertIsNone(check.disabled_assignment("! q = cw h^1.5 (m3/s)"))
        self.assertIsNone(check.disabled_assignment("! west = i=1 (left edge)"))
        self.assertIsNone(check.disabled_assignment("! titype = 1 : 一様固定潮位"))

    def test_real_examples_are_kept(self):
        self.assertEqual(check.disabled_assignment("  !dt = 0.05   ! 時間刻み"), ("dt", "=", "0.05"))
        self.assertEqual(check.disabled_assignment("! fn_x = 'a.txt'"), ("fn_x", "=", "'a.txt'"))
        self.assertEqual(check.disabled_assignment("! prval(:,1) = 0, 100"),
                         ("prval", "(", ":", ",", "1", ")", "=", "0", ",", "100"))
        self.assertEqual(check.disabled_assignment("! f_x = .true."), ("f_x", "=", ".true."))

    def test_translated_prose_lines_do_not_differ(self):
        ja = "! f_evmodel = 0 でファイルを残したまま一時無効化できる。\n f_evmodel = 1"
        en = "! f_evmodel = 0 temporarily disables it while keeping the file.\n f_evmodel = 1"
        self.assertEqual(check.parameter_issues(ja, en), [])

    def test_unbalanced_parenthesis_is_prose(self):
        self.assertIsNone(check.disabled_assignment("! f_fluvial = 1)"))
        self.assertIsNotNone(check.disabled_assignment("! a(1) = (1, 2)"))

    def test_unbalanced_quote_in_prose_is_ignored(self):
        line = '!  fn_q(n) = "..."  : each line "time(min) rate(m3/s'
        self.assertIsNone(check.disabled_assignment(line))
        self.assertEqual(check.parameter_issues(line, line), [])

    def test_missing_example_is_still_reported(self):
        self.assertTrue(check.parameter_issues("!f_nh = 0\n x=1", " x=1"))

    def test_multiline_warning_only_for_real_examples(self):
        self.assertEqual(check.parameter_issues("! a = b,\n", "! a = c,\n"), [])
        self.assertTrue(check.parameter_issues("!arr = 1, 2,\n", "!arr = 1, 2,\n"))


class LinkTests(unittest.TestCase):
    def test_footnote_definition_is_not_a_link(self):
        md = "text[^k]\n\n[^k]: Author, A. (2020): Title.\n[ref]: other.md\n"
        self.assertEqual([u for _, u, _ in check.markdown_links(md)], ["other.md"])

    def test_english_legal_source_from_english_mirror(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for name in ("TRADEMARKS.md", "TRADEMARKS.ja.md", "README.ja.md"):
                (root / name).write_text("x", encoding="utf-8")
            (root / "README.md").write_text("[policy](TRADEMARKS.md)", encoding="utf-8")
            mirrors = {"TRADEMARKS.md": "TRADEMARKS.ja.md", "README.ja.md": "README.md"}
            self.assertEqual(check.link_issues(root, "README.md", "README.ja.md", mirrors, "en"), [])
            self.assertTrue(check.link_issues(root, "README.md", "README.ja.md", mirrors, "fr"))


class NotebookTests(unittest.TestCase):
    def nb(self, *codes):
        return json.dumps({"cells": [{"cell_type": "code", "source": [c], "outputs": []} for c in codes]})

    def test_comment_only_difference_allowed(self):
        a = self.nb("# 地形\nx = 1  # 格子数\ns = '''\n dt = 0.1 ! 時間刻み\n! 降雨\n'''")
        b = self.nb("# Terrain\nx = 1  # cells\ns = '''\n dt = 0.1 ! time step\n! rain\n'''")
        self.assertEqual(check.notebook_issues(a, b), [])

    def test_string_literal_difference_warns(self):
        issues = check.notebook_issues(self.nb("print('書き出した')"), self.nb("print('wrote')"))
        self.assertEqual(len(issues), 1)
        self.assertTrue(issues[0].startswith("WARN:"))

    def test_code_difference_is_error(self):
        issues = check.notebook_issues(self.nb("if a != b: x = 1"), self.nb("if a != b: x = 2"))
        self.assertTrue(issues[0].startswith("ERROR:"))

    def test_string_with_hash_is_not_a_comment(self):
        self.assertEqual(check.code_essence("s = 'a # b'  # c"), ("s = ''", ["'a # b'"]))


class RepositoryRuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def put(self, path, value="text"):
        f = self.root / path
        f.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, bytes):
            f.write_bytes(value)
        else:
            f.write_text(value, encoding="utf-8")
        return f

    def scope(self, *patterns):
        self.put(check.SCOPE, json.dumps({"version": 1, "not_required": [
            {"pattern": p, "reason": "test"} for p in patterns]}))

    def test_not_required_status_and_strict(self):
        self.put("docs/x_plan.md", "計画")
        self.put("docs/page.md", "原文")
        self.scope("docs/*_plan.md")
        rows = {r["source"]: r["status"] for r in check.audit(self.root)}
        self.assertEqual(rows, {"docs/x_plan.md": "not-required", "docs/page.md": "missing"})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(check.main(["--root", str(self.root), "audit", "--strict"]), 1)
        self.assertNotIn("x_plan", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            check.main(["--root", str(self.root), "audit", "--all"])
        self.assertIn("x_plan", out.getvalue())
        (self.root / "docs/page.md").unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check.main(["--root", str(self.root), "audit", "--strict"]), 0)

    def test_existing_translation_is_checked_despite_scope(self):
        self.put("test/a/param.txt", "x=1")
        self.put("test/a/en/param.txt", "x=2")
        self.scope("test/*/param*.txt")
        row = check.audit(self.root)[0]
        self.assertEqual(row["status"], "unreviewed")
        self.assertTrue(row["issues"][0].startswith("ERROR:"))

    def test_invalid_scope_rejected(self):
        self.put(check.SCOPE, json.dumps({"version": 1, "not_required": [{"pattern": "x"}]}))
        with self.assertRaises(ValueError):
            check.load_scope(self.root)

    def test_structure_and_stamp(self):
        self.put("docs/page.md", "# 題\n\n## 節\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
        self.put("docs/en/page.md", "# Title\n\n> English mirror of docs/page.md.\n\n| a | b |\n|---|---|\n")
        issues = check.audit(self.root)[0]["issues"]
        self.assertTrue(any("heading structure" in i for i in issues))
        self.assertTrue(any("table rows" in i for i in issues))
        self.assertFalse(any("stamp" in i for i in issues))
        self.put("docs/en/page.md", "# Title\n\n## Section\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
        issues = check.audit(self.root)[0]["issues"]
        self.assertEqual([i for i in issues if "stamp" in i], issues)
        self.put("docs/en/page.md", "# Title\n\n[日本語](../page.md)\n\n## Section\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
        self.assertEqual(check.audit(self.root)[0]["issues"], [])

    def test_fenced_headings_ignored(self):
        self.assertEqual(check.markdown_structure("```\n# not\n| a |\n|---|\n| 1 |\n```\n## yes\n"), ([2], 0))

    def test_only_real_tables_are_counted(self):
        md = "text\n|V| exceeds a threshold\n\n| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\nafter\n|Z| again\n"
        self.assertEqual(check.markdown_structure(md), ([], 4))

    def test_presentation_warning_cleared_by_review(self):
        self.put("tutorials/a/figs/a.png", b"\x89PNG\xff")
        self.put("tutorials/a/en/figs/a.png", b"\x89PNG\xfe")
        self.assertTrue(check.audit(self.root)[0]["issues"])
        check.record(self.root, "tutorials/a/figs/a.png", "tutorials/a/en/figs/a.png",
                     "test", "assistant", "2026-10-23")
        self.assertEqual(check.audit(self.root)[0]["issues"], [])

    def test_git_dates(self):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@x", GIT_COMMITTER_NAME="t",
                   GIT_COMMITTER_EMAIL="t@x", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)

        def git(*args, date):
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True,
                           env=dict(env, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date))
        git("init", "-q", date="2026-01-01T00:00:00")
        self.put("docs/page.md", "原文")
        self.put("docs/en/page.md", "English mirror of docs/page.md")
        git("add", ".", date="2026-01-01T00:00:00")
        git("commit", "-q", "-m", "both", date="2026-01-01T00:00:00")
        self.assertEqual(check.audit(self.root, git_dates=True)[0]["issues"], [])
        self.put("docs/page.md", "新しい原文")
        git("commit", "-q", "-am", "source", date="2026-02-01T00:00:00")
        issues = check.audit(self.root, git_dates=True)[0]["issues"]
        self.assertEqual(len(issues), 1)
        self.assertIn("2026-02-01 > 2026-01-01", issues[0])
        self.assertEqual(check.audit(self.root)[0]["issues"], [])


if __name__ == "__main__":
    unittest.main()
