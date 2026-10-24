#!/usr/bin/env python3
"""namelist 宣言と全パラメータ索引(日英)の突合せ検査。Python 標準ライブラリのみ。

  python3 tools/params_index/check.py [--root DIR]

src/*.f90 の `namelist /group/ a, b, &` 宣言(継続行を連結、! 以降のコメントを除く。
再開ヘッダ &save_info は利用者パラメータでないため対象外)から (名前, グループ) を
抽出し、docs/users_guide/params_index.md とその英語ミラーの表、章ページ、索引の
項目数の記述と照合する(developer.md §35.1)。索引を生成・変更はしない。

検査項目:
  1. 索引(日)の行の集合 = コードの (名前, グループ) の集合(欠落・余分・重複)
  2. 索引(日)の並びが名前のアルファベット順(大文字小文字を無視。同名はグループ順)
  3. 索引(英)の行(名前・グループ・章リンク)が索引(日)と同じ並び
  4. 索引と docs/users_guide.md(日英)に書かれた項目数が行数と一致
  5. 各行の章ページ(日英)が存在し、その本文にパラメータ名が現れる
不一致があれば行ごとに報告して終了コード 1。
"""
from __future__ import annotations

import argparse
from collections import Counter
import fnmatch
from pathlib import Path
import re
import sys

INDEX_JA = "docs/users_guide/params_index.md"
INDEX_EN = "docs/en/users_guide/params_index.md"
GUIDE_JA = "docs/users_guide.md"
GUIDE_EN = "docs/en/users_guide.md"
EXCLUDE_GROUPS = {"save_info"}

NAMELIST = re.compile(r"^\s*namelist\s*/\s*(\w+)\s*/\s*(.*)$", re.I)
ROW = re.compile(r"^\|\s*(\S+)\s*\|\s*&(\w+)\s*\|\s*\[([^\]]*)\]\(([^)\s]+)\)[^|]*\|\s*$")
COUNT_INDEX = {"ja": re.compile(r"全\s*(\d+)\s*項目"), "en": re.compile(r"all\s+(\d+)\s+entries")}
COUNT_GUIDE = {"ja": re.compile(r"全\s*(\d+)\s*パラメータ"), "en": re.compile(r"all\s+(\d+)\s+parameter")}


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


def namelists(root: Path) -> dict[str, list[str]]:
    """src/*.f90 の namelist 宣言 → {group: [name, ...]}(重複宣言は 1 回に、宣言順)"""
    groups: dict[str, list[str]] = {}
    for path in sorted((root / "src").glob("*.f90")):
        for stmt in fortran_statements(text(path)):
            m = NAMELIST.match(stmt)
            if not m:
                continue
            group = m.group(1).lower()
            if group in EXCLUDE_GROUPS:
                continue
            names = [n.strip().lower() for n in m.group(2).split(",") if n.strip()]
            seen = groups.setdefault(group, [])
            for n in names:
                if n not in seen:
                    seen.append(n)
    return groups


def index_rows(path: Path) -> list[tuple[int, str, str, str, str]]:
    """索引の表の行 → [(行番号, 名前, グループ, 章の表示名, 章リンク), ...]"""
    rows = []
    for i, line in enumerate(text(path).split("\n"), 1):
        m = ROW.match(line)
        if m:
            rows.append((i, m.group(1), m.group(2).lower(), m.group(3), m.group(4)))
    return rows


def claimed_count(path: Path, pattern: re.Pattern) -> int | None:
    m = pattern.search(text(path))
    return int(m.group(1)) if m else None


WORD = r"(?<![A-Za-z0-9_*])%s(?![A-Za-z0-9_*])"
SHORTHAND = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z0-9_*]*\*[A-Za-z0-9_*]*)(?![A-Za-z0-9_])"   # fn_*_cell
                       r"|(?<![A-Za-z0-9_])([A-Za-z0-9_]+_)([A-Za-z0-9]+(?:/[A-Za-z0-9]+)+)(?![A-Za-z0-9_/])"  # bc_eta_w/e/n/s
                       r"|(?<![A-Za-z0-9_])([A-Za-z0-9_]+)\(_c\)")                                  # dt_maplist(_c)


