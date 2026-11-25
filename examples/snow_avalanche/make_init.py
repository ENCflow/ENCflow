#!/usr/bin/env python3
"""examples/snow_avalanche の入力と設定ファイルの生成(make が呼ぶ)。

  python3 make_init.py            CASES のすべてのケースの入力(data_<...>/)と設定(param_<case>.txt)を書く
  python3 make_init.py base dam   名前を挙げたケースだけ書く

地形・積雪・発生区は、沢に沿う座標の解析式で与える。s は沢筋を下る向きの水平距離(上端 0)、n は沢を
横切る向き(沢筋 0。下流を向いて左が正)。格子に対する沢の向き θ と格子間隔 Δx を変えても、同じ式を
各格子のセル中心で標本化するので、補間の誤差は入らない(違いは格子の離散化だけ)。s・n の長方形の外は領域外。

  地形   沢筋の縦断は、勾配が上端の S_TOP から直線的に緩む放物線(長さ L_P)と、その先の勾配 S_END の谷底。
         横断は、上部が浅い放物面のボウル(発生区)、中部が丸い底の V 字の沢(走路)、沢の出口(扇頂 S_A)
         から先が、出口の幅の線分を頂点とする円錐状の扇状地(堆積区)。山体は出口の線から 35° の山麓の崖で終わる。
  積雪   標高 z は雪面で、z − sd が、雪崩に連行されない面(地山と古い積雪)。連行できる雪の厚さ sd は、
         発生区では破断深、走路では沢底に沿う帯(沢筋で厚さ最大、横断は放物線で半幅 W_E の縁が 0)。
         補足の「全面の雪」のケースだけ、扇頂より上の全面に一様な厚さを置く。
  発生区 ボウルの上部の、角の丸い長方形(超楕円)。破断深は一様で、体積が V_REL になるように格子ごとに
         規格化する(粗い格子でも同じ雪の量)。
  誘導堤 扇状地の上に、沢の出口の右岸の山麓から斜めに伸びる土堤(地形として与える。堤体は連行されない)。
  家屋   誘導堤が守る範囲に並ぶ家屋の位置(houses.txt。計算には使わず、図化で流動深と速さを読む)。

出力(data_<...>/。入力ファイルは先頭行が北端):
  z.txt        雪面の標高 (m)
  sd.txt       連行できる雪の厚さ (m)
  dbinit.txt   破断深 (m)(fn_dbinit)
  mask.txt     領域マスク(1: 計算する)
  size.txt     nx ny ox oy dx theta(図化で沢沿いの座標へ戻すための格子の原点と向き)
houses.txt     家屋の位置 s n (m)(ケースによらない)
"""
import math
import os
import sys
import numpy as np

# ---------------------------------------------------------------- 地形(沢沿いの座標、m)
L_S = 1800.0             # 領域の長さ(上端 s = 0 から下流端まで)
W = 640.0                # 領域の幅(n = −W/2 〜 W/2)
S_TOP, S_END = 0.78, 0.05  # 沢筋の勾配: 上端(38°)と谷底(3°)
L_P = 1400.0             # 勾配が S_TOP から S_END へ直線的に緩む区間の長さ(放物線)
Z_END = 5.0              # 下流端(沢筋)の標高
R_B, W_B = 30.0, 150.0   # ボウル: 縁の比高、半幅(横断は放物線)
T_G, A_G = 0.6, 15.0     # 沢: 谷壁の勾配(31°)、底の丸みの長さ
R_G, R_G2 = 35.0, 15.0   # 沢の縁の比高(上流・出口)
L_T = 250.0              # 沢の縁を、出口の L_T 手前から R_G2 へ下げる
S_B0, S_B1 = 220.0, 420.0  # ボウルから沢へ横断形を切り替える区間
S_A = 950.0              # 沢の出口(扇頂)
N_A = 20.0               # 扇頂の半幅(扇状地の円錐の頂点を、出口の幅の線分にする)
TAN_FRONT = 0.7          # 山麓の崖の勾配(35°)
# ---------------------------------------------------------------- 発生区と積雪
S_C, A_S, A_N = 150.0, 70.0, 65.0   # 発生区の中心 s、半長(沢沿い)、半幅
V_REL = 17000.0          # 発生する雪の体積 (m³。破断深の体積。破断深は約 1 m)
SNOW_TRACK = 1.0         # 基本ケースの、走路の雪の帯の沢筋での厚さ (m)
S_E0, W_E = 300.0, 20.0  # 走路の雪の帯: 始まり(発生区の下)、半幅(横断は放物線で縁が 0)
LAMBDA = 0.1             # キャリアの割合(param の fluv_porosity と対)
# ---------------------------------------------------------------- 誘導堤(沢沿いの座標、m)
DAM_A = (S_A, -50.0)     # 起点(沢の出口の右岸の山麓。上流側ののり尻が出口の右岸の縁に来る)
DAM_B = (S_A + 300.0, 75.0)  # 終点
DAM_H = (18.0, 10.0)     # 堤高(その場の地表から。起点・終点。間は直線的に変える)
DAM_CREST, DAM_SLOPE = 5.0, 1.5   # 天端の幅、のり勾配(1 : 1.5)
# ---------------------------------------------------------------- 家屋(計算には使わない)
HOUSE_S, HOUSE_N, HOUSE_D = (1100.0, 1310.0), (-110.0, -20.0), 30.0

