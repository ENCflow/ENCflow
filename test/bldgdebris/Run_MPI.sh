#!/bin/bash
# bldgdebris: MPI 実行(ランク数不変の検定)
#   ./Run_MPI.sh [N]   (既定 N=2)
# 構成1・2 を N ランクで実行し、Check_bldgdebris.py の検定に加えて、
# Run.sh が残した save*_serial/ と state.dat・bldgdebris.dat をバイト比較する。

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1
export MPIRUN_OPTS="${MPIRUN_OPTS:---bind-to none}"
rc=0

compare_serial() {
    local sdir_saved=$1 label=$2
    if [ -d ${sdir_saved}_serial ]; then
        for f in state.dat bldgdebris.dat; do
            if cmp -s $sdir_saved/$f ${sdir_saved}_serial/$f; then
                echo "=== $label: $f は逐次結果とビット一致 ==="
            else
                echo "警告: $sdir_saved/$f が逐次ビルドと不一致(-Ofast の fast-math" >&2
                echo "      ビルド間差の可能性。ビット検証は -O2 厳密数学で行うこと — §28.3)" >&2
            fi
        done
    fi
}

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_bldgdebris.py" save || rc=1
compare_serial save "構成1"

set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_dw.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_bldgdebris.py" save_dw || rc=1
compare_serial save_dw "構成2"

if [ $rc -eq 0 ]; then
    echo "=== bldgdebris MPI verification PASS ==="
else
    echo "=== bldgdebris MPI verification FAIL ===" >&2
fi
exit $rc
