#!/usr/bin/env python3
"""開発記録(目次 docs/developer.md と節ごとの本文 docs/developer/NNN.md)・作業引き継ぎメモ(目次 docs/handoff.md と
項目ごとの本文 docs/handoff/<番号>.md)の一貫性と、Markdown の大きさの検査。Python 標準ライブラリのみ。

  python3 tools/devdocs/check.py [--root DIR] [index] [cites] [size] [handoff]   (省略時はすべて)

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
  節・項目のファイルが SOFT_KB を超えたら、新しい節を起こす(項目を分ける)目安として報告する(失敗にはしない)。
handoff: 作業引き継ぎメモの目次と項目のファイルを照合する。
  1. docs/handoff/ には Markdown だけを置く。<番号>.md(番号は数字の後に英小文字が続く形。00y・1l・4・000 など)は 1 行目が「<番号>. 」で始まり、
     2 行目以降に行頭の「<番号>. 」を持たない(1 ファイル 1 項目)。番号の形でないファイル(roadmap.md など)と
     目次にも行頭の「<番号>. 」を書かない(項目は自分のファイルに起こす)
  2. 目次の一覧に、README.md 以外の各ファイルが「- [<番号>](handoff/<番号>.md) 題名」(番号の形でないファイルは
     「- [名前](handoff/<ファイル>)」)の形で 1 回ずつあり、リンク先が実在する
  3. 項目の題名(1 行目の「<番号>. 」の後の太字。行をまたいでよく、改行は空白 1 つ)と目次の題名が一致する。
     目次の題名が「…」で終わるときは、「…」の前が項目の題名の先頭と一致すればよい(長い題名の短縮)
  4. 目次と項目のファイルの相対リンクが実在のファイルを指す
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
HANDOFF_INDEX = "docs/handoff.md"
HANDOFF_DIR = "docs/handoff"

FILE_NAME = re.compile(r"^(\d{3})\.md$")
SECTION_HEADING = re.compile(r"^## (\d+)\. (.+)$")
NUMBERED_SUB = re.compile(r"^#{3,6} (\d+)\.\d")
ENTRY = re.compile(r"^- \[§(\d+)\]\(developer/(\d{3})\.md\) (.+)$")
LINK = re.compile(r"\]\(([^)\s]+)\)")
CITE = re.compile(r"developer\.md(?:\]\([^)]*\))?\**[\s!#/*>(（、のでは:：]{0,12}§\s*(\d+)((?:\.\d+)*)")
ITEM_FILE = re.compile(r"^(\d+[a-z]*)\.md$")
ITEM_LINE = re.compile(r"^(\d+[a-z]*)\. (.*)$")
HANDOFF_ENTRY = re.compile(r"^- \[([^\]]+)\]\(handoff/([^)\s]+)\)(?: (.*))?$")


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
        elif rel.startswith((SECTIONS + "/", HANDOFF_DIR + "/")) and size > SOFT_KB * 1024:
            notes.append(f"{rel}: {size / 1024:.0f} KB is over {SOFT_KB} KB; "
                         f"start a new section (or split the item) instead of appending to it")
    return errors, notes


def item_title(lines: list[str]) -> str:
    """項目の題名: 1 行目の「<番号>. 」の後の太字(行をまたいでよい。改行は空白 1 つ)。太字がなければ 1 行目の残り"""
    m = ITEM_LINE.match(lines[0]) if lines else None
    if not m:
        return ""
    rest = m[2]
    if not rest.startswith("**"):
        return rest.strip()
    buf, i = rest[2:], 1
    while "**" not in buf and i < len(lines):
        buf += " " + lines[i].strip()
        i += 1
    return buf.split("**", 1)[0].strip()


def check_handoff(root: Path) -> tuple[list[str], list[str]]:
    errors, notes = [], []
    index, hdir = root / HANDOFF_INDEX, root / HANDOFF_DIR
    if not index.is_file():
        return [f"{HANDOFF_INDEX}: not found"], notes
    if not hdir.is_dir():
        return [f"{HANDOFF_DIR}/: not found"], notes
    files = {p.name: p for p in sorted(hdir.iterdir()) if p.is_file()}
    titles = {}
    for name, path in files.items():
        rel = path.relative_to(root).as_posix()
        if not name.endswith(".md"):
            errors.append(f"{rel}: only Markdown files belong here")
            continue
        lines = text(path).split("\n")
        m = ITEM_FILE.match(name)
        start = 0
        if m:
            first = ITEM_LINE.match(lines[0])
            if not first or first[1] != m[1]:
                errors.append(f"{rel}:1: the first line must start with '{m[1]}. '")
            else:
                titles[name] = item_title(lines)
            start = 1
        for no, line in enumerate(lines[start:], start + 1):
            s = ITEM_LINE.match(line)
            if s:
                errors.append(f"{rel}:{no}: item '{s[1]}.' must be a file of its own ({HANDOFF_DIR}/{s[1]}.md)")
    linked = {}
    for no, line in enumerate(text(index).split("\n"), 1):
        s = ITEM_LINE.match(line)
        if s:
            errors.append(f"{HANDOFF_INDEX}:{no}: item '{s[1]}.' must not be written in the index; "
                          f"create {HANDOFF_DIR}/{s[1]}.md and add a line to the list")
            continue
        m = HANDOFF_ENTRY.match(line)
        if not m:
            continue
        label, target, title = m[1], m[2], (m[3] or "")
        linked[target] = linked.get(target, 0) + 1
        if target not in files:
            errors.append(f"{HANDOFF_INDEX}:{no}: {HANDOFF_DIR}/{target} does not exist")
            continue
        if ITEM_FILE.match(target):
            if label != target[:-3]:
                errors.append(f"{HANDOFF_INDEX}:{no}: the link text must be the item number {target[:-3]}")
            full = titles.get(target)
            short = title.endswith("…") and title[:-1] and full is not None and full.startswith(title[:-1])
            if full is not None and title != full and not short:
                errors.append(f"{HANDOFF_INDEX}:{no}: the title of {target[:-3]} differs from the first line of {target}")
    for name in files:
        if name == "README.md" or not name.endswith(".md"):
            continue
        if not linked.get(name):
            errors.append(f"{HANDOFF_DIR}/{name} is not listed in {HANDOFF_INDEX}")
        elif linked[name] > 1:
            errors.append(f"{HANDOFF_INDEX}: {name} is listed {linked[name]} times")
    for path in [index, *(p for n, p in files.items() if n.endswith(".md"))]:
        errors += link_errors(root, path)
    notes.append(f"{len(titles)} item file(s), {sum(linked.values())} index entr(y/ies)")
    return errors, notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=Path(__file__).resolve().parents[2], type=Path)
    ap.add_argument("what", nargs="*", choices=["index", "cites", "size", "handoff"],
                    help="checks to run (default: all)")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    what = args.what or ["index", "cites", "size", "handoff"]
    errors_all = []
    for name, fn in (("index", check_index), ("cites", check_cites), ("size", check_size),
                     ("handoff", check_handoff)):
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