DT_PER_DX = 0.005        # 時間刻み dt = 0.005 Δx(s。Δx = 5 m で 0.025 s。クーラン数が格子によらずそろう)


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def drop(xi):
    """沢筋を上端から ξ 下ったときの落差。"""
    xi = np.asarray(xi, dtype=float)
    k = (S_TOP - S_END) / L_P
    xm = np.minimum(xi, L_P)
    return S_TOP * xm - 0.5 * k * xm ** 2 + S_END * np.clip(xi - L_P, 0.0, None)


def slope_axis(xi):
    """沢筋の勾配(扇状地では扇頂からの距離で読む)。"""
    return np.maximum(S_TOP - (S_TOP - S_END) * np.asarray(xi, dtype=float) / L_P, S_END)


def z_axis(xi):
    return Z_END + float(drop(L_S)) - drop(xi)


def wall(s, n):
    """沢筋からの比高(ボウルの放物面から、沢の V 字へ)。"""
    bowl = R_B * np.minimum((n / W_B) ** 2, 1.0)
    rim = R_G + (R_G2 - R_G) * smooth((s - (S_A - L_T)) / L_T)
    gully = np.minimum(T_G * (np.sqrt(n ** 2 + A_G ** 2) - A_G), rim)
    w = smooth((s - S_B0) / (S_B1 - S_B0))
    return (1.0 - w) * bowl + w * gully


def ground(s, n):
    """連行されない面の標高(誘導堤なし)。山体(ボウルと沢)と扇状地(円錐)の高い方。"""
    sa = float(slope_axis(S_A))
    ds = np.clip(s - S_A, 0.0, None)
    zv = z_axis(np.minimum(s, S_A)) - sa * ds
    z_mtn = zv + wall(np.minimum(s, S_A), n) - TAN_FRONT * ds
    r = np.hypot(ds, np.clip(np.abs(n) - N_A, 0.0, None))
    z_fan = np.where(s > S_A, z_axis(S_A + r), -1.0e9)
    return np.maximum(z_mtn, z_fan)


def dam_height(s, n):
    """誘導堤の高さ(地表からの盛土の厚さ)。中心線からの距離で決まる台形断面で、堤高は起点から終点へ直線的に変える。"""
    (s1, n1), (s2, n2) = DAM_A, DAM_B
    ax, ay = s2 - s1, n2 - n1
    t = np.clip(((s - s1) * ax + (n - n1) * ay) / (ax * ax + ay * ay), 0.0, 1.0)
    d = np.hypot(s - (s1 + t * ax), n - (n1 + t * ay))
    h = DAM_H[0] + (DAM_H[1] - DAM_H[0]) * t
    return np.clip((DAM_CREST / 2 + DAM_SLOPE * h - d) / DAM_SLOPE, 0.0, h)


def release_shape(s, n):
    """発生区(超楕円の内側が 1)。"""
    return (((s - S_C) / A_S) ** 4 + (n / A_N) ** 4 < 1.0).astype(float)


def track_snow(s, n, thick):
    """走路の雪の帯(沢底にたまった連行できる雪)。沢筋で厚さ thick、横断は放物線で半幅 W_E の縁が 0。"""
    return np.where((s >= S_E0) & (s <= S_A), thick * np.clip(1.0 - (n / W_E) ** 2, 0.0, None), 0.0)


def houses():
    """家屋の位置 (s, n)。HOUSE_D 間隔の格子状。"""
    out = [(s, n) for s in np.arange(HOUSE_S[0], HOUSE_S[1] + 1e-9, HOUSE_D)
           for n in np.arange(HOUSE_N[0], HOUSE_N[1] + 1e-9, HOUSE_D)]
    return np.array(out)


