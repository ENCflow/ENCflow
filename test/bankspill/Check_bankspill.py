#!/usr/bin/env python3
"""test/bankspill の検定: 河道の水が、河岸のくぼみ(河道に接する 1 セルだけ低い岸)へあふれ始めるときの振る舞い。

  くぼみ S(まっすぐな区間の脇。流れは河岸に平行)と、くぼみ H(屈曲の外側。上流から来る流れの正面)に
  ついて、あふれ始め(くぼみの水深が水膜より 1 cm 増えた最初の記録)の直前の記録の、隣の河道のセルの水位を
  くぼみの地盤から測る(η − z_p。負 = 水位が地盤より低いうちに入り始めた)。隣の河道のセルは、S では上流側の
  斜め隣(河床勾配の分だけ水位が高い)、H では手前(上流)のセル。

  エッジ水深の頭打ち f_dry_head_cap = 2(構成名の接頭辞なし)・3(接頭辞 c3_)と、4 つの値の組み合わせ(接頭辞 c4_。
  f_advection_donor・f_advection_bend・f_advection_lateral・f_dry_head_cap = 4・2・2・4)の、それぞれ 4 構成(濡れた・
  乾いたくぼみ × 時間刻み 6 s・1.5 s)を見る。2 と 3 の構成の、移流項の残りの 3 つは 3・1・1(明示)。

  どの組でも判定する項目:
    (1) 助走の終わりに、河道が等流(水深がマニングの等流水深)
    (2) S: あふれ始めが、隣の河道のセルの水位がくぼみの地盤に届く時(η − z_p が ±TOL_S)
    (3) S: あふれ始めの水位と時刻が時間刻みによらない
    (4) H: 上流のエネルギー水頭(η + u²/2g)がくぼみの地盤に届く前には入らない
    (5) H: 開いたあと(T_SAME から、流量を下げ始めて 20 分後まで)のくぼみの水深が時間刻みによらない
  3 と 4 つの値の組み合わせでは判定し、2 では記録する項目(2 の限界):
    (6) H: あふれ始めの水位と時刻が時間刻みによらない
    (7) H: あふれ始めの 1 分のくぼみの水深の増加が小さい(下流の流量の 1 分の変化の乱れは、どちらも記録)
    (8) H: 流量を上げて保持している間の、くぼみの水位が、上流のエネルギー水頭を超えない
標準ライブラリだけ。python3 Check_bankspill.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_bankspill import G, B, IS, IJ, T_SPIN, T_RAMP, T_HOLD, bed, H_LO, BASE, CAPS, OTHERS

RISE = 0.01              # あふれ始めの判定: くぼみの水深が水膜より増える量 (m)
TOL_UNI = 0.01           # (1) 助走の終わりの河道の水深の、等流水深からの相対差
TOL_S = 0.15             # (2) S のあふれ始めの水位(地盤から)の許容 (m)
TOL_DT_S = 0.02          # (3) S の水位の時間刻みによる違い (m)
TOL_E = 0.02             # (4) エネルギー水頭の余裕 (m)
T_SAME, TOL_SAME = 140.0, 0.02    # (5) この時刻(分)以降のくぼみ H の水深の、dt による違い (m)
TOL_DT_H = 0.02          # (6) H の水位の時間刻みによる違い (m)。3 で判定
TOL_JUMP = 0.15          # (7) H の 1 分の水深の増加の最大 (m)。3 で判定
TOL_OVER = 0.02          # (8) H のくぼみの水位 − 上流のエネルギー水頭 の最大 (m)。3 で判定


def read(d, kind, n):
    rows = []
    with open("%s/%s/%s%04d.csv" % (d, kind, "probe" if kind == "probes" else "flux", n)) as f:
        for ln in f:
            if not ln.startswith("#"):
                rows.append([float(v) for v in ln.split(",")[:8]])
    return rows


def pocket(d, n_ch, n_p, z_p, i_ch):
    """くぼみ(プローブ n_p)と、隣の河道のセル(プローブ n_ch。列 i_ch)の記録から、あふれ始めを求める"""
    ch = read(d, "probes", n_ch)
    pk = read(d, "probes", n_p)
    t = [r[1] for r in ch]
    lev = [bed(i_ch) + r[3] for r in ch]                   # 河道のセルの水位
    eng = [bed(i_ch) + r[3] + (r[4] ** 2 + r[5] ** 2) / (2 * G) for r in ch]     # エネルギー水頭
    hp = [r[3] for r in pk]
    sel = [h for tt, h in zip(t, hp) if T_SPIN - 20 <= tt <= T_SPIN]
    film = sum(sel) / len(sel)
    out = {"film": film, "t": t, "lev": lev, "eng": eng, "hp": hp, "open": None}
    for k in range(1, len(t)):
        if t[k] > T_SPIN and hp[k] > film + RISE:
            out["open"] = k
            break
    k = out["open"]
    if k is not None:
        out["t_open"] = t[k]
        out["d_open"] = lev[k - 1] - z_p                   # 直前の記録の水位(地盤から)
        out["e_open"] = eng[k - 1] - z_p                   # 直前の記録のエネルギー水頭(地盤から)
        out["jump"] = max(hp[m] - hp[m - 1] for m in range(k, len(t)))
        # 流量を上げて保持している間(下げ始めたあとは、くぼみに残った水が抜けるのが遅れるので見ない)
        t_hi = T_SPIN + T_RAMP + T_HOLD
        over = [(z_p + hp[m]) - eng[m] for m in range(k, len(t)) if hp[m] > film + RISE and t[m] <= t_hi]
        out["over"] = max(over) if over else float("nan")
    return out


def group(pre, cap):
    """f_dry_head_cap = cap の 4 構成(構成名の接頭辞 pre)を検定する。合格なら True"""
    ok = True
    strict = cap >= 3                 # 項目 (6)〜(8) を判定するか
    z_s, z_h = bed(IS) + B, bed(IJ) + B
    names = [pre + n for n in BASE]
    wet6, wet15, dry6, dry15 = names
    res = {}
    print("--- f_dry_head_cap = %d(%s。f_advection_donor・bend・lateral = %d・%d・%d) ---" % ((cap, "・".join(names)) + OTHERS[cap]))
    print("  構成             くぼみ S: 時刻  水位(地盤から)  | くぼみ H: 時刻  水位(地盤から)  エネルギー水頭  1 分の増加  水位 − エネルギー水頭")
    worst_uni = 0.0
    for name in names:
        d = "result_%s" % name
        s = pocket(d, 1, 3, z_s, IS - 1)
        h = pocket(d, 4, 5, z_h, IJ - 1)
        fl = read(d, "fluxes", 1)
        q = [r[2] for r in fl]
        tq = [r[1] for r in fl]
        # 下流の流量の 1 分の変化の乱れ: 2 階差分の最大(助走のあと)
        rough = max(abs(q[m + 1] - 2 * q[m] + q[m - 1]) for m in range(1, len(q) - 1) if tq[m] > T_SPIN + 5)
        ch = read(d, "probes", 2)
        h_spin = [r[3] for r in ch if abs(r[1] - T_SPIN) < 0.5][0]
        worst_uni = max(worst_uni, abs(h_spin / H_LO - 1.0))
        res[name] = (s, h, rough)
        if s["open"] is None or h["open"] is None:
            print("  %-13s  あふれ始めが見つからない" % name)
            ok = False
            continue
        print("  %-13s    %4.0f 分   %+.3f m        |   %4.0f 分   %+.3f m       %+.3f m       %.3f m     %+.3f m"
              % (name, s["t_open"], s["d_open"], h["t_open"], h["d_open"], h["e_open"], h["jump"], h["over"]))
    if not ok:
        return False

    def judge(label, good):
        nonlocal ok
        ok = ok and good
        print("  %s : %s" % (label, "PASS" if good else "FAIL"))

    def note(label, good):
        """3 では判定、2 では記録(判定しない)"""
        if strict:
            judge(label, good)
        else:
            print("  %s : 記録(判定しない。2 の限界)" % label)

    judge("(1) 助走の終わり(%.0f 分)の河道の水深の、等流水深 %.1f m からの相対差の最大 %.1e (< %.0e)" % (T_SPIN, H_LO, worst_uni, TOL_UNI),
          worst_uni < TOL_UNI)
    ds = [res[n][0]["d_open"] for n in names]
    judge("(2) S: あふれ始めの直前の隣の河道の水位(地盤から)%+.3f〜%+.3f m (±%.2f)" % (min(ds), max(ds), TOL_S), max(abs(v) for v in ds) < TOL_S)
    dds = max(abs(res[wet6][0]["d_open"] - res[wet15][0]["d_open"]), abs(res[dry6][0]["d_open"] - res[dry15][0]["d_open"]))
    dts = max(abs(res[wet6][0]["t_open"] - res[wet15][0]["t_open"]), abs(res[dry6][0]["t_open"] - res[dry15][0]["t_open"]))
    judge("(3) S: 時間刻み 6 s と 1.5 s の違い: 水位 %.3f m (< %.2f)、時刻 %.0f 分 (<= 1)" % (dds, TOL_DT_S, dts), dds < TOL_DT_S and dts <= 1.0)
    em = min(res[n][1]["e_open"] for n in names)
    judge("(4) H: あふれ始めの直前の上流のエネルギー水頭(地盤から)の最小 %+.3f m (> −%.2f)" % (em, TOL_E), em > -TOL_E)
    worst_same = 0.0
    for a, b in ((wet6, wet15), (dry6, dry15)):
        ha, hb = res[a][1], res[b][1]
        for m in range(len(ha["t"])):
            if T_SAME <= ha["t"][m] <= T_SPIN + T_RAMP + T_HOLD + 20.0:
                worst_same = max(worst_same, abs(ha["hp"][m] - hb["hp"][m]))
    judge("(5) H: %.0f 分から、流量を下げ始めて 20 分後までのくぼみの水深の、dt 6 s と 1.5 s の違いの最大 %.3f m (< %.2f)" % (T_SAME, worst_same, TOL_SAME),
          worst_same < TOL_SAME)
    ddh = max(abs(res[wet6][1]["d_open"] - res[wet15][1]["d_open"]), abs(res[dry6][1]["d_open"] - res[dry15][1]["d_open"]))
    dth = max(abs(res[wet6][1]["t_open"] - res[wet15][1]["t_open"]), abs(res[dry6][1]["t_open"] - res[dry15][1]["t_open"]))
    note("(6) H: あふれ始めの直前の上流の水位(地盤から)の、時間刻み 6 s と 1.5 s の違い %.3f m (< %.2f)、時刻 %.0f 分 (<= 1)" % (ddh, TOL_DT_H, dth),
         ddh < TOL_DT_H and dth <= 1.0)
    for a, b, lab in ((wet6, wet15, "濡れたくぼみ"), (dry6, dry15, "乾いたくぼみ")):
        print("        %s: dt 6 s %+.3f m(%.0f 分)、dt 1.5 s %+.3f m(%.0f 分)"
              % (lab, res[a][1]["d_open"], res[a][1]["t_open"], res[b][1]["d_open"], res[b][1]["t_open"]))
    jm = max(res[n][1]["jump"] for n in names)
    note("(7) H: あふれ始めの 1 分のくぼみの水深の増加の最大 %s m (< %.2f)" % ("・".join("%.2f" % res[n][1]["jump"] for n in names), TOL_JUMP),
         jm < TOL_JUMP)
    print("        下流の流量の 1 分の変化の乱れ(2 階差分の最大。記録)%s m3/s" % "・".join("%.0f" % res[n][2] for n in names))
    om = max(res[n][1]["over"] for n in names)
    note("(8) H: 開いてから流量を下げ始めるまでの、くぼみの水位 − 上流のエネルギー水頭 の最大 %s m (< %.2f)"
         % ("・".join("%+.2f" % res[n][1]["over"] for n in names), TOL_OVER), om < TOL_OVER)
    return ok


def main():
    print("=== bankspill: 河岸のくぼみへのあふれ始め(くぼみの地盤は河床 + %.1f m) ===" % B)
    ok = True
    for pre, cap in CAPS:
        ok = group(pre, cap) and ok
    print("=== bankspill checks %s ===" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
