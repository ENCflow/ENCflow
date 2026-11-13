#!/usr/bin/env python3
# examples/delta の入力生成: 河川が静水の海盆に突入してデルタを作る理想化地形
#   使い方: python3 make_init.py <case> <kind>   (case = base|sand|mud|varq|fix|wave|baseqb|tide|ens_w1〜w5|ens_c1、
#           kind = z|sd|rows|sw|tide|param)
#   z:    地盤高 (m。海面 0 m 基準)。西側 LCH m は幅 W の河道(河床 ZCH0 から勾配 S0 で下る)、
#         両岸は +ZLAND の乾いた非侵食の陸地。河口から LRAMP m の斜面で海盆底 ZSEA へ、残りは平坦な海盆
#   sd:   土層厚 (m)。河道内 SDCH = 可動、陸地と海盆底は 0 = 非侵食(海盆への堆積は sd を増やす)。
#         固定給砂の構成(FIXEDCH)は河道も 0 = 給砂を運ぶ固い水路(河口に出てから動く)
#   rows: 西端の河道セルの行番号(区間流入の inflow_cell に使う)
#   sw:   海域マスク(1 = 海)。東端 NSEA 列を潮位を与える海の帯にする(段 6 の tide)
#   tide: 潮位の &list_tide(M2 分潮。周期 TM2 分、振幅 ATIDE m の正弦を NCYC 周期分、1 周期 NPC 点の
#         細かさで。潮位は毎ステップ更新する。README「注意」の「潮位の与え方」)
#   param: 実現ごとの違いを見るアンサンブル(ens_*)の設定。param.txt(base)の地盤高・結果の
#         ディレクトリ・計算時間(地形 1200 h)だけを替える。ens_w1〜w5 は海盆(河口より沖)の地盤高に
#         ±ENS_AMP の一様乱数の白色の擾乱、ens_c1 は相関長 ENS_LC の擾乱(白色の擾乱をガウス核で
#         平滑化し、標準偏差を白色の擾乱にそろえる)を足す。乱数の種は実現ごとに固定(README「注意」)
import sys
import numpy as np

CASES = {
    #        NX   NY   DX   LCH   ZSEA
    "base": (200, 120, 5.0, 150.0, -2.0),   # 1000 x 600 m、海盆 2 m(段 1)
    "sand": (240, 320, 5.0, 200.0, -1.5),   # 1200 x 1600 m、海盆 1.5 m(段 2 砂の多いデルタ)
    "mud":  (320, 520, 5.0, 200.0, -1.5),   # 1600 x 2600 m(段 2 泥の多いデルタ。南北 ±1300 m)
    "varq": (240, 320, 5.0, 200.0, -1.5),   # 1200 x 1600 m(段 3 流量変動・定着なし)
    "fix":  (240, 320, 5.0, 200.0, -1.5),   # 1200 x 1600 m(段 3 流量変動+定着+冠水減衰+河岸係数)
    "wave": (200, 120, 5.0, 150.0, -2.0),   # base + 沖波(段 4・5。param_wave.txt・param_wfsed.txt)
    "baseqb": (200, 120, 5.0, 150.0, -2.0), # base の固定給砂版(段 4 の波なしの基準。param_baseqb.txt)
    "tide": (200, 120, 5.0, 150.0, -2.0),   # baseqb + 潮汐(段 6。param_tide.txt・param_notide.txt)
}
ENS = {"ens_w%d" % k: ("white", k) for k in range(1, 6)}
ENS["ens_c1"] = ("corr", 11)                # 擾乱の種類と乱数の種
ENS_AMP, ENS_LC, ENS_TT = 0.02, 50.0, 43200  # 白色の擾乱の幅 ±0.02 m、相関長 50 m、水理 12 h = 地形 1200 h
FIXEDCH = {"wave", "baseqb", "tide"}       # 固定給砂の構成: 陸地内の河道も非侵食(土層 0。給砂はそのまま通過)
NSEA, TM2, ATIDE, NCYC = 3, 745.2, 1.0, 24  # 海の帯の列数、M2 の周期 (min)、振幅 (m) = 潮差 2 m、周期数
#   (段 6・7 は 5 周期。morfac を下げた確かめに 24 周期まで。範囲外は端値を保持するので、表を長くしても
#   短い計算の結果は変わらない)
NPC = 166                                   # 1 周期あたりの tival の点数(4.5 分ごと)
assert NPC * NCYC + 1 <= 9999               # tival の上限 9999 点(developer.md §67.1)
W, LRAMP, S0, ZCH0, ZLAND, SDCH = 30.0, 50.0, 0.001, -1.0, 1.5, 3.0

