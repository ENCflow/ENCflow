#!/bin/bash
# slide: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# 構成1(release)と構成2(f_slide)の両方を実行・比較する

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_dbinit.py" > dbinit.txt || exit 1

export ENCFLOW_EXPECT_NP="$NP"
rc=0

set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_slide.py" save release || rc=1
if [ -d save_serial ]; then
    if cmp -s save/state.dat save_serial/state.dat; then
        echo "=== release: state.dat is bit-identical to the serial result ==="
    else
        echo "MISMATCH: save/state.dat != save_serial/state.dat" >&2
        rc=1
    fi
fi

set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_fs.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_slide.py" save_fs fslide || rc=1
if [ -d save_fs_serial ]; then
    if cmp -s save_fs/state.dat save_fs_serial/state.dat; then
        echo "=== fslide: state.dat is bit-identical to the serial result ==="
    else
        echo "MISMATCH: save_fs/state.dat != save_fs_serial/state.dat" >&2
        rc=1
    fi
fi

exit $rc
