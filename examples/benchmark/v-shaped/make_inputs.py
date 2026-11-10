#!/usr/bin/env python3
"""examples/benchmark/v-shaped の入力と設定ファイルの生成(make が呼ぶ)。

  python3 make_inputs.py            全ケースの入力(data_<格子>/)と設定(param_<ケース>.txt)を書く
  python3 make_inputs.py 20 45      格子間隔 20 m・向き 45° の入力と、その格子の全ケースの設定だけ書く
                                    (格子間隔は任意。DXS・DX_SUP にない値は主ケースと、W より粗ければ _sgc だけ)

地形・粗度・マスクは、流域に沿う座標 (s, n) の式を各格子のセル中心で評価して与える(補間しない。
セルは水路か斜面のどちらかに丸ごと割り当てる)。s は水路に沿って下流へ測る距離(上流端 0、出口 L)、
n は水路の軸からの横断距離(正の側を「左岸側」と呼ぶ)。格子に対する流域の向き θ と格子間隔 Δx を
変えても同じ式を使うので、違いは格子の離散化だけになる。

  斜面   幅 B = 800 m、水路へ向かう勾配 S_S = 0.05、水路方向の勾配 S_O = 0(Tada 2026 と同じ)。
         脚の標高は上流端の水路床より D_UP = 1 m 高く、水路方向に一定(So = 0 のため)
  水路   幅 W = 20 m、縦断勾配 S_C = 0.02、出口(s = L)の床の標高 Z_OUT。上流端で斜面の脚より
         1 m、出口で 21 m 低い
  出口   出口の計測面は s = L。流域の下流に同じ断面の区間(斜面と水路。雨も降る)を L_EXT = 200 m 続け、
         その先に水路だけの延長 N_EXT セルと、海域マスク N_SEA セル(標高 0 m・水深 H_SEA = 1 m に固定された
         吸い込み。入った水は消える)を置く。下流の区間を置くのは、斜面が終わって水路の軸のセルの隣が領域外
         (壁)になる所の手前の数セル(20 m・45° で 3 セル、40 m で 2 セル)で水路の水深が理論の 1.8 倍まで
         上がるためで、計測面と出口のプローブ P1 をその影響の 200 m 上流に置く(水路だけを延長しても上がる
         場所は斜面の終わりのまま動かない)。海の水位 1 m は延長の末端の床(40 m で 1.6 m)より低いので背水は
         生じない。海の水深を 0 にしないのは、境界の水深が両側の平均で絞られて落差の手前に水が溜まるのを
         防ぐため(潮位の機能の hsea0 と同じ考え)。延長部と海の両脇、斜面の上流端と尾根、下流の区間の
         下流端は領域外(壁)
  粗度   斜面 0.015、水路 0.15(マニング)
  向き   θ = 0 では水路の軸 n = 0 がセル中心(水路が 1 行。20・40 m)か格子線(2・4 行。10・5 m)に
         乗るように、θ = 45° では軸がセル中心を通り(水路は 20 m で 1 本、10 m で 3 本、5 m で 5 本の
         斜めのセルの列)、出口の計測面がセル中心の列に重なるように格子の原点を置く
  追補   水路(W = 20 m)より粗い 40 m の格子(DX_SUP)では、河道マスクとサブグリッド河道幅(水路と延長の
         セルに W)の入力も書き、幅を与えるケース _sgc を加える(幅がセル幅以上のセルは解像扱いで幅が
         効かないので、20 m 以下の格子には書かない)

出力(data_dx<Δx>_r<θ>/。入力ファイルは先頭行が北端):
  z.txt     地盤高 (m)     rn.txt   粗度係数     mask.txt  領域マスク(1: 計算する)
  sw.txt    海域マスク(1: 吸い込みの海セル)     hinit.txt 初期水深 (m)(海セルだけ H_SEA)
  size.txt  nx ny ox oy dx theta(図化で (s, n) へ戻すための格子の原点と向き)
  rw.txt    河道マスク(1: 水路と延長のセル)     width.txt  サブグリッド河道幅 (m)(河道セルに W。Δx > W の格子だけ)
  斜面の脚のプローブ P2 は水路から 2 列目(脚の列の隣)。1 列目(脚)は水路との辺の粗度で水が溜まるので、
  時系列は 2 列目で理論と比べ、1 列目は check.py が分布 H0003 の脚の列の平均で見る
設定(param_<ケース>.txt)は、注釈付きの雛形 param.txt(10 m・0°・8 近傍)の格子・時間刻み・計測・
入出力の行と、比較ケースで変える行(p_diagratio / f_govequation / f_opening_dynamic。_sgc は
fn_channel と fn_rw の 2 行と、末尾に足す &list_channel)を差し替えて書く。雛形そのもののケースは
書かない(雛形の計測の行が計算値と違えば止まる)。
"""
import math
import os
import sys
import numpy as np