def perturb(kind, seed, shape, dx):
    """アンサンブルの擾乱 (m)。white: ±ENS_AMP の一様乱数。corr: 白色の擾乱を標準偏差 ENS_LC/2 のガウス核で
    平滑化し(相関が 1/e になる距離が ENS_LC)、標準偏差を白色の擾乱(ENS_AMP/√3)にそろえる。"""
    rng = np.random.default_rng(seed)
    w = rng.uniform(-ENS_AMP, ENS_AMP, shape)
    if kind == "white":
        return w
    ky = np.fft.fftfreq(shape[0], dx)[:, None]
    kx = np.fft.fftfreq(shape[1], dx)[None, :]
    sig = ENS_LC / 2.0
    c = np.real(np.fft.ifft2(np.fft.fft2(w) * np.exp(-2.0 * (np.pi * sig) ** 2 * (kx ** 2 + ky ** 2))))
    return c * (ENS_AMP / np.sqrt(3.0)) / c.std()

def build(case):
    if case in ENS:                          # アンサンブル: base の地形 + 海盆の擾乱
        z, sd, rows = build("base")
        NX, NY, DX, LCH, ZSEA = CASES["base"]
        x = (np.arange(1, NX + 1) - 0.5) * DX
        kind, seed = ENS[case]
        z = z + np.where(x[None, :] > LCH, perturb(kind, seed, z.shape, DX), 0.0)
        return z, sd, rows
    NX, NY, DX, LCH, ZSEA = CASES[case]
    YC = NY * DX / 2.0
    x = (np.arange(1, NX + 1) - 0.5) * DX
    n = (np.arange(1, NY + 1) - 0.5) * DX - YC
    X, N = np.meshgrid(x, n)
    zmouth = ZCH0 - S0 * LCH
    inch = (X <= LCH) & (np.abs(N) <= W / 2)
    z = np.where(X <= LCH, np.where(inch, ZCH0 - S0 * X, ZLAND),
                 np.where(X <= LCH + LRAMP, zmouth + (ZSEA - zmouth) * (X - LCH) / LRAMP, ZSEA))
    sd = np.where(inch, 0.0 if case in FIXEDCH else SDCH, 0.0)
    rows = [int(j) for j in np.arange(1, NY + 1)[inch[:, 0]]]
    return z, sd, rows

if __name__ == "__main__":
    case, kind = sys.argv[1], sys.argv[2]
    z, sd, rows = build(case)
    if kind == "param":
        import re
        txt = open("param.txt", encoding="utf-8").read()
        lab = {"white": "海盆の地盤高に ±%.0f cm の白色の擾乱" % (ENS_AMP * 100),
               "corr": "海盆の地盤高に相関長 %.0f m の擾乱" % ENS_LC}[ENS[case][0]]
        print("! 生成: python3 make_init.py %s param(make ens)。param.txt(base)の地盤高・結果のディレクトリ・\n"
              "!   計算時間だけを替えたアンサンブルの 1 実現(%s、地形 %d h。README「注意」の「形は実現ごとに違う」)"
              % (case, lab, ENS_TT // 36))
        for key, val in (("tt", "%d                ! 水理 %d h(地形 %d h)" % (ENS_TT, ENS_TT // 3600, ENS_TT // 36)),
                         ("dir_result", "'result_%s'" % case),
                         ("fn_z", "'z_%s.txt'          ! 地盤高(make_init.py %s z)" % (case, case))):
            txt, nsub = re.subn(r"^(\s*%s\s*=\s*).*$" % key, lambda m: m.group(1) + val, txt, count=1, flags=re.M)
            assert nsub == 1, key
        sys.stdout.write(txt)
    elif kind == "rows":
        print(" ".join(str(j) for j in rows))
    elif kind == "sw":
        sw = np.zeros(z.shape, dtype=int)
        sw[:, -NSEA:] = 1
        np.savetxt(sys.stdout, sw, fmt="%d")
    elif kind == "tide":
        # 初期水位 0 m(平均潮位)から上げ潮で始める。hsea0 は海盆の水深(2 m)と同じにする。
        #   この海盆の固有周期(4L/√(gh)、奥行き L = 835 m、水深 1〜3 m で 10〜18 分)に比べて、潮位の段差
        #   (既定の 1 分ごとの更新)と線形補間の折れ点の間隔が粗いと固有振動が起きるので、潮位は毎ステップ
        #   (dt_tiupdate = 0.005 分 = 0.3 s ≤ dt)更新し、tival は 1/NPC 周期ごとに与える
        t = np.arange(NPC * NCYC + 1) * TM2 / NPC
        eta = ATIDE * np.sin(2 * np.pi * t / TM2)
        print("&list_tide\n  titype = 2\n  hsea0 = 2.0\n  dt_tiupdate = 0.005")
        for k, (a, b) in enumerate(zip(t, eta), 1):
            print("  tival(1:2,%d) = %.4f, %.4f" % (k, a, b))
        print("/")
    else:
        np.savetxt(sys.stdout, {"z": z, "sd": sd}[kind], fmt="%.4f")
