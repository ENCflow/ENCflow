#!/bin/bash
# lava: 溶岩流(Bingham 粘性重力流)の検定(逐次実行)
#   ./Run.sh
# 構成1: Huppert 相似解ベンチマーク(Newton 極限 + 台帳)
# 構成2: Bingham 停止・固化(h∞ 解析解 + 固化台帳)
# 構成4: 格子の向きによらない広がり(塑性ドームの静止形の解析解 + 等方性)
# 構成5: 溶岩より高い壁の前の溶岩だまりの全量固化(台帳 + 壁際の固化)
# 構成6: 固化した溶岩の下の土層の埋没と地下水の保存(Green-Ampt 併用)
# 構成7: 静止した層の冷却(温度モード。後退 Euler の漸化式・厳密解・温度による固化・熱の台帳)
#        7m: 気温を fn_meteo から読む同じ計算(save のバイト一致)
# 構成8: 熱の移流(温度モード・冷却なし。熱の保存・温度の範囲)
#        8': 同じ入力の等温の計算(f_lvtemp = 0)と lavaflow.dat・state.dat がバイト一致
# 構成9: 冷えて止まる流れ(温度モード。同じ体積で噴出率 4 倍の流れが長い。等温の対照では同じ長さ)
#        9r: 温度モードのリスタートの往復(1800 s で保存 → 再開)が通しの計算とバイト一致
# 合否は Check_lava.py。save は save*_serial にも複製(Run_MPI 比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" > zinit.txt
python3 "$sdir/make_init.py" wall > zwall.txt
python3 "$sdir/make_init.py" cool > cool_cells.txt
python3 "$sdir/make_init.py" run > zrun.txt

rc=0

# 構成1: Huppert(τ_y=0 の Newton 極限。相似解検定)
set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save huppert || rc=1
rm -rf save_serial && cp -r save save_serial

# 構成2: Bingham 停止・固化
set -o pipefail
./encflow param_ty.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_ty bingham || rc=1
rm -rf save_ty_serial && cp -r save_ty save_ty_serial

# 構成3: 最小入力(既定値)と構成3'(既定値の明示)の同値検定(§66)
set -o pipefail
./encflow param_min.txt | tee Screen_min.log || exit 1
./encflow param_minx.txt | tee Screen_minx.log || exit 1
set +o pipefail
echo ""
if diff -r -I '^! ENCflow restart save' save_min save_minx > /dev/null && cmp -s result_min/Log.txt result_minx/Log.txt; then
    echo "=== defaults: save/ and Log.txt are bit-identical between the minimal input and the explicit defaults ==="
else
    echo "FAIL: minimal input (defaults) and explicit defaults differ" >&2
    rc=1
fi
ndef=$(grep -c "(default)" Screen_min.log)
[ "$ndef" -eq 2 ] || { echo "FAIL: expected 2 '(default)' lines, got $ndef" >&2; rc=1; }

# 構成4: 塑性ドームの静止形(格子の向きによらない広がり。§51.4)
set -o pipefail
./encflow param_dome.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_dome dome || rc=1
rm -rf save_dome_serial && cp -r save_dome save_dome_serial

# 構成5: 溶岩より高い壁の前にたまった溶岩の固化(§51.5)
set -o pipefail
./encflow param_wall.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_wall wall || rc=1
rm -rf save_wall_serial && cp -r save_wall save_wall_serial

# 構成6: 固化した溶岩の下の土層の埋没(§51.6)
set -o pipefail
./encflow param_bury.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_bury bury || rc=1
rm -rf save_bury_serial && cp -r save_bury save_bury_serial

# 構成7: 静止した層の冷却(温度モード。lava_plan.md §8.10)
set -o pipefail
./encflow param_cool.txt | tee Screen_cool.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_cool cool Screen_cool.log || rc=1
rm -rf save_cool_serial && cp -r save_cool save_cool_serial

# 構成7m: 気温を fn_meteo(一様定数 20 °C)から読む同じ計算
set -o pipefail
./encflow param_coolm.txt | tee Screen_coolm.log || exit 1
set +o pipefail
echo ""
same=1
for f in state.dat lavaflow.dat lavaflow_temp.dat; do
    cmp -s save_cool/$f save_coolm/$f || same=0
done
if [ $same -eq 1 ]; then
    echo "=== 構成7m: 気温を meteo から読んだ計算の save が構成7 とバイト一致 ==="
else
    echo "FAIL: 構成7m(気温を meteo から読む)の save が構成7 と異なる" >&2
    rc=1
fi

# 構成8: 熱の移流(冷却なし)と、同じ入力の等温の計算 8'(f_lvtemp = 0)
set -o pipefail
./encflow param_adv.txt | tee Screen_adv.log || exit 1
./encflow param_adv0.txt | tee Screen_adv0.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_adv adv Screen_adv.log || rc=1
same=1
for f in state.dat lavaflow.dat; do
    cmp -s save_adv/$f save_adv0/$f || same=0
done
if [ $same -eq 1 ]; then
    echo "=== 構成8': 温度モード(β = 0・冷却なし)の流れが等温の計算とバイト一致 ==="
else
    echo "FAIL: 構成8 の lavaflow.dat / state.dat が等温の計算 8' と異なる" >&2
    rc=1
fi
rm -rf save_adv_serial && cp -r save_adv save_adv_serial

# 構成9: 冷えて止まる流れ(温度モード Q・4Q と等温の対照 Q・4Q。同じ体積)
set -o pipefail
for c in run run4 runi runi4; do
    ./encflow param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_run run Screen_run.log Screen_run4.log || rc=1
for c in run run4; do
    rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial
done

# 構成9r: 温度モードのリスタートの往復(構成9 を 1800 s まで計算して保存し、
#         そこから再開して 7200 s まで。溶岩が噴出・流動中の時刻で切る)
sed -e "s/  tt = 7200/  tt = 1800/" -e "s/  dt_file = 7200/  dt_file = 1800/" \
    -e "s/  dt_recrd = 7200/  dt_recrd = 1800/" \
    -e "s/'result_run'/'result_runa'/" -e "s/'save_run'/'save_runa'/" param_run.txt > wrk_runa.txt
sed -e "s/  f_state_save = 1/  f_state_save = 1, f_state_restore = 1/" \
    -e "s/'result_run'/'result_runb'/" -e "s/'save_run'/'save_runb'/" param_run.txt > wrk_runb.txt
set -o pipefail
./encflow wrk_runa.txt | tee Screen_runa.log || exit 1
rm -rf save_runb && cp -r save_runa save_runb
./encflow wrk_runb.txt | tee Screen_runb.log || exit 1
set +o pipefail
echo ""
same=1
for f in state.dat lavaflow.dat lavaflow_temp.dat; do
    cmp -s save_run/$f save_runb/$f || same=0
done
if [ $same -eq 1 ]; then
    echo "=== 構成9r: リスタートの往復が通しの計算とバイト一致(state.dat・lavaflow.dat・lavaflow_temp.dat) ==="
else
    echo "FAIL: 構成9r のリスタートの往復が通しの計算(構成9)と異なる" >&2
    rc=1
fi
python3 "$sdir/Check_lava.py" - heat Screen_runb.log || rc=1

if [ $rc -eq 0 ]; then
    echo "=== lava 検定 PASS ==="
else
    echo "=== lava 検定 FAIL ===" >&2
fi
exit $rc
