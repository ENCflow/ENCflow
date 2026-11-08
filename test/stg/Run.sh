#!/bin/bash
# stg: STG 格子(f_gridsystem = 1。旧互換の比較用で凍結中。developer.md §7)の動作確認(逐次実行)
#   ./Run.sh
# make_init.py が入力と設定を生成し、マスクなしの閉じた斜面の雨(p_stg.txt)を実行して
# Check_stg.py が連続式の保存を判定する。続いて領域マスク付き(p_stgmask.txt)を実行し、STG が
# 初期化で明示的に止まること(領域マスクは STG 非対応)を確かめる。reference は持たない。
# 結果の Log.txt は result_serial/ に複製する(Run_MPI.sh のバイト比較用)
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}   # 40 × 24 の小さな格子なので 1 スレッドで十分

python3 "$sdir/make_init.py" || exit 1
rm -rf result_stg result_stgmask
./encflow p_stg.txt > Screen_stg.log 2>&1 \
    || { echo "ERROR: p_stg run failed (see Screen_stg.log)" >&2; exit 1; }
python3 "$sdir/Check_stg.py" result_stg || exit 1

# 領域マスクは STG 非対応: 初期化で止まるのが正しい
if ./encflow p_stgmask.txt > Screen_stgmask.log 2>&1; then
    echo "  FAIL p_stgmask ran to the end; STG must stop on a domain mask" >&2
    exit 1
fi
grep -q "not supported with STG" Screen_stgmask.log \
    || { echo "  FAIL p_stgmask stopped without the expected message (see Screen_stgmask.log)" >&2; exit 1; }
echo "  ok   p_stgmask stops at initialization ($(grep -m1 -o 'a domain mask.*STG (f_gridsystem=1)' Screen_stgmask.log))"

rm -rf result_serial && mkdir result_serial && cp result_stg/Log.txt result_serial/Log_stg.txt
echo "=== stg verification PASS ==="
