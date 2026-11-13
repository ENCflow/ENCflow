#!/bin/bash
# driftwood: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# state.dat / driftwood.dat は gather → rank0 書きのためランク数不変
# (バイト一致)のはず

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

rc=0
compare_serial() {
    local sdir_saved=$1 label=$2
    if [ -d ${sdir_saved}_serial ]; then
        for f in state.dat driftwood.dat; do
            if cmp -s $sdir_saved/$f ${sdir_saved}_serial/$f; then
                echo "=== $label: $f は逐次結果とビット一致 ==="
            else
                echo "警告: $sdir_saved/$f が逐次ビルドと不一致(-Ofast の fast-math" >&2
                echo "      ビルド間差の可能性。ビット検証は -O2 厳密数学で行うこと — §28.3)" >&2
            fi
        done
    fi
}

export ENCFLOW_EXPECT_NP="$NP"

# 構成1: 土石流+流木(侵食連行)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_driftwood.py" save || rc=1
compare_serial save "構成1"

# 構成2: 洪水氾濫での流木(水理的流失)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_flood.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_driftwood.py" save_flood || rc=1
compare_serial save_flood "構成2"

# 構成5: 構造物での捕捉と集積、集積の抵抗(fn_dwtrap。集積流木 s%wj のハロ交換を通る)
python3 "$sdir/make_jam.py" z > jam_z.txt
python3 "$sdir/make_jam.py" h > jam_h.txt
python3 "$sdir/make_jam.py" stock > jam_stock.txt
python3 "$sdir/make_jam.py" trap 1.0 > jam_trap_1.txt
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_jam.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_woodjam.py" jam result_jam save_jam || rc=1
compare_serial save_jam "構成5"

# 構成6a: カルバートの流入口の集積流木と流量則の損失(culv_jam。取水セル群 3 セルの実材積を
#   帯をまたいで集める。np = 2・4 では 3 セルが 2 つのランクに分かれる)
python3 "$sdir/make_jam.py" cz > jam_cz.txt
python3 "$sdir/make_jam.py" ch > jam_ch.txt
python3 "$sdir/make_jam.py" cstock3 > jam_cstock3.txt
python3 "$sdir/make_jam.py" cstage > jam_cstage.txt
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_jamculv3.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_woodjam.py" culv result_jamculv3 0.06 both || rc=1
compare_serial save_jamculv3 "構成6a"

# 構成6h: 本流の水の一部を引くカルバートの流入口の捕捉(取水セル群の 4 セルは行 3〜6。
#   np = 2・4 では 2 つのランクに分かれ、各ランクが自帯のセルの「引いた水の割合」を捕捉する)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_jamculvshare.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_woodjam.py" share result_jamculvshare || rc=1
compare_serial save_jamculvshare "構成6h"

exit $rc
