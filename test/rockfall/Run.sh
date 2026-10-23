#!/bin/bash
# rockfall: 崩落と崖錐の検定(逐次実行)
#   ./Run.sh
# 合否は Check_rockfall.py。save/ は save_serial/ にも複製(Run_MPI.sh の比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" > zinit.txt

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_rockfall.py" save || rc=1
rm -rf save_serial && cp -r save save_serial
# 基岩版(rf_bedrock = 1。土層 0。z は param.txt とビット一致)
python3 "$sdir/make_init.py" --sdzero
./encflow param_bed.txt | tee Screen_bed.log || exit 1
echo ""
python3 "$sdir/Check_rockfall.py" save_bed result_bed bed=save || rc=1
rm -rf save_bed_serial && cp -r save_bed save_bed_serial
# 窓版(rf_rc = 3 m)
./encflow param_rc.txt | tee Screen_rc.log || exit 1
echo ""
python3 "$sdir/Check_rockfall.py" save_rc result_rc rc=3 || rc=1
rm -rf save_rc_serial && cp -r save_rc save_rc_serial
# 支え方式(rf_fface = 0。柱の崩落)
./encflow param_face.txt | tee Screen_face.log || exit 1
echo ""
python3 "$sdir/Check_rockfall.py" save_face result_face rc=3 face=1 || rc=1
rm -rf save_face_serial && cp -r save_face save_face_serial
# 張り出し版(rf_uc = 0.05 m。降雨 + 乾式侵食)
./encflow param_uc.txt 2>&1 | tee Screen_uc.log || exit 1
echo ""
python3 "$sdir/Check_rockfall.py" save_uc result_uc rc=3 face=1 uc=Screen_uc.log hc=15 || rc=1
rm -rf save_uc_serial && cp -r save_uc save_uc_serial
# 海セル版(台地の西壁が海に面する)
python3 "$sdir/make_init.py" --sea
./encflow param_sea.txt 2>&1 | tee Screen_sea.log || exit 1
echo ""
python3 "$sdir/Check_rockfall.py" save_sea result_sea sea=Screen_sea.log || rc=1
rm -rf save_sea_serial && cp -r save_sea save_sea_serial

if [ $rc -eq 0 ]; then
    echo "=== rockfall verification PASS ==="
else
    echo "=== rockfall verification FAIL ===" >&2
fi
exit $rc
