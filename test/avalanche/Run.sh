#!/bin/bash
# avalanche: 流れ型雪崩(等価流体+速度比例連行)の検定(逐次実行)
#   ./Run.sh
# 合否は Check_avalanche.py(構成 1: 固体台帳・共動更新・連行活性・成長・停止)と
# Check_sheet.py(構成 2〜5: 一様な斜面の常微分方程式の解との比較)、構成 3 のリスタートの往復

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" > dbinit.txt || exit 1

rc=0
set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_avalanche.py" save || rc=1
rm -rf save_serial && cp -r save save_serial

# 構成 2〜5: 一様な斜面の一斉発生(連行した雪の運動量 f_dbmom・Hungr の則 f_dbed = 5・連行する流動深の
# 下限 db_hent を、時間だけの常微分方程式の解と比べる。Check_sheet.py)と、構成 3 のリスタートの往復
python3 "$sdir/make_init.py" sheet || exit 1
set -o pipefail
for k in sh0 shm shh sht shm1 shm2; do
    ./encflow param_$k.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_sheet.py" || rc=1
for f in state.dat swflow_enc.dat geomorph_debris.dat; do
    if cmp -s save_shm/$f save_shmr/$f; then
        echo "リスタート(構成 3。4 秒で保存して復元): $f は通しの計算とビット一致 : PASS"
    else
        echo "リスタート(構成 3): $f が通しの計算と不一致 : FAIL" >&2
        rc=1
    fi
done
for k in sh0 shm shh sht; do
    rm -rf save_${k}_serial && cp -r save_$k save_${k}_serial
done

if [ $rc -eq 0 ]; then
    echo "=== avalanche 検定 PASS ==="
else
    echo "=== avalanche 検定 FAIL ===" >&2
fi
exit $rc