# ---------------------------------------------------------------- 幾何(流域に沿う座標、m)
L = 1000.0               # 水路の長さ(上流端 s = 0、出口 s = L)
W = 20.0                 # 水路の幅
B = 800.0                # 斜面の幅(水路の縁から尾根まで)
S_C = 0.02               # 水路の縦断勾配
S_S = 0.05               # 斜面の横断勾配(水路へ向かう)
S_O = 0.0                # 斜面の水路方向の勾配
D_UP = 1.0               # 上流端での水路の深さ(斜面の脚 − 水路床)
Z_OUT = 8.0              # 出口(s = L)の水路床の標高(延長の末端の床が海セルの水位 H_SEA より高く、背水を作らない値)
H_SEA = 1.0              # 海セルの水深 = 水位 (m)(標高 0 m に固定。吸い込み側の水深を 0 にしないための水柱)
N_S, N_C = 0.015, 0.15   # マニングの粗度(斜面・水路)
L_EXT = 200.0            # 流域の下流に同じ断面(斜面と水路)を続ける区間の長さ (m)
N_EXT, N_SEA = 3, 3      # その先の水路だけの延長と海セルの長さ(セル数)
# ---------------------------------------------------------------- 降雨・時間
P_MMH = 10.8             # 降雨強度 (mm/h)
T_RAIN = 90.0            # 降雨の継続時間 (min)
T_END = 180.0            # 計算時間 (min)
DT_PER_DX = 0.1          # 時間刻み dt = 0.1 Δx (s)(20 m で 2 s、5 m で 0.5 s。クーラン数 0.5 以下)
# ---------------------------------------------------------------- ケース
DXS = (20.0, 10.0, 5.0)  # 主ケースの格子(水路の幅 W 以下)
DX_SUP = (40.0,)         # 追補の格子(W より粗い。サブグリッド河道幅の有無を比べる)
THETAS = (0.0, 45.0)
WH = W / 2 + B           # 水路の軸から尾根まで
S_END = None             # 格子ごとに L + L_EXT + (N_EXT + N_SEA) Δx

# 比較ケース(接尾辞 → 雛形から差し替える 1 行)
VARIANTS = {
    "": {},                                  # 既定(8 近傍・力学波・開口の振り替え 3)
    "_4nb": {"p_diagratio": "0.0"},          # 4 近傍(斜めのエッジを使わない)
    "_dif": {"f_govequation": "1"},          # 拡散波(移流項なし。局所慣性は残る)
    "_kin": {"f_govequation": "2"},          # 運動波(圧力項もなし)
    "_od2": {"f_opening_dynamic": "2"},      # 開口の振り替えの旧既定(通過幅の調整の解説の比較用)
    "_sgc": {"fn_channel": "'-'", "fn_rw": "'rw.txt'"},   # 河道マスク + サブグリッド河道幅(追補。Δx > W の格子)
}
# 比較ケースで末尾に足す namelist(_sgc の &list_channel。fn_channel = '-' でこのファイルから読む)
EXTRA = {
    "_sgc": "&list_channel\n"
            "  fn_width = 'width.txt'    ! サブグリッド河道幅 (m)。水路と延長のセルに W = 20 m(堤防は置かない = 自然河岸)\n"
            "/\n",
}


def case_name(dx, theta, suffix=""):
    return f"dx{dx:g}_r{theta:g}{suffix}"


def cases_of(dx, theta):
    """その格子で計算するケースの接尾辞。"""
    out = [""]
    if dx in DXS:
        out.append("_4nb")
    if dx == 10.0:
        out += ["_dif", "_kin"]
    if theta == 0.0 and dx in DXS:
        out.append("_od2")
    if dx > W:
        out.append("_sgc")
    return out


BASE = case_name(10.0, 0.0)   # param.txt そのもののケース


