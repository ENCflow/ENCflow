#!/usr/bin/env python3
"""模式実験 D1・D2(地表の底層重力流と仮想壁)の検定。事前に ./Run_wall.sh が必要。

終状態は倍精度の保存ファイル(save_wall_*/state.dat と saltwater.dat)から読む。
  D1(堤防 bank0)・D2(海岸堤防 seawall0): 西の陸(z = 0)の水は全層塩水(界面 +1.2 m)、
  東の河道・海側(z = −3 m)は淡水、水面は水平で天端 +2 m より低い。塩水の界面が天端より
  低いので重力流は壁を越えない(developer.md §47.8)。解析的な終状態は陸 Hss = 1.2、
  河道・海側 Hss = 0、H は初期のまま(陸 1.2・河道/海側 4.2)。判定は相対 1e-12。
"""
import sys

sys.dont_write_bytecode = True
from Check_exch import load      # noqa: E402(保存状態の読み取りを共用)

ok = True
for tag, savedir in (("D1 levee", "save_wall_bank"), ("D2 seawall", "save_wall_sea")):
    s = load(savedir)
    land = [i for i, z in enumerate(s["z"]) if z > -1.0]
    chan = [i for i, z in enumerate(s["z"]) if z < -1.0]
    e_land = max(abs(s["hss"][i] - 1.2) for i in land) / 1.2
    e_chan = max(abs(s["hss"][i]) for i in chan)
    e_h = max(max(abs(s["h"][i] - 1.2) for i in land), max(abs(s["h"][i] - 4.2) for i in chan)) / 1.2
    good = e_land < 1e-12 and e_chan < 1e-12 and e_h < 1e-12
    ok &= good
    print(f"{tag}: land Hss rel.err {e_land:.1e}, other side max Hss {e_chan:.1e} m, "
          f"H rel.err {e_h:.1e}  {'PASS' if good else 'FAIL'}")

print("=== Check_wall PASS ===" if ok else "=== Check_wall FAIL ===")
sys.exit(0 if ok else 1)
