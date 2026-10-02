#!/bin/bash
# sewer_wq: 逐次実行 + 回帰テスト(下水噴出の衛生リスク = 水質×管路層)
#   ./Run.sh [-u]
# 水収支(Log.txt)に加えて物質収支(wq.csv。in_gwc/to_gwc の連携列)
# も比較対象にする
export FILES="Log.txt wq.csv"
export ULP=0
# 本ケースは release(-Ofast -march=native -flto)の同一ビナリ以外との
# ULP=0 比較が成立しない(Runge サブステップの閾値敏感性がビルド差を
# 相対 ~5e-6 に増幅。developer.md §10、2026-10-02 決定)。実装バグの検出は
# -Og -fcheck=all での逐次=np2 ビット一致(nightly の debug-fcheck 層)で
# 担い、release の回帰は RTOL で合否判定する(環境変数で上書き可。
# nightly の debug-fcheck 層は RTOL=0 を与えてビット一致を要求する)
export RTOL=${RTOL:-1e-5}
export SKIPCOLS=6      # 検査対象外とする列番号(Log の Runge 列。
                       # wq.csv の第4列 in_map_g はこのケースでは恒等 0)
exec ../Scripts/Run_case.sh serial "$@"
