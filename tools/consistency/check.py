#!/usr/bin/env python3
"""設定例(List_samples)・検証ケースの一覧(test/README)・チュートリアルの詳説ページの表の一貫性検査。
Python 標準ライブラリのみ。

  python3 tools/consistency/check.py [--root DIR] [samples] [tests] [guide]   (省略時はすべて)

samples: examples/List_samples/list_*.txt と英語ミラー en/list_*.txt の各グループ(`&名前` から
  `/` の行まで。名前の末尾の `_数字` は同じグループの別の例で、その名前の namelist が src に
  なければ外して照合する)の代入を、src/*.f90 の namelist 宣言と照合する。代入として読むのは、
  有効な行 `名前 = 値` と、コメントアウトした例 `!名前 = 値`(! の直後に名前)だけ。! の後に
  空白がある行は説明文として読まない(「E = …」のような式の説明を代入と取り違えないため)。
  1. グループが src の namelist にある
  2. 代入の名前がそのグループに宣言されている(綴りの誤り・廃止したパラメータの検出。廃止して指定の検出の
     ためだけに namelist に残すパラメータ REMOVED(developer.md §103)は宣言に数えず、書かれていたら報告する)
  3. 日英の組で (グループ, 名前, 添字, 値, 有効/コメント) の並びが一致する(設定例はコメントだけを
     訳し、値・識別子・有効状態を保つ規約。docs/multilingual.md)
  参考に、どの設定例にも現れないパラメータの数をグループ別に表示する(失敗にはしない。説明文の
  中の例も「現れた」に数える)。
tests: test/README.md(英語版 test/README.en.md)のケース一覧の表を test/ のディレクトリと照合する。
  1. test/ の各ディレクトリ(Scripts を除く)が表に 1 行ずつあり、表の各行のディレクトリが存在する
  2. 英語版の表が同じディレクトリを同じ順に並べる
  3. 「検証」の列(表の最後の列)に ref と書くのは reference/ を持つケースだけで、reference/ を
     持つケースには ref と書く
guide: docs/tutorial.md(英語版 docs/en/tutorial.md)の「分野(章ページ) | 詳説ページ」の表を、
  docs/users_guide.md(英語版)の目次(最初の水平線まで)で章の下に字下げして並ぶ詳説ページと照合する。
  1. 目次の詳説ページが表に 1 回ずつあり、表の詳説ページが目次にある
  2. 表の行の左の列に、その詳説ページの目次での親の章がある
imports: 毎 push の CI(.github/workflows/ci.yml の `for c in …` の一覧)と夜間(nightly.yml の REF_CASES・VERIFY_CASES・
  VERIFY_MPI_CASES)で回すケースの Run.sh・Run_MPI.sh が実行する Python(呼ぶスクリプト、`python3 -c` の文字列、
  `python3 - <<EOF` のヒアドキュメント)と、そこから読む同じディレクトリのモジュールの import を調べる。
  1. 読むモジュールは Python の標準ライブラリ(sys.stdlib_module_names)か、同じディレクトリのモジュールに限る
     (ランナーには numpy などがない。developer.md §10)。ImportError を捕まえる try の中の import は数えない
  シェルのコメント行とヒアドキュメントの中に書かれたファイル名は、実行するスクリプトに数えない。
  Python 3.10 より前の Python では調べない(参考として表示し、失敗にはしない)。
不一致があれば行ごとに報告して終了コード 1。索引・文書を生成・変更はしない(developer.md §35.1)。
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from pathlib import Path
import re
import sys

SAMPLES = "examples/List_samples"
TEST_DIR = "test"
TEST_README = {"ja": "test/README.md", "en": "test/README.en.md"}
EXCLUDE_GROUPS = {"save_info", "wavefield_info"}   # 再開ヘッダ(利用者パラメータでない)
# 廃止したパラメータ (グループ, 名前)。namelist には指定を検出して案内付きで停止させるためだけに残すので、
# 宣言に数えず、設定例に書かれていたら誤りとする(developer.md §103)。tools/params_index/check.py にも同じ集合がある
REMOVED = {("list_sysparam", "fn_reservoir")}
EXCLUDE_TEST_DIRS = {"Scripts"}
GUIDE = {"ja": "docs/users_guide.md", "en": "docs/en/users_guide.md"}
TUTORIAL = {"ja": "docs/tutorial.md", "en": "docs/en/tutorial.md"}
TUTORIAL_HEADER = {"ja": "| 分野(章ページ) | 詳説ページ |", "en": "| Field (chapter page) | Explanation pages |"}

NAMELIST = re.compile(r"^\s*namelist\s*/\s*(\w+)\s*/\s*(.*)$", re.I)
HEADER = re.compile(r"^\s*&(\w+)")
ASSIGN = re.compile(r"^\s*(!?)([A-Za-z]\w*)\s*(\([^)]*\))?\s*=(?!=)\s*([^!]*)")
MENTION = re.compile(r"^\s*!*\s*([A-Za-z]\w*)\s*(?:\([^)]*\))?\s*=(?!=)")
ROW = re.compile(r"^\|\s*\[([^\]/]+)/?\]\([^)]*\)\s*\|.*\|\s*([^|]*?)\s*\|\s*$")
REF = re.compile(r"\bref\b")
TOC_CHAPTER = re.compile(r"^- \[[^\]]*\]\((users_guide/[\w.-]+\.md)\)")
TOC_SUB = re.compile(r"^ {2,4}- \[[^\]]*\]\((users_guide/[\w.-]+\.md)\)")
GUIDE_LINK = re.compile(r"\]\((users_guide/[\w.-]+\.md)\)")
CI_WORKFLOW = ".github/workflows/ci.yml"
NIGHTLY_WORKFLOW = ".github/workflows/nightly.yml"
NIGHTLY_LISTS = ("REF_CASES", "VERIFY_CASES", "VERIFY_MPI_CASES")
RUN_SCRIPTS = ("Run.sh", "Run_MPI.sh")
CASE_LOOP = re.compile(r"for c in ([^;$\n]+); do")
ENV_LIST = re.compile(r"^[ \t]+(" + "|".join(NIGHTLY_LISTS) + r"):[ \t]*(.*?)[ \t]*$", re.M)
PY_REF = re.compile(r"[\w./-]*\.py\b")
PY_INLINE = re.compile(r"""\bpython3?\s+-c\s+(?:"([^"]*)"|'([^']*)')""")
HEREDOC = re.compile(r"(?<!<)<<(-?)(?!<)\s*(['\"]?)([A-Za-z_]\w*)\2")
PY_HEREDOC_CMD = re.compile(r"\bpython3?\s+-\s*(?:\|\||&&|;|$|<<)")
IMPORT_ERRORS = {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}


