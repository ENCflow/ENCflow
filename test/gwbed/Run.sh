#!/bin/bash
# gwbed: 逐次実行 + 回帰テスト + 解析検定(河床交換能 f_gwbed。developer.md §16.5)
#   ./Run.sh [-u]
# 構成 1(param.txt: 堤内地→河道の得水が k_bed で律速)は reference 比較
# (Log.txt、ULP=0)と Check_gwbed.py gain、構成 2(param_lined.txt: k_bed=0 の
# 遮断)と構成 3(param_vert.txt: 鉛直浸透能の置き換え)は Check_gwbed.py の
# 解析検定のみ(reference 非依存)
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export SKIPCOLS=6      # 検査対象外とする列番号(Runge 列)
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

python3 Check_gwbed.py gain result || exit 1

for tag in lined vert; do
    rm -rf result_$tag
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 || { echo "ERROR: param_$tag run failed" >&2; exit 1; }
    python3 Check_gwbed.py $tag result_$tag || exit 1
done

echo "=== gwbed verification PASS ==="
