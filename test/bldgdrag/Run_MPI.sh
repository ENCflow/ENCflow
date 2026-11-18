#!/bin/bash
# bldgdrag: MPI 実行(N ランク)+ 検定
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt
for c in shallow deep dense; do
    python3 "$sdir/make_init.py" gv $c > gv_$c.txt
    python3 "$sdir/make_init.py" bb $c > bb_$c.txt
done

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
: > Screen.log
for c in shallow deep dense; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_bldgdrag.py"
