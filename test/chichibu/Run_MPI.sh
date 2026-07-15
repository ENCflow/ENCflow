#!/bin/bash
# chichibu: MPI 実行 + 回帰テスト
#   ./Run_MPI.sh [ランク数] [-u]
#   
# 使い方:  ./Run_MPI.sh            2ランクで実行して reference と比較
#          ./Run_MPI.sh 4          4ランクで実行して比較
#          ./Run_MPI.sh -u         実行して reference を更新
#          ./Run_MPI.sh 4 -u      (引数の順序は自由)

# --- ケース固有の設定(必要に応じて) ---
#export PARAM=param.txt
#export FILES="Log.txt"
#export RTOL=1e-8
export ULP=1      # 印字の最終桁を単位とした許容誤差
#export MPIRUN_OPTS="--oversubscribe"

#export OMP_NUM_THREADS=6
#export MPIRUN_OPTS="--map-by l3cache:pe=$OMP_NUM_THREADS --bind-to core"

exec ../Scripts/Run_case.sh mpi "$@"
