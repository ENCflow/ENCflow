#!/bin/bash
# saltledger: MPI 実行(N ランク)+ 検定(developer.md §140)
#   ./Run_MPI.sh [N](既定 2。N <= 4。どのケースも 8 行以上)
# 全ケースを N ランクで回して Check_cases.sh で判定し、1 ランク(同じ実行ファイル)でも回して、
# Log.txt・台帳 salt.csv・最後の塩水の分布(Hss・Hgs)をバイト比較する(台帳の行部分和の集約が
# ランク数によらないこと、底層重力流の受け側の上限と構造物の転送が帯の境で同じ値になること。
# sea2d は地盤高が x・y の両方で変わり、帯の境をまたいで流れの向きが変わる)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

cases="sea sea2d evap pump0 pump1 pump2 xfer exin exout gwsea"

tmp=$(mktemp -p .)
trap 'rm -f "$tmp"' EXIT
: > Screen.log
rc=0
for c in $cases; do
    echo "--- $c (np=$NP)"
    rm -rf result_$c result_${c}_np1
    export ENCFLOW_EXPECT_NP="$NP"
    if ! mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt >> Screen.log 2>&1; then
        echo "FAIL: $c の実行が異常終了した(Screen.log)" >&2
        exit 1
    fi
    sed "s/^  dir_result = 'result_$c'/  dir_result = 'result_${c}_np1'/" param_$c.txt > "$tmp"
    export ENCFLOW_EXPECT_NP=1
    mpirun -np 1 $MPIRUN_OPTS ./encflow_mpi "$tmp" >> Screen.log 2>&1 || exit 1
    for f in Log.txt salt.csv Hss9998.bil Hgs9998.bil; do
        [ -e "result_${c}_np1/$f" ] || continue          # Hss・Hgs は、その層を使うケースだけが出力する
        if cmp -s "result_$c/$f" "result_${c}_np1/$f"; then
            echo "  ok   result_$c/$f identical between np=$NP and np=1"
        else
            echo "FAIL: result_$c/$f differs between np=$NP and np=1" >&2
            rc=1
        fi
    done
done
echo ""

"$sdir/Check_cases.sh" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== saltledger MPI verification PASS ==="
else
    echo "=== saltledger MPI verification FAIL ===" >&2
fi
exit $rc
