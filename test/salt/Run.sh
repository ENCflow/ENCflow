#!/bin/bash
# salt: 逐次実行 + 回帰テスト(模式実験 A: プール仕切り = ロック交換の終状態)
#   ./Run.sh [-u]
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Runge 列)
exec ../Scripts/Run_case.sh serial "$@"
