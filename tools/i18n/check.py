#!/usr/bin/env python3
"""ENCflow の翻訳対応・更新状態・設定値を検査する。Python 標準ライブラリのみ。"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import sys
import subprocess
from urllib.parse import unquote, urlsplit

REGISTRY = "tools/i18n/reviews.json"
SCOPE = "tools/i18n/scope.json"
LEGAL_ENGLISH = ("LICENSE", "TRADEMARKS.md")
DOMAINS = ("docs", "tutorials", "test", "examples", "bmi", "utils")
PRESENTATION = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".plt"}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "vendor", "bin", "build"}
GENERATED_DIR = re.compile(r"^(?:result|save|reference)(?:$|[_-])")
LOCALES = {"en", "ja", "fr", "de", "es", "pt", "zh", "ko"}
# 数字・演算子の並びを保持し、空白を除いても「1 2」を「12」と同一視しない。
TOKEN = re.compile(r"\s+|![^\n]*|'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|"
                   r"\.[A-Za-z]+\.|(?:\d+\.\d*|\.\d+|\d+)(?:[eEdD][+-]?\d+)?"
                   r"(?:_[A-Za-z0-9_]+)?|[A-Za-z_][A-Za-z0-9_]*|.", re.S)
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:%[A-Za-z_][A-Za-z0-9_]*)*"
                    r"\s*(?:\([^=]*\))?\s*=")
# namelist の値として現れ得る字句(小文字化後)。これ以外が右辺にあれば散文とみなす。
VALUE = re.compile(r"(?:\d+\.\d*|\.\d+|\d+)(?:[ed][+-]?\d+)?(?:_[a-z0-9_]+)?"
                   r"|\.(?:true|false)\.|[tf]|[,*()+\-&]")
# Notebook のコード比較用: 1 行完結の文字列リテラルと、# / !(!= を除く)以降のコメント。
STRING = re.compile(r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"")
COMMENT = re.compile(r"\s*(?:#|!(?!=)).*$")
HEADING = re.compile(r"^ {0,3}(#{1,6})\s")
TABLE_RULE = re.compile(r"^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*$")


def text(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        try:
            data = data.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
        except UnicodeDecodeError:
            pass
    return hashlib.sha256(data).hexdigest()


def inside(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError(f"repository-relative path required: {name}")
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"path escapes repository: {name}")
    return path


def tokens(value: str) -> tuple[str, ...]:
    result = []
    for match in TOKEN.finditer(value):
        token = match.group()
        if token.isspace() or token.startswith("!"):
            continue
        if token in ("'", '"'):
            raise ValueError("unterminated quoted string")
        result.append(token if token[0] in "\"'" else token.lower())
    return tuple(result)


def disabled_assignment(line: str) -> tuple[str, ...] | None:
    """コメント行が 1 行完結の代入例(右辺が namelist の値だけ)ならその字句列を返す。

    「! dt = 0.05 を使うこと」「! q = cw h^1.5」のような説明文は代入例ではないので
    None(翻訳で変わって当然の散文を、値の不一致として報告しない)。
    """
    candidate = line.lstrip()
    if not candidate.startswith("!"):
        return None
    candidate = candidate[1:].lstrip()
    if not ASSIGN.match(candidate):
        return None
    try:
        items = tokens(candidate)
    except ValueError:
        return None
    rhs = items[items.index("=") + 1:]
    if not rhs or any(not (t[0] in "\"'" or VALUE.fullmatch(t)) for t in rhs):
        return None
    if rhs.count("(") != rhs.count(")"):
        return None  # 「! q = 0)」のような説明文の断片
    return items


def parameters(value: str) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    """有効入力と、1行完結のコメントアウトされた代入例を別々に抽出する。"""
    disabled = [items for items in map(disabled_assignment, value.splitlines()) if items]
    return tokens(value), tuple(disabled)


def parameter_issues(source: str, target: str) -> list[str]:
    left, right = parameters(source), parameters(target)
    issues = []
    if left[0] != right[0]:
        issues.append("ERROR: active parameter tokens differ")
    if left[1] != right[1]:
        issues.append("ERROR: commented-out assignment examples differ")
    if any(item[-1] in (",", "&") for item in left[1] + right[1]):
        issues.append("WARN: multiline commented examples need manual review")
    return issues


def code_essence(code: str) -> tuple[str, list[str]]:
    """コメントと文字列リテラルの中身を除いたコードと、文字列リテラルの一覧。

    行単位の近似(複数行文字列の中の namelist コメントも '!' 以降として除く)。
    """
    strings: list[str] = []
    lines = []
    for line in code.splitlines():
        line = STRING.sub(lambda m: strings.append(m.group()) or "''", line)
        line = COMMENT.sub("", line).rstrip()
        if line.strip():
            lines.append(line)
    return "\n".join(lines), strings


def validate_direction(source: str, target: str) -> None:
    """入口の表示言語と正本を取り違えない。登録方向の明白な違反を拒否。"""
    if source == target:
        raise ValueError("source and target must differ")
    legal = {"LICENSE": "LICENSE.ja.md", "TRADEMARKS.md": "TRADEMARKS.ja.md"}
    if source in legal:
        stem = "LICENSE" if source == "LICENSE" else "TRADEMARKS"
        match = re.fullmatch(re.escape(stem) + r"\.([a-z]{2}(?:-[A-Za-z0-9]+)?)\.md", target)
        if not match or match[1] == "en":
            raise ValueError("legal-document mirror needs an explicit non-English language suffix")
        return
    if source in legal.values() or source == "README.md":
        raise ValueError("translation cannot be registered as the authoritative source")
    rel = Path(source)
    if any(locale(part, "en") for part in rel.parts[:-1]) or re.search(
            r"\.(?:en|fr|de|es|pt|zh|ko)(?:-[A-Za-z0-9]+)?\.md$", rel.name):
        raise ValueError("ordinary documents must use the Japanese source")


def load_registry(root: Path) -> dict:
    path = root / REGISTRY
    if not path.is_file():
        return {"version": 1, "reviews": []}
    data = json.loads(text(path))
    if data.get("version") != 1 or not isinstance(data.get("reviews"), list):
        raise ValueError("invalid review registry")
    seen = set()
    for entry in data["reviews"]:
        key = (entry["source"], entry["target"])
        validate_direction(*key)
        if key in seen:
            raise ValueError(f"duplicate review: {key}")
        seen.add(key)
        for field in ("source", "target"):
            inside(root, entry[field])
        for field in ("source_sha256", "target_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}", entry[field]):
                raise ValueError(f"invalid digest: {key}, {field}")
        if entry["method"] not in ("human", "assistant") or not entry["reviewer"].strip():
            raise ValueError(f"invalid reviewer: {key}")
        date.fromisoformat(entry["reviewed_on"])
    return data


def is_parameter(path: Path) -> bool:
    return path.suffix == ".txt" and path.name.startswith(("param", "list_"))


def locale(part: str, language: str) -> bool:
    return part in LOCALES | {language} or bool(re.fullmatch(
        r"(?:en|ja|fr|de|es|pt|zh|ko)(?:-[A-Za-z0-9]+)+", part))


def repository_files(root: Path) -> list[Path]:
    """Gitでは管理対象+未追跡(非ignore)だけを走査。Git外の単体テストにも対応。"""
    names = None
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                             capture_output=True, check=True).stdout.decode().strip()
        if Path(top).resolve() == root.resolve():
            out = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached",
                                  "--others", "--exclude-standard"],
                                 capture_output=True, check=True).stdout
            names = [Path(n.decode("utf-8")) for n in out.split(b"\0") if n]
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
        pass
    if names is None:
        names = [p.relative_to(root) for domain in DOMAINS
                 for p in (root / domain).rglob("*") if p.is_file()]
    found = []
    for rel in sorted(set(names)):
        if not rel.parts or rel.parts[0] not in DOMAINS:
            continue
        if any(part in SKIP_DIRS or part.startswith(".") or GENERATED_DIR.match(part)
               for part in rel.parts[:-1]):
            continue
        path = root / rel
        if path.is_file() and not path.is_symlink():
            inside(root, rel.as_posix())
            found.append(rel)
    return found


def kind(path: Path) -> str:
    if path.suffix == ".md":
        return "markdown"
    if path.suffix == ".ipynb":
        return "notebook"
    if path.suffix == ".txt":
        return "parameter"
    return "presentation" if path.suffix.lower() in PRESENTATION | {".py"} else "text"


def target_path(root: Path, source: Path, language: str) -> Path:
    """docsはroot、それ以外は最も近い実行単位に言語ディレクトリを挿入。"""
    parts = source.parts
    at = 1
    if parts[0] != "docs" and len(parts) > 2:
        at = 1 if parts[0] == "bmi" else 2
        for depth in range(1, len(parts)):
            directory = root.joinpath(*parts[:depth])
            if any((directory / name).is_file() for name in ("Makefile", "Run.sh")):
                at = depth
    return Path(*parts[:at], language, *parts[at:])


def discover(root: Path, language: str) -> dict[tuple[str, str], bool]:
    result = {}
    files = repository_files(root)
    file_set = set(files)
    for rel in files:
        if any(locale(part, language) for part in rel.parts[1:-1]):
            continue
        if re.search(r"\.(?:en|ja|fr|de|es|pt|zh|ko)(?:-[A-Za-z0-9]+)?\.md$", rel.name):
            continue
        ordinary = rel.suffix in (".md", ".ipynb") or is_parameter(rel)
        presentation = rel.suffix.lower() in PRESENTATION or (
            rel.suffix == ".py" and rel.name.startswith(("Fig", "Plot", "plot_")))
        if not ordinary and not presentation:
            continue
        target = target_path(root, rel, language)
        # 既存の同一ケース内en/も認識。複数ある場合はauditで重複を報告する。
        existing = [Path(*rel.parts[:i], language, *rel.parts[i:])
                    for i in range(1, len(rel.parts))
                    if Path(*rel.parts[:i], language, *rel.parts[i:]) in file_set]
        if target not in file_set and len(existing) == 1:
            target = existing[0]
        old = rel.with_name(f"{rel.stem}.{language}{rel.suffix}")
        legacy = target not in file_set and old in file_set
        if presentation and not existing:
            continue  # 共有画像の全件に不要な翻訳を要求しない
        result[(rel.as_posix(), (old if legacy else target).as_posix())] = legacy
    for source, target in (
        ("README.ja.md", "README.md" if language == "en" else f"README.{language}.md"),
        ("CONTRIBUTING.md", f"CONTRIBUTING.{language}.md"),
    ):
        if (root / source).is_file():
            result[(source, target)] = False
    legal_language = "ja" if language == "en" else language
    for source, stem in (("TRADEMARKS.md", "TRADEMARKS"), ("LICENSE", "LICENSE")):
        target = f"{stem}.{legal_language}.md"
        if (root / source).is_file() and (root / target).is_file():
            result[(source, target)] = False
    # 原文を削除した未登録の翻訳も見落とさない。
    for rel in files:
        if not (rel.suffix in (".md", ".ipynb") or is_parameter(rel)):
            continue
        if language in rel.parts[1:-1]:
            parts = list(rel.parts)
            parts.remove(language)
            source = Path(*parts)
            if not (root / source).is_file():
                result[(source.as_posix(), rel.as_posix())] = False
    return result


def selected_review(entry: dict, language: str) -> bool:
    target = Path(entry["target"])
    if (entry["source"], entry["target"]) in (
        ("LICENSE", "LICENSE.ja.md"), ("TRADEMARKS.md", "TRADEMARKS.ja.md")):
        return language == "en"
    return language in target.parts[:-1] or target.name.endswith(f".{language}.md") or (
        entry["source"] == "README.ja.md" and entry["target"] == "README.md" and language == "en")


def notebook_issues(source: str, target: str) -> list[str]:
    left, right = json.loads(source), json.loads(target)
    a, b = left.get("cells"), right.get("cells")
    if not isinstance(a, list) or not isinstance(b, list):
        raise ValueError("notebook cells must be lists")
    if any(not isinstance(c, dict) or c.get("cell_type") not in ("code", "markdown", "raw")
           or not (isinstance(c.get("source", []), str) or
                   isinstance(c.get("source", []), list) and
                   all(isinstance(x, str) for x in c.get("source", []))) for c in a + b):
        raise ValueError("invalid notebook cell")
    issues = []
    if [c.get("cell_type") for c in a] != [c.get("cell_type") for c in b]:
        issues.append("ERROR: notebook cell types or order differ")
    ac = ["".join(c.get("source", [])) for c in a if c.get("cell_type") == "code"]
    bc = ["".join(c.get("source", [])) for c in b if c.get("cell_type") == "code"]
    if ac != bc:
        # コメントと表示用文字列だけの違いは許す(§34.2 の「コメント以外は完全一致」)。
        ea, eb = [code_essence(c) for c in ac], [code_essence(c) for c in bc]
        if [e[0] for e in ea] != [e[0] for e in eb]:
            issues.append("ERROR: notebook code cells differ beyond comments and string literals")
        else:
            changed = sum(1 for x, y in zip(ea, eb) if x[1] != y[1])
            if changed:
                issues.append(f"WARN: notebook string literals differ in {changed} code cell(s); "
                              "confirm they are display text, not paths or values")
    if any(c.get("outputs") for c in b):
        issues.append("WARN: notebook contains saved outputs; execution was not checked")
    return issues


def layout_issues(root: Path, source: str, target: str, language: str) -> list[str]:
    rel = Path(source)
    candidates = [Path(*rel.parts[:i], language, *rel.parts[i:])
                  for i in range(1, len(rel.parts))]
    candidates.append(rel.with_name(f"{rel.stem}.{language}{rel.suffix}"))
    copies = []
    for candidate in candidates:
        path = root / candidate
        if path.is_file() and candidate.as_posix() != target:
            if path.suffix == ".md" and "<!-- i18n-redirect -->" in text(path):
                continue
            copies.append(candidate.as_posix())
    return ["ERROR: duplicate translation bodies: " + ", ".join(copies)] if copies else []


def markdown_links(value: str):
    """通常のinlineリンク・画像・reference定義を走査。完全なMarkdownパーサではない。"""
    fence = None
    for number, line in enumerate(value.splitlines(), 1):
        mark = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if mark:
            run = mark[1]
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence):
                fence = None
            continue
        if fence or line.startswith("    "):
            continue
        line = re.sub(r"(`+).*?\1", "", line)
        # リンク先の丸括弧を対応させる。末尾の任意タイトルは対象外。
        starts = [m.end() for m in re.finditer(r"\]\(", line)]
        # reference 定義。GitHub の脚注定義 [^key]: はリンクではないので除く。
        definition = re.match(r"^ {0,3}\[(?!\^)[^\]]+\]:\s*", line)
        if definition:
            starts.append(definition.end())
        for start in starts:
            s = line[start:].lstrip()
            if s.startswith("<"):
                end = s.find(">")
                if end >= 0:
                    yield number, s[1:end], line
                continue
            depth, chars, escaped = 0, [], False
            for char in s:
                if escaped:
                    chars.append(char)
                    escaped = False
                    continue
                if char == "\\":
                    escaped = True
                    continue
                if char == "(" :
                    depth += 1
                elif char == ")":
                    if depth == 0:
                        break
                    depth -= 1
                elif char.isspace() and depth == 0:
                    break
                chars.append(char)
            if chars:
                yield number, "".join(chars), line


def markdown_structure(value: str) -> tuple[list[int], int]:
    """見出しレベルの並びと表の行数(コードブロック外)。ミラーは構成を保つ(§1)。

    表は「ヘッダ行+区切り行(|---|---|)」で始まる塊だけを数える。本文中の「|V| が…」
    のような絶対値記号で始まる行を表と誤認しない。
    """
    levels, rows, fence, in_table = [], 0, None, False
    lines = value.splitlines()
    for number, line in enumerate(lines):
        mark = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if mark:
            run = mark[1]
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence):
                fence = None
            in_table = False
            continue
        if fence:
            continue
        heading = HEADING.match(line)
        if heading:
            levels.append(len(heading[1]))
            in_table = False
            continue
        piped = line.lstrip().startswith("|")
        if piped and TABLE_RULE.match(line) and number and lines[number - 1].lstrip().startswith("|"):
            if not in_table:
                rows += 1  # 直前のヘッダ行
            in_table = True
        if in_table:
            if piped:
                rows += 1
            else:
                in_table = False
    return levels, rows


def structure_issues(source: str, target: str) -> list[str]:
    (la, ra), (lb, rb) = markdown_structure(source), markdown_structure(target)
    issues = []
    if la != lb:
        issues.append(f"WARN: heading structure differs ({len(la)} vs {len(lb)} headings)")
    if ra != rb:
        issues.append(f"WARN: table rows differ ({ra} vs {rb})")
    return issues


def stamp_issues(root: Path, target: str, source: str) -> list[str]:
    """ミラーの冒頭に正本の明示(パスの刻印、または正本へのリンク)があるか(§34.2)。"""
    path = inside(root, target)
    head = "\n".join(text(path).splitlines()[:30])
    if source in head:
        return []
    src = inside(root, source)
    for _, url, _ in markdown_links(head):
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        dest = (path.parent / unquote(parsed.path)).resolve()
        if dest == src:
            return []
    return [f"WARN: no stamp or link naming the source {source} in the first 30 lines"]


def link_issues(root: Path, target: str, source: str, mirrors: dict[str, str],
                language: str = "en") -> list[str]:
    issues = []
    path = inside(root, target)
    for number, url, context in markdown_links(text(path)):
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        dest = ((root if parsed.path.startswith("/") else path.parent)
                / unquote(parsed.path).lstrip("/")).resolve()
        if not dest.is_relative_to(root.resolve()):
            issues.append(f"ERROR: line {number}: link escapes repository: {url}")
            continue
        if not dest.exists():
            issues.append(f"ERROR: line {number}: missing local link: {url}")
            continue
        name = dest.relative_to(root.resolve()).as_posix()
        selector = re.search(r"日本語|Japanese|正本|authoritative|master copy", context, re.I)
        if name in LEGAL_ENGLISH and language == "en":
            continue  # 英語正本の法的文書は英語ミラーからそのまま参照してよい
        if name in mirrors and name != source and not selector:
            issues.append(f"WARN: line {number}: link to source; mirror is {mirrors[name]}")
    return issues


def load_scope(root: Path) -> list[dict]:
    """翻訳を要求しない正本のパターン(scope.json)。欠けていても無効ではない。"""
    path = root / SCOPE
    if not path.is_file():
        return []
    data = json.loads(text(path))
    if data.get("version") != 1 or not isinstance(data.get("not_required"), list):
        raise ValueError("invalid scope file")
    for item in data["not_required"]:
        if not isinstance(item.get("pattern"), str) or not item.get("reason", "").strip():
            raise ValueError("scope entries need a pattern and a reason")
    return data["not_required"]


def not_required(scope: list[dict], source: str) -> bool:
    return any(fnmatch.fnmatchcase(source, item["pattern"]) for item in scope)


def git_date(root: Path, name: str, cache: dict[str, str | None]) -> str | None:
    """最終コミット日(ISO 日付)。未コミットや Git 外では None。"""
    if name not in cache:
        try:
            out = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%cs", "--", name],
                                 capture_output=True, check=True).stdout.decode().strip()
            cache[name] = out or None
        except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
            cache[name] = None
    return cache[name]


def audit(root: Path, language: str = "en", links: bool = False,
          recorded_only: bool = False, git_dates: bool = False) -> list[dict]:
    registry = load_registry(root)
    scope = load_scope(root)
    reviews = {(e["source"], e["target"]): e for e in registry["reviews"]
               if selected_review(e, language)}
    discovered = discover(root, language)
    pairs = {} if recorded_only else dict(discovered)
    # 明示登録で自動発見の対象外(任意名の設定ファイル等)も扱える。
    for key in reviews:
        pairs.setdefault(key, False)
    mirrors = {s: t for s, t in discovered.keys() | reviews.keys()
               if (root / t).is_file()}
    rows, dates = [], {}
    for (source, target), legacy in sorted(pairs.items()):
        src, dst = inside(root, source), inside(root, target)
        entry, issues = reviews.get((source, target)), []
        status = "unreviewed"
        if not src.is_file():
            status = "missing-source"
            issues.append("ERROR: source file is missing")
        elif not dst.is_file():
            status = "not-required" if not_required(scope, source) else "missing"
        else:
            if entry:
                if digest(src) != entry["source_sha256"]:
                    status = "stale"
                elif digest(dst) != entry["target_sha256"]:
                    status = "translation-changed"
                else:
                    status = "reviewed"
            if src.suffix == ".txt":
                try:
                    issues.extend(parameter_issues(text(src), text(dst)))
                except ValueError as exc:
                    issues.append(f"ERROR: parameter lexer: {exc}")
            if src.suffix == ".ipynb":
                issues.extend(notebook_issues(text(src), text(dst)))
            if src.suffix == ".md" and dst.suffix == ".md":
                issues.extend(structure_issues(text(src), text(dst)))
                issues.extend(stamp_issues(root, target, source))
            if kind(src) == "presentation" and src.suffix != ".txt" and status != "reviewed":
                issues.append("WARN: presentation asset; data and rendering logic require manual review")
            issues.extend(layout_issues(root, source, target, language))
            if links and dst.suffix == ".md":
                issues.extend(link_issues(root, target, source, mirrors, language))
            if git_dates and status == "unreviewed":
                newer, older = git_date(root, source, dates), git_date(root, target, dates)
                if newer and older and newer > older:
                    issues.append(f"WARN: source committed after translation ({newer} > {older})")
        if legacy:
            issues.append("WARN: legacy suffix layout (allowed until migrated to en/)")
        rows.append({"source": source, "target": target, "status": status,
                     "recorded": entry is not None, "kind": kind(src), "issues": issues})
    if not recorded_only:
        for rel in repository_files(root):
            if language not in rel.parts[1:-1]:
                continue
            if rel.name in {"Makefile", "Run.sh", "Run_MPI.sh", "make_init.py"} or (
                    rel.name.startswith("Check_") and rel.suffix == ".py") or (
                    rel.suffix.lower() in {".tif", ".tiff", ".bil", ".dat"}):
                parts = list(rel.parts)
                parts.remove(language)
                rows.append({"source": Path(*parts).as_posix(), "target": rel.as_posix(),
                             "status": "shared-copy", "recorded": False, "kind": "shared",
                             "issues": ["ERROR: execution/input/reference asset duplicated in language directory"]})
    return rows


def record(root: Path, source: str, target: str, reviewer: str, method: str,
           reviewed_on: str) -> None:
    if source == target or not reviewer.strip() or method not in ("human", "assistant"):
        raise ValueError("distinct paths, a reviewer and a valid method are required")
    date.fromisoformat(reviewed_on)
    validate_direction(source, target)
    src, dst = inside(root, source), inside(root, target)
    if not src.is_file() or not dst.is_file():
        raise ValueError("both source and target must exist")
    if src.suffix == ".txt":
        problems = parameter_issues(text(src), text(dst))
        if any(i.startswith("ERROR:") for i in problems):
            raise ValueError("; ".join(problems))
    if src.suffix == ".ipynb":
        problems = notebook_issues(text(src), text(dst))
        if any(i.startswith("ERROR:") for i in problems):
            raise ValueError("; ".join(problems))
    data = load_registry(root)
    data["reviews"] = [e for e in data["reviews"]
                       if (e["source"], e["target"]) != (source, target)]
    data["reviews"].append({"source": source, "target": target,
                            "source_sha256": digest(src), "target_sha256": digest(dst),
                            "reviewer": reviewer, "method": method, "reviewed_on": reviewed_on})
    data["reviews"].sort(key=lambda e: (e["source"], e["target"]))
    path = root / REGISTRY
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("audit", help="対応・更新状況を確認する(ファイルは変更しない)")
    check.add_argument("--language", default="en")
    check.add_argument("--links", action="store_true")
    check.add_argument("--recorded-only", action="store_true")
    check.add_argument("--strict", action="store_true", help="未翻訳・未確認も不合格にする")
    check.add_argument("--strict-recorded", action="store_true", help="登録済みの更新漏れを不合格にする")
    check.add_argument("--git-dates", action="store_true",
                       help="未確認の組で正本の最終コミットが訳文より新しいものを警告する")
    check.add_argument("--all", action="store_true", help="not-required の組も一覧に出す")
    check.add_argument("--json", action="store_true")
    review = sub.add_parser("record", help="内容確認後に指定した1組だけを登録する")
    review.add_argument("source")
    review.add_argument("target")
    review.add_argument("--reviewer", required=True)
    review.add_argument("--method", choices=("human", "assistant"), required=True)
    review.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if not root.is_dir():
            raise ValueError(f"repository directory does not exist: {root}")
        if args.command == "record":
            record(root, args.source, args.target, args.reviewer, args.method, args.date)
            print(f"Recorded: {args.source} -> {args.target}")
            return 0
        if not re.fullmatch(r"[a-z]{2}(?:-[A-Za-z0-9]+)?", args.language) or args.language == "ja":
            raise ValueError("use a translation language such as en, fr or zh-CN; ja is the default source")
        rows = audit(root, args.language, args.links, args.recorded_only, args.git_dates)
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for row in rows:
                if row["status"] == "not-required" and not args.all:
                    continue
                print(f"{row['status']:20} {row['source']} -> {row['target']}")
                for issue in row["issues"]:
                    print(f"  {issue}")
            print("Summary:", dict(Counter(row["status"] for row in rows)))
        failed = any(any(i.startswith("ERROR:") for i in row["issues"])
                     or (args.strict and row["status"] not in ("reviewed", "not-required"))
                     or (args.strict_recorded and row["recorded"] and row["status"] != "reviewed")
                     for row in rows)
        return 1 if failed else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
