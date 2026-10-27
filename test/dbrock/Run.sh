#!/bin/bash
# dbrock: 土石流による岩盤侵食(f_rockinc の rock_kdb)の検定(逐次実行)
#   ./Run.sh
# 構成 db1・db1_dtg(DB1 自己被覆の解析解と更新間隔の不変)、db3_cmin・db3_vstop(DB3 濃度と
# 速度の門)、db2(DB2 閉じた箱の保存と台帳)を Check_dbrock.py で検定し、db7_*(DB7 入力の
# 誤り)が初期化で停止することを確かめる。reference は持たない(解析解・保存則・バイト一致で
# 判定)。実行後の save_*/ は save_*_serial/ にも複製する(Run_MPI.sh のバイト比較用)
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

cfgs="db1 db1_dtg db3_cmin db3_vstop db2"
set -o pipefail
for c in $cfgs; do
    ./encflow param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_dbrock.py" db1 || rc=1
python3 "$sdir/Check_dbrock.py" db3 || rc=1
python3 "$sdir/Check_dbrock.py" db2 Screen_db2.log || rc=1

# DB7: 入力の誤りは初期化で停止する(構成名と期待する表示の組)
while read -r c msg; do
    if ./encflow param_$c.txt > Screen_$c.log 2>&1; then
        echo "FAIL: $c did not stop" >&2
        rc=1
    elif grep -qF -- "$msg" Screen_$c.log; then
        echo "PASS: $c stops with \"$msg\""
    else
        echo "FAIL: $c stopped for another reason (see Screen_$c.log)" >&2
        rc=1
    fi
done << 'LIST'
db7_kp f_rockinc uses only the debris-flow term
db7_tauc requires rock_taucdb > 0
db7_cmin requires db_cmin in (0, C*)
db7_nodb rock_kdb > 0 requires f_debris=1
db7_none requires f_fluvial=1 (bed load carries the plucked rock) or f_debris=1
LIST

for c in $cfgs; do
    rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial
done

if [ $rc -eq 0 ]; then
    echo "=== dbrock verification PASS ==="
else
    echo "=== dbrock verification FAIL ===" >&2
fi
exit $rc
