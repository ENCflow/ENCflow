#!/bin/bash
# dambreak: MPI 実行 + 回帰テスト + Stoker 解析解との比較
#   ./Run_MPI.sh [N] [-u]      N = ランク数(既定 2)

export MPIRUN_OPTS="--bind-to none"   # Open MPI ではこれが無いと全スレッドが1CPUに乗る
export SKIPCOLS=4      # 検査対象外とする列番号(Runge 列)

../Scripts/Run_case.sh mpi "$@"
rc=$?
echo ""
python3 ./Check_stoker.py || true
exit $rc
