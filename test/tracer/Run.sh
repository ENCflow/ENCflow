#!/bin/bash
# tracer: 逐次実行 + 回帰テスト(構成 A dx=10・dt=1)+ 数値拡散の検定
#   ./Run.sh [-u]
# 回帰(Log.txt + wq.csv)の後、構成 A の dt=2・dx=20 と構成 B、および
# それぞれの f_scalar_scheme = 3(MUSCL。*_m.txt)を走らせ、Check_tracer.py で
# 1 次風上の等価拡散係数を理論値と比べ、MUSCL の低減率と正値性を検定する
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列、wq.csv の in_map_g = 0)
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

for p in param_a10dt2.txt param_a20.txt param_b.txt param_m.txt param_a10dt2_m.txt param_a20_m.txt param_b_m.txt; do
  echo "run $p"
  ./encflow $p > Screen_${p%.txt}.log 2>&1 || { tail -5 Screen_${p%.txt}.log; exit 1; }
done
python3 Check_tracer.py || exit 1
echo "=== tracer verification PASS ==="
