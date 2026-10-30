#!/usr/bin/env python3
"""設定例(List_samples)と検証ケースの一覧(test/README)の一貫性検査。Python 標準ライブラリのみ。

  python3 tools/consistency/check.py [--root DIR] [samples] [tests]   (省略時は両方)

samples: examples/List_samples/list_*.txt と英語ミラー en/list_*.txt の各グループ(`&名前` から
  `/` の行まで。名前の末尾の `_数字` は同じグループの別の例で、その名前の namelist が src に
  なければ外して照合する)の代入を、src/*.f90 の namelist 宣言と照合する。代入として読むのは、
  有効な行 `名前 = 値` と、コメントアウトした例 `!名前 = 値`(! の直後に名前)だけ。! の後に
  空白がある行は説明文として読まない(「E = …」のような式の説明を代入と取り違えないため)。
  1. グループが src の namelist にある
  2. 代入の名前がそのグループに宣言されている(綴りの誤り・廃止したパラメータの検出)
  3. 日英の組で (グループ, 名前, 添字, 値, 有効/コメント) の並びが一致する(設定例はコメントだけを
     訳し、値・識別子・有効状態を保つ規約。docs/multilingual.md)
  参考に、どの設定例にも現れないパラメータの数をグループ別に表示する(失敗にはしない。説明文の
  中の例も「現れた」に数える)。
tests: test/README.md(英語版 test/README.en.md)のケース一覧の表を test/ のディレクトリと照合する。
  1. test/ の各ディレクトリ(Scripts を除く)が表に 1 行ずつあり、表の各行のディレクトリが存在する
  2. 英語版の表が同じディレクトリを同じ順に並べる
  3. 「検証」の列(表の最後の列)に ref と書くのは reference/ を持つケースだけで、reference/ を
     持つケースには ref と書く
不一致があれば行ごとに報告して終了コード 1。索引・文書を生成・変更はしない(developer.md §35.1)。
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
import sys

SAMPLES = "examples/List_samples"
TEST_DIR = "test"
TEST_README = {"ja": "test/README.md", "en": "test/README.en.md"}
EXCLUDE_GROUPS = {"save_info", "wavefield_info"}   # 再開ヘッダ(利用者パラメータでない)
EXCLUDE_TEST_DIRS = {"Scripts"}

NAMELIST = re.compile(r"^\s*namelist\s*/\s*(\w+)\s*/\s*(.*)$", re.I)
HEADER = re.compile(r"^\s*&(\w+)")
ASSIGN = re.compile(r"^\s*(!?)([A-Za-z]\w*)\s*(\([^)]*\))?\s*=(?!=)\s*([^!]*)")
MENTION = re.compile(r"^\s*!*\s*([A-Za-z]\w*)\s*(?:\([^)]*\))?\s*=(?!=)")
ROW = re.compile(r"^\|\s*\[([^\]/]+)/?\]\([^)]*\)\s*\|.*\|\s*([^|]*?)\s*\|\s*$")
REF = re.compile(r"\bref\b")


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
                names = {n.strip().lower() for n in m.group(2).split(",") if n.strip()}
                groups.setdefault(m.group(1).lower(), set()).update(names)
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=Path(__file__).resolve().parents[2], type=Path)
    ap.add_argument("what", nargs="*", choices=["samples", "tests"], help="checks to run (default: both)")
    args = ap.parse_args(argv)
    what = args.what or ["samples", "tests"]
    errors_all = []
    for name, fn in (("samples", check_samples), ("tests", check_tests)):
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