def text(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def fortran_statements(source: str):
    """コメントを除き、継続行(& で終わる行。次行の先頭 & も可)を連結した文を順に返す"""
    buf = ""
    for raw in source.split("\n"):
        line = raw.split("!", 1)[0].rstrip()
        if buf:
            line = line.lstrip()
            if line.startswith("&"):
                line = line[1:]
        if line.endswith("&"):
            buf += line[:-1]
            continue
        buf += line
        if buf.strip():
            yield buf
        buf = ""
    if buf.strip():
        yield buf


def namelists(root: Path) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for path in sorted((root / "src").glob("*.f90")):
        for st in fortran_statements(text(path)):
            m = NAMELIST.match(st)
            if m and m.group(1).lower() not in EXCLUDE_GROUPS:
                group = m.group(1).lower()
                names = {n.strip().lower() for n in m.group(2).split(",") if n.strip()}
                groups.setdefault(group, set()).update(n for n in names if (group, n) not in REMOVED)
    return groups


def group_of(name: str, groups: dict[str, set[str]]) -> str:
    name = name.lower()
    if name in groups:
        return name
    base = re.sub(r"_\d+$", "", name)
    return base if base in groups else name


def sample_assignments(path: Path, groups: dict[str, set[str]]):
    """(行番号, グループ, 名前, 添字, 値, 有効か) を順に返す。グループの外の行は読まない"""
    out, group = [], None
    for no, line in enumerate(text(path).split("\n"), 1):
        m = HEADER.match(line)
        if m:
            group = group_of(m.group(1), groups)
            continue
        if group is None:
            continue
        if line.strip() == "/":
            group = None
            continue
        m = ASSIGN.match(line)
        if m:
            out.append((no, group, m.group(2).lower(), (m.group(3) or "").replace(" ", ""),
                        " ".join(m.group(4).split()), m.group(1) == ""))
    return out


def check_samples(root: Path) -> tuple[list[str], list[str]]:
    groups = namelists(root)
    errors, notes = [], []
    mentioned: set[str] = set()
    files = sorted((root / SAMPLES).glob("list_*.txt"))
    if not files:
        errors.append(f"{SAMPLES}: list_*.txt not found")
    for ja in files:
        en = ja.parent / "en" / ja.name
        seqs = {}
        for lang, path in (("ja", ja), ("en", en)):
            if not path.exists():
                notes.append(f"{path.relative_to(root)}: no English mirror (not checked)")
                continue
            rel = path.relative_to(root)
            items = sample_assignments(path, groups)
            for no, group, name, _idx, _val, _active in items:
                if group not in groups:
                    errors.append(f"{rel}:{no}: &{group} is not a namelist group in src/*.f90")
                elif (group, name) in REMOVED:
                    errors.append(f"{rel}:{no}: {name} was removed from namelist /{group}/ "
                                  f"(kept in src only to stop the run with guidance)")
                elif name not in groups[group]:
                    errors.append(f"{rel}:{no}: {name} is not declared in namelist /{group}/")
            seqs[lang] = items
            for line in text(path).split("\n"):
                m = MENTION.match(line)
                if m:
                    mentioned.add(m.group(1).lower())
        if len(seqs) == 2:
            a = [x[1:] for x in seqs["ja"]]
            b = [x[1:] for x in seqs["en"]]
            if a != b:
                k = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
                where_ja = seqs["ja"][k][0] if k < len(a) else "end"
                where_en = seqs["en"][k][0] if k < len(b) else "end"
                errors.append(f"{ja.relative_to(root)} vs en/{ja.name}: the sequence of assignments "
                              f"(group, name, index, value, active) differs from item {k + 1} "
                              f"(ja line {where_ja}, en line {where_en}; {len(a)} vs {len(b)} items)")
    absent = {g: sorted(n for n in names if n not in mentioned) for g, names in groups.items()}
    total = sum(len(v) for v in absent.values())
    if total:
        detail = ", ".join(f"{g} {len(v)}" for g, v in sorted(absent.items()) if v)
        notes.append(f"info: {total} of {sum(len(v) for v in groups.values())} parameters appear in no "
                     f"settings example ({detail})")
    return errors, notes


def readme_rows(path: Path) -> list[tuple[int, str, str]]:
    rows = []
    for no, line in enumerate(text(path).split("\n"), 1):
        m = ROW.match(line)
        if m:
            rows.append((no, m.group(1), m.group(2)))
    return rows


def check_tests(root: Path) -> tuple[list[str], list[str]]:
    errors, notes = [], []
    tdir = root / TEST_DIR
    dirs = sorted(d.name for d in tdir.iterdir()
                  if d.is_dir() and d.name not in EXCLUDE_TEST_DIRS and not d.name.startswith((".", "_")))
    rows = {}
    for lang, rel in TEST_README.items():
        path = root / rel
        if not path.exists():
            errors.append(f"{rel}: not found")
            continue
        rows[lang] = readme_rows(path)
    if "ja" not in rows:
        return errors, notes
    names = [r[1] for r in rows["ja"]]
    for name, n in Counter(names).items():
        if n > 1:
            errors.append(f"{TEST_README['ja']}: {name}/ is listed {n} times")
    for name in sorted(set(dirs) - set(names)):
        errors.append(f"{TEST_README['ja']}: test/{name}/ is not listed in the case table")
    for no, name, _v in rows["ja"]:
        if name not in dirs:
            errors.append(f"{TEST_README['ja']}:{no}: {name}/ is listed but test/{name}/ does not exist")
    if "en" in rows:
        en_names = [r[1] for r in rows["en"]]
        if en_names != names:
            k = next((i for i, (x, y) in enumerate(zip(names, en_names)) if x != y), min(len(names), len(en_names)))
            errors.append(f"{TEST_README['en']}: the case table differs from {TEST_README['ja']} from row {k + 1} "
                          f"({len(en_names)} vs {len(names)} rows)")
    for lang, lrows in rows.items():
        for no, name, verify in lrows:
            if name not in dirs:
                continue
            has_ref = (tdir / name / "reference").is_dir()
            says_ref = bool(REF.search(verify))
            if has_ref and not says_ref:
                errors.append(f"{TEST_README[lang]}:{no}: {name}/ has reference/ but the verification column "
                              f"does not say ref ({verify!r})")
            elif says_ref and not has_ref:
                errors.append(f"{TEST_README[lang]}:{no}: {name}/ says ref but has no reference/ ({verify!r})")
    return errors, notes


def guide_explanations(path: Path) -> dict[str, str]:
    """ユーザーガイドの目次(最初の水平線まで)の詳説ページ → 親の章ページ"""
    parent, out = None, {}
    for line in text(path).split("\n"):
        if line.strip() == "---":
            break
        m = TOC_CHAPTER.match(line)
        if m:
            parent = m.group(1)
            continue
        m = TOC_SUB.match(line)
        if m and parent:
            out[m.group(1)] = parent
    return out


def tutorial_rows(path: Path, header: str):
    """チュートリアルの「分野(章ページ) | 詳説ページ」の表 → [(行番号, {章ページ}, [詳説ページ])]。表がなければ None"""
    lines = text(path).split("\n")
    if header not in lines:
        return None
    rows = []
    for i in range(lines.index(header) + 2, len(lines)):
        if not lines[i].startswith("|"):
            break
        cells = lines[i].strip().strip("|").split("|")
        left, right = (cells[0], "|".join(cells[1:])) if len(cells) > 1 else (cells[0], "")
        rows.append((i + 1, set(GUIDE_LINK.findall(left)), GUIDE_LINK.findall(right)))
    return rows


def check_guide(root: Path) -> tuple[list[str], list[str]]:
    errors, notes = [], []
    for lang in ("ja", "en"):
        guide, tutorial = root / GUIDE[lang], root / TUTORIAL[lang]
        missing = [str(p.relative_to(root)) for p in (guide, tutorial) if not p.exists()]
        if missing:
            errors.append(f"{', '.join(missing)}: not found")
            continue
        toc = guide_explanations(guide)
        rows = tutorial_rows(tutorial, TUTORIAL_HEADER[lang])
        if rows is None:
            errors.append(f"{TUTORIAL[lang]}: the table {TUTORIAL_HEADER[lang]!r} was not found")
            continue
        seen = Counter()
        for no, chapters, pages in rows:
            for page in pages:
                seen[page] += 1
                if page not in toc:
                    errors.append(f"{TUTORIAL[lang]}:{no}: {page} is not an explanation page in the table of "
                                  f"contents of {GUIDE[lang]}")
                elif toc[page] not in chapters:
                    errors.append(f"{TUTORIAL[lang]}:{no}: {page} is under {toc[page]} in {GUIDE[lang]}, "
                                  f"which is not in the left column of this row")
        for page, n in sorted(seen.items()):
            if n > 1:
                errors.append(f"{TUTORIAL[lang]}: {page} is listed {n} times")
        for page in sorted(set(toc) - set(seen)):
            errors.append(f"{TUTORIAL[lang]}: {page} (under {toc[page]} in {GUIDE[lang]}) is missing from the table")
    return errors, notes


def ci_cases(root: Path) -> list[str]:
    """毎 push の CI と夜間で Run.sh・Run_MPI.sh を回すケースの名前(重複なし、名前の順)"""
    cases: set[str] = set()
    ci, nightly = root / CI_WORKFLOW, root / NIGHTLY_WORKFLOW
    if ci.exists():
        for m in CASE_LOOP.finditer(text(ci)):
            cases.update(m.group(1).split())
    if nightly.exists():
        for m in ENV_LIST.finditer(text(nightly)):
            cases.update(m.group(2).split())
    return sorted(cases)


def strip_shell_comment(line: str) -> str:
    """引用符の外の、行頭か空白の後の # から行末までを除く"""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1].isspace()):
            return line[:i]
    return line