# ---------------------------------------------------------------- 格子
def frame(dx, theta):
    """格子の大きさと原点(ox, oy)。セル中心 (x, y) と流域の座標の関係は
         s = (x − ox) cosθ − (y − oy) sinθ,  n = (x − ox) sinθ + (y − oy) cosθ
    θ = 0 では流域の長方形の角を格子線に乗せ(外側に 1 セルの余白)、水路の軸 n = 0 がセル中心か
    格子線に乗るように(格子に乗せた水路の幅 N Δx が W に近い方。20・40 m はセル中心で 1 行、10・5 m は
    格子線で 2・4 行)、必要なら 1 セル未満だけ原点を上へずらす。θ = 45° では水路の軸 n = 0 が
    セル中心を通り、かつ出口の計測面(s = L − Δx/(2√2))がセル中心の列に重なるように原点を選ぶ。"""
    th = math.radians(theta)
    c, sn = math.cos(th), math.sin(th)
    s_end = L + L_EXT + (N_EXT + N_SEA) * dx
    corners = [(s, n) for s in (0.0, s_end) for n in (-WH, WH)]
    xs = [s * c + n * sn for s, n in corners]
    ys = [-s * sn + n * c for s, n in corners]
    ox, oy = dx - min(xs), dx - min(ys)
    if theta == 0.0:
        n_c = 1 + 2 * sum(1 for k in range(1, 1000) if k * dx < W / 2 - 1e-9)          # 軸がセル中心のときの水路の行数
        n_l = 2 * sum(1 for k in range(0, 1000) if (k + 0.5) * dx < W / 2 - 1e-9)      # 軸が格子線のとき
        want = 0.0 if abs(n_l * dx - W) < abs(n_c * dx - W) else 0.5                 # 軸のセル内の位置
        d = (want - (oy / dx) % 1.0) % 1.0
        if d > 1e-9 and d < 1.0 - 1e-9:
            oy += d * dx
    if theta == 45.0:
        # ox + oy = m Δx(軸がセル中心を通る)、oy − ox = √2 L − (p + 1/2) Δx(s = L − Δx/(2√2) の
        # セル中心の列。m + p は奇数)を満たす最小の原点
        u = (2 * ox + math.sqrt(2) * L) / dx - 0.5       # m + p の下限
        v = (2 * oy - math.sqrt(2) * L) / dx + 0.5       # m − p の下限
        u = math.ceil(u) if math.ceil(u) % 2 == 1 else math.ceil(u) + 1
        v = math.ceil(v) if math.ceil(v) % 2 == 1 else math.ceil(v) + 1
        ox = ((u + 0.5) * dx - math.sqrt(2) * L) / 2
        oy = ((v - 0.5) * dx + math.sqrt(2) * L) / 2
    elif theta != 0.0:
        sys.exit("向きは 0 か 45 だけ")
    nx = int(math.ceil((max(xs) + ox) / dx - 1e-9)) + 1
    ny = int(math.ceil((max(ys) + oy) / dx - 1e-9)) + 1
    return nx, ny, ox, oy, c, sn, s_end


def to_sn(dx, theta):
    """各セル中心の流域の座標 (s, n)。配列の行 0 が南端。"""
    nx, ny, ox, oy, c, sn, _ = frame(dx, theta)
    x = (np.arange(nx) + 0.5) * dx - ox
    y = (np.arange(ny) + 0.5) * dx - oy
    X, Y = np.meshgrid(x, y)
    return X * c - Y * sn, X * sn + Y * c


def classify(dx, theta):
    """セルの種類: 0 領域外、1 斜面、2 水路(ここまでが流域)、3 水路の延長(下流の区間と、その先の水路だけの
    延長)、4 海(吸い込み)、5 下流の区間の斜面。"""
    nx, ny, ox, oy, c, sn, s_end = frame(dx, theta)
    s, n = to_sn(dx, theta)
    kind = np.zeros((ny, nx), dtype=int)
    inchan = np.abs(n) < W / 2
    inhill = (np.abs(n) < WH) & ~inchan
    kind[(s >= 0.0) & (s < L) & inhill] = 1
    kind[(s >= 0.0) & (s < L) & inchan] = 2
    kind[(s >= L) & (s < L + L_EXT + N_EXT * dx) & inchan] = 3
    kind[(s >= L + L_EXT + N_EXT * dx) & (s < s_end) & inchan] = 4
    kind[(s >= L) & (s < L + L_EXT) & inhill] = 5
    return kind, s, n


