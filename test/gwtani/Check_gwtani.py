#!/usr/bin/env python3
# gwtani(谷(Tani)型のシナリオ: 急勾配・薄い土層の斜面の地下水)の検定(developer.md §16.7)
#   使い方: Check_gwtani.py uni_thin|uni_thick|thin_toe|thin_toe_k2 [resdir]
#           Check_gwtani.py l2only        (構成 5: 層2だけの側方流)
#           Check_gwtani.py kcompare      (構成 3 と 4 の飽和の時刻を比べる)
#           Check_gwtani.py restart       (構成 R0 の通し計算と R1 → R2 の分割の一致)
#   読むもの: result_<構成>/ の分布出力 Hg*.bil(float32・BIL・リトルエンディアン)・FILENUMBER.csv・
#             Log.txt、data_gwtani/sd_<地形>.txt(make_data.py)、save_rt0/・save_rt/
#
#   斜面: 基盤の勾配 S_b = 0.5、長さ 40 セル × Δ = 5 m(セル i = 1..40 は分水界から数える。
#   下に渓流のセル 41)、sy = 0.2、一定の雨 r = 10 mm/h(浸透能が十分大きく、飽和するまで全量
#   浸透)、側方流 K = K_sh(構成 4 は半分)。地下水の飽和帯厚 h = hg/sy、容量 cap = d·sy。
#   運動学的な斜面の地下水流(Beven 1981)の考え方で、離散式(界面の飽和帯厚は上流側の値で
#   頭打ちの算術平均、水頭差はセル中心間)から次を導く(導出は本検定のもの):
#   (1) 雨の初期(鉛直浸透支配): 地下水の側方の出入りが釣り合うので、分水界から伝わる変化と
#       渓流の影響が届かないセルの地下貯留は hg = r·t で一様に上がる(K・d によらない)。
#       12000 s(飽和の前)にセル 25〜34 で |hg − r t| ≤ 1e-8 m(float32 の丸めの程度)。
#   (2) 飽和の時刻(鉛直浸透支配): そのまま上がり続けて飽和するセルは、鉛直到達時間
#       T_v = d·sy/r に飽和する。定常に達する時刻 t_ss = sy·g·i·Δ/r が T_v の 1.4 倍以上のセル
#       (分水界から伝わる変化より先に満ちる)で、渓流に接する 2 セルを除き |t_sat/T_v − 1| ≤ 3 %。
#       t_sat は飽和の直前の出力から速度 r で延ばした時刻。
#   (3) 定常(側方流支配): 飽和しないセルの流量はそのセルより上流の雨の総量に等しく、
#       K·h_i·(S_b·Δ + h_i − h_{i+1})/Δ·Δ = r·i·Δ² の離散の定常解は h_i = g·i·Δ(直線)、
#       g = (S_b − √(S_b² − 4r/K))/2(運動学的な r/(K S_b) に水面勾配の補正 1 % が乗る)。
#       飽和域の上端より 4 セル以上上流(と渓流から 7 セル以上上流)で |hg/(sy g i Δ) − 1| ≤ 1.5e-3
#       (降った雨の一部が浸透の前に地表流で下流へ運ばれ、地下の流量が一定量だけ減る分を含む。
#       分水界のセルで 1e-3)。飽和するセルは g·i·Δ ≥ d のセル(集水 r·i·Δ が側方の通水能を超える
#       セル)で、セル 1〜39 の飽和の有無が予測と一致すること。飽和の判定は hg ≥ cap − r·dt
#       (飽和域の上端のセルは、出ていく量を毎ステップの雨が補い、容量のすぐ下で揺れる)。
#       セル 40 は渓流へ抜ける浸出面で地下水位が下がるので比べない。
#   (4) uni_thick: 厚い土層はどの時刻も飽和しない(側方流が雨をすべて運ぶ)。
#   l2only: 構成 5(土層の側方流なし、層2の側方流だけ。層2の底は基盤から 3 m 下の同じ勾配の
#       平面、sy2 = 0.2、K2 = 1e-3 m/s)。土層に入った雨は毎ステップすべて層2へ移るので、層2の
#       地下貯留 hg2 に (1)(3) が同じ形で成り立つ: 12000 s にセル 25〜34 で hg2 = r t、定常の
#       飽和帯厚 h2 = hg2/sy2 が g·i·Δ(セル 1〜33)、層2はどのセルも満ちない。斜面は幅 1 セルで
#       斜めのリンクがすべて塞がれるので、振り替え(f_gw_opening の既定 1)が層2に効かなければ
#       軸の通過幅が (1 − d)Δ になり h2 は 2.45 倍になる(d = gw_diagratio の既定)。
#   kcompare: 構成 3 と 4(K を半分)で、両方の (2) の対象のセルの t_sat の差が 1.5 % 以内
#       (飽和の時刻は鉛直浸透で決まる)、定常の飽和域は構成 4 の方が広い(側方流で決まる)。
#   restart: 保存状態のファイル(save_info.txt は保存日時の行を除く)と、共通の時刻の分布出力
#       (9999 = ラン内最大値の統計を除く)がバイト一致し、Log の水量の列が共通の行で全桁一致、
#       Runge・区間統計の列も分割後の最初の行を除いて一致すること。
#   構成は param*.txt・make_data.py と対で保守する。
import filecmp
import math
import os
import struct
import sys

