#!/bin/bash
# rockfall: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" > zinit.txt

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_rockfall.py" save || rc=1
if [ -d save_serial ]; then
    if cmp -s save/state.dat save_serial/state.dat; then
        echo "=== state.dat is bit-identical to the serial result (save_serial) ==="
    else
        echo "MISMATCH: save/state.dat != save_serial/state.dat" >&2
        rc=1
    fi
fi
# 窓版(rf_rc = 3 m)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_rc.txt | tee Screen_rc.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_rockfall.py" save_rc result_rc rc=3 || rc=1
if [ -d save_rc_serial ]; then
    if cmp -s save_rc/state.dat save_rc_serial/state.dat; then
        echo "=== save_rc/state.dat is bit-identical to the serial result (save_rc_serial) ==="
    else
        echo "MISMATCH: save_rc/state.dat != save_rc_serial/state.dat" >&2
        rc=1
    fi
fi
exit $rc
