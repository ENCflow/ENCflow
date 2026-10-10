#!/usr/bin/env python3
"""BMI の多格子公開(ネスト系)の受け入れ試験。test/bmi_nest で実行する:

    cd test/bmi_nest && python3 ../../bmi/python/test_nest.py

ケース: wave のルート(385x385)に比 1:1・双方向(nest_fb=2)の子(121x121。
親セル 133..253)を置く。比 1 の自己ネストでは子の内部がルートの同領域と
ビット一致し、ルートは単独ランとビット一致する(test/nest_identity と同じ
性質)ので、BMI 越しの格子の取り違え・行順・配置のずれが機械的に検出できる。

手順(1 プロセス 1 component なので同一プロセスで順に initialize する):
  A: 単独ラン(param_single.txt = fn_nest なし)。t0 の水深を BMI で取り、
     子の足元(親セル 133..253)を切り出して子の初期水深ファイルを書く。
     最後まで進めて最終水深 hA と Log を保存。
  B: ネスト(param_root.txt)。格子情報(grids = [0, 1]、形・刻み・原点。
     子の原点は親の原点 + 整列位置から導かれる)、変数表(16 出力・6 入力、
     ~grid1 の修飾名)、var_grid を検査。毎ステップ、子の内部(帯の外)の
     水深と速さがルートの足元とビット一致すること。最終のルート水深が hA と
     一致し、Log が A と全行一致すること(= 格子の区別と置換が正しい)。
     誤用検査: 存在しない格子の変数、サイズ不一致、負の水深の set。
  C: ネストを再度 initialize(ネスト後の再 initialize 経路)。半分の時点で
     子の h と ルートの z を get してそのまま set(同値 set)。最終水深が hA と
     一致し Log が A と全行一致(set が格子を取り違えず副作用がないこと)。
判定: すべて厳密一致(ULP 0)。不合格なら非零終了。
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from encflow import ENCflow, BmiError, VAR_DEPTH, VAR_ELEVATION, VAR_SPEED, var_on_grid  # noqa: E402

I0, J0 = 133, 133          # 子セル (1,1) が整列する親セル(nest.txt と同じ)
NB = 3                     # 帯幅(移流スキーム 3 の自動値。比較は帯の外)
HINIT = "hinit_child.txt"


def fail(msg):
    print(f"test_nest: FAILED: {msg}")
    sys.exit(1)


def footprint(arr_root, ny_c, nx_c):
    """ルートの BMI 2 次元配列(行 0 = 南)から子の足元を切り出す(子配列と同じ並び)。"""
    ny_r = arr_root.shape[0]
    r0 = ny_r - (J0 - 1) - ny_c
    c0 = I0 - 1
    return arr_root[r0:r0 + ny_c, c0:c0 + nx_c]


def read_log(path):
    return Path(path).read_text().splitlines()


# ---------------------------------------------------------------- A: 単独ラン
with ENCflow("param_single.txt") as m:
    if m.grids != [0]:
        fail(f"single run: grids = {m.grids}")
    if m.output_var_names != [n for n in m.output_var_names if "~grid" not in n]:
        fail("single run: a grid-qualified name appeared")
    h0 = m.get2d(VAR_DEPTH)
    ny_r, nx_r = h0.shape
    # 子の初期水深ファイル(行 = 北から南 = 子の j 順。17 桁で往復厳密)
    nyc = nxc = 121
    fp = footprint(h0, nyc, nxc)
    with open(HINIT, "w") as f:
        for row in fp[::-1]:
            f.write(" ".join(f"{v:.17e}" for v in row) + "\n")
    while m.time < m.end_time:
        m.update()
    hA = m.get(VAR_DEPTH)
    tA = m.time
logA = read_log("result_single/Log.txt")
print(f"test_nest: A single run done: t = {tA}, max h = {hA.max():.6e}, hinit written ({nyc}x{nxc})")

# ------------------------------------------------------------- B: ネスト
with ENCflow("param_root.txt") as m:
    if m.grids != [0, 1]:
        fail(f"nested run: grids = {m.grids}")
    if m.shape_of(0) != (ny_r, nx_r) or m.shape_of(1) != (nyc, nxc):
        fail(f"nested run: shapes {m.shape_of(0)} {m.shape_of(1)}")
    if m.size_of(1) != nyc * nxc:
        fail("nested run: size_of(1)")
    dy, dx = m.spacing_of(0)
    if m.spacing_of(1) != (dy, dx):
        fail(f"nested run: child spacing {m.spacing_of(1)} != {(dy, dx)}")
    y0, x0 = m.origin_of(0)
    yc, xc = m.origin_of(1)
    # 子の原点 = 親の原点 + 整列位置(x: (i0-1)·dx、y: (ny_r-(j0-1))·dy - nyc·dy)
    y_exp = y0 + (ny_r - (J0 - 1)) * dy - nyc * dy
    x_exp = x0 + (I0 - 1) * dx
    if abs(yc - y_exp) > 1e-9 or abs(xc - x_exp) > 1e-9:
        fail(f"nested run: child origin {(yc, xc)} != {(y_exp, x_exp)}")
    names = m.output_var_names
    if len(names) != 16 or len(m.input_var_names) != 6:
        fail(f"nested run: {len(names)} outputs, {len(m.input_var_names)} inputs")
    hc_name = var_on_grid(VAR_DEPTH, 1)
    if hc_name != "surface_water~grid1__depth" or hc_name not in names:
        fail(f"nested run: child depth name {hc_name} not in output list")
    if m.var_grid(VAR_DEPTH) != 0 or m.var_grid(hc_name) != 1:
        fail("nested run: var_grid")
    # 誤用: 存在しない格子・サイズ不一致・負の水深
    for bad in (var_on_grid(VAR_DEPTH, 2), "surface_water~grid__depth", "no_such__variable"):
        try:
            m.get(bad)
        except BmiError:
            pass
        else:
            fail(f"get({bad}) did not fail")
    try:
        m.set(hc_name, np.zeros(ny_r * nx_r))
    except (ValueError, BmiError):
        pass
    else:
        fail("set child h with the root size did not fail")
    try:
        m.set(hc_name, -np.ones(nyc * nxc))
    except BmiError:
        pass
    else:
        fail("set negative child h did not fail")
    # 毎ステップ: 子の内部 == ルートの足元(帯の外。h と速さ)
    nmis = 0
    nstep = 0
    while m.time < m.end_time:
        m.update()
        nstep += 1
        for vname in (VAR_DEPTH, VAR_SPEED):
            r = footprint(m.get2d(vname), nyc, nxc)[NB:-NB, NB:-NB]
            c = m.get2d(var_on_grid(vname, 1))[NB:-NB, NB:-NB]
            if not np.array_equal(r, c):
                nmis += 1
                print(f"test_nest:   step {nstep} t = {m.time:.3f}: {vname} child != root, "
                      f"max |d| = {np.abs(r - c).max():.3e}")
                break
    hB = m.get(VAR_DEPTH)
    hcB = m.get2d(hc_name)
    if hcB.shape != (nyc, nxc):
        fail("child get2d shape")
if nmis:
    fail(f"nested run: child interior != root footprint at {nmis} steps")
if not np.array_equal(hB, hA):
    fail(f"nested run: final root h != single run (max |d| = {np.abs(hB - hA).max():.3e})")
logB = read_log("result_root/Log.txt")
if logB != logA:
    fail("nested run: result_root/Log.txt != result_single/Log.txt")
print(f"test_nest: B nested run done: {nstep} steps, child interior == root footprint, "
      f"root == single (bit-identical), Log identical")

# ------------------------------------------- C: 再 initialize + 同値 set
with ENCflow("param_root.txt") as m:
    if m.grids != [0, 1]:
        fail(f"re-initialized nested run: grids = {m.grids}")
    m.update_until(m.start_time + m.time_step * (nstep // 2))
    hc = m.get(hc_name)
    zr = m.get(VAR_ELEVATION)
    m.set(hc_name, hc)                 # 子の水深を同値で置換
    m.set(VAR_ELEVATION, zr)           # ルートの地形を同値で置換
    while m.time < m.end_time:
        m.update()
    hC = m.get(VAR_DEPTH)
if not np.array_equal(hC, hA):
    fail(f"same-value set: final root h != single run (max |d| = {np.abs(hC - hA).max():.3e})")
logC = read_log("result_root/Log.txt")
if logC != logA:
    fail("same-value set: result_root/Log.txt != result_single/Log.txt")
print("test_nest: C re-initialize + same-value set on grid 1 / grid 0: root == single, Log identical")
print("test_nest: all checks passed")
