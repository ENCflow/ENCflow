#!/usr/bin/env python3
"""bmi_dam: ダムの量の BMI 公開と外部運転(f_dam_mode = 6)の受け入れ試験
(test/bmi_dam で実行。developer.md §133)。

  A. 変数表と格子: ダムの量 5 つ(水位・貯水量・流入・放流・スピル)と目標放流量が
     出力表に、目標放流量が入力表に載る。ダムの点の格子は "unstructured"、節点数 =
     ダム数 4、節点の座標 = 捕捉帯のセルの中心。initialize 直後の値(初期水位、
     目標放流量の初期値 = dam_q0、ほかのダムはその運転則の放流 = 0)。負の目標と
     長さの違う配列は拒否される
  B. 外部運転の等価性: ダム 2(外部運転)に、ダム 1(放流量の時系列 = モデルが
     放流する)と同じ段状の放流量を毎歩 set すると、ダム 1 と 2 の CSV が全行一致
  C. 見本の制御器(dam_control.LevelController。貯水位を保つ・上限・変化の速さの
     制限)で運転したダム 3: 目標の変化が毎歩 rate × dt 以内(制限は洪水の流入の
     立ち上がりより小さく、洪水の間は効き続ける = 履歴を使う規則が働く)、水位は
     初期値の ±10 cm に収まり、放流 ≤ 上限、実際の放流 = 目標(死水に当たらない)
  D. 外部運転でないダム(1 = 時系列、4 = 一定量放流方式)へ set した要素(999)は
     無視される(放流がその運転則のまま)
  E. get の値が同時刻のダム CSV(印字の桁)と一致。閉じた系の体積保存(Log の S)
  F. 同一プロセスでの再 initialize: 外部運転のダムのない設定では目標放流量が表に
     なく(ダムの量 5 つは残る)、set は BmiError
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from encflow import (ENCflow, BmiError, VAR_RESERVOIR_LEVEL, VAR_RESERVOIR_VOLUME,  # noqa: E402
                     VAR_RESERVOIR_INFLOW, VAR_RESERVOIR_OUTFLOW, VAR_RESERVOIR_SPILL,
                     VAR_RESERVOIR_TARGET)
from dam_control import LevelController  # noqa: E402

DAM_VARS = [VAR_RESERVOIR_LEVEL, VAR_RESERVOIR_VOLUME, VAR_RESERVOIR_INFLOW,
            VAR_RESERVOIR_OUTFLOW, VAR_RESERVOIR_SPILL]
NDAM = 4
XY = [(15.0, 85.0), (15.0, 65.0), (15.0, 45.0), (15.0, 25.0)]   # 捕捉帯 (2, 2/4/6/8) の中心
STEPS = [(0.0, 0.3), (1200.0, 0.6), (3600.0, 0.4)]   # ダム 1 の段状の放流量(時刻 s, m3/s)
QMAX, RATE, TAU = 2.0, 0.0004, 1800.0                # ダム 3 の制御器(RATE は洪水の流入の
                                                     # 立ち上がり 1.5/3600 m3/s/s より小さい = 洪水の間は効く)
TOLQ, TOLH = 1.5e-4, 1.5e-4
NVALID, AREA = 4 + 20 * 10, 100.0                    # 有効セル数(捕捉帯 4 + 池)とセル面積
SRC = [(0.0, 0.2), (3600.0, 1.7), (7200.0, 0.2), (24000.0, 0.2)]   # ソース(4 つとも同じ)


def fail(msg):
    print(f"test_dam: FAIL: {msg}")
    sys.exit(1)


def ok(msg):
    print(f"test_dam: ok   {msg}")


def expect_error(what, func, errors=(BmiError,)):
    try:
        func()
    except errors:
        return
    fail(f"{what} did not raise {errors}")


def step_release(t):
    """ダム 1 の段状の放流量(interp_series と同じく、段の時刻ちょうどは後の値)。"""
    q = STEPS[0][1]
    for tk, qk in STEPS:
        if t >= tk:
            q = qk
    return q


def interp(series, t):
    if t <= series[0][0]:
        return series[0][1]
    for k in range(1, len(series)):
        if t < series[k][0]:
            (t0, q0), (t1, q1) = series[k - 1], series[k]
            return q0 + (t - t0) / (t1 - t0) * (q1 - q0)
    return series[-1][1]


def read_csv(path):
    rows = []
    for line in open(path):
        if line.startswith("#"):
            continue
        v = [float(x) for x in line.split(",")]
        rows.append(v)
    return np.array(rows)


def part_a(m):
    out, inp = m.output_var_names, m.input_var_names
    for v in DAM_VARS + [VAR_RESERVOIR_TARGET]:
        if v not in out:
            fail(f"{v} not in output variables")
    if VAR_RESERVOIR_TARGET not in inp or any(v in inp for v in DAM_VARS):
        fail(f"input variables: {inp}")
    g = m.dam_grid
    if g is None or m.grid_type(g) != "unstructured" or m.ndam != NDAM:
        fail(f"dam grid {g}: type {m.grid_type(g) if g is not None else None}, ndam {m.ndam}")
    if any(m.var_grid(v) != g for v in DAM_VARS):
        fail("dam variables are not on the dam grid")
    x, y = m.dam_xy()
    if not np.allclose(np.c_[x, y], XY, atol=1e-9):
        fail(f"dam coordinates {list(zip(x, y))} != {XY}")
    lv, tg = m.get(VAR_RESERVOIR_LEVEL), m.get(VAR_RESERVOIR_TARGET)
    if not np.allclose(lv, [104.0, 104.0, 104.0, 103.0], atol=1e-12):
        fail(f"initial levels {lv}")
    if not np.allclose(tg, [0.0, 0.3, 0.2, 0.0], atol=1e-12) or np.any(m.get(VAR_RESERVOIR_INFLOW) != 0.0):
        fail(f"initial target {tg}")
    expect_error("negative target", lambda: m.set(VAR_RESERVOIR_TARGET, [0.0, -0.1, 0.2, 0.0]))
    expect_error("target of wrong length", lambda: m.set(VAR_RESERVOIR_TARGET, [0.3, 0.2]),
                 (BmiError, ValueError))
    if not np.allclose(m.get(VAR_RESERVOIR_TARGET), [0.0, 0.3, 0.2, 0.0], atol=1e-12):
        fail("a rejected set changed the targets")
    ok(f"variables, dam grid (unstructured, {NDAM} nodes at the capture cells), initial values, "
       "rejected sets")


def run_controlled(param):
    """A〜E: ダム 2 = 段状の放流量、ダム 3 = 見本の制御器、ダム 1・4 には 999 を set。"""
    rec = {}
    with ENCflow(param) as m:
        part_a(m)
        dt = m.time_step
        ctl = LevelController(m.get(VAR_RESERVOIR_VOLUME)[2], tau=TAU, qmax=QMAX, rate=RATE,
                              q_init=0.2)
        targets3 = []
        while m.time < m.end_time - 0.5 * dt:
            t_next = m.time + dt
            q3 = float(ctl.target(m.get(VAR_RESERVOIR_VOLUME)[2],
                                  m.get(VAR_RESERVOIR_INFLOW)[2], dt))
            targets3.append(q3)
            m.set(VAR_RESERVOIR_TARGET, [999.0, step_release(t_next), q3, 999.0])
            m.update()
            if abs(m.time / 60.0 - round(m.time / 60.0)) < 1e-9:
                rec[round(m.time)] = {v: m.get(v).copy() for v in DAM_VARS}
    return rec, np.array(targets3)


def main():
    case = os.getcwd()
    param = os.path.join(case, "param.txt")
    rec, tg3 = run_controlled(param)
    d = [read_csv(os.path.join(case, "result", "dams", f"dam{k:04d}.csv")) for k in range(1, 5)]

    # B. ダム 1(時系列)と 2(外部運転で同じ放流量)の全行一致
    if d[0].shape != d[1].shape or not np.array_equal(d[0], d[1]):
        diff = np.max(np.abs(d[0] - d[1])) if d[0].shape == d[1].shape else "shape"
        fail(f"dam 2 (external) differs from dam 1 (release series): max |d| = {diff}")
    ok(f"dam 2 driven through BMI with the release series of dam 1 matches dam 1 on all "
       f"{len(d[0])} rows")

    # C. ダム 3: 見本の制御器
    h3 = d[2][1:, 2]
    if np.max(np.abs(h3 - 104.0)) > 0.10:
        fail(f"dam 3 level left 104 m +- 10 cm (max |dH| = {np.max(np.abs(h3 - 104.0)):.4f})")
    dq = np.abs(np.diff(np.r_[0.2, tg3]))
    nbind = int(np.sum(np.isclose(dq, RATE * 1.0)))
    if np.max(dq) > RATE * 1.0 + 1e-12 or np.max(tg3) > QMAX + 1e-12 or nbind < len(dq) // 2:
        fail(f"dam 3 target: max step change {np.max(dq):.3e}, max {np.max(tg3):.3f}, "
             f"steps at the rate limit {nbind}/{len(dq)}")
    worst = max(abs(rec[t][VAR_RESERVOIR_OUTFLOW][2] - tg3[t - 1]) for t in rec)
    if worst > 1e-9:
        fail(f"dam 3 release differs from its target (max |d| = {worst:.3e})")
    ok(f"dam 3 with the sample controller: target change <= {RATE} m3/s/s (at the limit in "
       f"{nbind}/{len(dq)} steps), level within 104 m +- {np.max(np.abs(h3 - 104.0)):.4f} m, "
       f"release = target")

    # D. 外部運転でないダムへの 999 は無視される
    if np.max(d[0][1:, 5]) > 0.6 + TOLQ or np.max(d[3][1:, 5]) > 0.5 + TOLQ:
        fail(f"dams 1 and 4 released {np.max(d[0][1:, 5])}, {np.max(d[3][1:, 5])} (999 not ignored)")
    ok("the elements of dams not in external operation (999) are ignored (dam 1 <= 0.6, dam 4 <= 0.5)")

    # E. get の値 = 同時刻の CSV(印字の桁)
    worst = 0.0
    for k in range(4):
        rows = {round(r[1] * 60.0): r for r in d[k]}
        for t, vals in rec.items():
            r = rows[t]
            for col, v in ((2, VAR_RESERVOIR_LEVEL), (4, VAR_RESERVOIR_INFLOW),
                           (5, VAR_RESERVOIR_OUTFLOW), (6, VAR_RESERVOIR_SPILL)):
                worst = max(worst, abs(vals[v][k] - r[col]))
            if abs(vals[VAR_RESERVOIR_VOLUME][k] - r[3]) > 1e-6 * max(1.0, abs(r[3])):
                fail(f"dam {k + 1} volume at t={t}: get {vals[VAR_RESERVOIR_VOLUME][k]} vs CSV {r[3]}")
    if worst > TOLQ:
        fail(f"get values differ from the dam CSV (max |d| = {worst:.2e})")
    ok(f"get values equal the dam CSV at {len(rec)} record times (max |d| = {worst:.1e})")
    # 閉じた系の体積保存: S × 有効面積 = 初期貯水量 + ソースの累計
    v0 = 3 * 16000.0 + 12000.0
    logrows = []
    for line in open(os.path.join(case, "result", "Log.txt")):
        p = line.split()
        if p and p[0][0].isdigit():
            hh, mm, ss = p[0].split(":")
            logrows.append((int(hh) * 3600 + int(mm) * 60 + float(ss), float(p[2])))
    vol, k, cum = v0, 0, {0: v0}
    while k < max(t for t, _ in logrows):
        k += 1
        vol += 4 * interp(SRC, float(k))
        cum[k] = vol
    worst = max(abs(sv - cum[round(t)] / (NVALID * AREA)) for t, sv in logrows)
    if worst > 1e-9:
        fail(f"closed-system volume: max |dS| = {worst:.2e} m")
    ok(f"closed-system volume conserved with external releases (max |dS| = {worst:.1e} m)")

    # F. 外部運転のダムのない設定(同一プロセスで再 initialize)
    rule = os.path.join(case, "wrk_param_rule.txt")
    txt = open(param).read()
    for a, b in (("f_dam_mode(2) = 6", "f_dam_mode(2) = 1"), ("f_dam_mode(3) = 6", "f_dam_mode(3) = 1"),
                 ("dir_result = 'result'", "dir_result = 'result_rule'")):
        if txt.count(a) != 1:
            fail(f"cannot make the rule-only variant ({a})")
        txt = txt.replace(a, b)
    open(rule, "w").write(txt)
    with ENCflow(rule) as m:
        if m.has(VAR_RESERVOIR_TARGET) or VAR_RESERVOIR_TARGET in m.input_var_names:
            fail("target listed without externally operated dams")
        if not all(m.has(v) for v in DAM_VARS) or m.ndam != NDAM:
            fail("dam variables missing in the rule-only variant")
        expect_error("set target without externally operated dams",
                     lambda: m.set(VAR_RESERVOIR_TARGET, [0.1] * NDAM))
    ok("re-initialize without externally operated dams: no target variable, set raises BmiError")
    print("test_dam: all checks passed")


if __name__ == "__main__":
    main()
