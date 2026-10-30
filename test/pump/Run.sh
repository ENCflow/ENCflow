#!/bin/bash
# pump: 逐次実行 + 回帰テスト + 解析検定(井戸揚水の線形水位低下)
#   ./Run.sh [-u]
# reference 比較(Log.txt)のあと Check_pump.py で貯留・地下貯留の分布・揚水量を解析値と比べる
export ULP=0
export SKIPCOLS=6      # 検査対象外とする列番号(Runge 列)
../Scripts/Run_case.sh serial "$@" || exit 1
echo ""
python3 ./Check_pump.py result Screen.log || exit 1
