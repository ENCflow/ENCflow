#!/bin/bash
# gwwidth: 逐次実行 + 回帰テスト(地下⇔地表の水の受け渡しの体積換算。§26.1)
#   ./Run.sh [-u]
# param.txt(湧出 + 水質)の Log.txt・wq.csv を reference と比較したあと、
# reference 非依存の検定を行う:
#   param.txt        総水量の保存・雨の総量との一致・濃度 1 mg/L・水質の台帳
#   param_nowidth.txt 河道幅なしの対照: 総水量の保存と param.txt との最終総水量の一致
#   param_gwc.txt    管路層の流入・噴出・吐口: 総水量の保存・雨の総量との一致・濃度・台帳
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export SKIPCOLS=6      # 検査対象外とする列番号(Log の Runge 列)
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

AREA=9600              # 有効セルの総面積 (m2) = 12 × 8 セル × 100 m2
python3 Check_gwwidth.py conserve result || exit 1
python3 Check_gwwidth.py rain result $AREA || exit 1
python3 Check_gwwidth.py conc result 6 || exit 1
python3 Check_gwwidth.py ledger result || exit 1

rm -rf result_nowidth result_gwc
./encflow param_nowidth.txt > Screen_nowidth.log 2>&1 || { echo "ERROR: param_nowidth run failed" >&2; exit 1; }
python3 Check_gwwidth.py conserve result_nowidth || exit 1
python3 Check_gwwidth.py match result result_nowidth || exit 1

./encflow param_gwc.txt > Screen_gwc.log 2>&1 || { echo "ERROR: param_gwc run failed" >&2; exit 1; }
python3 Check_gwwidth.py conserve result_gwc || exit 1
python3 Check_gwwidth.py rain result_gwc $AREA || exit 1
python3 Check_gwwidth.py conc result_gwc 4 || exit 1
python3 Check_gwwidth.py ledger result_gwc || exit 1

echo "=== gwwidth verification PASS ==="
