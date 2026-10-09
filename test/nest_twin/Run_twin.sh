#!/bin/bash
# nest_twin の実行本体(Run.sh / Run_MPI.sh から呼ぶ)
#   Run_twin.sh serial | mpi [N]
mode=$1; shift
NP=${1:-2}
cases="wave chichibu"
sdir=$(dirname "$(readlink -f "$0")")

"$sdir/../Scripts/Check_mode.sh" "$mode" || exit 1
if [ "$mode" = mpi ]; then
    make -s MODE=mpi twin_mpi links || exit 1
    run="mpirun -np $NP $MPIRUN_OPTS"
    sfx=_mpi
    export ENCFLOW_EXPECT_NP="$NP"
else
    make -s twin links || exit 1
    run=
    sfx=
fi

rm -rf result_* single_*
# 1) 単独実行(製品バイナリ encflow)
for c in $cases; do
    $run ./encflow$sfx param_$c.txt > Screen_single_$c.log 2>&1 || { echo "ERROR: single run $c failed"; exit 1; }
    mv result_$c single_$c
done
# 2) 交互実行(twin ドライバ。パラメータの並び順に select/update を回す)
$run ./twin$sfx $(for c in $cases; do echo param_$c.txt; done) > Screen_twin.log 2>&1 \
    || { echo "ERROR: twin run failed"; exit 1; }
# 3) 比較(結果ディレクトリの全ファイル。Log.txt を含む)
fail=0
for c in $cases; do
    if diff -rq single_$c result_$c > /dev/null; then
        echo "nest_twin $c: IDENTICAL ($(ls result_$c | wc -l) files)"
    else
        echo "nest_twin $c: DIFFER"
        diff -rq single_$c result_$c | head
        fail=1
    fi
done
if [ $fail -eq 0 ]; then
    echo "nest_twin ($mode): verification PASS"
else
    echo "nest_twin ($mode): verification FAIL"
    exit 1
fi
