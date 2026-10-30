#!/bin/bash
# conduit: 逐次実行 + 回帰テスト + 解析検定(模式実験 A: 一様・解析平衡)
#   ./Run.sh [-u]
# reference 比較(Log.txt)のあと Check_conduit.py A で貯留の平衡値・単調性・分布を解析値と比べる
export ULP=0
export SKIPCOLS=6      # 検査対象外とする列番号(Runge 列)
../Scripts/Run_case.sh serial "$@" || exit 1
echo ""
python3 ./Check_conduit.py A result || exit 1
