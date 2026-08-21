#!/bin/bash
# driftwood: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# state.dat / driftwood.dat は gather → rank0 書きのためランク数不変
# (バイト一致)のはず

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

rc=0
compare_serial() {
    local sdir_saved=$1 label=$2
    if [ -d ${sdir_saved}_serial ]; then
        for f in state.dat driftwood.dat; do
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

# 構成1: 土石流+流木(侵食連行)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_driftwood.py" save || rc=1
compare_serial save "構成1"

# 構成2: 洪水氾濫での流木(水理的流失)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_flood.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_driftwood.py" save_flood || rc=1
compare_serial save_flood "構成2"

exit $rc
