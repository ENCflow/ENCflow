#!/bin/bash
# nhbottom: 逐次実行 + 回帰テスト(uplift ドライバ。param.txt = NH + 加速度項)
#   ./Run.sh [-u]
#   比較用の静水圧・加速度項なしは手動: ./uplift param_h.txt / ./uplift param_n.txt
#   図表: python3 Fig.py(3 ケースの実行後)
export ULP=1      # 印字の最終桁を単位とした許容誤差
export SKIPCOLS=4      # 検査対象外とする列番号(Runge 列)
export EXE=uplift
make -s uplift || exit 1
exec ../Scripts/Run_case.sh serial "$@"
