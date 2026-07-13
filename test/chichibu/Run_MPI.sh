#!/bin/bash
# 使い方:  ./Run_MPI.sh            2ランクで実行して reference と比較
#          ./Run_MPI.sh 4          4ランクで実行して比較
#          ./Run_MPI.sh -u         実行して reference を更新
#          ./Run_MPI.sh 4 -u      (引数の順序は自由)

../Scripts/Check_mode.sh mpi || exit 1

# --- 引数解析: 数値はランク数、-u は reference 更新 ---
NP=2
update=
for a in "$@"; do
    case $a in
        -u)         update=-u ;;
        *[!0-9]*|'') echo "usage: ./Run_MPI.sh [ランク数] [-u]" >&2; exit 2 ;;
        *)          NP=$a ;;
    esac
done

#export OMP_NUM_THREADS=6

# ハイブリッド実行時の注意(必要に応じて mpirun に追加):
#   OpenMPI: --bind-to none または --map-by l3cache:pe=$OMP_NUM_THREADS
#            ランク数 > 物理コア数のときは --oversubscribe
#   MPICH  : -bind-to numa など

# 実行(pipefail: tee でなく mpirun の終了コードを拾う)
set -o pipefail
time mpirun -np $NP ./a.out param.txt | tee Log.txt
rc=$?
set +o pipefail

if [ $rc -ne 0 ]; then
    echo "ERROR: 実行が異常終了しました (rc=$rc)。回帰テストは行いません。" >&2
    exit $rc
fi
echo ""

# 逐次版と MPI 版で丸め順序が異なるため、許容誤差付きで比較する
# (未設定のときだけ既定値を使う。RTOL=1e-8 ./Run_MPI.sh 4 で上書き可)
export RTOL=${RTOL:-1e-5}
files=Log.txt

# 回帰テスト
../Scripts/Compare_ref.sh $update $files
