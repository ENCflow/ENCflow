#!/bin/bash
# debris: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# state.dat は gather → rank0 書きのためランク数不変(バイト一致)のはず

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_debris.py" save || rc=1

if [ -d save_serial ]; then
    if cmp -s save/state.dat save_serial/state.dat; then
        echo "=== state.dat is bit-identical to the serial result (save_serial) ==="
    else
        echo "警告: save/state.dat が逐次ビルドと不一致(-Ofast の fast-math" >&2
        echo "      ビルド間差の可能性。ビット検証は -O2 厳密数学で行うこと — §28.3)" >&2
    fi
fi

# 構成2: 江頭則
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_eg.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_eg eg || rc=1
if [ -d save_eg_serial ]; then
    if cmp -s save_eg/state.dat save_eg_serial/state.dat; then
        echo "=== 江頭則: state.dat は逐次結果とビット一致 ==="
    else
        echo "警告: save_eg/state.dat が逐次ビルドと不一致(同上)" >&2
    fi
fi

# 構成3: 高橋・中川則
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_tk.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_tk eg || rc=1
if [ -d save_tk_serial ]; then
    if cmp -s save_tk/state.dat save_tk_serial/state.dat; then
        echo "=== 高橋・中川則: state.dat は逐次結果とビット一致 ==="
    else
        echo "警告: save_tk/state.dat が逐次ビルドと不一致(同上)" >&2
    fi
fi

# 構成4: 構成3 + 間隙水連行(f_dbwet=1)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_tkwet.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_tkwet wet || rc=1
if [ -d save_tkwet_serial ]; then
    if cmp -s save_tkwet/state.dat save_tkwet_serial/state.dat; then
        echo "=== 間隙水連行: state.dat は逐次結果とビット一致 ==="
    else
        echo "警告: save_tkwet/state.dat が逐次ビルドと不一致(同上)" >&2
    fi
fi

# 構成5: 構成1 + 掃流砂(土石流 E-D の後のハロ交換の回帰検定。developer.md §28.13)。
# 同じ MPI ビルドの np = 1 とのバイト一致を合否にする(ビルド内のランク数不変。
# 逐次ビルドとの比較は他の構成と同じく警告)
python3 "$sdir/make_fluv.py" > z_fluv.txt || exit 1
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_fluv.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_fluv fluv || rc=1
if [ "$NP" != 1 ]; then
    tmp=$(mktemp)
    sed "s/dir_save = 'save_fluv'/dir_save = 'save_fluv_np1'/" param_fluv.txt > "$tmp"
    rm -rf save_fluv_np1
    ENCFLOW_EXPECT_NP=1 mpirun -np 1 $MPIRUN_OPTS ./encflow_mpi "$tmp" > Screen_fluv_np1.log 2>&1
    rc1=$?
    rm -f "$tmp"
    if [ $rc1 -ne 0 ]; then
        echo "ERROR: np=1 run of param_fluv.txt failed (Screen_fluv_np1.log)" >&2
        rc=1
    elif cmp -s save_fluv/state.dat save_fluv_np1/state.dat; then
        echo "=== 掃流砂の併用: state.dat は np=$NP と np=1 でビット一致 ==="
    else
        echo "MISMATCH: save_fluv/state.dat が np=$NP と np=1 で不一致(ランク数依存)" >&2
        rc=1
    fi
fi
if [ -d save_fluv_serial ]; then
    if cmp -s save_fluv/state.dat save_fluv_serial/state.dat; then
        echo "=== 掃流砂の併用: state.dat は逐次結果とビット一致 ==="
    else
        echo "警告: save_fluv/state.dat が逐次ビルドと不一致(同上)" >&2
    fi
fi

# 構成6: 構成1 + 地下水計算と併用する間隙水(f_dbwet=2)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_gw.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_gw gw || rc=1
if [ -d save_gw_serial ]; then
    if cmp -s save_gw/state.dat save_gw_serial/state.dat; then
        echo "=== 地下水計算と併用する間隙水: state.dat は逐次結果とビット一致 ==="
    else
        echo "警告: save_gw/state.dat が逐次ビルドと不一致(同上)" >&2
    fi
fi

# 構成7: 斜面等流の平衡濃度(水路は 300 行。developer.md §28.15)
python3 "$sdir/make_eq.py" z > z_eq.txt || exit 1
python3 "$sdir/make_eq.py" h > h_eq.txt || exit 1
rm -rf result_eq save_eq
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_eq.txt > Screen_eq.log 2>&1 \
    || { echo "ERROR: param_eq.txt (np=$NP) run failed" >&2; exit 1; }
python3 "$sdir/Check_debris_eq.py" save_eq || rc=1
if [ -d save_eq_serial ]; then
    if cmp -s save_eq/state.dat save_eq_serial/state.dat; then
        echo "=== 斜面等流の平衡濃度: state.dat は逐次結果とビット一致 ==="
    else
        echo "警告: save_eq/state.dat が逐次ビルドと不一致(同上)" >&2
    fi
fi
exit $rc
