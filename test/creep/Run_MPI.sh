#!/bin/bash
# creep: MPI 実行(N ランク)+ 解析解比較 + 逐次結果とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# プローブ CSV は点集約方式によりランク数不変(ULP=0)なので、
# 逐次実行の result/ が存在すればバイト比較も行う。深さ依存クリープ(creep_hstar)の
# 4 構成は Check_hstar.py の検定と、Run.sh が残す save_hstar_*_serial との state.dat の
# バイト比較を行う

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")

../Scripts/Check_mode.sh mpi || exit 1

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
for c in thick thin lim bare; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_hstar_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_analytic.py" result/probes 1.0 || rc=1
python3 "$sdir/Check_analytic.py" result_hstar_thick/probes 1.0 || rc=1
for c in thick thin lim bare; do
    python3 "$sdir/Check_hstar.py" $c || rc=1
    if [ -d save_hstar_${c}_serial ]; then
        if cmp -s save_hstar_$c/state.dat save_hstar_${c}_serial/state.dat; then
            echo "=== hstar_$c: state.dat is bit-identical to the serial result ==="
        else
            echo "MISMATCH: save_hstar_$c/state.dat" >&2
            rc=1
        fi
    fi
done

if [ -d result_serial ]; then
    ok=1
    for f in result_serial/probes/probe*.csv; do
        cmp -s "$f" "result/probes/$(basename "$f")" || { echo "MISMATCH: $f" >&2; ok=0; }
    done
    if [ $ok -eq 1 ]; then
        echo "=== probe CSVs are bit-identical to the serial result (result_serial) ==="
    else
        rc=1
    fi
fi

exit $rc
