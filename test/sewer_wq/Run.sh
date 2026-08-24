#!/bin/bash
# sewer_wq: 逐次実行 + 回帰テスト(下水噴出の衛生リスク = 水質×管路層)
#   ./Run.sh [-u]
# 水収支(Log.txt)に加えて物質収支(wq.csv。in_gwc/to_gwc の連携列)
# も比較対象にする
export FILES="Log.txt wq.csv"
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列。
                       # wq.csv の第4列 in_map_g はこのケースでは恒等 0)
exec ../Scripts/Run_case.sh serial "$@"