NY, NT, DY = 40, 41, 5.0                # 斜面のセル数・出力の行数(渓流を含む)・格子間隔
SB, SY = 0.5, 0.2                        # 基盤の勾配・比湧水量
R = 10.0 / 1000.0 / 3600.0               # 雨 (m/s)
DT = 2.0                                 # 時間刻み (s)
CASES = {"uni_thin": ("uni_thin", 1e-3), "uni_thick": ("uni_thick", 1e-3),
         "thin_toe": ("thin_toe", 1e-3), "thin_toe_k2": ("thin_toe", 5e-4)}
T_EARLY, CELLS_EARLY, ATOL_EARLY = 12000.0, range(25, 35), 1e-8
TSS_TV, TOL_TSAT, TOL_STEADY, TOL_KCMP = 1.4, 0.03, 1.5e-3, 0.015


def frames(resdir):
    out = []
    with open(os.path.join(resdir, "FILENUMBER.csv")) as f:
        for line in f:
            if line.startswith("#"):
                continue
            c = [v.strip() for v in line.split(",")]
            out.append((int(c[0]), float(c[2])))
    return out


def read_bil(path):
    with open(path, "rb") as f:
        return struct.unpack("<%df" % NT, f.read())


def soil_depth(geom):
    with open(os.path.join("data_gwtani", "sd_%s.txt" % geom)) as f:
        return [float(v) for v in f.read().split()][:NY]


def analyse(case, resdir):
    geom, ksh = CASES[case]
    sd = soil_depth(geom)
    cap = [d * SY for d in sd]
    g = (SB - math.sqrt(SB * SB - 4.0 * R / ksh)) / 2.0
    data = [(t, read_bil(os.path.join(resdir, "Hg%04d.bil" % k))) for k, t in frames(resdir) if 0 < k < 9000]
    sat = lambda a, i: a[i - 1] >= cap[i - 1] - R * DT
    tsat = {}
    for i in range(1, NY + 1):
        prev = None
        for t, a in data:
            if sat(a, i):
                if prev is not None:
                    tsat[i] = min(max(prev[0] + (cap[i - 1] - prev[1]) / R, prev[0]), t)
                break
            prev = (t, a[i - 1])
    return sd, cap, g, data, sat, tsat


def vertical_cells(sd, g, pred):
    """(2) の対象: 予測で飽和し、t_ss ≥ 1.4 T_v、渓流に接する 2 セル(39・40)を除く。"""
    return [i for i in pred if i <= NY - 2 and (g * i * DY) / sd[i - 1] >= TSS_TV]


