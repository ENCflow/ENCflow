#!/usr/bin/env python3
"""examples/coarse_channel: 計算結果から通水の幅などを読み取る(plot_results.py と make table が使う)

  python3 analyze.py [系列 ...]     系列ごとの数表を標準出力に書く(英語は ENCFLOW_LANG=en)

直線の河道: 中ほどの 2 km(中心線の距離 3〜5 km)の河道セルの水深の平均 h と、水位を中心線の距離に当てはめた直線の
傾き I から、通水の幅 B_eff = n Q /(h^(5/3) √I) を逆算し、川幅 B で割る(細かい格子は表した幅 round(B/δ) δ で割る)。
屈曲: 上流の直線区間(中心線の距離 1〜2.5 km)の河道セルの水位が等流の水位より高い分(背水の高さ)。
河道の脇の水: 直線の河道と同じ通水の幅。雨のケースは、流入の流量に、測る区間の中ほどより上流に降った雨を足す。
"""
import math
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_cases as mc

EN = os.environ.get("ENCFLOW_LANG", "ja") == "en"


def T(ja, en):
    return en if EN else ja


def last_out(kw):
    return 4 if kw.get("rep") == "fine" else 8


def load_e(name, k):
    return np.loadtxt(os.path.join(mc.RUNS, f"result_{name}", f"E{k:04d}.txt"))


def done(name, kw):
    return os.path.exists(os.path.join(mc.RUNS, f"result_{name}", f"E{last_out(kw):04d}.txt"))


def beff_of(e, z, s, chan, q):
    """測る区間の水深の平均・水面勾配から通水の幅を逆算する"""
    sel = chan & (s >= mc.S1) & (s <= mc.S2)
    h = float((e - z)[sel].mean())
    slope = -float(np.polyfit(s[sel], e[sel], 1)[0])
    return mc.RN * q / (math.sqrt(slope) * h ** (5.0 / 3.0)), h, slope


def measure(name, kind, kw):
    k = last_out(kw)
    e1, e0 = load_e(name, k), load_e(name, k - 1)
    if kind == "straight":
        g = mc.straight(kw["an"], kw["b"], kw["rep"], kw["dx"], kw.get("off", 0.0))
        chan = g["width"] > 0
        b = kw["b"]
        beff, h, slope = beff_of(e1, g["z"], g["s"], chan, mc.QB * b)
        ref = g["brep"] if kw["rep"] == "fine" else b
        drift = float(np.abs(e1 - e0)[chan & (np.arange(g["nx"])[None, :] > 0)].max())
        return dict(rel=beff / ref, beff=beff, h=h, slope=slope / mc.S, area=g["area"] / b, drift=drift)
    if kind == "bend":
        g = mc.bend(kw["r"], kw["b"], kw["rep"], kw["dx"])
        chan = g["width"] > 0
        s = g["s"]
        up = chan & (s >= 1000.0) & (s <= 2500.0)
        eta_n = mc.Z0 - mc.S * s + mc.hn(mc.QB)
        rise = float((e1 - eta_n)[up].mean())
        drift = float(np.abs(e1 - e0)[chan & (np.arange(g["nx"])[None, :] > 0)].max())
        return dict(rise=rise, drift=drift)
    # 河道の脇の水
    g = mc.wet(kw["var"])
    chan = g["chan"]
    q = mc.QB * mc.WET_B
    if kw["var"] in ("rain", "wall_rain"):
        # 測る区間の中ほどより上流に降った雨(壁があれば河道のセルの分だけ。壁の向こうの雨は河道へ入らない)
        smid = 0.5 * (mc.S1 + mc.S2)
        catch = chan if kw["var"] == "wall_rain" else (chan | g["bank"])
        area = float((catch & (g["s"] < smid)).sum()) * mc.DX * mc.DX
        q += mc.RAIN / 1000.0 / 3600.0 * area
    beff, h, slope = beff_of(e1, g["z"], g["s"], chan, q)
    bank = g["bank"]
    hb = (e1 - g["z"])[bank]
    drift = float(np.abs(e1 - e0)[chan & (np.arange(g["nx"])[None, :] > 0)].max())
    near = bank & near_channel(chan)
    return dict(rel=beff / mc.WET_B, h=h, slope=slope / mc.S, q=q, hbank=float(hb.mean()),
                hnear=float((e1 - g["z"])[near].mean()), drift=drift)


def near_channel(chan):
    """河道セルに 8 近傍で接するセル"""
    m = np.zeros_like(chan)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            m |= np.roll(np.roll(chan, di, 0), dj, 1)
    return m & ~chan


def results(series):
    out = {}
    for name, kind, kw in mc.cases(series):
        if done(name, kw):
            out[name] = dict(kind=kind, kw=kw, **measure(name, kind, kw))
    return out


def skipped(series):
    """河道マスクが途切れるため作らなかったケース(make_cases.py gen が runs/skipped_<系列>.txt に書く)"""
    p = os.path.join(mc.RUNS, f"skipped_{series}.txt")
    return set(open(p).read().split()) if os.path.exists(p) else set()


def table(series):
    val = results(series)
    missing = [c[0] for c in mc.cases(series) if c[0] not in val and c[0] not in skipped(series)]
    if missing:
        print(T("計算していない: ", "not computed: ") + " ".join(missing))
    for name, v in val.items():
        keys = [k for k in v if k not in ("kind", "kw")]
        print(f"  {name:26s} " + " ".join(f"{k}={v[k]:.4f}" for k in keys))


if __name__ == "__main__":
    for se in sys.argv[1:] or mc.SERIES:
        print(f"== {se}")
        table(se)
