#!/bin/bash
# chichibu: 逐次実行 + 回帰テスト
#   ./Run.sh [-u]
#
# 使い方:  ./Run.sh        実行して reference と比較(なければ作成)
#          ./Run.sh -u     実行して reference を更新

# --- ケース固有の設定(必要に応じて) ---
#export PARAM=param.txt
#export FILES="Log.txt"
#export RTOL=1e-5

#export OMP_NUM_THREADS=24
#export OMP_PROC_BIND=close
#export OMP_PLACES=cores

exec ../Scripts/Run_case.sh serial "$@"
