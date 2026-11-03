#!/bin/bash
# wqbound: 逐次実行 + 回帰テスト(水質の系外との出入りの台帳と水位規定セル。§30.9)
#   ./Run.sh [-u]
# 回帰(Log.txt + wq.csv)に加えて reference 非依存の検定を行う:
#   台帳の閉合と各経路の活性(param.txt)、水位規定セルからの逆流の濃度の上限と
#   境界濃度・台帳の閉合(param_rev.txt → result_rev)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列)
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

python3 Check_wqbound.py closure result || exit 1
python3 Check_wqbound.py paths result || exit 1

rm -rf result_rev
./encflow param_rev.txt > Screen_rev.log 2>&1 || { echo "ERROR: param_rev run failed" >&2; exit 1; }
python3 Check_wqbound.py closure result_rev || exit 1
python3 Check_wqbound.py reverse result_rev || exit 1

echo "=== wqbound verification PASS ==="
