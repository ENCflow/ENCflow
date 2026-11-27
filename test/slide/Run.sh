#!/bin/bash
# slide: 瞬時流動化(f_release)と斜面安定判定(f_slide)の疎通・保存則検定
#   ./Run.sh
# 構成1(param.txt): 崩壊深指定の時刻発火 → 流下・堆積(save/)
# 構成2(param_fs.txt): 降雨 → 飽和 → Fs<1 → 自動流動化(save_fs/)
# 構成3(param_fs2.txt): f_slide=2 判定のみ(Fs 危険度マップ。save_fs2/)
# 構成4(param_wet.txt): 構成1 + 地下水計算 + 保持水の授受 f_dbwet=3 + 初期地下水 gw_sat0 = 1
#   (飽和した土層の流動化。save_wet/)。同じ設定の gw_sat0 = 0(乾いた土層。保持水の不足の
#   台帳が働く)も回す(save_wetdry/。設定は param_wet.txt から作る)
# 構成5〜8(make_fs.py が設定 p_fs_*.txt と入力 d_fs/ を書く): 斜面安定判定の選択子
#   f_slide_seep(浸透力を全水頭の勾配で)・slide_dmax(深さの上限)・f_slide_wet(間隙水圧の崩壊に限る)・
#   f_slide_noflow(濃い混合体の下を判定しない。薄い膜の下は判定する)。安全率の出力を式の値と比べる
#   (Check_slide_fs.py。developer.md §28.19・§28.24)
# 実行後の save/, save_fs/ などは *_serial/ にも複製する(Run_MPI.sh 用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

# 崩壊深分布(D=1m, i∈[5,15], j∈[5,16]。Check_slide.py の期待値と対)
python3 "$sdir/make_dbinit.py" > dbinit.txt || exit 1

rc=0

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_slide.py" save release || rc=1
rm -rf save_serial && cp -r save save_serial

set -o pipefail
./encflow param_fs.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_slide.py" save_fs fslide result || rc=1
rm -rf save_fs_serial && cp -r save_fs save_fs_serial
cp -f result/Fs9999.txt result/D9999.txt result/F9999.txt save_fs_serial/

# 構成3(param_fs2.txt): f_slide=2 判定のみ(Fs 危険度マップ。§28.9)
set -o pipefail
./encflow param_fs2.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_slide.py" save_fs2 fsdiag result_fs2 || rc=1
rm -rf save_fs2_serial && cp -r save_fs2 save_fs2_serial
cp -f result_fs2/Fs9999.txt save_fs2_serial/

# 構成4(param_wet.txt): 飽和した土層の瞬時流動化と保持水の授受(developer.md §28.17)。
# 水台帳は終了時の「保持水の不足」の表示を読むので、画面出力を別に取る
set -o pipefail
./encflow param_wet.txt | tee Screen_wet.log || exit 1
set +o pipefail
cat Screen_wet.log >> Screen.log
echo ""
python3 "$sdir/Check_slide.py" save_wet wet Screen_wet.log 1.0 || rc=1
rm -rf save_wet_serial && cp -r save_wet save_wet_serial
# 同 乾いた土層(gw_sat0 = 0): 堆積のとき保持水が足りず、不足の台帳が働く
sed -e "s/gw_sat0 = 1.0 /gw_sat0 = 0.0 /" -e "s/'save_wet'/'save_wetdry'/" \
    -e "s/'result_wet'/'result_wetdry'/" param_wet.txt > param_wetdry.txt
set -o pipefail
./encflow param_wetdry.txt | tee Screen_wetdry.log || exit 1
set +o pipefail
cat Screen_wetdry.log >> Screen.log
echo ""
python3 "$sdir/Check_slide.py" save_wetdry wet Screen_wetdry.log 0.0 || rc=1
rm -rf save_wetdry_serial && cp -r save_wetdry save_wetdry_serial

# 構成5〜8: 斜面安定判定の選択子(developer.md §28.19)。安全率の出力(bil)も Run_MPI.sh 用に複製する
python3 "$sdir/make_fs.py" || exit 1
for c in $(python3 "$sdir/make_fs.py" list); do
    echo "--- $c"
    ./encflow p_$c.txt > Screen_fs.log 2>&1 || { tail -5 Screen_fs.log; exit 1; }
    cat Screen_fs.log >> Screen.log
    rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial
    cp -f result_$c/Fs0001.bil save_${c}_serial/
done
echo ""
for c in fs_u0 fs_u1 fs_g0 fs_g1 fs_l0 fs_l1 fs_lq1 fs_le1 fs_d2; do
    python3 "$sdir/Check_slide_fs.py" fs $c || rc=1
done
python3 "$sdir/Check_slide_fs.py" pair fs_u1 fs_u0 same || rc=1
python3 "$sdir/Check_slide_fs.py" pair fs_g1 fs_g0 differ || rc=1
python3 "$sdir/Check_slide_fs.py" pair fs_l1 fs_l0 differ || rc=1
python3 "$sdir/Check_slide_fs.py" twin fs_m1 fs_m0 || rc=1
python3 "$sdir/Check_slide_fs.py" ledger fs_gdyn || rc=1
python3 "$sdir/Check_slide_fs.py" dmax1 fs_d1 || rc=1
python3 "$sdir/Check_slide_fs.py" wet fs_w1 fs_w0 fs_w2 || rc=1
python3 "$sdir/Check_slide_fs.py" noflow fs_n1 fs_n0 || rc=1
python3 "$sdir/Check_slide_fs.py" film fs_f1 fs_f0 fs_k1 fs_k0 || rc=1

if [ $rc -eq 0 ]; then
    echo "=== slide verification PASS ==="
else
    echo "=== slide verification FAIL ===" >&2
fi
exit $rc