def main_case(case, resdir):
    resdir = resdir or "result_" + case
    sd, cap, g, data, sat, tsat = analyse(case, resdir)
    nfail = 0

    def check(ok, msg):
        nonlocal nfail
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            nfail += 1

    pred = [i for i in range(1, NY) if g * i * DY >= sd[i - 1]]      # セル 1〜39
    print("== gwtani %s: d = %.3f..%.3f m, K = %.1e m/s, g = %.7f (r/(K S_b) = %.7f), predicted saturated %s"
          % (case, sd[0], sd[-1], CASES[case][1], g, R / (CASES[case][1] * SB),
             ("cells %d-%d" % (pred[0], pred[-1])) if pred else "none"))
    # (1) 雨の初期の一様な上昇
    a = [v for t, v in data if abs(t - T_EARLY) < 1e-6][0]
    dev = max(abs(a[i - 1] - R * T_EARLY) for i in CELLS_EARLY)
    check(dev <= ATOL_EARLY, "t = %.0f s: hg = r t = %.8f m uniformly in cells %d-%d (max |dev| %.1e m): vertical infiltration dominates"
          % (T_EARLY, R * T_EARLY, CELLS_EARLY[0], CELLS_EARLY[-1], dev))
    # (2) 飽和の時刻 = 鉛直到達時間
    vc = vertical_cells(sd, g, pred)
    if vc:
        rel = [(i, tsat[i] / (cap[i - 1] / R) - 1.0) for i in vc if i in tsat]
        miss = [i for i in vc if i not in tsat]
        worst = max(rel, key=lambda x: abs(x[1])) if rel else (0, 0.0)
        check(not miss and abs(worst[1]) <= TOL_TSAT,
              "cells %d-%d saturate at T_v = d sy / r (%.0f..%.0f s) within %.0f %% (worst cell %d: %+.2f %%)%s"
              % (vc[0], vc[-1], cap[vc[-1] - 1] / R, cap[vc[0] - 1] / R, TOL_TSAT * 100, worst[0], worst[1] * 100,
                 (", not saturated: %s" % miss) if miss else ""))
    # (3) 定常
    t_end, a = data[-1]
    i_hi = min((pred[0] - 4) if pred else NY, NY - 7)
    devs = [(i, a[i - 1] / (SY * g * i * DY) - 1.0) for i in range(1, i_hi + 1)]
    worst = max(devs, key=lambda x: abs(x[1]))
    check(abs(worst[1]) <= TOL_STEADY,
          "t = %.0f s: unsaturated cells 1-%d follow the steady profile h = g i dx (worst cell %d: %+.1e): lateral flow dominates"
          % (t_end, i_hi, worst[0], worst[1]))
    model = [i for i in range(1, NY) if sat(a, i)]
    check(model == pred, "saturated cells at t = %.0f s: %s (predicted %s; cell 40 next to the stream excluded)"
          % (t_end, ("%d-%d" % (model[0], model[-1])) if model else "none", ("%d-%d" % (pred[0], pred[-1])) if pred else "none"))
    if case == "uni_thick":
        ever = sorted({i for t, v in data for i in range(1, NY) if sat(v, i)})
        check(not ever, "the thick soil never saturates in cells 1-39 (lateral flow carries all the rain)%s"
              % ((": saturated %s" % ever) if ever else ""))
    return nfail


def main_l2only(resdir):
    resdir = resdir or "result_l2only"
    sy2, k2, d2, diag = 0.2, 1e-3, 3.0, 2.0 / (2.0 + math.sqrt(2.0))
    g = (SB - math.sqrt(SB * SB - 4.0 * R / k2)) / 2.0
    g_none = (SB - math.sqrt(SB * SB - 4.0 * R / (k2 * (1.0 - diag)))) / 2.0
    data = [(t, read_bil(os.path.join(resdir, "Hg2%04d.bil" % k))) for k, t in frames(resdir) if 0 < k < 9000]
    nfail = 0

    def check(ok, msg):
        nonlocal nfail
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            nfail += 1

    print("== gwtani l2only: lateral flow in layer 2 only (f_gwlateral = 0), K2 = %.1e m/s, g = %.7f "
          "(without the transfer the axis width is (1 - d) dx and g = %.7f)" % (k2, g, g_none))
    a = [v for t, v in data if abs(t - T_EARLY) < 1e-6][0]
    dev = max(abs(a[i - 1] - R * T_EARLY) for i in CELLS_EARLY)
    check(dev <= ATOL_EARLY, "t = %.0f s: hg2 = r t = %.8f m uniformly in cells %d-%d (max |dev| %.1e m)"
          % (T_EARLY, R * T_EARLY, CELLS_EARLY[0], CELLS_EARLY[-1], dev))
    t_end, a = data[-1]
    devs = [(i, a[i - 1] / (sy2 * g * i * DY) - 1.0) for i in range(1, NY - 6)]
    worst = max(devs, key=lambda x: abs(x[1]))
    check(abs(worst[1]) <= TOL_STEADY,
          "t = %.0f s: layer-2 saturated thickness in cells 1-%d follows h2 = g i dx with the full axis width "
          "(worst cell %d: %+.1e; the transfer of blocked diagonal shares applies to layer 2)"
          % (t_end, NY - 7, worst[0], worst[1]))
    full = [i for t, v in data for i in range(1, NY) if v[i - 1] >= d2 * sy2 - R * DT]
    check(not full, "layer 2 never fills in cells 1-39%s" % ((": full %s" % sorted(set(full))) if full else ""))
    return nfail


