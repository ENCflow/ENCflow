#!/usr/bin/env python3
"""Check_modstate.py — src/ のモジュールスコープ状態の台帳と検査

目的(docs/nesting_plan.md §3.2・§13.3):
  複数インスタンス化(ネスティング)では「モジュール変数 = 格子ごとに
  分かれていない状態」を把握し続ける必要がある。本スクリプトは src/*.f90 の
  各 module / submodule の仕様部(contains より前)から、parameter でない
  変数宣言を抜き出して一覧にする。あわせて、手続き内の初期化付き宣言
  (暗黙 SAVE)を検出する。

使い方:
  python3 test/Scripts/Check_modstate.py            # 台帳を表示
  python3 test/Scripts/Check_modstate.py --check    # 許可表と突き合わせて
                                                     # 不一致なら終了コード 1

許可表(ALLOWED)は nesting_plan.md §3.2 の分類表の機械写し。
  A 群: 所有の明示(型の成分へ移す予定。Phase 0b で消える)
  B 群: 文脈の付け替え(bind)。宣言部に残る
  X   : 実行コンテキスト・定数的な状態(共有でよい)
Phase 0b 以降は、A 群の行が消えたら許可表からも消す(消し忘れは
--check が「許可表にあるが存在しない」として報告する)。
新しいモジュール変数は原則として型に置く(§12)。やむを得ず増やす場合は
理由を developer.md に書き、ここに登録する。
"""
import re
import sys
import glob
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
SRC = os.path.join(ROOT, "src")

# 許可表: ファイル名 -> {変数名: 群}
ALLOWED = {
    # 並列層(実行コンテキスト。dcp は B: par_decomp_bind で付け替え)
    "m_parallel_serial.f90": {"nrank": "X", "nproc": "X", "is_root": "X", "dcp": "B"},
    "m_parallel_mpi.f90": {"nrank": "X", "nproc": "X", "is_root": "X", "dcp": "B",
                            "js_tab": "B", "je_tab": "B", "MPI_WP": "X", "owns_mpi": "X"},
    # m_main のインスタンス(Phase 0c で enc(:) になる)
    "m_main.f90": {"enc": "X"},
    # list_* の namelist 作業配列(読み込み時の一時領域。読んだ直後に型へ写す)
    "list_boundary.f90": {"src_cell": "X", "src_val": "X", "stage_cell": "X", "stage_val": "X",
                          "inflow_cell": "X", "inflow_val": "X", "inflow_cs": "X", "inflow_qs": "X"},
    "list_lavaflow.f90": {"lv_cell": "X", "lv_val": "X"},
    "list_structure.f90": {"pump_in_cell": "X", "pump_out_cell": "X", "pump_rule": "X",
                           "culv_in_cell": "X", "culv_out_cell": "X", "culv_gate_rule": "X",
                           "div_in_cell": "X", "div_out_cell": "X", "div_rule": "X",
                           "dam_in_cell": "X", "dam_out_cell": "X", "dam_hv": "X", "dam_hq_rule": "X"},
    # A 群
    "m_gwflow_bucket.f90": {"gwb": "A"},
    "m_gwflow_greenampt.f90": {"ga": "A"},
    "m_gwflow_lateral.f90": {"glt": "A", "lay1": "A"},
    "m_gwflow_layer2.f90": {"gl2": "A"},
    "m_gwflow_conduit.f90": {"gwc": "A"},
    "m_gwflow_pump.f90": {"gp": "A", "gwp_cell": "A", "gwp_val": "A"},
    "m_gwflow_frost.f90": {"fro": "A"},
    "m_geomorph.f90": {"crp": "A", "flv": "A", "dbr": "A", "spl": "A", "bsl": "A", "wrk": "A"},
    "m_glacier.f90": {"glw": "A"},
    "m_lavaflow.f90": {"lvw": "A"},
    "m_saltwater.f90": {"sw": "A"},
    "m_intercept_fixed.f90": {"icf": "A"},
    "m_intercept_initloss.f90": {"ici": "A"},
    "m_boundary_structure.f90": {"pump_src_checked": "A"},
    "m_output.f90": {"un_fnolist": "A", "wk_out": "A", "wk_out_i": "A"},
    # B 群(m_swflow_enc 本体は変数が多いので「全て B」として扱う)
    "m_swflow_enc.f90": "B",
    "m_swflow_enc_adv.f90": {"tx_mod": "B"},
    "m_swflow_enc_diff.f90": {"td_mod": "B"},
    "m_swflow_enc_nh.f90": {"nh_mod": "B"},
    "m_swflow_enc_bc.f90": {"f_bc_side": "B", "bt_cell": "B", "bc_eta_cell": "B",
                            "infl_wseg": "B", "infl_cfac": "B", "infl_hseg": "B"},
    "m_ffactor.f90": {"powf": "B", "ff_nn": "B", "ff_h": "B", "ff_f": "B", "ff_a0": "B", "ff_a1": "B"},
    # STG(凍結。ネスト非対応で par_stop)
    "m_swflow_stg.f90": "X",
}

DECL = re.compile(r"^\s*(real|integer|logical|character|double\s+precision|complex|type\s*\(|class\s*\()",
                  re.I)
PROC = re.compile(r"^\s*(?:(?:pure|elemental|recursive|impure|module)\s+)*(subroutine|function)\s+([A-Za-z_]\w*)",
                  re.I)
