#!/bin/bash
# pump: MPI 実行 + 回帰テスト + 解析検定(井戸揚水の線形水位低下)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)。そのあと Check_pump.py
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=6
../Scripts/Run_case.sh mpi "$@" || exit 1
echo ""
python3 ./Check_pump.py result Screen.log || exit 1
