#!/usr/bin/env python3
"""開発記録(目次 docs/developer.md と節ごとの本文 docs/developer/NNN.md)の一貫性と、Markdown の大きさの検査。
Python 標準ライブラリのみ。

  python3 tools/devdocs/check.py [--root DIR] [index] [cites] [size]   (省略時はすべて)

index: 目次と節のファイルを照合する。
  1. docs/developer/ には NNN.md(節番号 N を 3 桁にしたもの)と README.md だけを置く
  2. NNN.md の 1 行目は「## N. 題名」で、ほかに「## 」の見出しを持たない(1 ファイル 1 節)
  3. NNN.md の番号付きの小節見出し(### N.M など)は、その節の番号 N で始まる(他の節の小節を混ぜない)
  4. 節の番号は 1 から欠番なく続く
  5. 目次の「## 全節の一覧」に、各節が「- [§N](developer/NNN.md) 題名」の形で番号順に 1 行ずつあり、
     題名が節のファイルの見出しと一致する
  6. 目次に置く番号付きの節は §0(基本方針 policy.md への案内)だけ(新しい節は docs/developer/ に起こす)
  7. 目次・節のファイル・docs/policy.md の相対リンクが実在のファイルを指す
cites: リポジトリ内の「developer.md §N」「developer.md §N.M」の引用(改行・コメント記号をまたいでよい)が
  実在の節を指し、小節まで書いた引用はその節のファイルに見出し N.M(またはその下位の見出し)がある。
  §0 は policy.md への案内なので小節を検査しない。本ツールのディレクトリ(検査用の例を含む)は対象外。
size: リポジトリ内の Markdown が LIMIT_KB 以下であること(GitHub が Markdown を表示できるのは約 500 KB まで)。
  節のファイルが SOFT_KB を超えたら、新しい節を起こす目安として報告する(失敗にはしない)。
不一致があれば行ごとに報告して終了コード 1。目次・文書を生成・変更はしない(developer.md §35.1)。
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys

INDEX = "docs/developer.md"
SECTIONS = "docs/developer"
POLICY = "docs/policy.md"
LIST_HEADING = "## 全節の一覧"
LIMIT_KB = 400
SOFT_KB = 200
SKIP_DIRS = {".git"}
SELF_DIR = "tools/devdocs"

FILE_NAME = re.compile(r"^(\d{3})\.md$")
SECTION_HEADING = re.compile(r"^## (\d+)\. (.+)$")
NUMBERED_SUB = re.compile(r"^#{3,6} (\d+)\.\d")
ENTRY = re.compile(r"^- \[§(\d+)\]\(developer/(\d{3})\.md\) (.+)$")
LINK = re.compile(r"\]\(([^)\s]+)\)")
CITE = re.compile(r"developer\.md(?:\]\([^)]*\))?\**[\s!#/*>(（、のでは:：]{0,12}§\s*(\d+)((?:\.\d+)*)")


def text(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def section_files(root: Path) -> tuple[dict[int, Path], list[str]]:
    files, errors = {}, []
    sdir = root / SECTIONS
    if not sdir.is_dir():
        return files, [f"{SECTIONS}/: not found"]
    for path in sorted(sdir.iterdir()):
        m = FILE_NAME.match(path.name)
        if m and path.is_file():
            files[int(m[1])] = path
        elif path.name != "README.md":
            errors.append(f"{SECTIONS}/{path.name}: only NNN.md and README.md belong here")
    return files, errors


def link_errors(root: Path, path: Path) -> list[str]:
    errors = []
    rel = path.relative_to(root).as_posix()
    for no, line in enumerate(text(path).split("\n"), 1):
        for url in LINK.findall(re.sub(r"(`+).*?\1", "", line)):
            if re.match(r"^[a-z][a-z0-9+.-]*:", url) or url.startswith("#"):
                continue
            target = url.split("#", 1)[0]
            if not target:
                continue
            dest = (path.parent / target).resolve()
            if dest.exists() and dest.is_relative_to(root.resolve()):
                continue
            # 散文の括弧([a](b) の形の式など)をリンクと取り違えない: パスらしいものだけを報告する
            if re.fullmatch(r"[\w./-]+", target) and ("/" in target or "." in target):
                errors.append(f"{rel}:{no}: missing local link: {url}")
    return errors


def check_index(root: Path) -> tuple[list[str], list[str]]:
    errors, notes = [], []
    files, errs = section_files(root)
    errors += errs
    titles = {}
    for n, path in sorted(files.items()):
        rel = path.relative_to(root).as_posix()
        lines = text(path).split("\n")
        m = SECTION_HEADING.match(lines[0]) if lines else None
        if not m or int(m[1]) != n:
            errors.append(f"{rel}:1: the first line must be '## {n}. <title>'")
        else:
            titles[n] = m[2]
        for no, line in enumerate(lines[1:], 2):
            if line.startswith("## "):
                errors.append(f"{rel}:{no}: a second '## ' heading (one section per file)")
            s = NUMBERED_SUB.match(line)
            if s and int(s[1]) != n:
                errors.append(f"{rel}:{no}: subsection of §{s[1]} inside §{n} (move it to {int(s[1]):03d}.md)")
    numbers = sorted(files)
    if numbers and numbers != list(range(1, numbers[-1] + 1)):
        gaps = sorted(set(range(1, numbers[-1] + 1)) - set(numbers))
        errors.append(f"{SECTIONS}/: section numbers must run from 1 without gaps (missing: {gaps})")
    index = root / INDEX
    if not index.is_file():
        return errors + [f"{INDEX}: not found"], notes
    lines = text(index).split("\n")
    try:
        start = lines.index(LIST_HEADING)
    except ValueError:
        return errors + [f"{INDEX}: heading '{LIST_HEADING}' not found"], notes
    for no, line in enumerate(lines, 1):
        m = SECTION_HEADING.match(line)
        if m and int(m[1]) != 0:
            errors.append(f"{INDEX}:{no}: §{m[1]} must not be written in the index; "
                          f"create {SECTIONS}/{int(m[1]):03d}.md and add a line to '{LIST_HEADING}'")
    listed = []
    for no, line in enumerate(lines[start + 1:], start + 2):
        if line.startswith("## "):
            break
        if not line.strip():
            continue
        m = ENTRY.match(line)
        if not m:
            errors.append(f"{INDEX}:{no}: not an entry '- [§N](developer/NNN.md) <title>': {line[:60]}")
            continue
        n, f, title = int(m[1]), int(m[2]), m[3]
        listed.append(n)
        if n != f:
            errors.append(f"{INDEX}:{no}: §{n} links to developer/{m[2]}.md")
        if n not in files:
            errors.append(f"{INDEX}:{no}: §{n} has no file {SECTIONS}/{n:03d}.md")
        elif n in titles and title != titles[n]:
            errors.append(f"{INDEX}:{no}: the title of §{n} differs from the heading of {n:03d}.md")
    if listed != sorted(listed) or len(set(listed)) != len(listed):
        errors.append(f"{INDEX}: '{LIST_HEADING}' must list each section once, in order")
    for n in sorted(set(files) - set(listed)):
        errors.append(f"{INDEX}: §{n} ({SECTIONS}/{n:03d}.md) is not listed in '{LIST_HEADING}'")
    for path in [index, root / POLICY, *(p for _, p in sorted(files.items()))]:
        if path.is_file():
            errors += link_errors(root, path)
    if not (root / POLICY).is_file():
        errors.append(f"{POLICY}: not found (the project policy, formerly §0)")
    notes.append(f"{len(files)} section file(s), {len(listed)} index entr(y/ies)")
    return errors, notes


def repository_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            yield Path(dirpath) / name


def headings_of(root: Path) -> dict[int, set[str]]:
    files, _ = section_files(root)
    heads = {}
    for n, path in files.items():
        heads[n] = set(re.findall(r"^#{3,6} (\d+(?:\.\d+)+)", text(path), re.M))
    return heads


def check_cites(root: Path) -> tuple[list[str], list[str]]:
    errors, notes = [], []
    heads = headings_of(root)
    count = 0
    for path in repository_files(root):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(SELF_DIR + "/"):
            continue
        try:
            value = text(path)
        except (UnicodeDecodeError, OSError):
            continue
        if "developer.md" not in value:
            continue
        for m in CITE.finditer(value):
            count += 1
            n, sub = int(m[1]), m[2]
            if n == 0:
                continue
            no = value.count("\n", 0, m.start()) + 1
            ref = f"{n}{sub}"
            if n not in heads:
                errors.append(f"{rel}:{no}: developer.md §{ref}: no section §{n} ({SECTIONS}/{n:03d}.md)")
            elif sub and not any(h == ref or h.startswith(ref + ".") for h in heads[n]):
                errors.append(f"{rel}:{no}: developer.md §{ref}: no heading {ref} in {SECTIONS}/{n:03d}.md")
    notes.append(f"{count} citation(s) checked")
    return errors, notes


def check_size(root: Path) -> tuple[list[str], list[str]]:
    errors, notes = [], []
    for path in repository_files(root):
        if path.suffix.lower() != ".md":
            continue
        size = path.stat().st_size
        rel = path.relative_to(root).as_posix()
        if size > LIMIT_KB * 1024:
            errors.append(f"{rel}: {size / 1024:.0f} KB exceeds {LIMIT_KB} KB "
                          f"(GitHub renders Markdown only up to about 500 KB; split the document)")
        elif rel.startswith(SECTIONS + "/") and size > SOFT_KB * 1024:
            notes.append(f"{rel}: {size / 1024:.0f} KB is over {SOFT_KB} KB; "
                         f"start a new section instead of appending to it")
    return errors, notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=Path(__file__).resolve().parents[2], type=Path)
    ap.add_argument("what", nargs="*", choices=["index", "cites", "size"], help="checks to run (default: all)")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    what = args.what or ["index", "cites", "size"]
    errors_all = []
    for name, fn in (("index", check_index), ("cites", check_cites), ("size", check_size)):
        if name not in what:
            continue
        errors, notes = fn(root)
        for line in notes:
            print(f"{name}: {line}")
        for line in errors:
            print(f"{name}: ERROR {line}")
        print(f"{name}: {len(errors)} issue(s)")
        errors_all += errors
    return 1 if errors_all else 0


if __name__ == "__main__":
    sys.exit(main())
