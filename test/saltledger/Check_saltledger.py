#!/usr/bin/env python3
"""saltledger の検定(Python 標準ライブラリのみ)。塩水の台帳 salt.csv(developer.md §140)を読む。

  Check_saltledger.py close RESDIR
      台帳の閉合(記録の全行): 地表の体積 = 初期 + 海から − 海へ + 辺から − 辺へ − 水位規定 − 浸透 + 湧出
      − 構造物 − lost_surf、地下の体積 = 初期 + 浸透 − 湧出 + gvadj + 海から − 海へ − 揚水 − lost_gw。
  Check_saltledger.py evap RESDIR AREA HSS0 E DT T
      蒸発: 最後の行で lost_surf = (E·(T − DT))·AREA、地表の体積 = (HSS0 − E·(T − DT))·AREA
      (蒸発散は塩水の処理の後に働くので、整合クランプは 1 ステップ遅れる)。
  Check_saltledger.py pump RESDIR AREA VOL STRUCT LOST
      域外へ排水するポンプ: 最後の行の地表の体積 VOL、out_struct = STRUCT、lost_surf = LOST(m3)。
  Check_saltledger.py xfer RESDIR NX NY DX N VOL IW IE HSSE
      域内の転送: 地表の体積が全行で VOL のまま、out_struct = lost_surf = 0、分布 N で西の池(列 1〜IW)の
      塩水層が 0、東の池(列 IE〜NX)が HSSE。
  Check_saltledger.py exin RESDIR AREA INFIL VSURF
      浸透の配分: 最後の行で infil = INFIL、地表の体積 = VSURF、地下の体積 = INFIL(m3)、gvadj = 0。
  Check_saltledger.py well RESDIR QT
      塩水だけの帯水層から汲む井戸: 最後の行で、out_pump が需要 QT(流量 × 時間。m3)の 9 割以上・QT 以下
      (塩水が井戸に届くまでは汲めない)、地下の整合クランプ lost_gw が海からの流入の 1e-6 以下
      (汲んだ水はすべて塩水として揚水に数える)。
  Check_saltledger.py pos RESDIR COLUMN [COLUMN ...]
      最後の行で、挙げた列が正(その経路が実際に働いている)。
"""
import csv
import struct
import sys

TOL = 2.0e-6          # 台帳の閉合の相対誤差(CSV は有効 8 桁)


def read_bil(path, nx, ny):
    with open(path, "rb") as f:
        raw = f.read()
    if len(raw) != 4 * nx * ny:
        raise SystemExit(f"FAIL: {path} の大きさが {nx} x {ny} の float32 と合わない")
    v = struct.unpack("<%df" % (nx * ny), raw)
    return [v[j * nx:(j + 1) * nx] for j in range(ny)]


def read_ledger(res):
    with open(f"{res}/salt.csv", newline="") as f:
        rows = list(csv.reader(f))
    head = [h.strip() for h in rows[0]]
    return [dict(zip(head, [float(x) for x in r])) for r in rows[1:] if r]


def line(good, text):
    print(f"  {'ok  ' if good else 'FAIL'} {text}")
    return good


def near(a, b, scale=None, tol=TOL):
    s = max(abs(b), 1.0e-30) if scale is None else scale
    return abs(a - b) <= tol * s


def check_close(args):
    L = read_ledger(args[0])
    v0 = L[0]
    worst_s = worst_g = 0.0
    scale = 1.0e-30
    for v in L:
        scale = max(scale, v["vol_surf_m3"], v["vol_gw_m3"], v["in_sea_m3"], v["in_sea_gw_m3"], v["infil_m3"], v["seep_m3"])
    for v in L:
        rs = v["vol_surf_m3"] - (v0["vol_surf_m3"] + v["in_sea_m3"] - v["out_sea_m3"] + v["in_edge_m3"]
                                 - v["out_edge_m3"] - v["out_stage_m3"] - v["infil_m3"] + v["seep_m3"]
                                 - v["out_struct_m3"] - v["lost_surf_m3"])
        rg = v["vol_gw_m3"] - (v0["vol_gw_m3"] + v["infil_m3"] - v["seep_m3"] + v["gvadj_m3"]
                               + v["in_sea_gw_m3"] - v["out_sea_gw_m3"] - v["out_pump_m3"] - v["lost_gw_m3"])
        worst_s = max(worst_s, abs(rs))
        worst_g = max(worst_g, abs(rg))
    ok = line(worst_s <= TOL * scale, f"地表の塩水の収支の残差 {worst_s:.2e} m3(最大の項 {scale:.4e} m3 の {worst_s/scale:.1e})")
    ok = line(worst_g <= TOL * scale, f"地下の塩水の収支の残差 {worst_g:.2e} m3({worst_g/scale:.1e})") and ok
    return ok


