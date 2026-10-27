#!/bin/bash
# dbrock: 土石流による岩盤侵食(f_rockinc の rock_kdb)の検定(逐次実行)
#   ./Run.sh
# 構成 db1・db1_dtg(DB1 自己被覆の解析解と更新間隔の不変)、db3_cmin・db3_vstop(DB3 濃度と
# 速度の門)、db2(DB2 閉じた箱の保存と台帳)、db5_*(DB5 リスタートと交互計算の連鎖)を
# Check_dbrock.py とバイト比較で検定し、db7_*(DB7 入力の誤り)が初期化で停止することを
# 確かめる。reference は持たない(解析解・保存則・バイト一致で判定)。実行後の save_*/ は
# save_*_serial/ にも複製する(Run_MPI.sh のバイト比較用)
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

cfgs="db1 db1_dtg db3_cmin db3_vstop db2"
saves="$cfgs db5_rt db5_f1 db5_d db5_f2"
set -o pipefail
for c in $cfgs; do
    ./encflow param_$c.txt | tee Screen_$c.log || exit 1
done
# DB5: db2 を 10 s で保存して再開(save_db5_rt)。出水 → 土石流 → 出水の連鎖は同じ save_db5 を
# 次の段が復元する(f_state_restore = 2)ので、各段の後の save を save_db5_<段>/ に写す
for c in db5_rt1 db5_rt2; do
    ./encflow param_$c.txt | tee Screen_$c.log || exit 1
done
for s in f1 d f2; do
    ./encflow param_db5_$s.txt | tee Screen_db5_$s.log || exit 1
    rm -rf save_db5_$s && cp -r save_db5 save_db5_$s
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_dbrock.py" db1 || rc=1
python3 "$sdir/Check_dbrock.py" db3 || rc=1
python3 "$sdir/Check_dbrock.py" db2 Screen_db2.log || rc=1
python3 "$sdir/Check_dbrock.py" db5 || rc=1
# DB5: 土石流の途中の save からの継続は通し計算とバイト一致
for f in state.dat geomorph_rockinc.dat; do
    if cmp -s save_db5_rt/$f save_db2/$f; then
        echo "(DB5-0) 継続: save_db5_rt/$f (restart at t = 10 s) is bit-identical to save_db2/$f : PASS"
    else
        echo "(DB5-0) 継続: save_db5_rt/$f != save_db2/$f : FAIL" >&2
        rc=1
    fi
done

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

for c in $saves; do
    rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial
done

if [ $rc -eq 0 ]; then
    echo "=== dbrock verification PASS ==="
else
    echo "=== dbrock verification FAIL ===" >&2
fi
exit $rc
