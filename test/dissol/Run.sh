#!/bin/bash
# dissol: 逐次実行 + 解析解比較 + リスタート往復 + 回帰テスト(構成 A の Log.txt)
#   ./Run.sh [-u]
#
# 構成 A(param.txt。面的溶食)・B(param_sink.txt。集中溶食)・
# C(param_rain.txt。降雨源)・D(param_lat.txt。側方溶食)を Check_analytic.py で解析値と比較し、
# A のリスタート分割 rt1 → rt2 が通し計算と state.dat・Z9998 でバイト
# 一致することを確かめる。A の Log.txt は reference とも比較する。
export ULP=${ULP:-1}      # 印字の最終桁を単位とした許容誤差(A の Log.txt)
export SKIPCOLS=6         # 検査対象外とする列番号(Runge 列)

sdir=$(dirname "$(readlink -f "$0")")
update=
[ "$1" = "-u" ] && update=-u

../Scripts/Check_mode.sh serial || exit 1

export ENCFLOW_EXE=./encflow
set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
./encflow param_sink.txt | tee -a Screen.log || exit 1
./encflow param_rain.txt | tee -a Screen.log || exit 1
./encflow param_lat.txt | tee -a Screen.log || exit 1
./encflow param_rt1.txt | tee -a Screen.log || exit 1
./encflow param_rt2.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_analytic.py" a result || rc=1
python3 "$sdir/Check_analytic.py" b result_sink || rc=1
python3 "$sdir/Check_analytic.py" c result_rain || rc=1
python3 "$sdir/Check_analytic.py" d result_lat || rc=1

# リスタート往復: 通し(save_all / result)と分割(save_rt / result_rt2)
for f in state.dat geomorph_dissol.dat; do
    if cmp -s save_all/$f save_rt/$f; then
        echo "PASS: restart continuation matches the straight run: $f"
    else
        echo "FAIL: restart continuation differs from the straight run: $f" >&2
        rc=1
    fi
done
if cmp -s result/Z9998.bil result_rt2/Z9998.bil; then
    echo "PASS: restart continuation matches the straight run: Z9998.bil"
else
    echo "FAIL: restart continuation differs from the straight run: Z9998.bil" >&2
    rc=1
fi

# 回帰テスト(構成 A の Log.txt)
"$sdir/../Scripts/Compare_ref.sh" $update Log.txt || rc=1

if [ $rc -eq 0 ]; then
    echo "=== dissol verification PASS ==="
else
    echo "=== dissol verification FAIL ===" >&2
fi
exit $rc
