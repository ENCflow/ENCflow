#!/bin/bash
# rockfall: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" > zinit.txt

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_rockfall.py" save || rc=1
if [ -d save_serial ]; then
    if cmp -s save/state.dat save_serial/state.dat; then
        echo "=== state.dat is bit-identical to the serial result (save_serial) ==="
    else
        echo "MISMATCH: save/state.dat != save_serial/state.dat" >&2
        rc=1
    fi
fi
# 基岩版(rf_bedrock = 1)
python3 "$sdir/make_init.py" --sdzero
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_bed.txt | tee Screen_bed.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_rockfall.py" save_bed result_bed bed=save || rc=1
if [ -d save_bed_serial ]; then
    if cmp -s save_bed/state.dat save_bed_serial/state.dat; then
        echo "=== save_bed/state.dat is bit-identical to the serial result (save_bed_serial) ==="
    else
        echo "MISMATCH: save_bed/state.dat != save_bed_serial/state.dat" >&2
        rc=1
    fi
fi
# 窓版(rf_rc = 3 m)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_rc.txt | tee Screen_rc.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_rockfall.py" save_rc result_rc rc=3 || rc=1
if [ -d save_rc_serial ]; then
    if cmp -s save_rc/state.dat save_rc_serial/state.dat; then
        echo "=== save_rc/state.dat is bit-identical to the serial result (save_rc_serial) ==="
    else
        echo "MISMATCH: save_rc/state.dat != save_rc_serial/state.dat" >&2
        rc=1
    fi
fi
# 支え方式(rf_fface = 0。柱の崩落)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_face.txt | tee Screen_face.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_rockfall.py" save_face result_face rc=3 face=1 || rc=1
if [ -d save_face_serial ]; then
    if cmp -s save_face/state.dat save_face_serial/state.dat && cmp -s save_face/geomorph_rockfall.dat save_face_serial/geomorph_rockfall.dat; then
        echo "=== save_face/{state,geomorph_rockfall}.dat are bit-identical to the serial result (save_face_serial) ==="
    else
        echo "MISMATCH: save_face/* != save_face_serial/*" >&2
        rc=1
    fi
fi
# 張り出し版(rf_uc = 0.05 m。降雨 + 乾式侵食)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_uc.txt 2>&1 | tee Screen_uc.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_rockfall.py" save_uc result_uc rc=3 face=1 uc=Screen_uc.log hc=15 || rc=1
if [ -d save_uc_serial ]; then
    if cmp -s save_uc/state.dat save_uc_serial/state.dat && cmp -s save_uc/geomorph_rockfall.dat save_uc_serial/geomorph_rockfall.dat; then
        echo "=== save_uc/{state,geomorph_rockfall}.dat are bit-identical to the serial result (save_uc_serial) ==="
    else
        echo "MISMATCH: save_uc/* != save_uc_serial/*" >&2
        rc=1
    fi
fi
# 海セル版
python3 "$sdir/make_init.py" --sea
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_sea.txt 2>&1 | tee Screen_sea.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_rockfall.py" save_sea result_sea sea=Screen_sea.log || rc=1
if [ -d save_sea_serial ]; then
    if cmp -s save_sea/state.dat save_sea_serial/state.dat; then
        echo "=== save_sea/state.dat is bit-identical to the serial result (save_sea_serial) ==="
    else
        echo "MISMATCH: save_sea/state.dat != save_sea_serial/state.dat" >&2
        rc=1
    fi
fi
exit $rc
