#!/bin/bash
# volcano: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# state.dat は gather → rank0 書きのためランク数不変(バイト一致)のはず

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" db > dbinit.txt

export ENCFLOW_EXPECT_NP="$NP"
rc=0

# 構成1: Voellmy
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_volcano.py" save voellmy || rc=1
if [ -d save_serial ]; then
    if cmp -s save/state.dat save_serial/state.dat; then
        echo "=== Voellmy: state.dat は逐次結果とビット一致 ==="
    else
        echo "警告: save/state.dat が逐次ビルドと不一致(-Ofast の fast-math" >&2
        echo "      ビルド間差の可能性。ビット検証は -O2 厳密数学で — §28.3)" >&2
    fi
fi

# 構成2: τ_y 一定停止応力
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_ty.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_volcano.py" save_ty tauy || rc=1
if [ -d save_ty_serial ]; then
    if cmp -s save_ty/state.dat save_ty_serial/state.dat; then
        echo "=== τ_y: state.dat は逐次結果とビット一致 ==="
    else
        echo "警告: save_ty/state.dat が逐次ビルドと不一致(同上)" >&2
    fi
fi
exit $rc
