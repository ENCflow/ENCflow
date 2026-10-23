"""翻訳検査の回帰テスト。モデルの回帰 reference には触れない。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import check


class LexerTests(unittest.TestCase):
    def test_comments_and_case(self):
        self.assertEqual(check.tokens('&list\n X = 1 ! 日本語\n/'),
                         check.tokens('&LIST\nx=1 ! English\n/'))

    def test_exclamation_in_string(self):
        self.assertNotEqual(check.tokens("file='a!b'"), check.tokens("file='a!c'"))

    def test_doubled_quotes(self):
        self.assertEqual(check.tokens("name='can''t!' ! 説明"), ("name", "=", "'can''t!'"))
        self.assertEqual(check.tokens('name="a""!b" !説明'), ('name', '=', '"a""!b"'))

    def test_string_space_and_case_preserved(self):
        for left, right in (("f='A'", "f='a'"), ("f='a b'", "f='ab'")):
            self.assertNotEqual(check.tokens(left), check.tokens(right))

    def test_token_boundaries(self):
        self.assertNotEqual(check.tokens('x=1 2'), check.tokens('x=12'))

    def test_values_and_order(self):
        self.assertNotEqual(check.tokens('x=1D-2'), check.tokens('x=1D-3'))
        self.assertNotEqual(check.tokens('x=1 x=2'), check.tokens('x=2 x=1'))

    def test_unterminated_quote(self):
        with self.assertRaises(ValueError):
            check.tokens("x='not closed")

    def test_disabled_assignments(self):
        a = '!dt = 0.05 ! 日本語\n dt = 0.01'
        b = '!dt = 0.05 ! English\n DT = 0.01'
        self.assertEqual(check.parameter_issues(a, b), [])
        self.assertIn('commented-out', check.parameter_issues(a, b.replace('0.05', '0.5'))[0])

    def test_activation_changes(self):
        self.assertTrue(check.parameter_issues('!x=1\nx=2', 'x=1\nx=2'))

    def test_disabled_array_assignment(self):
        self.assertTrue(check.parameter_issues('! prval(:,1)=0,1', '! prval(:,1)=0,2'))

    def test_multiline_disabled_warning(self):
        self.assertTrue(any(i.startswith('WARN:') for i in
                            check.parameter_issues('!a=1,&\n!2', '!a=1,&\n!2')))


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)

    def put(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value, encoding='utf-8')
        return p

    def review(self, s='docs/page.md', t='docs/en/page.md'):
        check.record(self.root, s, t, 'test reviewer', 'assistant', '2026-10-20')

    def test_missing_not_current(self):
        self.put('docs/page.md', '原文')
        self.assertEqual(check.audit(self.root)[0]['status'], 'missing')

    def test_existing_not_automatically_reviewed(self):
        self.put('docs/page.md', '原文')
        self.put('docs/en/page.md', 'Translation')
        self.assertEqual(check.audit(self.root)[0]['status'], 'unreviewed')
        self.assertFalse((self.root / check.REGISTRY).exists())

    def test_source_change_is_stale(self):
        self.put('docs/page.md', '原文')
        self.put('docs/en/page.md', 'Translation')
        self.review()
        self.assertEqual(check.audit(self.root)[0]['status'], 'reviewed')
        self.put('docs/page.md', '更新した原文')
        self.assertEqual(check.audit(self.root)[0]['status'], 'stale')

    def test_translation_edit_requires_review(self):
        self.put('docs/page.md', '原文')
        self.put('docs/en/page.md', 'Translation')
        self.review()
        self.put('docs/en/page.md', 'Changed')
        self.assertEqual(check.audit(self.root)[0]['status'], 'translation-changed')

    def test_missing_registered_target(self):
        self.put('docs/page.md', '原文')
        p = self.put('docs/en/page.md', 'Translation')
        self.review()
        p.unlink()
        self.assertEqual(check.audit(self.root, recorded_only=True)[0]['status'], 'missing')

    def test_missing_registered_source(self):
        p = self.put('docs/page.md', '原文')
        self.put('docs/en/page.md', 'Translation')
        self.review()
        p.unlink()
        self.assertEqual(check.audit(self.root)[0]['status'], 'missing-source')

    def test_legacy_and_case_mapping(self):
        self.put('test/README.md', '正本')
        self.put('test/README.en.md', 'English')
        self.put('test/wave/notes/detail.md', '詳細')
        pairs = check.discover(self.root, 'en')
        self.assertTrue(pairs[('test/README.md', 'test/README.en.md')])
        self.assertIn(('test/wave/notes/detail.md', 'test/wave/en/notes/detail.md'), pairs)

    def test_root_and_legal_directions(self):
        for p in ('README.md', 'README.ja.md', 'LICENSE', 'TRADEMARKS.md', 'TRADEMARKS.ja.md'):
            self.put(p, 'text')
        pairs = check.discover(self.root, 'en')
        self.assertIn(('README.ja.md', 'README.md'), pairs)
        self.assertIn(('TRADEMARKS.md', 'TRADEMARKS.ja.md'), pairs)
        self.assertNotIn(('LICENSE', 'LICENSE.ja.md'), pairs)

    def test_additional_language(self):
        self.put('docs/page.md', '日本語')
        self.put('docs/en/page.md', 'English')
        pairs = check.discover(self.root, 'fr')
        self.assertEqual(set(pairs), {('docs/page.md', 'docs/fr/page.md')})

    def test_no_record_for_mismatched_parameters(self):
        self.put('test/wave/param.txt', 'x=1')
        self.put('test/wave/en/param.txt', 'x=2')
        with self.assertRaises(ValueError):
            self.review('test/wave/param.txt', 'test/wave/en/param.txt')
        self.assertFalse((self.root / check.REGISTRY).exists())

    def test_arbitrary_registered_namelist_name(self):
        self.put('test/wave/forcing.txt', 'x=1')
        self.put('test/wave/en/forcing.txt', 'x=2')
        with self.assertRaises(ValueError):
            self.review('test/wave/forcing.txt', 'test/wave/en/forcing.txt')
        self.put('test/wave/en/forcing.txt', 'x=1 ! English')
        self.review('test/wave/forcing.txt', 'test/wave/en/forcing.txt')
        self.assertEqual(check.audit(self.root, recorded_only=True)[0]['status'], 'reviewed')

    def test_nonexistent_repository(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(check.main(['--root', str(self.root / 'missing'), 'audit']), 2)

    def test_paths_cannot_escape(self):
        with self.assertRaises(ValueError):
            check.inside(self.root, '../secret')
        with self.assertRaises(ValueError):
            check.inside(self.root, str(self.root / 'a'))

    def test_symlink_cannot_escape(self):
        (self.root / 'outside').symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaises(ValueError):
            check.inside(self.root, 'outside/a')

    def test_crlf_hashes(self):
        a = self.put('a', 'a\nb\n')
        b = self.root / 'b'
        b.write_bytes(b'a\r\nb\r\n')
        self.assertEqual(check.digest(a), check.digest(b))

    def test_cli_staging(self):
        self.put('docs/page.md', '原文')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check.main(['--root', str(self.root), 'audit']), 0)
            self.assertEqual(check.main(['--root', str(self.root), 'audit', '--strict']), 1)

    def test_strict_recorded(self):
        self.put('docs/page.md', '原文')
        self.put('docs/en/page.md', 'English')
        self.review()
        self.put('docs/page.md', '新版')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check.main(['--root', str(self.root), 'audit', '--strict-recorded']), 1)

    def test_duplicate_registry_is_invalid(self):
        self.put('docs/page.md', '原文')
        self.put('docs/en/page.md', 'Translation')
        self.review()
        data = check.load_registry(self.root)
        data['reviews'] *= 2
        self.put(check.REGISTRY, json.dumps(data))
        with self.assertRaises(ValueError):
            check.load_registry(self.root)

    def test_link_files_and_language(self):
        self.put('docs/page.md', '原文')
        self.put('docs/other.md', '参照先')
        self.put('docs/en/other.md', 'English destination')
        self.put('docs/en/page.md', '[日本語正本](../page.md)\n'
                 '[next](../other.md)\n[broken](missing.md)')
        issues = check.link_issues(self.root, 'docs/en/page.md', 'docs/page.md',
                                  {'docs/page.md': 'docs/en/page.md',
                                   'docs/other.md': 'docs/en/other.md'})
        self.assertEqual(len(issues), 2)
        self.assertTrue(issues[0].startswith('WARN:'))
        self.assertTrue(issues[1].startswith('ERROR:'))

    def test_link_parsing(self):
        md = '[caption](file(a).md "title")\n![fig](<a b.png>)\n'
        md += '[ref]: other.md\n```text\n[not](absent.md)\n```\n'
        md += '`[not](absent2.md)`\n'
        self.assertEqual([item[1] for item in check.markdown_links(md)],
                         ['file(a).md', 'a b.png', 'other.md'])

    def test_external_and_anchor_links_skipped(self):
        self.put('docs/en/page.md', '[x](https://example.org/x) [y](#section)')
        self.assertEqual(check.link_issues(self.root, 'docs/en/page.md', 'docs/page.md', {}), [])


if __name__ == '__main__':
    unittest.main()
