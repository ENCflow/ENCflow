#!/bin/bash
# gwseep: 逐次実行 + 回帰テスト(水質 W3 = 浸透→地下側方→湧出。§30.5)
#   ./Run.sh [-u]
# 回帰(Log.txt + wq.csv)に加えて reference 非依存の検定を行う:
#   台帳の閉合(to_gw − seep = mass_gw、総質量保存)と
#   wq_rg=1e12 の完全不動化(param_rg.txt → result_rg)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列。
                       # wq.csv の第4列 in_map_g はこのケースでは恒等 0)
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

python3 Check_gwseep.py closure result/wq.csv || exit 1

rm -rf result_rg
./encflow param_rg.txt > Screen_rg.log 2>&1 || { echo "ERROR: param_rg run failed" >&2; exit 1; }
python3 Check_gwseep.py immobile result_rg/wq.csv || exit 1

echo "=== gwseep verification PASS ==="
