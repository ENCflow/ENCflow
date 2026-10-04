#!/bin/bash
# sewer_wq: MPI 実行 + 回帰テスト(下水噴出の衛生リスク)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0 を基本とするが(CLAUDE.md 検証規律)、
# 本ケースは release の逐次/MPI ビナリ差が Runge サブステップの閾値敏感性で
# 相対 ~5e-6 に増幅されるため RTOL で判定する(developer.md §10、
# 2026-10-02 決定。ビット一致は -Og -fcheck=all 層が RTOL=0 を与えて検査)
export FILES="Log.txt wq.csv"
export ULP=0
export RTOL=${RTOL:-1e-5}
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=6
exec ../Scripts/Run_case.sh mpi "$@"
