#!/bin/bash
# vchannel: 一様な V 字水路の流れの横断分布を、厳密解と比べる検定(逐次実行)
#   ./Run.sh
# 入力と構成ごとの設定は make_init.py が書く(data_<向き>/、p_<構成>_<向き>.txt)。
# 合否は Check_vchannel.py(摩擦なしの加速度、4 近傍の流量、8 近傍の流量と向きによる幅)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" || exit 1

rc=0
: > Screen.log
set -o pipefail
for p in p_*_r*.txt; do
    ./encflow "$p" | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_vchannel.py" || rc=1

# Run_MPI.sh のバイト比較用に、逐次の出力を複製する
for d in result_*_r*; do
    case "$d" in *_serial) continue ;; esac
    rm -rf "${d}_serial" && cp -r "$d" "${d}_serial"
done

exit $rc
