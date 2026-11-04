#!/bin/bash
# gwsect: 逐次実行 + 回帰テスト(断面形 σ のセルでの水の受け渡しの体積。§26.2)
#   ./Run.sh [-u]
# param.txt(σ の河道 + 河道幅、湧出 + 水質)の Log.txt・wq.csv を reference と
# 比較したあと、reference 非依存の検定を行う:
#   param.txt         総水量の保存・雨の総量との一致・濃度 1 mg/L・水質の台帳
#   param_nowidth.txt 河道幅なし(σ がセル全幅): 同じ 4 つ
#   param_gwc.txt     管路層の流入・噴出・吐口: 同じ 4 つ
#   param_snow.txt    融雪: 総水量(地表 + 積雪)の保存(開始時から)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export SKIPCOLS=6      # 検査対象外とする列番号(Log の Runge 列)
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

AREA=9600              # 有効セルの総面積 (m2) = 12 × 8 セル × 100 m2
python3 Check_gwsect.py conserve result || exit 1
python3 Check_gwsect.py rain result $AREA || exit 1
python3 Check_gwsect.py conc result 6 || exit 1
python3 Check_gwsect.py ledger result || exit 1

rm -rf result_nowidth result_gwc result_snow
./encflow param_nowidth.txt > Screen_nowidth.log 2>&1 || { echo "ERROR: param_nowidth run failed" >&2; exit 1; }
python3 Check_gwsect.py conserve result_nowidth || exit 1
python3 Check_gwsect.py rain result_nowidth $AREA || exit 1
python3 Check_gwsect.py conc result_nowidth 6 || exit 1
python3 Check_gwsect.py ledger result_nowidth || exit 1

./encflow param_gwc.txt > Screen_gwc.log 2>&1 || { echo "ERROR: param_gwc run failed" >&2; exit 1; }
python3 Check_gwsect.py conserve result_gwc || exit 1
python3 Check_gwsect.py rain result_gwc $AREA || exit 1
python3 Check_gwsect.py conc result_gwc 4 || exit 1
python3 Check_gwsect.py ledger result_gwc || exit 1

./encflow param_snow.txt > Screen_snow.log 2>&1 || { echo "ERROR: param_snow run failed" >&2; exit 1; }
python3 Check_gwsect.py conserve result_snow 0 || exit 1

echo "=== gwsect verification PASS ==="
