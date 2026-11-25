#!/usr/bin/env python3
# vchannel: 入力(data_<向き>/)と、構成ごとの設定 p_<構成>_<向き>.txt の生成
#   make_init.py          全部を書く(Run.sh が呼ぶ)
#
# 一様な勾配 S の斜面に、壁の勾配 WALL の V 字の水路(底は丸める)を置き、長さ LS の区間に、表面が横断方向に水平に
# なる厚さの雪(または水)を置く。流れの向き(沢筋)だけを、格子に対して THETAS の角度に回す。
#   沢筋に沿う座標 s(下流が正)、横断方向の座標 n:  s = x cosθ + y sinθ、 n = −x sinθ + y cosθ
#   (x は東、y は北。原点は領域の中心)
#   基盤の高さ   zb = Z0 − S s + zc(n)、 zc(n) = WALL (sqrt(n² + A²) − A)
#   初期の厚さ   d0 = max(D − zc(n), 0)(S0 <= s <= S0 + LS。ほかは 0)
# 値と式は Check_vchannel.py が import して使う(対で保守する)
import math
import os
import re
import sys

LDOM, DX = 1400.0, 5.0                 # 領域の 1 辺 (m)、格子間隔 (m)
N = int(round(LDOM / DX))
S, WALL, A, D = 0.4, 0.6, 21.0, 5.0    # 縦断の勾配、壁の勾配、底の丸みの長さ (m)、谷底の初期の厚さ (m)
S0, LS, Z0 = -600.0, 600.0, 1000.0     # 区間の上流端の s (m)、長さ (m)、原点の基盤の高さ (m)
MU, XI, RN, GG = 0.25, 1750.0, 0.1, 9.8
TEND = 20.0
THETAS = (("r0", 0.0), ("r22p5", 22.5), ("r45", 45.0))

# 構成: 名前 → (ひな形、差し替えるキー、向き)。キーは (グループ, 名前, 値)
CONFIGS = {
    # Voellmy 則・既定の数値設定
    "vo": ("param_voellmy.txt", [], ("r0", "r22p5", "r45")),
    # Voellmy 則・塞がれた開口の動的振り替えなし(格子で解像された谷の土砂流動に勧める設定)
    "vo0": ("param_voellmy.txt", [("list_enc", "f_opening_dynamic", "0")], ("r0", "r22p5", "r45")),
    # Voellmy 則・4 近傍(格子に沿う向きだけ。横断方向の結合がなく、厳密解に合う。検定の組み方の確認)
    "vo4": ("param_voellmy.txt", [("list_enc", "p_diagratio", "0.0")], ("r0",)),
    # 摩擦なし(最初の 1 秒の加速度が g S になること)
    "fr": ("param_voellmy.txt", [("list_geomorph", "db_mu", "1.0e-4"), ("list_geomorph", "db_xi", "1.0e9"),
                                 ("list_sysparam", "tt", "1"), ("list_sysparam", "dt_disp", "1"),
                                 ("list_sysparam", "dt_file", "1"), ("list_sysparam", "dt_recrd", "1")],
           ("r0", "r22p5", "r45")),
    # 水(マニング則)・既定の数値設定
    "w": ("param_water.txt", [], ("r0", "r22p5", "r45")),
    # 水・4 近傍(格子に沿う向きだけ)
    "w4": ("param_water.txt", [("list_enc", "p_diagratio", "0.0")], ("r0",)),
}


def zc(n):
    return WALL * (math.sqrt(n * n + A * A) - A)


def sn(i, j, theta):
    """セル (i, j)(0 始まり。i は東向き、j は北向き)の中心の (s, n)。"""
    x = (i + 0.5) * DX - LDOM / 2
    y = (j + 0.5) * DX - LDOM / 2
    c, si = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    return x * c + y * si, -x * si + y * c


def depth0(s, n):
    if s < S0 or s > S0 + LS:
        return 0.0
    return max(D - zc(n), 0.0)


def write_data(name, theta):
    os.makedirs(f"data_{name}", exist_ok=True)
    rows = {"z_bed": [], "z_snow": [], "d0": []}
    for j in range(N - 1, -1, -1):          # ファイルの先頭の行が北端
        zb, zs, d0 = [], [], []
        for i in range(N):
            s, n = sn(i, j, theta)
            b = Z0 - S * s + zc(n)
            d = depth0(s, n)
            zb.append("%.4f" % b)
            zs.append("%.4f" % (b + d))
            d0.append("%.4f" % d)
        rows["z_bed"].append(" ".join(zb))
        rows["z_snow"].append(" ".join(zs))
        rows["d0"].append(" ".join(d0))
    # z_snow: 雪面(基盤 + 雪。土砂流動の構成)。z_bed: 基盤(水の構成)。sd・dbinit・hinit は初期の厚さ
    for fn, key in (("z_bed.txt", "z_bed"), ("z_snow.txt", "z_snow"), ("sd.txt", "d0"),
                    ("dbinit.txt", "d0"), ("hinit.txt", "d0")):
        with open(f"data_{name}/{fn}", "w") as f:
            f.write("\n".join(rows[key]) + "\n")


def setkey(text, group, key, val):
    """namelist のグループの中の key を置き換える。なければグループの先頭に足す。"""
    m = re.search(rf"(&{group}\b.*?\n)(.*?)(\n/)", text, flags=re.S)
    assert m, group
    body = m.group(2)
    pat = re.compile(rf"^(\s*){key}\s*=\s*[^!\n]*", flags=re.M)
    if pat.search(body):
        body = pat.sub(lambda mm: f"{mm.group(1)}{key} = {val} ", body, count=1)
    else:
        body = f"  {key} = {val}\n" + body
    return text[:m.start(2)] + body + text[m.end(2):]


def write_params(sdir):
    for cfg, (tmpl, mods, oris) in CONFIGS.items():
        base = open(os.path.join(sdir, tmpl), encoding="utf-8").read()
        for name in oris:
            t = base
            for g, k, v in [("list_sysparam", "dir_data", f"'data_{name}'"),
                            ("list_sysparam", "dir_result", f"'result_{cfg}_{name}'")] + mods:
                t = setkey(t, g, k, v)
            with open(f"p_{cfg}_{name}.txt", "w", encoding="utf-8") as f:
                f.write(t)


if __name__ == "__main__":
    for name, theta in THETAS:
        write_data(name, theta)
    write_params(os.path.dirname(os.path.abspath(__file__)))
    sys.exit(0)
