#!/bin/bash
# wave: 逐次実行 + 回帰テスト
#   ./Run.sh [-u]
#
# 使い方:  ./Run.sh        実行して reference と比較(なければ作成)
#          ./Run.sh -u     実行して reference を更新

# --- ケース固有の設定(必要に応じて) ---
#export PARAM=param.txt
#export FILES="Log.txt"
export ULP=1.1      # 印字の最終桁を単位とした許容誤差

#export OMP_NUM_THREADS=24
#export OMP_PROC_BIND=close
#export OMP_PLACES=cores

export SKIPCOLS=4      # 検査対象外とする列番号

exec ../Scripts/Run_case.sh serial "$@"
