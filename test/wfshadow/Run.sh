#!/bin/bash
# wfshadow: 逐次実行 + 回帰テスト + 検定(沿岸の波浪場 fn_wavefield の 2 次元。developer.md §90)
#   ./Run.sh [-u]
# param.txt(防波堤と菱形の囲い、方向分散 20° の不規則波)は reference 比較(Log.txt・
# wavefield.csv・Wh0001.txt、ULP=0)と Check_wfshadow.py base(独立に実装した
# 掃引解との一致、斜めの壁の遮断)。param_aligned.txt(格子の軸に揃った単一方向)は
# Check_wfshadow.py aligned(陰の縁が厳密に鋭い)の検定のみ(reference 非依存)
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列)
export FILES=${FILES:-"Log.txt wavefield.csv Wh0001.txt"}
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

python3 Check_wfshadow.py base result || exit 1

rm -rf result_aligned
./encflow param_aligned.txt > Screen_aligned.log 2>&1 || { echo "ERROR: param_aligned run failed" >&2; exit 1; }
python3 Check_wfshadow.py aligned result_aligned || exit 1

echo "=== wfshadow verification PASS ==="
