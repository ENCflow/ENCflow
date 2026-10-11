#!/usr/bin/env python3
"""bmi_vars: 機能依存の BMI 変数(動的変数表)の受け入れ試験(test/bmi_vars で実行)。

developer.md §76。変数表は「その量を生産する機能が有効な格子にだけ載る」:

  A. 構成 none(機能なし): 出力 = 基本 11・入力 = 基本 3。地下貯留 hg・
     積雪 swe は変数表になく、get / set は BmiError(機能無効 = 未知名と同じ)。
  B. 構成 full(バケツ地下水 + 気温 + 積雪): hg・swe が出力表に載り、
     - t0 の swe = snow_swe0、hg = 0(厳密)
     - 半分まで進めた hg・swe が解析値(毎ステップ一定増分)と一致
     - get の場が同時刻の分布出力(Hg/Sw/H ファイル。4 桁)と一致 = 行順の整合
     - 期間最大 hmax >= h、終了時の hmax が H9999(期間最大の要約出力)と一致
  C. 構成 ga(Green-Ampt): hg・swe の get は full と同じ。土層厚 sd(Green-Ampt
     が使う)も載り、値は sd0
  D. 同一プロセスでの再 initialize(none → full → none)で変数表が作り直される

同値 set の不変性(hg・swe の set。§76 段 2)は run_set_* が検査する:
  E. full を半分まで進めて get した hg・swe をそのまま set して継続したランの
     Log が、無介入ランの Log と全行一致。負値の set は BmiError
  F. ga の hg set(私有の累積浸透と不整合)と none の hg set は BmiError
"""

import os
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from encflow import (ENCflow, BmiError, VAR_DEPTH, VAR_DEPTH_MAX,  # noqa: E402
                     VAR_GW_STORAGE, VAR_SWE, VAR_SOIL_THICKNESS)

N_BASE_OUT = 11      # 無条件に存在する出力変数(h, z, pre, e, vv, qq, ux, uy, hmax, vvmax, qqmax)
N_BASE_IN = 3        # 同 入力(h, z, pre)
RATE = 10.0 / 3600.0 / 1000.0     # バケツの浸透能 (m/s。param_full の gw_infil_mmh)
PRE = 36.0 / 3600.0 / 1000.0      # 降雨強度 (m/s。全て雪になる)
SWE0 = 100.0e-3                   # 初期積雪水量 (m)
DT = 0.5
T_HALF = 30.0
T_END = 60.0


def fail(msg):
    print(f"test_vars: FAIL: {msg}")
    sys.exit(1)


def expect_error(what, func):
    try:
        func()
    except BmiError:
        return
    fail(f"{what} did not raise BmiError")


def load_field(path):
    """分布出力(行 1 = 北)を BMI 標準形(行 0 = 南)に"""
    return np.flipud(np.loadtxt(path))


def check_names(m, tag, extra_out, extra_in):
    names = m.output_var_names
    inames = m.input_var_names
    if len(names) != N_BASE_OUT + len(extra_out):
        fail(f"{tag}: {len(names)} output names, expected {N_BASE_OUT + len(extra_out)}: {names}")
    if len(inames) != N_BASE_IN + len(extra_in):
        fail(f"{tag}: {len(inames)} input names, expected {N_BASE_IN + len(extra_in)}: {inames}")
    for v in extra_out:
        if v not in names or not m.has(v):
            fail(f"{tag}: {v} missing from output names")
    for v in extra_in:
        if v not in inames:
            fail(f"{tag}: {v} missing from input names")
    for v in (VAR_GW_STORAGE, VAR_SWE):
        if v not in extra_out and (v in names or v in inames or m.has(v)):
            fail(f"{tag}: {v} listed although the feature is disabled")


def run_none():
    with ENCflow("param_none.txt") as m:
        check_names(m, "none", [], [])
        expect_error("none: get(hg)", lambda: m.get(VAR_GW_STORAGE))
        expect_error("none: get(swe)", lambda: m.get(VAR_SWE))
        zeros = np.zeros(m.nx * m.ny)
        expect_error("none: set(hg)", lambda: m.set(VAR_GW_STORAGE, zeros))
        expect_error("none: set(swe)", lambda: m.set(VAR_SWE, zeros))
        m.update_until(m.end_time)
    print("test_vars: A (none): hg/swe absent, get/set rejected")


