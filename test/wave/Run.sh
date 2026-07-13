#!/bin/bash
# 使い方:  ./Run.sh        実行して reference と比較(なければ作成)
#          ./Run.sh -u     実行して reference を更新

../Scripts/Check_mode.sh serial || exit 1

#export OMP_NUM_THREADS=48

#export OMP_SCHEDULE="static"
#export OMP_SCHEDULE="dynamic,10"

#export OMP_PROC_BIND=spread
#export OMP_PROC_BIND=close
#export OMP_PLACES=cores

# 実行(pipefail: tee でなく a.out の終了コードを拾う)
set -o pipefail
time ./a.out param.txt | tee Log.txt
rc=$?
set +o pipefail

if [ $rc -ne 0 ]; then
    echo "ERROR: a.out が異常終了しました (rc=$rc)。回帰テストは行いません。" >&2
    exit $rc
fi
echo ""

export RTOL=1e-5
files=Log.txt

# 回帰テスト("$@" 経由で -u が Compare_ref.sh に渡る)
../Scripts/Compare_ref.sh "$@" $files
