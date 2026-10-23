"""2026-10-23構成への追随で追加した検査。モデルを実行しない。"""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import check


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def put(self, path, value='text'):
        f = self.root / path
        f.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, bytes): f.write_bytes(value)
        else: f.write_text(value, encoding='utf-8')
        return f

    def review(self, source, target):
        check.record(self.root, source, target, 'test', 'assistant', '2026-10-23')

    def test_nested_independent_case(self):
        self.put('examples/benchmark/slope/Makefile')
        self.put('examples/benchmark/slope/README.md')
        self.assertIn(('examples/benchmark/slope/README.md',
                       'examples/benchmark/slope/en/README.md'), check.discover(self.root, 'en'))

    def test_notes_belong_to_nearest_case(self):
        self.put('examples/a/Makefile')
        self.put('examples/a/notes/details.md')
        self.assertIn(('examples/a/notes/details.md', 'examples/a/en/notes/details.md'),
                      check.discover(self.root, 'en'))

    def test_existing_nested_mirror_without_makefile(self):
        self.put('examples/group/a/README.md')
        self.put('examples/group/a/en/README.md')
        self.assertIn(('examples/group/a/README.md', 'examples/group/a/en/README.md'),
                      check.discover(self.root, 'en'))

    def test_bmi_legacy(self):
        self.put('bmi/README.md'); self.put('bmi/README.en.md')
        self.assertTrue(check.discover(self.root, 'en')[('bmi/README.md','bmi/README.en.md')])

    def test_utils_unit(self):
        self.put('utils/tool/Makefile'); self.put('utils/tool/README.md')
        self.assertIn(('utils/tool/README.md', 'utils/tool/en/README.md'),
                      check.discover(self.root, 'en'))

    def test_vendor_excluded(self):
        self.put('bmi/vendor/README.md')
        self.assertFalse(check.discover(self.root, 'en'))

    def test_generated_output_excluded(self):
        for path in ('test/a/result/param.txt', 'test/a/result_vmax/README.md',
                     'test/a/reference/param.txt', 'test/a/save_new/notes.md'):
            self.put(path)
        self.assertFalse(check.discover(self.root, 'en'))

    def test_shared_figure_not_translation_candidate(self):
        self.put('tutorials/a/figs/a.png', b'\x89PNG\xff')
        self.assertFalse(check.discover(self.root, 'en'))

    def test_existing_translated_figures_discovered(self):
        self.put('tutorials/a/figs/a.png', b'\x89PNG\xff')
        self.put('tutorials/a/en/figs/a.png', b'\x89PNG\xfe')
        rows=check.audit(self.root)
        self.assertEqual(rows[0]['kind'], 'presentation')
        self.assertTrue(rows[0]['issues'][0].startswith('WARN:'))

    def test_translated_plot_script(self):
        self.put('tutorials/a/Fig.plt', "set title '図'")
        self.put('tutorials/a/en/Fig.plt', "set title 'Figure'")
        self.assertIn(('tutorials/a/Fig.plt', 'tutorials/a/en/Fig.plt'),
                      check.discover(self.root, 'en'))

    def test_binary_review_and_change(self):
        a='docs/figs/a.png';b='docs/en/figs/a.png'
        self.put(a,b'\xff\x00');self.put(b,b'\xff\x01')
        self.review(a,b)
        self.assertEqual(check.audit(self.root)[0]['status'],'reviewed')
        self.put(a,b'\xfe\x00')
        self.assertEqual(check.audit(self.root)[0]['status'],'stale')

    def test_no_cross_language_review_leak(self):
        self.put('docs/a.md');self.put('docs/en/a.md');self.review('docs/a.md','docs/en/a.md')
        rows=check.audit(self.root,'fr')
        self.assertEqual([r['target'] for r in rows],['docs/fr/a.md'])
        self.assertEqual(check.audit(self.root,'fr',recorded_only=True),[])

    def test_region_locale_not_source(self):
        self.put('docs/a.md');self.put('docs/zh-CN/a.md')
        self.assertEqual(len(check.discover(self.root,'en')),1)

    def test_orphan_unregistered_mirror(self):
        self.put('docs/en/lost.md')
        self.assertEqual(check.audit(self.root)[0]['status'],'missing-source')

    def test_duplicate_bodies(self):
        for p in ('test/README.md','test/README.en.md','test/en/README.md'):self.put(p)
        self.assertTrue(any('duplicate' in i for i in check.audit(self.root)[0]['issues']))

    def test_legacy_stub_allowed(self):
        self.put('test/README.md'); self.put('test/en/README.md', '[日本語](../README.md)')
        self.put('test/README.en.md','<!-- i18n-redirect -->\n[English](en/README.md)')
        self.assertEqual(check.audit(self.root)[0]['issues'],[])

    def test_shared_run_script_copy_is_error(self):
        self.put('test/a/en/Run.sh')
        self.assertEqual(check.audit(self.root)[0]['status'],'shared-copy')

    def test_shared_data_copy_is_error(self):
        self.put('tutorials/a/en/data/dem.tif',b'123')
        self.assertEqual(check.audit(self.root)[0]['status'],'shared-copy')

    def nb(self, markdown='原文', code='print(1)', outputs=None):
        return json.dumps({'cells':[{'cell_type':'markdown','source':[markdown]},
            {'cell_type':'code','source':[code],'outputs':outputs or []}]})

    def test_notebook_translation_keeps_code(self):
        self.assertEqual(check.notebook_issues(self.nb(),self.nb('English')),[])

    def test_notebook_code_change_detected(self):
        self.assertTrue(check.notebook_issues(self.nb(),self.nb('English','print(2)'))[0].startswith('ERROR:'))

    def test_notebook_outputs_warn(self):
        self.assertTrue(check.notebook_issues(self.nb(),self.nb(outputs=[{'text':'1'}]))[0].startswith('WARN:'))

    def test_notebook_cell_structure_detected(self):
        b=json.loads(self.nb());b['cells'].reverse()
        self.assertTrue(check.notebook_issues(self.nb(),json.dumps(b))[0].startswith('ERROR:'))

    def test_invalid_notebook(self):
        with self.assertRaises(ValueError):check.notebook_issues('{"cells":[1]}',self.nb())

    def test_notebook_record_refuses_code_change(self):
        self.put('docs/a.ipynb',self.nb());self.put('docs/en/a.ipynb',self.nb('English','print(2)'))
        with self.assertRaises(ValueError):self.review('docs/a.ipynb','docs/en/a.ipynb')

    def test_notebook_discovered(self):
        self.put('docs/a.ipynb',self.nb())
        self.assertIn(('docs/a.ipynb','docs/en/a.ipynb'),check.discover(self.root,'en'))

    def test_wrong_authority_rejected(self):
        self.put('docs/en/a.md');self.put('docs/a.md')
        with self.assertRaises(ValueError):self.review('docs/en/a.md','docs/a.md')

    def test_legal_reverse_rejected(self):
        self.put('TRADEMARKS.md');self.put('TRADEMARKS.ja.md')
        with self.assertRaises(ValueError):self.review('TRADEMARKS.ja.md','TRADEMARKS.md')

    def test_legal_correct_direction(self):
        self.put('TRADEMARKS.md');self.put('TRADEMARKS.ja.md')
        self.review('TRADEMARKS.md','TRADEMARKS.ja.md')
        self.assertEqual(check.audit(self.root)[0]['status'],'reviewed')
        self.assertFalse(check.audit(self.root,'fr'))

    def test_git_ignored_scratch_excluded(self):
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        self.put('.gitignore','docs/scratch/\n')
        self.put('docs/scratch/a.md');self.put('docs/a.md')
        self.assertEqual(len(check.discover(self.root,'en')),1)

    def test_single_quote_exclamation_preserved(self):
        self.assertEqual(check.parameter_issues("f='a!b' ! 説明", "f='a!b' ! description"),[])

    def test_parameter_path_change_rejected(self):
        self.assertTrue(check.parameter_issues("fn_z='a.txt'", "fn_z='../a.txt'"))

    def test_comma_continued_disabled_example_warns(self):
        a='!arr=1,\n!2,3'
        self.assertTrue(any(i.startswith('WARN:') for i in check.parameter_issues(a,a)))

if __name__ == '__main__':unittest.main()
