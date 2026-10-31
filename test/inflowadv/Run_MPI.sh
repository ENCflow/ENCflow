#!/bin/bash
# inflowadv: MPI 実行(N ランク)+ 検定
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

for c in osc5 osc3 jet3 side steep; do
    python3 "$sdir/make_init.py" z $c > z_$c.txt
    python3 "$sdir/make_init.py" h $c > h_$c.txt
done

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
for c in osc5 osc3 jet3 side steep; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_inflowadv.py"
