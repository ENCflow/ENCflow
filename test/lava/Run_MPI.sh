#!/bin/bash
# lava: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# state.dat / lavaflow.dat(温度モードは lavaflow_temp.dat も)は gather → rank0
# 書きのためランク数不変(バイト一致)のはず

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" > zinit.txt
python3 "$sdir/make_init.py" wall > zwall.txt
python3 "$sdir/make_init.py" cool > cool_cells.txt
python3 "$sdir/make_init.py" run > zrun.txt
python3 "$sdir/make_init.py" runnz > wrk_zrunnz.txt
python3 "$sdir/make_init.py" x0 > wrk_zx0.txt
python3 "$sdir/make_init.py" x45 > wrk_zx45.txt
for k in x0c1 x0c2 x45c1 x45c2 ch0w1c ch0w3c ch45w1c ch45w3c; do
    python3 "$sdir/make_init.py" $k > wrk_$k.txt
done
for k in ch0w1 ch0w3 ch45w1 ch45w3; do
    python3 "$sdir/make_init.py" $k > wrk_z$k.txt
done

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

# 構成4': 構成4 と同じ入力を流動の 4 近傍(lv_diagratio = 0)で計算する対照(既定は 8 近傍の 9 点。§96)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_dome4.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_dome4 dome || rc=1
if [ -d save_dome4_serial ]; then
    for f in state.dat lavaflow.dat; do
        if cmp -s save_dome4/$f save_dome4_serial/$f; then
            echo "=== ドーム(4 近傍の対照): $f は逐次結果とビット一致 ==="
        else
            echo "警告: save_dome4/$f が逐次ビルドと不一致(同上)" >&2
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

# 構成7: 静止した層の冷却(温度モード)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_cool.txt | tee Screen_cool.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_cool cool Screen_cool.log || rc=1
if [ -d save_cool_serial ]; then
    for f in state.dat lavaflow.dat lavaflow_temp.dat; do
        if cmp -s save_cool/$f save_cool_serial/$f; then
            echo "=== 冷却: $f は逐次結果とビット一致 ==="
        else
            echo "警告: save_cool/$f が逐次ビルドと不一致(同上)" >&2
        fi
    done
fi

# 構成8: 熱の移流(温度モード・冷却なし)と等温の計算 8'
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_adv.txt | tee Screen_adv.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_adv0.txt | tee Screen_adv0.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_adv adv Screen_adv.log || rc=1
same=1
for f in state.dat lavaflow.dat; do
    cmp -s save_adv/$f save_adv0/$f || same=0
done
if [ $same -eq 1 ]; then
    echo "=== 構成8': 温度モード(β = 0・冷却なし)の流れが等温の計算とバイト一致 ==="
else
    echo "FAIL: 構成8 の lavaflow.dat / state.dat が等温の計算 8' と異なる" >&2
    rc=1
fi
if [ -d save_adv_serial ]; then
    for f in state.dat lavaflow.dat lavaflow_temp.dat; do
        if cmp -s save_adv/$f save_adv_serial/$f; then
            echo "=== 移流: $f は逐次結果とビット一致 ==="
        else
            echo "警告: save_adv/$f が逐次ビルドと不一致(同上)" >&2
        fi
    done
fi

# 構成9: 冷えて止まる流れ(温度モード Q・4Q と等温の対照 Q・4Q。同じ体積)
set -o pipefail
for c in run run4 runi runi4; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_run run Screen_run.log Screen_run4.log || rc=1
if [ -d save_run_serial ]; then
    for c in run run4; do
        for f in state.dat lavaflow.dat lavaflow_temp.dat; do
            if cmp -s save_$c/$f save_${c}_serial/$f; then
                echo "=== 冷えて止まる流れ($c): $f は逐次結果とビット一致 ==="
            else
                echo "警告: save_$c/$f が逐次ビルドと不一致(同上)" >&2
            fi
        done
    done
fi

# 構成9n: 構成9 の温度モードの 2 本を ±1 mm の乱れのある斜面で(§94 の訂正)
set -o pipefail
for c in runnz run4nz; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" - runnz Screen_runnz.log Screen_run4nz.log || rc=1
if [ -d save_runnz_serial ]; then
    for c in runnz run4nz; do
        for f in state.dat lavaflow.dat lavaflow_temp.dat; do
            if cmp -s save_$c/$f save_${c}_serial/$f; then
                echo "=== 乱れのある冷えて止まる流れ($c): $f は逐次結果とビット一致 ==="
            else
                echo "警告: save_$c/$f が逐次ビルドと不一致(同上)" >&2
            fi
        done
    done
fi

# 構成10: 熱の横断の数値拡散(0°・45° のシート流、1 次風上と MUSCL。§94)
set -o pipefail
for c in x0 x0m x45 x45m; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" - xdiff || rc=1
if [ -d save_x0_serial ]; then
    for c in x0 x0m x45 x45m; do
        for f in state.dat lavaflow.dat lavaflow_temp.dat; do
            if cmp -s save_$c/$f save_${c}_serial/$f; then
                echo "=== 熱の横断の数値拡散($c): $f は逐次結果とビット一致 ==="
            else
                echo "警告: save_$c/$f が逐次ビルドと不一致(同上)" >&2
            fi
        done
    done
fi

# 構成10d: 構成10 を流動の 8 近傍の 9 点(d = 1/3)で(§96)
set -o pipefail
for c in x0d x0dm x45d x45dm; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" - xdiff8 || rc=1
if [ -d save_x0d_serial ]; then
    for c in x0d x0dm x45d x45dm; do
        for f in state.dat lavaflow.dat lavaflow_temp.dat; do
            if cmp -s save_$c/$f save_${c}_serial/$f; then
                echo "=== 熱の横断の数値拡散 8 近傍($c): $f は逐次結果とビット一致 ==="
            else
                echo "警告: save_$c/$f が逐次ビルドと不一致(同上)" >&2
            fi
        done
    done
fi

# 構成11: 谷の通水能の向きによる差(8 近傍の 9 点と塞がれた配分の振り替え。§96)
set -o pipefail
for c in ch0w1 ch45w1 ch0w3 ch45w3 ch45w3q; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" - chan || rc=1
if [ -d save_ch0w1_serial ]; then
    for c in ch0w1 ch45w1 ch0w3 ch45w3 ch45w3q; do
        for f in state.dat lavaflow.dat; do
            if cmp -s save_$c/$f save_${c}_serial/$f; then
                echo "=== 谷の通水能($c): $f は逐次結果とビット一致 ==="
            else
                echo "警告: save_$c/$f が逐次ビルドと不一致(同上)" >&2
            fi
        done
    done
fi
exit $rc
