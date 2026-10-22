#!/bin/bash
# rockfall: 逐次実行 + 漸化式の検定 + 回帰テスト(Log.txt)
#   ./Run.sh [-u]
export ULP=${ULP:-1}
export SKIPCOLS=4         # 検査対象外とする列番号(Runge 列)

sdir=$(dirname "$(readlink -f "$0")")
update=
[ "$1" = "-u" ] && update=-u

../Scripts/Check_mode.sh serial || exit 1

export ENCFLOW_EXE=./encflow
set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_rockfall.py" result || rc=1
"$sdir/../Scripts/Compare_ref.sh" $update Log.txt || rc=1

if [ $rc -eq 0 ]; then
    echo "=== rockfall verification PASS ==="
else
    echo "=== rockfall verification FAIL ===" >&2
fi
exit $rc
