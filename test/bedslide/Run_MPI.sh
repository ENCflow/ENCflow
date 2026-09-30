#!/bin/bash
# bedslide: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# state.dat / geomorph_bedslide.dat は gather → rank0 書きのため
# ランク数不変(バイト一致)のはず(-O2 厳密数学ビルドで。§28.5)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

for k in zbench dbbench zrot dbrot z db; do
    python3 "$sdir/make_init.py" $k > $k.txt || exit 1
done

export ENCFLOW_EXPECT_NP="$NP"
rc=0
cmp_save() {   # $1 = save dir(逐次は $1_serial)
    if [ -d "$1_serial" ]; then
        if cmp -s "$1/state.dat" "$1_serial/state.dat" \
           && cmp -s "$1/geomorph_bedslide.dat" "$1_serial/geomorph_bedslide.dat"; then
            echo "=== $1: state.dat / geomorph_bedslide.dat は逐次結果とビット一致 ==="
        else
            echo "警告: $1 が逐次ビルドと不一致(-Ofast の fast-math ビルド間差の可能性。" >&2
            echo "      ビット検証は -O2 厳密数学で — §28.5)" >&2
        fi
    fi
}

set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_bench.txt | tee Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_rot.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_bedslide.py" bench || rc=1
cmp_save save_bench
cmp_save save_rot

set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen_tsunami.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_bedslide.py" tsunami || rc=1
cmp_save save
exit $rc
