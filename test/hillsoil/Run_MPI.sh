#!/bin/bash
# hillsoil: MPI 実行(N ランク)+ 同じ検定 + 逐次とのバイト一致
#   ./Run_MPI.sh [N](既定 2)
# 倍率の分布は行ごとに並びがずれ(9 行周期)、負の倍率は最後の行の帯に置く(負のセルを持つ
# ランクだけが検出し、全ランク集約の判定で全ランクが停止すること)。C2 の渓流は南北向き
# (流れと掃流砂が j 方向の帯界面を横切る)。逐次の Run.sh の後に実行すると、save_*/ の
# state.dat を save_*_serial/ と比べる
export MPIRUN_OPTS=${MPIRUN_OPTS:---bind-to none}

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

cfgs="wthr_none wthr_map wthr_map_rt1 wthr_map_rt2 c2_w3 c2_w6 c2s c2s_rt1 c2s_rt2"
set -o pipefail
for c in $cfgs; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
rc=0
expect_stop() {
    if mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$1.txt > Screen_$1.log 2>&1; then
        echo "FAIL: $1 did not stop" >&2
        rc=1
    elif grep -q "$2" Screen_$1.log; then
        echo "PASS: $1 stops with \"$2\""
    else
        echo "FAIL: $1 stopped for another reason (see Screen_$1.log)" >&2
        rc=1
    fi
}
expect_stop wthr_bad "fn_wthr must be >= 0"
expect_stop wthr_nof "fn_wthr requires f_wthr=1"
echo ""

python3 "$sdir/Check_hillsoil.py" wthr || rc=1
python3 "$sdir/Check_hillsoil.py" c2 || rc=1
for d in wthr_map c2s; do
    if cmp -s save_$d/state.dat save_${d}_rt/state.dat; then
        echo "PASS: restart continuation matches the straight run ($d): state.dat"
    else
        echo "FAIL: restart continuation differs from the straight run ($d): state.dat" >&2
        rc=1
    fi
done

for d in save_wthr_none save_wthr_map save_c2_w3 save_c2_w6; do
    if [ -d ${d}_serial ]; then
        if cmp -s $d/state.dat ${d}_serial/state.dat; then
            echo "=== $d/state.dat is bit-identical to the serial result ==="
        else
            echo "MISMATCH: $d/state.dat != ${d}_serial/state.dat" >&2
            rc=1
        fi
    fi
done

if [ $rc -eq 0 ]; then
    echo "=== hillsoil MPI verification PASS ==="
else
    echo "=== hillsoil MPI verification FAIL ===" >&2
fi
exit $rc