ENDPROC = re.compile(r"^\s*end\s+(subroutine|function)\b", re.I)
TYPEDEF = re.compile(r"^\s*type\s*(?:,[^:]*)?(?:::)?\s*([A-Za-z_]\w*)\s*(!.*)?$", re.I)
ENDTYPE = re.compile(r"^\s*end\s+type\b", re.I)
IFACE = re.compile(r"^\s*(abstract\s+)?interface\b", re.I)
ENDIFACE = re.compile(r"^\s*end\s+interface\b", re.I)
MODHEAD = re.compile(r"^\s*(?:module\s+(?!procedure\b|subroutine\b|function\b|pure\b|elemental\b|recursive\b)[A-Za-z_]|submodule\s*\()", re.I)
CONTAINS = re.compile(r"^\s*contains\s*(!.*)?$", re.I)


def strip_comment(line):
    # 文字列中の ! は無視する(簡易: 引用符の外だけ)
    out = []
    q = None
    for ch in line:
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in ("'", '"'):
            q = ch
            out.append(ch)
        elif ch == "!":
            break
        else:
            out.append(ch)
    return "".join(out)


def join_continuations(lines):
    """& 継続行を 1 行にまとめる(行番号は先頭行)"""
    out = []
    buf = None
    bufno = 0
    for no, raw in enumerate(lines, 1):
        code = strip_comment(raw).rstrip()
        if buf is not None:
            code = code.lstrip()
            if code.startswith("&"):
                code = code[1:]
            buf += " " + code
        else:
            buf = code
            bufno = no
        if buf.rstrip().endswith("&"):
            buf = buf.rstrip()[:-1]
            continue
        out.append((bufno, buf))
        buf = None
    if buf is not None:
        out.append((bufno, buf))
    return out


def declared_names(decl):
    """宣言文から変数名の並びを返す(parameter は除外。成分の初期化は切る)"""
    if "::" in decl:
        attrs, names = decl.split("::", 1)
    else:
        # 旧形式 real x, y
        m = re.match(r"^\s*(real|integer|logical|character|double\s+precision|complex)\s*(\*\s*\d+|\([^)]*\))?\s*(.*)$",
                     decl, re.I)
        if not m:
            return [], False
        attrs, names = m.group(1), m.group(3)
    is_param = re.search(r"\bparameter\b", attrs, re.I) is not None
    out = []
    depth = 0
    cur = ""
    for ch in names:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    result = []
    for item in out:
        name = re.split(r"[=(\s*]", item.strip(), 1)[0]
        if name:
            result.append(name)
    return result, is_param


def scan_file(path):
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    joined = join_continuations(lines)
    modvars = []       # (lineno, name, decl)
    implicit_save = []  # (lineno, proc, decl)
    in_spec = False
    in_type = False
    in_iface = False
    proc = None
    for no, code in joined:
        if not code.strip():
            continue
        m = PROC.match(code)
        if m and not in_iface:
            proc = m.group(2)
            continue
        if MODHEAD.match(code):
            in_spec = True
            continue
        if CONTAINS.match(code) and proc is None and in_spec:
            in_spec = False
            continue
        if TYPEDEF.match(code) and not re.match(r"^\s*type\s*\(", code, re.I):
            in_type = True
            continue
        if ENDTYPE.match(code):
            in_type = False
            continue
        if IFACE.match(code):
            in_iface = True
            continue
        if ENDIFACE.match(code):
            in_iface = False
            continue
        if ENDPROC.match(code):
            proc = None
            continue
        if in_type or in_iface:
            continue
        if DECL.match(code):
            names, is_param = declared_names(code)
            if is_param:
                continue
            if in_spec and proc is None:
                for n in names:
                    modvars.append((no, n, code.strip()))
            elif proc is not None and "=" in code.split("::", 1)[-1] \
                    and not re.search(r"\bintent\b", code, re.I):
                # 手続き内の初期化付き宣言 = 暗黙 SAVE。
                # ただし配列の寸法式 (1:n) 中の = は除く: '::' 右側に = がある場合のみ
                rhs = code.split("::", 1)[-1] if "::" in code else ""
                if "=" in re.sub(r"\([^)]*\)", "", rhs):
                    implicit_save.append((no, proc, code.strip()))
    return modvars, implicit_save


def main():
    check = "--check" in sys.argv
    files = sorted(glob.glob(os.path.join(SRC, "*.f90")))
    problems = []
    print("# モジュールスコープの状態変数(parameter を除く)")
    for path in files:
        base = os.path.basename(path)
        modvars, implicit_save = scan_file(path)
        allowed = ALLOWED.get(base, {})
        if modvars:
            print(f"\n## {base}")
            for no, name, decl in modvars:
                if allowed == "B" or allowed == "X":
                    grp = allowed
                else:
                    grp = allowed.get(name)
                tag = grp if grp else "??"
                print(f"  {no:5d}  [{tag}] {name:20s} {decl[:70]}")
                if check and not grp:
                    problems.append(f"{base}:{no}: 許可表にないモジュール変数 {name}")
        if isinstance(allowed, dict):
            present = {n for _, n, _ in modvars}
            for n in allowed:
                if n not in present:
                    problems.append(f"{base}: 許可表にあるが存在しない {n}(表を更新すること)")
        for no, proc, decl in implicit_save:
            print(f"  {no:5d}  [SAVE!] {proc}: {decl[:70]}")
            problems.append(f"{base}:{no}: 手続き {proc} 内の初期化付き宣言(暗黙 SAVE)")
    if check:
        if problems:
            print("\n# 不一致")
            for p in problems:
                print("  " + p)
            sys.exit(1)
        print("\n# OK: 許可表と一致、暗黙 SAVE なし")


if __name__ == "__main__":
    main()