def mentioned_names(page: str) -> set[str]:
    """章ページが名前を挙げているとみなす表記: 名前そのもの、`fn_*_cell` 形のワイルドカード、
    `bc_eta_w/e/n/s` 形の末尾の選択、`dt_maplist(_c)` 形の文字列版の併記。`*_c` 版(時間の
    文字列指定)は、ページが `_c` に触れていれば元の名前の記載で足りる(time.md の規約)。"""
    names: set[str] = set()
    globs: list[str] = []
    for m in SHORTHAND.finditer(page):
        if m.group(1):
            globs.append(m.group(1).lower())
        elif m.group(2):
            names.update(m.group(2).lower() + a.lower() for a in m.group(3).split("/"))
        else:
            names.update({m.group(4).lower(), m.group(4).lower() + "_c"})
    return names, globs


def mentions(page: str, name: str) -> bool:
    if re.search(WORD % re.escape(name), page, re.I):
        return True
    names, globs = mentioned_names(page)
    if name in names or any(fnmatch.fnmatchcase(name, g) for g in globs):
        return True
    if name.endswith("_c") and "_c" in page and mentions(page.replace("_c", ""), name[:-2]):
        return True
    return False


def check(root: Path) -> list[str]:
    issues: list[str] = []
    code = {(n, g) for g, names in namelists(root).items() for n in names}
    ja_path, en_path = root / INDEX_JA, root / INDEX_EN
    ja = index_rows(ja_path)
    en = index_rows(en_path)

    # 1. 集合の一致
    pairs = Counter((n, g) for _, n, g, _, _ in ja)
    for (n, g), c in sorted(pairs.items()):
        if c > 1:
            issues.append(f"{INDEX_JA}: duplicate row {n} (&{g}) x{c}")
    for n, g in sorted(code - set(pairs)):
        issues.append(f"{INDEX_JA}: missing {n} (&{g}) declared in src")
    for n, g in sorted(set(pairs) - code):
        issues.append(f"{INDEX_JA}: extra row {n} (&{g}) not declared in src")

    # 2. 並び
    keys = [(n.lower(), g) for _, n, g, _, _ in ja]
    for (line, n, g, _, _), k, prev in zip(ja[1:], keys[1:], keys[:-1]):
        if k < prev:
            issues.append(f"{INDEX_JA}:{line}: out of order: {n} (&{g}) after {prev[0]} (&{prev[1]})")

    # 3. 英語ミラーの行の対応
    if len(en) != len(ja):
        issues.append(f"{INDEX_EN}: {len(en)} rows, {INDEX_JA} has {len(ja)}")
    for (lj, nj, gj, _, kj), (le, ne, ge, _, ke) in zip(ja, en):
        if (nj, gj, kj) != (ne, ge, ke):
            issues.append(f"{INDEX_EN}:{le}: {ne} (&{ge}) -> {ke} differs from {INDEX_JA}:{lj}: {nj} (&{gj}) -> {kj}")

    # 4. 項目数の記述
    for path, pattern, lang in [(ja_path, COUNT_INDEX["ja"], "ja"), (en_path, COUNT_INDEX["en"], "en"),
                                (root / GUIDE_JA, COUNT_GUIDE["ja"], "ja"), (root / GUIDE_EN, COUNT_GUIDE["en"], "en")]:
        if not path.exists():
            issues.append(f"{path.relative_to(root)}: missing")
            continue
        claimed = claimed_count(path, pattern)
        if claimed is None:
            issues.append(f"{path.relative_to(root)}: no entry-count statement found")
        elif claimed != len(ja):
            issues.append(f"{path.relative_to(root)}: states {claimed} entries, index has {len(ja)}")

    # 5. 章ページの存在と名前の出現
    pages: dict[Path, str | None] = {}
    for rows, base in [(ja, ja_path.parent), (en, en_path.parent)]:
        for line, n, g, _, link in rows:
            page = (base / link.split("#", 1)[0]).resolve()
            if page not in pages:
                pages[page] = text(page) if page.is_file() else None
            rel = page.relative_to(root.resolve()) if page.is_relative_to(root.resolve()) else page
            if pages[page] is None:
                issues.append(f"{rel}: chapter page missing (linked from {n} &{g})")
            elif not mentions(pages[page], n):
                issues.append(f"{rel}: does not mention {n} (&{g})")
    return issues


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="namelist 宣言と全パラメータ索引(日英)の突合せ")
    parser.add_argument("--root", default=".", help="リポジトリのルート")
    args = parser.parse_args(argv)
    root = Path(args.root)
    issues = check(root)
    for line in issues:
        print(line)
    groups = namelists(root)
    total = sum(len(v) for v in groups.values())
    print(f"Summary: {len(groups)} groups, {total} parameters in src, {len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