def shell_python(path: Path):
    """シェルスクリプトが実行する Python → (参照するファイル名の並び, [(行番号, 種類, ソース)])"""
    refs, inline = [], []
    lines = text(path).split("\n")
    i = 0
    while i < len(lines):
        line = strip_shell_comment(lines[i])
        m = HEREDOC.search(line)
        if m:
            dash, delim = m.group(1), m.group(3)
            body, j = [], i + 1
            while j < len(lines) and (lines[j].lstrip("\t") if dash else lines[j]) != delim:
                body.append(lines[j])
                j += 1
            if PY_HEREDOC_CMD.search(line[:m.start()] + " <<"):
                inline.append((i + 1, "heredoc", "\n".join(body)))
            head = line[:m.start()]
            refs += PY_REF.findall(head)
            for mm in PY_INLINE.finditer(head):
                inline.append((i + 1, "python3 -c", mm.group(1) if mm.group(1) is not None else mm.group(2)))
            i = j + 1
            continue
        refs += PY_REF.findall(PY_INLINE.sub("", line))
        for mm in PY_INLINE.finditer(line):
            inline.append((i + 1, "python3 -c", mm.group(1) if mm.group(1) is not None else mm.group(2)))
        i += 1
    return refs, inline


def catches_import_error(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    types = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    names = [t.id if isinstance(t, ast.Name) else t.attr if isinstance(t, ast.Attribute) else "" for t in types]
    return any(n in IMPORT_ERRORS for n in names)


def python_imports(tree: ast.AST) -> list[tuple[int, str]]:
    """(行番号, 最上位のモジュール名)。相対 import と、ImportError を捕まえる try の中の import は除く"""
    out: list[tuple[int, str]] = []

    def walk(node, guarded):
        if isinstance(node, ast.Import):
            if not guarded:
                out.extend((node.lineno, a.name.split(".")[0]) for a in node.names)
            return
        if isinstance(node, ast.ImportFrom):
            if not guarded and node.level == 0 and node.module:
                out.append((node.lineno, node.module.split(".")[0]))
            return
        if isinstance(node, ast.Try) or type(node).__name__ == "TryStar":
            inner = guarded or any(catches_import_error(h) for h in node.handlers)
            for child in node.body:
                walk(child, inner)
            for child in node.handlers + node.orelse + node.finalbody:
                walk(child, guarded)
            return
        for child in ast.iter_child_nodes(node):
            walk(child, guarded)

    walk(tree, False)
    return out


def local_module(base: Path, name: str):
    for cand in (base / f"{name}.py", base / name / "__init__.py"):
        if cand.is_file():
            return cand
    return None


def check_imports(root: Path) -> tuple[list[str], list[str]]:
    errors, notes = [], []
    stdlib = getattr(sys, "stdlib_module_names", None)
    if stdlib is None:
        notes.append("skipped: Python 3.10 or later is needed (sys.stdlib_module_names)")
        return errors, notes
    cases = ci_cases(root)
    if not cases:
        errors.append(f"no case lists found in {CI_WORKFLOW} / {NIGHTLY_WORKFLOW}")
        return errors, notes
    queue: list[tuple[str, str, Path]] = []    # (表示名, ソース, 同じディレクトリのモジュールを探す場所)
    seen: set[Path] = set()

    def add_file(path: Path):
        path = path.resolve()
        if path in seen or not path.is_file():
            return
        seen.add(path)
        queue.append((str(path.relative_to(root.resolve())), text(path), path.parent))

    for case in cases:
        cdir = root / TEST_DIR / case
        if not cdir.is_dir():
            errors.append(f"test/{case}/: listed in the CI or nightly case lists but does not exist")
            continue
        for script in RUN_SCRIPTS:
            sh = cdir / script
            if not sh.is_file():
                continue
            refs, inline = shell_python(sh)
            for ref in refs:
                if "/" in ref and not ref.startswith(("sdir/", "/")):
                    add_file(cdir / ref)
                add_file(cdir / Path(ref).name)
            for no, kind, source in inline:
                queue.append((f"test/{case}/{script}:{no} ({kind})", source, cdir))
    checked = 0
    while queue:
        label, source, base = queue.pop(0)
        checked += 1
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            errors.append(f"{label}: cannot parse as Python ({e.msg}, line {e.lineno})")
            continue
        for no, name in python_imports(tree):
            if name in stdlib:
                continue
            mod = local_module(base, name)
            if mod is not None:
                add_file(mod)
                continue
            where = f"{label}:{no}" if label.endswith(".py") else f"{label}, line {no}"
            errors.append(f"{where}: imports {name}, which is not in the Python standard library "
                          f"(the CI and nightly runners have no numpy etc.; developer.md §10)")
    notes.append(f"info: {checked} Python source(s) run by {len(cases)} CI/nightly case(s) checked")
    return errors, notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=Path(__file__).resolve().parents[2], type=Path)
    ap.add_argument("what", nargs="*", choices=["samples", "tests", "guide", "imports"],
                    help="checks to run (default: all)")
    args = ap.parse_args(argv)
    what = args.what or ["samples", "tests", "guide", "imports"]
    errors_all = []
    for name, fn in (("samples", check_samples), ("tests", check_tests), ("guide", check_guide),
                     ("imports", check_imports)):
        if name not in what:
            continue
        errors, notes = fn(args.root)
        for line in notes:
            print(f"{name}: {line}")
        for line in errors:
            print(f"{name}: ERROR {line}")
        print(f"{name}: {len(errors)} issue(s)")
        errors_all += errors
    return 1 if errors_all else 0


if __name__ == "__main__":
    sys.exit(main())
