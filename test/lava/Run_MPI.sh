#!/bin/bash
# lava: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# state.dat / lavaflow.dat は gather → rank0 書きのためランク数不変
# (バイト一致)のはず

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" > zinit.txt
python3 "$sdir/make_init.py" wall > zwall.txt

export ENCFLOW_EXPECT_NP="$NP"
rc=0

# 構成1: Huppert
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save huppert || rc=1
if [ -d save_serial ]; then
    for f in state.dat lavaflow.dat; do
        if cmp -s save/$f save_serial/$f; then
            echo "=== Huppert: $f は逐次結果とビット一致 ==="
        else
            echo "警告: save/$f が逐次ビルドと不一致(-Ofast の fast-math" >&2
            echo "      ビルド間差の可能性。ビット検証は -O2 厳密数学で — §28.3)" >&2
        fi
    done
fi

# 構成2: Bingham 停止・固化
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_ty.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_ty bingham || rc=1
if [ -d save_ty_serial ]; then
    for f in state.dat lavaflow.dat; do
        if cmp -s save_ty/$f save_ty_serial/$f; then
            echo "=== Bingham: $f は逐次結果とビット一致 ==="
        else
            echo "警告: save_ty/$f が逐次ビルドと不一致(同上)" >&2
        fi
    done
fi

# 構成4: 塑性ドームの静止形(等方性)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_dome.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_dome dome || rc=1
if [ -d save_dome_serial ]; then
    for f in state.dat lavaflow.dat; do
        if cmp -s save_dome/$f save_dome_serial/$f; then
            echo "=== ドーム: $f は逐次結果とビット一致 ==="
        else
            echo "警告: save_dome/$f が逐次ビルドと不一致(同上)" >&2
        fi
    done
fi

# 構成5: 壁の前の溶岩だまりの固化
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_wall.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_wall wall || rc=1
if [ -d save_wall_serial ]; then
    for f in state.dat lavaflow.dat; do
        if cmp -s save_wall/$f save_wall_serial/$f; then
            echo "=== 壁: $f は逐次結果とビット一致 ==="
        else
            echo "警告: save_wall/$f が逐次ビルドと不一致(同上)" >&2
        fi
    done
fi

# 構成6: 固化した溶岩の下の土層の埋没
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_bury.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_bury bury || rc=1
if [ -d save_bury_serial ]; then
    for f in state.dat lavaflow.dat; do
        if cmp -s save_bury/$f save_bury_serial/$f; then
            echo "=== 埋没: $f は逐次結果とビット一致 ==="
        else
            echo "警告: save_bury/$f が逐次ビルドと不一致(同上)" >&2
        fi
    done
fi
exit $rc
