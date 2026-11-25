#!/bin/bash
# damwq: 逐次実行 + 回帰テスト(水質 §30.7 = ダム完全混合放流+ため池同伴)
#   ./Run.sh [-u]
# 回帰(Log.txt + wq.csv)に加えて reference 非依存の検定を行う:
#   台帳の閉合(surf+dam+rs = 初期質量、to_dam − rel_dam = mass_dam)と
#   一様濃度 100 mg/L の端到端保存(最終 C 場)
# reference 比較は ULP=1(印字の最終桁 1 つ分まで)。Log.txt の S は丸め誤差の積み重ねで 0.05 から
# 5e-15 ほど増え、1:00 以降は印字の丸めの境目(0.05 + 5.000e-15)の上に乗る。reference を作った
# マシン(AVX-512 の Xeon)と CPU の違うマシン(CI の AMD のランナー)では、-march=native の生成
# コードの差(S で 6e-17)がこの境目をまたぎ、1:00 と 1:15 の行の最終桁が 1 つ変わる
# (developer.md §10 の damwq の項)。同じマシンでは環境変数で上書きしてビット比較できる:
#   ULP=0 ./Run.sh
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=${ULP:-1}   # 印字の最終桁 1 つ分まで(CPU の違うマシンの最終桁の差。上の注)
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列。
                       # wq.csv の第4列 in_map_g はこのケースでは恒等 0)
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

echo "Check_damwq closure: result/wq.csv"
python3 Check_damwq.py closure result/wq.csv || exit 1
echo "Check_damwq uniform: result"
python3 Check_damwq.py uniform result || exit 1

echo "=== damwq verification PASS ==="
