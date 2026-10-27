#!/bin/bash
# hillsoil: 斜面の土層(風化による土層生成)の検定(逐次実行)
#   ./Run.sh
# 構成 wthr_none・wthr_map(W1 風化の一様・分布の解析解)、wthr_map_rt1 → rt2(リスタート
# 往復)、wthr_bad・wthr_nof(入力の誤りで初期化が停止すること)を Check_hillsoil.py と
# バイト比較で検定する。reference は持たない(解析解・バイト一致で判定)。
# 実行後の save_*/ は save_*_serial/ にも複製する(Run_MPI.sh のバイト比較用)
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

cfgs="wthr_none wthr_map wthr_map_rt1 wthr_map_rt2"
set -o pipefail
for c in $cfgs; do
    ./encflow param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
rc=0
# 入力の誤りは初期化で停止する($1 = 構成、$2 = 停止の表示)
expect_stop() {
    if ./encflow param_$1.txt > Screen_$1.log 2>&1; then
        echo "FAIL: $1 did not stop" >&2
        rc=1
    elif grep -q "$2" Screen_$1.log; then
        echo "PASS: $1 stops with \"$2\""
    else
        echo "FAIL: $1 stopped for another reason (see Screen_$1.log)" >&2
        rc=1
    fi
}
expect_stop wthr_bad "fn_wthr must be >= 0"
expect_stop wthr_nof "fn_wthr requires f_wthr=1"
echo ""

python3 "$sdir/Check_hillsoil.py" wthr || rc=1
if cmp -s save_wthr_map/state.dat save_wthr_map_rt/state.dat; then
    echo "PASS: restart continuation matches the straight run (wthr_map): state.dat"
else
    echo "FAIL: restart continuation differs from the straight run (wthr_map): state.dat" >&2
    rc=1
fi

for d in save_wthr_none save_wthr_map; do
    rm -rf ${d}_serial && cp -r $d ${d}_serial
done

if [ $rc -eq 0 ]; then
    echo "=== hillsoil verification PASS ==="
else
    echo "=== hillsoil verification FAIL ===" >&2
fi
exit $rc