# ---------------------------------------------------------------- ケース
def case(dx=5.0, theta=0.0, track=SNOW_TRACK, dam=False, allsnow=False, **rep):
    """dx 格子間隔、theta 格子に対する沢の向き、track 走路の雪の厚さ(帯の沢筋での値。allsnow では一様な厚さ)、
    dam 誘導堤、allsnow 扇頂より上の全面に雪、rep 設定ファイルの差し替え(名前 = 値)。"""
    return dict(dx=dx, theta=theta, track=track, dam=dam, allsnow=allsnow, rep=rep)


CASES = {
    # 走路の雪の量と誘導堤(本文)
    "base": case(),                                   # param.txt そのもの
    "nosnow": case(track=0.0),
    "deep": case(track=2.0),
    "dam": case(dam=True),
    "deep_dam": case(track=2.0, dam=True),
    # 摩擦係数(RAMMS の表のほかの行)
    "mu155": case(db_mu="0.155", db_xi="3000.0"),
    "mu340": case(db_mu="0.34", db_xi="1350.0"),
    # 格子間隔・沢の向き・時間刻み
    "dx10": case(dx=10.0),
    "dx2p5": case(dx=2.5),
    "r22p5": case(theta=22.5),
    "r45": case(theta=45.0),
    "dt2": case(dt="0.05"),
    "dthalf": case(dt="0.0125"),
    # 塞がれた開口の動的振り替え(param.txt は使わない = 0。既定は 3)と沢の向き。雪を取り込まない流れの頭で差が出る
    "nosnow_r45": case(track=0.0, theta=45.0),
    "open3": case(f_opening_dynamic="3"),
    "open3_r45": case(theta=45.0, f_opening_dynamic="3"),
    "nosnow_open3": case(track=0.0, f_opening_dynamic="3"),
    "nosnow_open3_r45": case(track=0.0, theta=45.0, f_opening_dynamic="3"),
    # 連行の与え方と限界: 限界水深、全面の雪
    "dd3": case(dd="0.001"),
    "dd3_dthalf": case(dd="0.001", dt="0.0125"),
    "dd5": case(dd="0.00001"),
    "allsnow": case(track=0.5, allsnow=True),
    "allsnow_dd3": case(track=0.5, allsnow=True, dd="0.001"),
    "allsnow_dd5": case(track=0.5, allsnow=True, dd="0.00001"),
    # 連行した雪の運動量を数えない(f_dbmom = 0)
    "nomom": case(f_dbmom="0"),
    "deep_nomom": case(track=2.0, f_dbmom="0"),
    # Hungr の連行則(f_dbed = 5)と、連行する流動深の下限(db_hent)
    "hungr": case(f_dbed="5", db_er="0.01"),
    "allsnow_h": case(track=0.5, allsnow=True, f_dbed="5", db_er="0.01"),
    "allsnow_h_dd3": case(track=0.5, allsnow=True, f_dbed="5", db_er="0.01", dd="0.001"),
    "allsnow_h_dd5": case(track=0.5, allsnow=True, f_dbed="5", db_er="0.01", dd="0.00001"),
    "allsnow_t": case(track=0.5, allsnow=True, db_hent="0.3"),
    "allsnow_t_dd3": case(track=0.5, allsnow=True, db_hent="0.3", dd="0.001"),
    "allsnow_t_dd5": case(track=0.5, allsnow=True, db_hent="0.3", dd="0.00001"),
}
BASE = "base"
MAIN = ("nosnow", "base", "deep", "dam", "deep_dam")


def data_name(c):
    s = f"dx{c['dx']:g}_r{c['theta']:g}_t{c['track']:g}".replace(".", "p")
    return "data_" + s + ("_all" if c["allsnow"] else "") + ("_dam" if c["dam"] else "")


# ---------------------------------------------------------------- 格子
def frame(dx, theta):
    """格子の大きさと、沢沿いの座標 ↔ 格子座標の変換の原点(外枠の長方形の外側に 1 セルの余白)。"""
    th = math.radians(theta)
    c, sn = math.cos(th), math.sin(th)
    corners = [(s, n) for s in (0.0, L_S) for n in (-W / 2, W / 2)]
    xs = [s * c + n * sn for s, n in corners]
    ys = [-s * sn + n * c for s, n in corners]
    ox, oy = dx - min(xs), dx - min(ys)
    nx = int(math.ceil((max(xs) - min(xs)) / dx - 1e-9)) + 2
    ny = int(math.ceil((max(ys) - min(ys)) / dx - 1e-9)) + 2
    return nx, ny, ox, oy, c, sn


