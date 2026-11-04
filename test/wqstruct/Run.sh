#!/bin/bash
# wqstruct: 逐次実行 + 回帰テスト(構造物・取水が運ぶ水質の質量。§30.10)
#   ./Run.sh [-u]
# param.txt(地表の構造物・取水)の Log.txt・wq.csv を reference と比較したあと、
# reference 非依存の検定を行う:
#   param.txt     地表の濃度 1 mg/L・ため池の濃度・水質の台帳の閉合・
#                 out_intake_g = 域外へ出た水の体積 × 1 g/m3・構造物が水を動かしたこと
#   param_gw.txt  井戸揚水と管路から汲むポンプ: 地表・地下の濃度・台帳・
#                 out_intake_g(井戸)・in_gwc_g(管路から汲んだ水)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列)
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

AREA=28900             # 有効セルの総面積 (m2) = 17 × 17 セル × 100 m2
for k in 1 2; do
    python3 Check_wqstruct.py conc result $k || exit 1
done
python3 Check_wqstruct.py tank result 2 3 11 || exit 1
python3 Check_wqstruct.py ledger result || exit 1
python3 Check_wqstruct.py intake result $AREA 1e-6 || exit 1
python3 Check_wqstruct.py active result 2 || exit 1

rm -rf result_gw
./encflow param_gw.txt > Screen_gw.log 2>&1 || { echo "ERROR: param_gw run failed" >&2; exit 1; }
for k in 1 2; do
    python3 Check_wqstruct.py conc result_gw $k || exit 1
    python3 Check_wqstruct.py gwconc result_gw $k || exit 1
done
python3 Check_wqstruct.py ledger result_gw || exit 1
python3 Check_wqstruct.py intake result_gw $AREA 1e-3 || exit 1
python3 Check_wqstruct.py gwc result_gw 2 || exit 1

echo "=== wqstruct verification PASS ==="
