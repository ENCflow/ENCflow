#!/bin/bash
# culvert: MPI 実行 + 回帰テスト(カルバート流量則の 3 レジーム通過)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4      # 検査対象外とする列番号(Runge 列)
exec ../Scripts/Run_case.sh mpi "$@"
