#!/bin/bash
# coastal_drain: 逐次実行 + 回帰テスト(海抜下ポルダーの排水。§46.5 (7)(8))
#   ./Run.sh [-u]
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Runge 列)
exec ../Scripts/Run_case.sh serial "$@"
