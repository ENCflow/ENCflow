#!/bin/bash
# frost: 逐次実行 + 回帰テスト(凍土による浸透抑制の線形低減)
#   ./Run.sh [-u]
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Runge 列)
exec ../Scripts/Run_case.sh serial "$@"
