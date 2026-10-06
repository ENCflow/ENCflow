#!/bin/bash
# nhbottom 構成 3: fn_bedmotion で構成 1 と同じ隆起を与え、ドライバの reference と比較する
#   ./Run_bm.sh        (入力 bm/ がなければ Bedmotion_inputs.py で生成)
#   S 列(全有効桁)は増分適用の丸めで最終桁が異なり得るので ULP=1
sdir=$(dirname "$(readlink -f "$0")")
cd "$sdir" || exit 1
../Scripts/Check_mode.sh serial || exit 1
[ -f bm/bmlist.txt ] || python3 Bedmotion_inputs.py || exit 1
set -o pipefail
./encflow param_bm.txt | tee Screen_bm.log || exit 1
set +o pipefail
export ULP=1 SKIPCOLS=4 RESDIR=result_bm ENCFLOW_EXE=./encflow
exec ../Scripts/Compare_ref.sh Log.txt
