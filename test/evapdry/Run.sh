#!/bin/bash
# evapdry: 逐次実行 + 回帰テスト(土の乾き具合で抑える地下水の段の蒸発散。§27.2)
#   ./Run.sh [-u]
# param.txt の Log.txt・evap.csv を reference と比較したあと、reference 非依存の
# 検定を行う:
#   param.txt    evap_hglim = 0.02 m: 地下の貯留が解析解(線形 → 指数減衰)に一致・
#                総水量 + 蒸発散 = 雨・水質の台帳
#   param_b.txt  evap_hglim = 0.1 m(雨の後の貯留より大きい): はじめから指数減衰
#   param_c.txt  evap_hglim なし: 速さ PET で線形に 0 まで(従来のあるだけ引く)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt evap.csv"
export ULP=0
export SKIPCOLS=6      # 検査対象外とする列番号(Log の Runge 列)
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

AREA=10000             # 有効セルの総面積 (m2) = 10 × 10 セル × 100 m2
PET=48                 # evap0 (mm/day)
python3 Check_evapdry.py decay result $PET 0.02 || exit 1
python3 Check_evapdry.py evbal result $AREA || exit 1
python3 Check_evapdry.py ledger result || exit 1

rm -rf result_b result_c
./encflow param_b.txt > Screen_b.log 2>&1 || { echo "ERROR: param_b run failed" >&2; exit 1; }
python3 Check_evapdry.py decay result_b $PET 0.1 || exit 1
python3 Check_evapdry.py evbal result_b $AREA || exit 1

./encflow param_c.txt > Screen_c.log 2>&1 || { echo "ERROR: param_c run failed" >&2; exit 1; }
python3 Check_evapdry.py decay result_c $PET 0 || exit 1
python3 Check_evapdry.py evbal result_c $AREA || exit 1

echo "=== evapdry verification PASS ==="
