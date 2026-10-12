#!/bin/bash
# culvert: 逐次実行 + 回帰テスト(カルバート流量則の 3 レジーム通過)
#   ./Run.sh [-u]
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Runge 列)
exec ../Scripts/Run_case.sh serial "$@"