def run_full(param, tag, extra_in):
    with ENCflow(param) as m:
        extra_out = [VAR_GW_STORAGE, VAR_SWE]
        if tag == "ga":
            extra_out.append(VAR_SOIL_THICKNESS)      # Green-Ampt は土層厚を使う
        check_names(m, tag, extra_out, extra_in)
        if tag == "ga" and np.max(np.abs(m.get(VAR_SOIL_THICKNESS) - 1.0)) > 0.0:
            fail(f"{tag}: sd != sd0")
        swe = m.get(VAR_SWE)
        hg = m.get(VAR_GW_STORAGE)
        if np.max(np.abs(swe - SWE0)) > 1e-15 or np.any(hg != 0.0):
            fail(f"{tag}: initial swe/hg: swe {swe.min()}..{swe.max()}, hg max {hg.max()}")
        m.update_until(T_HALF)
        nstep = round(T_HALF / DT)
        swe = m.get2d(VAR_SWE)
        hg = m.get2d(VAR_GW_STORAGE)
        h = m.get2d(VAR_DEPTH)
        if tag == "full":
            # バケツ: fx = min(rate·dt, h, cap − hg) = rate·dt(h・容量は十分)。
            # 雪: 全て雪なので swe += pre·dt。いずれも毎ステップ一定増分
            if np.max(np.abs(hg - nstep * RATE * DT)) > 1e-9 * nstep * RATE * DT:
                fail(f"{tag}: hg at t={T_HALF}: {hg.min()}..{hg.max()} != {nstep * RATE * DT}")
        if np.max(np.abs(swe - (SWE0 + nstep * PRE * DT))) > 1e-9 * SWE0:
            fail(f"{tag}: swe at t={T_HALF}: {swe.min()}..{swe.max()} != {SWE0 + nstep * PRE * DT}")
        # 分布出力(dt_file = 30 s → 番号 1)との一致(4 桁。行順の整合を含む)
        rdir = {"full": "result_full", "ga": "result_ga"}[tag]
        for name, arr, scale in ((f"{rdir}/Hg0001.txt", hg, 1.0),
                                 (f"{rdir}/Sw0001.txt", swe, 1000.0),
                                 (f"{rdir}/H0001.txt", h, 1.0)):
            f = load_field(name)
            if f.shape != arr.shape or np.max(np.abs(f - arr * scale)) > 6e-5:
                fail(f"{tag}: get != file {name}: max diff {np.max(np.abs(f - arr * scale))}")
        m.update_until(m.end_time)
        hmax = m.get2d(VAR_DEPTH_MAX)
        h = m.get2d(VAR_DEPTH)
        if np.any(hmax < h):
            fail(f"{tag}: hmax < h")
    f = load_field(f"{rdir}/H9999.txt")
    if np.max(np.abs(f - hmax)) > 6e-5:
        fail(f"{tag}: hmax != H9999: max diff {np.max(np.abs(f - hmax))}")
    print(f"test_vars: {'B' if tag == 'full' else 'C'} ({tag}): hg/swe listed, values and files consistent")


def run_reinit():
    counts = []
    for param in ("param_none.txt", "param_full.txt", "param_none.txt"):
        with ENCflow(param) as m:
            counts.append(len(m.output_var_names))
    if counts != [N_BASE_OUT, N_BASE_OUT + 2, N_BASE_OUT]:   # full は hg・swe の 2 つが増える
        fail(f"re-initialize: output counts {counts}")
    print("test_vars: D (re-initialize): variable table regenerated per initialize")


def compare_logs(fa, fb, what):
    la = open(fa, encoding="utf-8").read().splitlines()
    lb = open(fb, encoding="utf-8").read().splitlines()
    if la != lb:
        for i, (a, b) in enumerate(zip(la, lb)):
            if a != b:
                fail(f"{what}: Log differs at line {i + 1}:\n  {a}\n  {b}")
        fail(f"{what}: Log differs in length ({len(la)} vs {len(lb)})")
    print(f"test_vars: {what}: Log identical ({len(la)} lines)")


def run_set_invariance():
    """E. 同値 set の不変性(hg・swe)"""
    with ENCflow("param_full.txt") as m:
        m.update_until(m.end_time)
    shutil.copy("result_full/Log.txt", "Log_full_noset.txt")
    with ENCflow("param_full.txt") as m:
        m.update_until(T_HALF)
        hg = m.get(VAR_GW_STORAGE)
        swe = m.get(VAR_SWE)
        expect_error("full: set(hg < 0)", lambda: m.set(VAR_GW_STORAGE, -np.ones_like(hg)))
        expect_error("full: set(swe < 0)", lambda: m.set(VAR_SWE, -np.ones_like(swe)))
        m.set(VAR_GW_STORAGE, hg)
        m.set(VAR_SWE, swe.reshape(m.ny, m.nx))
        m.update_until(m.end_time)
        if np.any(m.get(VAR_GW_STORAGE) < hg) or np.any(m.get(VAR_SWE) < swe):
            fail("full: state decreased after same-value set")
    compare_logs("Log_full_noset.txt", "result_full/Log.txt",
                 "E (full): same-value set of hg/swe is invariant")


def run_set_rejection():
    """F. 受理条件: Green-Ampt の hg set は拒否、swe set は受理"""
    with ENCflow("param_ga.txt") as m:
        m.update_until(T_HALF)
        hg = m.get(VAR_GW_STORAGE)
        if VAR_GW_STORAGE in m.input_var_names:
            fail("ga: hg listed as input although Green-Ampt cannot accept a replacement")
        expect_error("ga: set(hg)", lambda: m.set(VAR_GW_STORAGE, hg))
        m.set(VAR_SWE, m.get(VAR_SWE))
        m.update_until(m.end_time)
    print("test_vars: F (ga): hg set rejected, swe set accepted")


def main():
    os.chdir(os.getcwd())
    for d in ("result_none", "result_full", "result_ga"):
        shutil.rmtree(d, ignore_errors=True)
    run_none()
    run_full("param_full.txt", "full", extra_in=[VAR_GW_STORAGE, VAR_SWE] if "--set" in sys.argv else [])
    run_full("param_ga.txt", "ga", extra_in=[VAR_SWE] if "--set" in sys.argv else [])
    run_reinit()
    if "--set" in sys.argv:
        run_set_invariance()
        run_set_rejection()
    print("test_vars: all checks passed")


if __name__ == "__main__":
    main()
