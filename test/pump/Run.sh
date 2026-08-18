#!/bin/bash
# pump: 逐次実行 + 回帰テスト(井戸揚水の線形水位低下)
#   ./Run.sh [-u]
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Runge 列)
exec ../Scripts/Run_case.sh serial "$@"
