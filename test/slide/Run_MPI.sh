#!/bin/bash
# slide: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# 構成1(release)・構成2(f_slide)・構成3(f_slide=2 診断)・構成4(保持水の授受と初期地下水。
# 飽和・乾燥の 2 つ)・構成5〜8(斜面安定判定の選択子。make_fs.py の 18 ケース)を実行・比較する

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

# 構成4(param_wet.txt): 飽和した土層の瞬時流動化と保持水の授受(developer.md §28.17)と、
# 同じ設定の乾いた土層(gw_sat0 = 0。設定は param_wet.txt から作る)
sed -e "s/gw_sat0 = 1.0 /gw_sat0 = 0.0 /" -e "s/'save_wet'/'save_wetdry'/" \
    -e "s/'result_wet'/'result_wetdry'/" param_wet.txt > param_wetdry.txt
for c in wet wetdry; do
    if [ $c = wet ]; then sat0=1.0; else sat0=0.0; fi
    set -o pipefail
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee Screen_$c.log || exit 1
    set +o pipefail
    cat Screen_$c.log >> Screen.log
    echo ""
    python3 "$sdir/Check_slide.py" save_$c wet Screen_$c.log $sat0 || rc=1
    if [ -d save_${c}_serial ]; then
        if cmp -s save_$c/state.dat save_${c}_serial/state.dat; then
            echo "=== $c: state.dat is bit-identical to the serial result ==="
        else
            echo "警告: save_$c/state.dat が逐次ビルドと不一致(同上)" >&2
        fi
    fi
done

# 構成5〜8: 斜面安定判定の選択子(developer.md §28.19)。state.dat と、安全率の出力 Fs0001.bil
# (判定だけのケースは state.dat が動かないので、出力そのもののランク数不変を見る)を逐次と比べる
python3 "$sdir/make_fs.py" || exit 1
nsame=0
ndiff=0
for c in $(python3 "$sdir/make_fs.py" list); do
    echo "--- $c (np=$NP)"
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi p_$c.txt > Screen_fs.log 2>&1 || { tail -5 Screen_fs.log; exit 1; }
    cat Screen_fs.log >> Screen.log
    if [ -d save_${c}_serial ]; then
        if cmp -s save_$c/state.dat save_${c}_serial/state.dat \
           && cmp -s result_$c/Fs0001.bil save_${c}_serial/Fs0001.bil; then
            nsame=$((nsame + 1))
        else
            ndiff=$((ndiff + 1))
            echo "警告: $c の state.dat か Fs0001.bil が逐次ビルドと不一致(同上)" >&2
        fi
    fi
done
echo ""
for c in fs_u0 fs_u1 fs_g0 fs_g1 fs_l0 fs_l1 fs_lq1 fs_le1 fs_d2; do
    python3 "$sdir/Check_slide_fs.py" fs $c || rc=1
done
python3 "$sdir/Check_slide_fs.py" pair fs_u1 fs_u0 same || rc=1
python3 "$sdir/Check_slide_fs.py" pair fs_g1 fs_g0 differ || rc=1
python3 "$sdir/Check_slide_fs.py" pair fs_l1 fs_l0 differ || rc=1
python3 "$sdir/Check_slide_fs.py" twin fs_m1 fs_m0 || rc=1
python3 "$sdir/Check_slide_fs.py" ledger fs_gdyn || rc=1
python3 "$sdir/Check_slide_fs.py" dmax1 fs_d1 || rc=1
python3 "$sdir/Check_slide_fs.py" wet fs_w1 fs_w0 fs_w2 || rc=1
python3 "$sdir/Check_slide_fs.py" noflow fs_n1 fs_n0 || rc=1
if [ -d save_fs_u0_serial ]; then
    echo "=== 構成5〜8: state.dat と Fs0001.bil は逐次結果とビット一致 $nsame ケース、不一致 $ndiff ケース ==="
fi

exit $rc
