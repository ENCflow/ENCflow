#!/bin/bash
# avalanche: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" > dbinit.txt || exit 1

export ENCFLOW_EXPECT_NP="$NP"
rc=0
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_avalanche.py" save || rc=1
if [ -d save_serial ]; then
    if cmp -s save/state.dat save_serial/state.dat; then
        echo "=== avalanche: state.dat は逐次結果とビット一致 ==="
    else
        echo "警告: save/state.dat が逐次ビルドと不一致(-Ofast の fast-math" >&2
        echo "      ビルド間差の可能性。ビット検証は -O2 厳密数学で — §28.3)" >&2
    fi
fi

# 構成 2〜5(一様な斜面)とリスタートの往復
python3 "$sdir/make_init.py" sheet || exit 1
set -o pipefail
for k in sh0 shm shh sht shm1 shm2; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$k.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_sheet.py" || rc=1
for f in state.dat swflow_enc.dat geomorph_debris.dat; do
    if cmp -s save_shm/$f save_shmr/$f; then
        echo "リスタート(構成 3。4 秒で保存して復元): $f は通しの計算とビット一致 : PASS"
    else
        echo "リスタート(構成 3): $f が通しの計算と不一致 : FAIL" >&2
        rc=1
    fi
done
for k in sh0 shm shh sht; do
    if [ -d save_${k}_serial ]; then
        nd=0
        for f in save_${k}_serial/*.dat; do
            cmp -s "$f" "save_$k/$(basename "$f")" || nd=$((nd + 1))
        done
        if [ $nd -eq 0 ]; then
            echo "=== avalanche $k: save は逐次結果とビット一致 ==="
        else
            echo "警告: save_$k が逐次ビルドと不一致($nd ファイル。-Ofast の fast-math ビルド間差の可能性 — §28.3)" >&2
        fi
    fi
done
exit $rc