def to_sn(dx, theta):
    """各セル中心の沢沿いの座標 (s, n)。配列の行 0 が南端。"""
    nx, ny, ox, oy, c, sn = frame(dx, theta)
    x = (np.arange(nx) + 0.5) * dx - ox
    y = (np.arange(ny) + 0.5) * dx - oy
    X, Y = np.meshgrid(x, y)
    return X * c - Y * sn, X * sn + Y * c


def grid(c):
    dx = c["dx"]
    nx, ny, ox, oy, _, _ = frame(dx, c["theta"])
    s, n = to_sn(dx, c["theta"])
    inside = (s >= 0.0) & (s < L_S) & (n >= -W / 2) & (n < W / 2)
    zb = ground(s, n)
    shape = np.where(inside, release_shape(s, n), 0.0)
    d = shape * V_REL / (shape.sum() * dx * dx)          # 体積を V_REL に規格化
    if c["allsnow"]:
        snow = np.where(s <= S_A, c["track"], 0.0)
    else:
        snow = track_snow(s, n, c["track"])
    if c["dam"]:
        dam = dam_height(s, n)
        zb = zb + dam
        snow = np.where(dam > 0.0, 0.0, snow)            # 堤体は連行されない
    sd = np.where(inside, np.maximum(d, snow), 0.0)
    z = np.where(inside, zb + sd, 0.0)
    out = {"z": z, "sd": sd, "dbinit": d, "mask": inside.astype(int)}
    return nx, ny, ox, oy, out


def write_data(c, done):
    """入力を書く。同じ入力を使うケース(摩擦係数・時間刻み・限界水深だけが違う)は 1 回だけ書く。"""
    ddir = data_name(c)
    if ddir in done:
        return ddir, None
    done.add(ddir)
    nx, ny, ox, oy, out = grid(c)
    os.makedirs(ddir, exist_ok=True)
    for k, g in out.items():
        np.savetxt(os.path.join(ddir, k + ".txt"), g[::-1], fmt="%d" if k == "mask" else "%.4f")   # 先頭行が北端
    with open(os.path.join(ddir, "size.txt"), "w") as f:
        f.write(f"{nx} {ny} {ox:.6f} {oy:.6f} {c['dx']:g} {c['theta']:g}\n")
    return ddir, out


def write_param(name, c, ddir):
    """param.txt(基本ケースの注釈付きの雛形)の格子・時間刻み・入出力・差し替えの行を書き換えて書く。
    雛形そのもののケース(BASE)は param.txt を使うので書かない。"""
    if name == BASE:
        return
    dx = c["dx"]
    nx, ny = frame(dx, c["theta"])[:2]
    rep = {"dt": f"{DT_PER_DX * dx:g}", "lx": f"{nx * dx:.1f}", "ly": f"{ny * dx:.1f}",
           "nx": f"{nx}", "ny": f"{ny}", "dir_data": f"'{ddir}'", "dir_result": f"'result_{name}'"}
    rep.update(c["rep"])
    lines = open("param.txt").read().splitlines()
    out = [f"! このファイルは make_init.py が param.txt から生成する(ケース {name})。編集は param.txt と make_init.py で"]
    done = set()
    for line in lines:
        key = line.split("=")[0].strip() if "=" in line and not line.lstrip().startswith("!") else None
        if key in rep:
            head, _, tail = line.partition("=")
            val_comment = tail.split("!", 1)
            comment = "!" + val_comment[1] if len(val_comment) > 1 else ""
            line = f"{head}= {rep[key]}"
            if comment:
                line = f"{line:<28}{comment}"
            done.add(key)
        out.append(line)
    missing = set(rep) - done
    if missing:
        sys.exit(f"param.txt に {sorted(missing)} の行がありません")
    with open(f"param_{name}.txt", "w") as f:
        f.write("\n".join(out) + "\n")


def main():
    names = sys.argv[1:] or list(CASES)
    done = set()
    for name in names:
        c = CASES[name]
        ddir, out = write_data(c, done)
        write_param(name, c, ddir)
        if out is not None:
            a = c["dx"] ** 2
            print(f"{ddir}: cells = {int(out['mask'].sum())}, D = {out['dbinit'].max():.3f} m, "
                  f"V = {out['dbinit'].sum() * a:.0f} m3, "
                  f"snow = {np.where(out['dbinit'] > 0, 0.0, out['sd']).sum() * a:.0f} m3")
    np.savetxt("houses.txt", houses(), fmt="%.1f", header="s n (m)  家屋の位置(沢沿いの座標)")


if __name__ == "__main__":
    main()
