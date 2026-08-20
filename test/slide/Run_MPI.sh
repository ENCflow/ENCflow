#!/bin/bash
# slide: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# 構成1(release)・構成2(f_slide)・構成3(f_slide=2 診断)を実行・比較する

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
        echo "警告: save/state.dat が逐次ビルドと不一致(-Ofast の fast-math" >&2
        echo "      ビルド間差の可能性。ビット検証は -O2 厳密数学で行うこと — §28.3)" >&2
    fi
fi

set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_fs.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_slide.py" save_fs fslide result || rc=1
if [ -d save_fs_serial ]; then
    if cmp -s save_fs/state.dat save_fs_serial/state.dat; then
        echo "=== fslide: state.dat is bit-identical to the serial result ==="
    else
        echo "警告: save_fs/state.dat が逐次ビルドと不一致(同上)" >&2
    fi
    # 危険度出力(§28.9)は state.dat に入らない(save 対象外の統計)ため
    # 出力ファイル自体のランク数不変を確認する
    for f in Fs9999.txt D9999.txt F9999.txt; do
        if cmp -s result/$f save_fs_serial/$f; then
            echo "=== fslide: $f は逐次結果とビット一致 ==="
        else
            echo "警告: result/$f が逐次ビルドと不一致(同上)" >&2
        fi
    done
fi

# 構成3(param_fs2.txt): f_slide=2 判定のみ(Fs 危険度マップ)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_fs2.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_slide.py" save_fs2 fsdiag result_fs2 || rc=1
if [ -d save_fs2_serial ]; then
    if cmp -s save_fs2/state.dat save_fs2_serial/state.dat; then
        echo "=== fsdiag: state.dat is bit-identical to the serial result ==="
    else
        echo "警告: save_fs2/state.dat が逐次ビルドと不一致(同上)" >&2
    fi
    if cmp -s result_fs2/Fs9999.txt save_fs2_serial/Fs9999.txt; then
        echo "=== fsdiag: Fs9999.txt は逐次結果とビット一致 ==="
    else
        echo "警告: result_fs2/Fs9999.txt が逐次ビルドと不一致(同上)" >&2
    fi
fi

exit $rc
