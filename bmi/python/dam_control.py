#!/usr/bin/env python3
"""ダムを BMI で外から運転する見本(developer.md §133)。

外部運転(&list_struct_dam の f_dam_mode = 6)のダムは、モデルの運転則ではなく、
BMI で与えた目標放流量で放流する。ここでは、貯水位を目標の水位に保つ簡単な
制御器を Python で書き、1 歩ごとに

    get(貯水量・流入) → 制御器が目標放流量を決める → set(目標放流量) → update

を繰り返す。制御器は、モデルの組み込みの運転則では表せない「放流量の増加・減少の
速さの制限」(前の歩の目標を覚えておく = 履歴)を持つ。死水の下限とサーチャージ
超過のスピルはモデルが守るので、制御器が過大な目標を出しても水を作り出しはしない
(実際の放流は VAR_RESERVOIR_OUTFLOW で確かめる)。

使い方(ダムのあるケースのディレクトリで):
    python3 ../../bmi/python/dam_control.py param.txt [--csv out.csv]

    外部運転のダムをすべて、初期の貯水量に保つように運転する(時定数 30 分、
    放流の上限 2 m3/s、変化の速さの上限 0.001 m3/s/s)。各歩の時刻・水位・流入・
    放流・目標を --csv に書く。

この制御器は見本で、実際のダムの操作規則を表すものではない。どの規則で運転するかは
利用者が決め、その規則のプログラムは結果と一緒に保存しておくこと(ENCflow の
出力には、外から与えた放流の決め方は残らない)。
"""

import argparse
import csv
import sys

import numpy as np

from encflow import (ENCflow, BmiError, VAR_RESERVOIR_LEVEL, VAR_RESERVOIR_VOLUME,
                     VAR_RESERVOIR_INFLOW, VAR_RESERVOIR_OUTFLOW, VAR_RESERVOIR_TARGET)


class LevelController:
    """貯水量を目標の貯水量 v_target へ戻す放流の制御(見本)。

    目標放流量 = 流入 + (V − v_target) / tau を、0 以上 qmax 以下に抑え、さらに
    前の歩の目標からの変化を rate × dt 以内に抑える(放流量の増加・減少の速さの
    制限。前の歩の目標 = 制御器が覚えている履歴)。
    v_target・qmax・rate はダムごとの配列でもよい。
    """

    def __init__(self, v_target, tau=1800.0, qmax=np.inf, rate=np.inf, q_init=None):
        self.v_target = np.asarray(v_target, dtype=float)
        self.tau = float(tau)
        self.qmax = qmax
        self.rate = rate
        self.q_prev = None if q_init is None else np.asarray(q_init, dtype=float).copy()

    def target(self, v, qin, dt):
        q = qin + (v - self.v_target) / self.tau
        q = np.clip(q, 0.0, self.qmax)
        if self.q_prev is not None:
            q = np.clip(q, self.q_prev - self.rate * dt, self.q_prev + self.rate * dt)
            q = np.maximum(q, 0.0)
        self.q_prev = q.copy()
        return q


def run(param, csv_path=None, tau=1800.0, qmax=2.0, rate=0.001):
    """param のケースを最後まで進め、外部運転のダムを LevelController で運転する。

    戻り値: 各歩の記録(dict のリスト)。外部運転のダムがなければ BmiError。
    """
    rows = []
    with ENCflow(param) as m:
        if not m.has(VAR_RESERVOIR_TARGET):
            raise BmiError("no externally operated dam (f_dam_mode = 6) in " + str(param))
        v0 = m.get(VAR_RESERVOIR_VOLUME)
        ctl = LevelController(v0, tau=tau, qmax=qmax, rate=rate,
                              q_init=m.get(VAR_RESERVOIR_TARGET))
        dt = m.time_step
        while m.time < m.end_time - 0.5 * dt:
            q = ctl.target(m.get(VAR_RESERVOIR_VOLUME), m.get(VAR_RESERVOIR_INFLOW), dt)
            m.set(VAR_RESERVOIR_TARGET, q)     # 外部運転でないダムの要素は無視される
            m.update()
            rows.append({"t": m.time,
                         "level": m.get(VAR_RESERVOIR_LEVEL),
                         "inflow": m.get(VAR_RESERVOIR_INFLOW),
                         "release": m.get(VAR_RESERVOIR_OUTFLOW),
                         "target": q})
    if csv_path:
        n = len(rows[0]["level"]) if rows else 0
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_s"] + [f"{k}_{i + 1}" for i in range(n)
                                  for k in ("level_m", "inflow_m3s", "release_m3s", "target_m3s")])
            for r in rows:
                w.writerow([f"{r['t']:.1f}"] + [f"{r[k][i]:.6f}" for i in range(n)
                                                for k in ("level", "inflow", "release", "target")])
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("param", help="parameter file of a case with f_dam_mode = 6 dams")
    ap.add_argument("--csv", help="write t, level, inflow, release and target of every dam")
    ap.add_argument("--tau", type=float, default=1800.0, help="time constant (s)")
    ap.add_argument("--qmax", type=float, default=2.0, help="maximum release (m3/s)")
    ap.add_argument("--rate", type=float, default=0.001, help="maximum change of release (m3/s/s)")
    a = ap.parse_args(argv)
    rows = run(a.param, a.csv, a.tau, a.qmax, a.rate)
    last = rows[-1]
    for i, (h, q) in enumerate(zip(last["level"], last["release"]), 1):
        print(f"dam {i}: final level {h:.4f} m, release {q:.4f} m3/s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
