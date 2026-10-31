#!/bin/bash
# uniflow: MPI 実行(N ランク)+ 検定
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

for W in 1 5; do
    python3 "$sdir/make_init.py" z $W > zinit_w$W.txt
    python3 "$sdir/make_init.py" h $W > hinit_w$W.txt
done
python3 "$sdir/make_init.py" z 1 sc > zinit_w1_sc.txt
python3 "$sdir/make_init.py" h 1 sc > hinit_w1_sc.txt

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
for c in w1_off w1_on w5_off w5_on w1_sc w1_on3 w5_on3; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_uniflow.py"
