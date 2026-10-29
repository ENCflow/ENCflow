#!/bin/bash
# salt: 逐次実行 + 回帰テスト(模式実験 A: プール仕切り = ロック交換の終状態)と
#   模式実験 C1・C2(地表—地下の交換の淡塩配分 f_salt_exch)の解析検定
#   ./Run.sh [-u]
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Runge 列)
../Scripts/Run_case.sh serial "$@" || exit 1
exec ./Run_exch.sh
