#!/bin/bash
# bankspill: 河岸のくぼみへのあふれ始め(逐次実行。濡れた・乾いたくぼみ × 時間刻み 6 s・1.5 s = 4 構成)
#   ./Run.sh
# 合否は Check_bankspill.py(まっすぐな区間の脇のくぼみは、隣の河道の水位が地盤に届く時に、時間刻みに
# よらずにあふれ始めること。屈曲の正面のくぼみは、上流のエネルギー水頭が地盤に届く前には入らないこと)。
# 屈曲の正面のくぼみのあふれ始めの水位の時間刻み依存と、あふれ始めの段は、判定せずに記録する(現行の限界。README)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_bankspill.py" z > bs_z.txt

set -o pipefail
: > Screen.log
for c in wet_dt6 wet_dt15 dry_dt6 dry_dt15; do
    ./encflow param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_bankspill.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== bankspill verification PASS ==="
else
    echo "=== bankspill verification FAIL ===" >&2
fi
exit $rc
