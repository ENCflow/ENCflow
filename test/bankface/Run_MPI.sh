#!/bin/bash
# bankface: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# state.dat は gather → rank0 書きのためランク数不変(バイト一致)のはず

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_thin.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_bankface.py" save 10.0 || rc=1
python3 "$sdir/Check_bankface.py" save_thin 0.0005 || rc=1
for c in save save_thin; do
    if [ -d ${c}_serial ]; then
        if cmp -s $c/state.dat ${c}_serial/state.dat; then
            echo "=== $c/state.dat is bit-identical to the serial result (${c}_serial) ==="
        else
            echo "MISMATCH: $c/state.dat != ${c}_serial/state.dat" >&2
            rc=1
        fi
    fi
done
exit $rc
