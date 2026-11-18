#!/bin/bash
# bankspill: MPI 実行(N ランク)+ 検定
#   ./Run_MPI.sh [N](既定 2)
# 屈曲の上流の河道(行 4)と下流の河道(行 5)の間が、np = 2 で帯の境界になる(屈曲の斜めの辺と、
# 屈曲の正面のくぼみから下流の河道へ出る辺が、帯の境界をまたぐ)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_bankspill.py" z > bs_z.txt

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
: > Screen.log
for c in wet_dt6 wet_dt15 dry_dt6 dry_dt15 c3_wet_dt6 c3_wet_dt15 c3_dry_dt6 c3_dry_dt15; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_bankspill.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== bankspill MPI verification PASS ==="
else
    echo "=== bankspill MPI verification FAIL ===" >&2
fi
exit $rc
