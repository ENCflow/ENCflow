#!/bin/bash
# splash: 逐次実行 + 回帰テスト(乾式斜面侵食 f_splash)
#   ./Run.sh [-u]
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Runge 列)
exec ../Scripts/Run_case.sh serial "$@"
