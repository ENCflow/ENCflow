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
