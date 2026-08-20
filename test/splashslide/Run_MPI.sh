#!/bin/bash
# splashslide: MPI 実行(N ランク)+ 対照検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_terrain.py" || exit 1

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_c.txt | tee Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_l.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_contrast.py" || rc=1

for s in save_c save_l; do
    if [ -d ${s}_serial ]; then
        if cmp -s $s/state.dat ${s}_serial/state.dat; then
            echo "=== $s/state.dat is bit-identical to the serial result ==="
        else
            echo "MISMATCH: $s/state.dat != ${s}_serial/state.dat" >&2
            rc=1
        fi
    fi
done
exit $rc
