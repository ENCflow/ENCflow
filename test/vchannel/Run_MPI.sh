#!/bin/bash
# vchannel: MPI 実行(N ランク)+ 検定 + 逐次の出力とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" || exit 1

export ENCFLOW_EXPECT_NP="$NP"
rc=0
: > Screen.log
set -o pipefail
for p in p_*_r*.txt; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi "$p" | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_vchannel.py" || rc=1

# 逐次の出力(Run.sh が result_<構成>_<向き>_serial/ に複製する)との比較
nd=0
nc=0
for d in result_*_r*_serial; do
    [ -d "$d" ] || continue
    for f in "$d"/*.bil; do
        nc=$((nc + 1))
        cmp -s "$f" "${d%_serial}/$(basename "$f")" || nd=$((nd + 1))
    done
done
if [ $nc -gt 0 ]; then
    if [ $nd -eq 0 ]; then
        echo "=== vchannel: 分布出力 $nc 個は逐次結果とビット一致 ==="
    else
        echo "警告: 分布出力 $nd / $nc 個が逐次ビルドと不一致(-Ofast の fast-math" >&2
        echo "      ビルド間差の可能性。ビット検証は -O2 厳密数学で — §28.3)" >&2
    fi
fi

exit $rc
