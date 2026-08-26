#!/bin/bash
# kdpart: 逐次実行 + 回帰テスト(水質 K1 = Kd 平衡二相分配。§30.6)
#   ./Run.sh [-u]
# 回帰(Log.txt + wq.csv)に加えて reference 非依存の検定を行う:
#   台帳の閉合(in_point = surf+gw+pool)・分配の活性と、
#   Kd 1000 倍(param_hi.txt → result_hi)での単調性(settle 増・to_gw 減)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列。
                       # wq.csv の第4列 in_map_g はこのケースでは恒等 0)
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

echo "Check_kdpart closure: result/wq.csv"
python3 Check_kdpart.py closure result/wq.csv || exit 1

rm -rf result_hi
./encflow param_hi.txt > Screen_hi.log 2>&1 || { echo "ERROR: param_hi run failed" >&2; exit 1; }
echo "Check_kdpart closure: result_hi/wq.csv"
python3 Check_kdpart.py closure result_hi/wq.csv || exit 1
echo "Check_kdpart monotonic: result vs result_hi"
python3 Check_kdpart.py monotonic result/wq.csv result_hi/wq.csv || exit 1

echo "=== kdpart verification PASS ==="
