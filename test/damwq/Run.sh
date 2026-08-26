#!/bin/bash
# damwq: 逐次実行 + 回帰テスト(水質 §30.7 = ダム完全混合放流+ため池同伴)
#   ./Run.sh [-u]
# 回帰(Log.txt + wq.csv)に加えて reference 非依存の検定を行う:
#   台帳の閉合(surf+dam+rs = 初期質量、to_dam − rel_dam = mass_dam)と
#   一様濃度 100 mg/L の端到端保存(最終 C 場)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列。
                       # wq.csv の第4列 in_map_g はこのケースでは恒等 0)
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

echo "Check_damwq closure: result/wq.csv"
python3 Check_damwq.py closure result/wq.csv || exit 1
echo "Check_damwq uniform: result"
python3 Check_damwq.py uniform result || exit 1

echo "=== damwq verification PASS ==="