def check_evap(args):
    res, area, hss0, e, dt, t = args[0], float(args[1]), float(args[2]), float(args[3]), float(args[4]), float(args[5])
    v = read_ledger(res)[-1]
    want = e * (t - dt) * area
    ok = line(near(v["lost_surf_m3"], want), f"lost_surf {v['lost_surf_m3']:.7e} m3 = 蒸発の速さ × (時間 − 1 ステップ) × 面積 {want:.7e}")
    want = (hss0 - e * (t - dt)) * area
    ok = line(near(v["vol_surf_m3"], want), f"地表の体積 {v['vol_surf_m3']:.7e} m3 = {want:.7e}(水深 + 1 ステップの蒸発)") and ok
    return ok


def check_pump(args):
    res, area, vol, st, lost = args[0], float(args[1]), float(args[2]), float(args[3]), float(args[4])
    v = read_ledger(res)[-1]
    sc = 0.3 * area
    ok = line(near(v["vol_surf_m3"], vol, sc), f"地表の体積 {v['vol_surf_m3']:.7e} m3(期待 {vol:.7e})")
    ok = line(near(v["out_struct_m3"], st, sc), f"out_struct {v['out_struct_m3']:.7e} m3(期待 {st:.7e})") and ok
    ok = line(near(v["lost_surf_m3"], lost, sc), f"lost_surf {v['lost_surf_m3']:.7e} m3(期待 {lost:.7e})") and ok
    return ok


def check_xfer(args):
    res, nx, ny, dx, n, vol = args[0], int(args[1]), int(args[2]), float(args[3]), int(args[4]), float(args[5])
    iw, ie, hsse = int(args[6]), int(args[7]), float(args[8])
    L = read_ledger(res)
    dev = max(abs(v["vol_surf_m3"] - vol) for v in L)
    ok = line(dev <= TOL * vol, f"地表の体積が {vol:.1f} m3 のまま(差の最大 {dev:.2e})")
    v = L[-1]
    ok = line(v["out_struct_m3"] == 0.0 and abs(v["lost_surf_m3"]) <= TOL * vol,
              f"out_struct {v['out_struct_m3']:.2e}、lost_surf {v['lost_surf_m3']:.2e} m3(域内の転送は合計を変えない)") and ok
    s = read_bil(f"{res}/Hss{n:04d}.bil", nx, ny)
    west = max(abs(s[j][i]) for j in range(ny) for i in range(iw))
    east = max(abs(s[j][i] - hsse) for j in range(ny) for i in range(ie - 1, nx))
    ok = line(west <= 1.0e-6, f"西の池の塩水層の最大 {west:.2e} m(すべて運ばれた)") and ok
    ok = line(east <= 1.0e-6, f"東の池の塩水層と {hsse} m の差の最大 {east:.2e} m") and ok
    return ok


def check_exin(args):
    res, area, infil, vsurf = args[0], float(args[1]), float(args[2]), float(args[3])
    v = read_ledger(res)[-1]
    ok = line(near(v["infil_m3"], infil), f"infil {v['infil_m3']:.7e} m3(期待 {infil:.7e} = 帯水層の容量 × 面積)")
    ok = line(near(v["vol_surf_m3"], vsurf), f"地表の体積 {v['vol_surf_m3']:.7e} m3(期待 {vsurf:.7e})") and ok
    ok = line(near(v["vol_gw_m3"], infil), f"地下の体積 {v['vol_gw_m3']:.7e} m3(期待 {infil:.7e})") and ok
    ok = line(v["gvadj_m3"] == 0.0, f"gvadj {v['gvadj_m3']:.2e} m3(家屋の空隙率 1 では 0)") and ok
    return ok


def check_well(args):
    res, qt = args[0], float(args[1])
    v = read_ledger(res)[-1]
    ok = line(0.9 * qt <= v["out_pump_m3"] <= qt * (1.0 + 1.0e-6),
              f"out_pump {v['out_pump_m3']:.6e} m3(需要 {qt:.6e} m3 の {v['out_pump_m3']/qt:.3f}。0.9 以上・1 以下)")
    ok = line(abs(v["lost_gw_m3"]) <= 1.0e-6 * v["in_sea_gw_m3"],
              f"lost_gw {v['lost_gw_m3']:.3e} m3(海からの流入 {v['in_sea_gw_m3']:.6e} m3 の 1e-6 以下)") and ok
    return ok


def check_pos(args):
    v = read_ledger(args[0])[-1]
    ok = True
    for c in args[1:]:
        ok = line(v[c] > 0.0, f"{c} = {v[c]:.6e} m3(> 0)") and ok
    return ok


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    mode, args = sys.argv[1], sys.argv[2:]
    table = {"close": check_close, "evap": check_evap, "pump": check_pump,
             "xfer": check_xfer, "exin": check_exin, "well": check_well, "pos": check_pos}
    if mode not in table:
        raise SystemExit(__doc__)
    ok = table[mode](args)
    print(("PASS" if ok else "FAIL") + f": saltledger {mode} {args[0]}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