def grid(dx, theta):
    kind, s, n = classify(dx, theta)
    zc = Z_OUT + S_C * (L - s)                                        # 水路床(延長も同じ勾配)
    zh = Z_OUT + S_C * L + D_UP + S_S * (np.abs(n) - W / 2) + S_O * (L - s)   # 斜面(下流の区間も同じ)
    hill = (kind == 1) | (kind == 5)
    z = np.where(hill, zh, np.where((kind == 2) | (kind == 3), zc, 0.0))
    rn = np.where(hill, N_S, N_C)
    hinit = np.where(kind == 4, H_SEA, 0.0)
    return {"z": z, "rn": rn, "mask": (kind > 0).astype(int), "sw": (kind == 4).astype(int), "hinit": hinit}, kind, s, n


# ---------------------------------------------------------------- 計測(セル番号。ENCflow は西端の列・北端の行が 1)
def ij_of(dx, theta, s0, n0):
    """点 (s0, n0) を含むセルの配列添字 (i, j)(j は南端が 0)。"""
    nx, ny, ox, oy, c, sn, _ = frame(dx, theta)
    x = s0 * c + n0 * sn + ox
    y = -s0 * sn + n0 * c + oy
    return int(math.floor(x / dx)), int(math.floor(y / dx))


def to_enc(i, j, ny):
    return i + 1, ny - j


def records(dx, theta, kind, s, n):
    """出口の計測面(全幅)・斜面の脚の計測線(左岸側の斜面 → 水路)・2 つのプローブのセル番号と、
    プローブの斜面の位置。dict: outlet, foot, p1, p2, nfoot(脚の計測線のセル数)、x1・x2(脚の 1 セル目・
    2 セル目のセル中心の尾根からの距離 (m)。理論の水深をこの位置で評価する)。"""
    ny, nx = kind.shape
    # 出口: s = L − Δx/2(θ = 0)または s = L − Δx/(2√2)(45°。frame で合わせた列)のセルの列。
    # 右岸側の尾根 (n < 0) から左岸側の尾根へ(始点→終点の右側 = 下流が正)
    i0, j0 = ij_of(dx, theta, L - dx / 2 / (math.sqrt(2) if theta == 45.0 else 1.0), 0.0)
    assert kind[j0, i0] == 2, "出口の列が水路のセルに乗っていない"
    if theta == 0.0:
        sel = (np.arange(nx)[None, :] == i0) & (kind > 0)
    else:
        I, J = np.meshgrid(np.arange(nx), np.arange(ny))
        sel = ((I - J) == (i0 - j0)) & (kind > 0)
    jj, ii = np.nonzero(sel)
    k = np.argsort(n[jj, ii])
    outlet = (*to_enc(ii[k[0]], jj[k[0]], ny), *to_enc(ii[k[-1]], jj[k[-1]], ny))
    # 斜面の脚: 左岸側 (n > 0) の斜面のセルのうち水路に最も近い列。上流から下流へ
    # (始点→終点の右側 = 水路側が正)
    hill = (kind == 1) & (n > 0)
    nmin = n[hill].min()
    sel = hill & (np.abs(n - nmin) < 1e-6)
    jj, ii = np.nonzero(sel)
    k = np.argsort(s[jj, ii])
    foot = (*to_enc(ii[k[0]], jj[k[0]], ny), *to_enc(ii[k[-1]], jj[k[-1]], ny))
    nfoot = int(sel.sum())
    # プローブ: P1 は出口の水路のセル(計測面の列の軸上のセル)、P2 は左岸側の斜面の水路から 2 列目(脚の列の隣)の
    # 中央(s = L/2 に最も近い)。脚の 1 セル目は水路との辺の粗度(両側の平均)で水が溜まり理論からずれるので、
    # 時系列は 2 セル目で理論の分布と比べ、1 セル目は分布 H0003 の脚の列の平均で見る(check.py)
    p1 = to_enc(i0, j0, ny)
    n2 = np.unique(np.round(n[hill], 6))[1]
    sel = hill & (np.abs(n - n2) < 1e-6)
    jj, ii = np.nonzero(sel)
    km = np.argmin(np.abs(s[jj, ii] - L / 2))
    p2 = to_enc(ii[km], jj[km], ny)
    return {"outlet": outlet, "foot": foot, "p1": p1, "p2": p2, "nfoot": nfoot, "x1": WH - nmin, "x2": WH - n2}


