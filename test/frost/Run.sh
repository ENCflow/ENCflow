#!/bin/bash
# frost: 逐次実行 + 回帰テスト + 解析検定(凍土による浸透抑制の線形低減)
#   ./Run.sh [-u]
# reference 比較(Log.txt)のあと Check_frost.py で貯留・低減係数・地下貯留の分布を解析値と比べる
export ULP=0
export SKIPCOLS=6      # 検査対象外とする列番号(Runge 列)
../Scripts/Run_case.sh serial "$@" || exit 1
echo ""
python3 ./Check_frost.py result || exit 1
