#!/bin/bash
# dambreak: 逐次実行 + 回帰テスト + Stoker 解析解との比較
#   ./Run.sh [-u]
#
# 使い方:  ./Run.sh        実行して reference と比較(なければ作成)
#          ./Run.sh -u     実行して reference を更新
# 解析解との比較(python3 Check_stoker.py)は回帰テストの後に表示だけ行う
# (合否には含めない。段波速度・中間状態・L1 誤差の診断用)

export SKIPCOLS=4      # 検査対象外とする列番号(Runge 列)

../Scripts/Run_case.sh serial "$@"
rc=$?
echo ""
python3 ./Check_stoker.py || true
exit $rc