# ---------------------------------------------------------------- 書き出し
def write_grid(dx, theta):
    out, kind, s, n = grid(dx, theta)
    nx, ny, ox, oy, _, _, _ = frame(dx, theta)
    ddir = f"data_{case_name(dx, theta)}"
    os.makedirs(ddir, exist_ok=True)
    if dx > W:   # 追補: 河道マスク(水路と延長)とサブグリッド河道幅(河道セルに W)
        out["rw"] = ((kind == 2) | (kind == 3)).astype(int)
        out["width"] = np.where(out["rw"] > 0, W, 0.0)
    for key, g in out.items():
        fmt = "%d" if key in ("mask", "sw", "rw") else ("%.4f" if key == "z" else ("%.1f" if key == "width" else "%.3f"))
        np.savetxt(os.path.join(ddir, key + ".txt"), g[::-1], fmt=fmt)   # 先頭行が北端
    with open(os.path.join(ddir, "size.txt"), "w") as f:
        f.write(f"{nx} {ny} {ox:.6f} {oy:.6f} {dx:g} {theta:g}\n")
    rec = records(dx, theta, kind, s, n)
    ncell = [int((kind == k).sum()) for k in range(6)]
    nchain = len(set(np.round(n[kind == 2], 3)))      # 水路を成すセルの列の数(横断方向)
    print(f"{case_name(dx, theta)}: nx = {nx}, ny = {ny}, 斜面 {ncell[1]} 水路 {ncell[2]} 下流の区間の斜面 {ncell[5]} "
          f"水路の延長 {ncell[3]} 海 {ncell[4]} セル(集水面積 {(ncell[1] + ncell[2]) * dx * dx / 1e6:.4f} km²、水路は横断方向に "
          f"{nchain} セル、脚の計測線 {rec['nfoot']} セル、P2 は尾根から {rec['x2']:.1f} m"
          + ("、河道マスクと幅 %g m の入力あり" % W if dx > W else "") + ")")
    return ddir, nx, ny, rec


def write_param(name, ddir, dx, nx, ny, rec, variant, extra=""):
    """param.txt(10 m・0°・8 近傍の注釈付きの雛形)の格子・時間刻み・計測・入出力の行と、
    比較ケースで変える行を差し替え、extra(末尾に足す namelist)があれば足して書く。
    雛形そのもの(BASE)は書かず、計測の行が合っているか確かめる。"""
    rep = {"dt": f"{DT_PER_DX * dx:g}", "dx": f"{dx:g}", "dy": f"{dx:g}", "nx": f"{nx}", "ny": f"{ny}",
           "dir_data": f"'{ddir}'", "dir_result": f"'result_{name}'",
           "flxy(:,1)": ", ".join(str(v) for v in rec["outlet"]), "flxy(:,2)": ", ".join(str(v) for v in rec["foot"]),
           "pbxy(:,1)": ", ".join(str(v) for v in rec["p1"]), "pbxy(:,2)": ", ".join(str(v) for v in rec["p2"])}
    rep.update(variant)
    lines = open("param.txt").read().splitlines()
    out = [f"! このファイルは make_inputs.py が param.txt から生成する(ケース {name})。編集は param.txt と make_inputs.py で"]
    done = set()
    for line in lines:
        key = line.split("=")[0].strip() if "=" in line and not line.lstrip().startswith("!") else None
        if key in rep:
            head, _, tail = line.partition("=")
            val_comment = tail.split("!", 1)
            if name == BASE and val_comment[0].strip().replace(" ", "") != rep[key].replace(" ", ""):
                sys.exit(f"param.txt の {key} = {val_comment[0].strip()} は計算値 {rep[key]} と違う")
            comment = "!" + val_comment[1] if len(val_comment) > 1 else ""
            line = f"{head}= {rep[key]}"
            if comment:
                line = f"{line:<28}{comment}"
            done.add(key)
        out.append(line)
    missing = set(rep) - done
    if missing:
        sys.exit(f"param.txt に {sorted(missing)} の行がありません")
    if name != BASE:
        with open(f"param_{name}.txt", "w") as f:
            f.write("\n".join(out) + "\n" + ("\n" + extra if extra else ""))


def main():
    args = sys.argv[1:]
    grids = [(float(args[0]), float(args[1]))] if args else [(dx, th) for dx in DXS + DX_SUP for th in THETAS]
    for dx, th in grids:
        ddir, nx, ny, rec = write_grid(dx, th)
        for suf in cases_of(dx, th):
            write_param(case_name(dx, th, suf), ddir, dx, nx, ny, rec, VARIANTS[suf], EXTRA.get(suf, ""))


if __name__ == "__main__":
    main()