def main_kcompare():
    print("== gwtani kcompare: thin_toe vs thin_toe_k2 (K halved)")
    r3, r4 = analyse("thin_toe", "result_thin_toe"), analyse("thin_toe_k2", "result_thin_toe_k2")
    pred3 = [i for i in range(1, NY) if r3[2] * i * DY >= r3[0][i - 1]]
    pred4 = [i for i in range(1, NY) if r4[2] * i * DY >= r4[0][i - 1]]
    cells = [i for i in vertical_cells(r3[0], r3[2], pred3) if i in vertical_cells(r4[0], r4[2], pred4)]
    rel = [(i, r4[5][i] / r3[5][i] - 1.0) for i in cells]
    worst = max(rel, key=lambda x: abs(x[1]))
    nfail = 0
    ok = abs(worst[1]) <= TOL_KCMP
    print(("  ok   " if ok else "  FAIL ") + "cells %d-%d saturate at the same time with K halved (worst cell %d: %+.2f %%): timing set by vertical infiltration"
          % (cells[0], cells[-1], worst[0], worst[1] * 100))
    nfail += 0 if ok else 1
    s3 = [i for i in range(1, NY) if r3[4](r3[3][-1][1], i)]
    s4 = [i for i in range(1, NY) if r4[4](r4[3][-1][1], i)]
    ok = len(s4) > len(s3) and set(s3) <= set(s4)
    print(("  ok   " if ok else "  FAIL ") + "steady saturated area grows from %d to %d cells with K halved: extent set by lateral flow" % (len(s3), len(s4)))
    nfail += 0 if ok else 1
    return nfail


def log_rows(path):
    out = {}
    with open(path) as f:
        f.readline()
        for line in f:
            c = line.split()
            out[c[0]] = c
    return out


def main_restart():
    print("== gwtani restart: straight run R0 (0-60000 s) vs R1 (0-30006 s, save) -> R2 (restore, -60000 s)")
    nfail = 0

    def check(ok, msg):
        nonlocal nfail
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            nfail += 1

    names = sorted(os.listdir("save_rt0"))
    bad = []
    for n in names:
        p, q = os.path.join("save_rt0", n), os.path.join("save_rt", n)
        if n == "save_info.txt":
            same = os.path.exists(q) and [l for l in open(p) if not l.startswith("! ENCflow restart save")] == \
                [l for l in open(q) if not l.startswith("! ENCflow restart save")]
        else:
            same = os.path.exists(q) and filecmp.cmp(p, q, shallow=False)
        if not same:
            bad.append(n)
    check(not bad and sorted(os.listdir("save_rt")) == names,
          "saved state identical (%s)%s" % (", ".join(names), (": differ " + ", ".join(bad)) if bad else ""))
    f0 = {t: k for k, t in frames("result_rt0") if k < 9000}
    nsame, bad = 0, []
    for k2, t in frames("result_rt2"):
        if k2 == 9999 or (k2 < 9000 and t not in f0):
            continue
        k0 = 9998 if k2 == 9998 else f0[t]
        for v in sorted({fn[:-8] for fn in os.listdir("result_rt2") if fn.endswith("%04d.bil" % k2)}):
            p, q = os.path.join("result_rt0", "%s%04d.bil" % (v, k0)), os.path.join("result_rt2", "%s%04d.bil" % (v, k2))
            if os.path.exists(p) and filecmp.cmp(p, q, shallow=False):
                nsame += 1
            else:
                bad.append(os.path.basename(q))
    check(not bad and nsame > 0, "%d output files at common times identical (Hg, Hg2, H, C, Cg, ...)%s"
          % (nsame, (": differ " + ", ".join(bad)) if bad else ""))
    l0, l2 = log_rows("result_rt0/Log.txt"), log_rows("result_rt2/Log.txt")
    common = [t for t in l2 if t in l0]
    bad_s = [t for t in common if l0[t][2:5] != l2[t][2:5]]
    bad_o = [t for t in common[1:] if l0[t][:5] + l0[t][6:] != l2[t][:5] + l2[t][6:]]
    check(not bad_s and not bad_o and len(common) > 2,
          "Log rows after the split agree (%d rows; storage columns in all, other columns except Runge from the second row)%s"
          % (len(common), (": differ " + ", ".join(bad_s + bad_o)) if (bad_s or bad_o) else ""))
    return nfail


def main(argv):
    if len(argv) < 2:
        print("usage: %s uni_thin|uni_thick|thin_toe|thin_toe_k2|l2only|kcompare|restart [resdir]" % os.path.basename(argv[0]), file=sys.stderr)
        return 2
    case = argv[1]
    if case in CASES:
        nfail = main_case(case, argv[2] if len(argv) > 2 else None)
    elif case == "l2only":
        nfail = main_l2only(argv[2] if len(argv) > 2 else None)
    elif case == "kcompare":
        nfail = main_kcompare()
    elif case == "restart":
        nfail = main_restart()
    else:
        print("unknown case: %s" % case, file=sys.stderr)
        return 2
    print("Check_gwtani %s: %s" % (case, "PASS" if nfail == 0 else "FAIL (%d)" % nfail))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
