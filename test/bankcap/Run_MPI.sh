#!/bin/bash
# bankcap: MPI 実行(N ランク)+ 検定
#   ./Run_MPI.sh [N](既定 2)
# 河岸の列(行 8)と河道(行 9)の間が、np = 2・4 で帯の境界になる(頭打ちの判定がハロのセルを読む)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_bankcap.py" z > bc_z.txt
python3 "$sdir/make_bankcap.py" rn > bc_rn.txt
python3 "$sdir/make_bankcap.py" h wet > bc_h_wet.txt
python3 "$sdir/make_bankcap.py" h dry > bc_h_dry.txt

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
: > Screen.log
for c in wet2 wet1 dry2 dry1; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_bankcap.py" || rc=1
nf=0
ok=1
for f in result_dry1/H[0-9]*.txt result_dry1/V[0-9]*.txt result_dry1/Log.txt; do
    nf=$((nf + 1))
    if ! cmp -s "$f" "result_dry2/$(basename "$f")"; then
        echo "FAIL: dry bank: f_dry_head_cap = 2 differs from 1: $(basename "$f")" >&2
        ok=0
        rc=1
    fi
done
[ $ok -eq 1 ] && echo "=== dry bank: f_dry_head_cap = 2 is bit-identical to 1 ($nf files of H, V and Log.txt) ==="
if [ $rc -eq 0 ]; then
    echo "=== bankcap MPI verification PASS ==="
else
    echo "=== bankcap MPI verification FAIL ===" >&2
fi
exit $rc
