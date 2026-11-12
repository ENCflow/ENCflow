#!/bin/bash
# driftwood: 流木ラスタ場の疎通・保存則・リスタート往復検定(逐次実行)
#   ./Run.sh
# 合否は Check_driftwood.py(材積保存・流木化/堆積の活性・平坦部到達)と、
# 集積流木の構成 5 の Check_woodjam.py(材積保存・堰上げの解析解・捕捉率)。
# 実行後の save 系は save*_serial/ にも複製する(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

# 構成1: 土石流+流木(侵食連行)
set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_driftwood.py" save || rc=1
rm -rf save_serial && cp -r save save_serial

# 構成2: 洪水氾濫での流木(水理的流失。geomorph なし)
set -o pipefail
./encflow param_flood.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_driftwood.py" save_flood || rc=1
rm -rf save_flood_serial && cp -r save_flood save_flood_serial

# 構成3: リスタート分割継続(0→15 + 復元 15→30 が通し 0→30 と一致するか。
# 本ケースはバイト一致で成立する(2026-08-21 実測)。将来一致が崩れた
# 場合は §28.4 の「継続等価は ULP 水準」に該当するか原因を特定すること)
rm -rf save_rt
set -o pipefail
./encflow param_rt1.txt | tee -a Screen.log || exit 1
./encflow param_rt2.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
for f in driftwood.dat state.dat; do
    if cmp -s save_rt/$f save/$f; then
        echo "=== restart continuation: $f is bit-identical to the straight run ==="
    else
        echo "FAIL: restart continuation differs from the straight run: $f" >&2
        rc=1
    fi
done

# 構成4: 最小入力(既定値)と構成4'(既定値の明示)の同値検定
set -o pipefail
./encflow param_min.txt | tee -a Screen.log || exit 1
./encflow param_minx.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_driftwood.py" save_min 0.001 || rc=1
for f in state.dat driftwood.dat; do
    if cmp -s save_min/$f save_minx/$f; then
        echo "=== defaults: $f is bit-identical between the minimal input and the explicit defaults ==="
    else
        echo "FAIL: $f differs between the minimal input (defaults) and the explicit defaults" >&2
        rc=1
    fi
done

# 構成5: 構造物での捕捉と集積、集積の抵抗(fn_dwtrap。developer.md §50.7)
#   入力(jam_*.txt)は make_jam.py が作る。5 = 捕捉率 1 と抵抗(既定の係数)、5a = 充填率の上限と
#   抗力係数、5b・5c = リスタートの分割継続、5d = 捕捉率 0.3・流れへの作用なし、5e = 流木なし
#   (5d と流れがバイト一致)、5f = 集積が進むと捕捉率 1
python3 "$sdir/make_jam.py" z > jam_z.txt
python3 "$sdir/make_jam.py" h > jam_h.txt
python3 "$sdir/make_jam.py" stock > jam_stock.txt
python3 "$sdir/make_jam.py" trap 1.0 > jam_trap_1.txt
python3 "$sdir/make_jam.py" trap 0.3 > jam_trap_0.3.txt
rm -rf save_jamrt
set -o pipefail
for c in jam jamcap jamrt1 jamrt2 jamoff jamnone jamgrow; do
    ./encflow param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""
python3 "$sdir/Check_woodjam.py" jam result_jam save_jam || rc=1
rm -rf save_jam_serial && cp -r save_jam save_jam_serial
python3 "$sdir/Check_woodjam.py" jam result_jamcap save_jamcap 2.0 0.02 || rc=1
python3 "$sdir/Check_woodjam.py" ratio result_jamoff 0.3 || rc=1
python3 "$sdir/Check_woodjam.py" grow result_jamgrow || rc=1
for f in driftwood.dat state.dat swflow_enc.dat; do
    if cmp -s save_jamrt/$f save_jam/$f; then
        echo "=== jam restart continuation: $f is bit-identical to the straight run ==="
    else
        echo "FAIL: jam restart continuation differs from the straight run: $f" >&2
        rc=1
    fi
done
nf=0
for f in result_jamnone/H[0-9]*.txt result_jamnone/V[0-9]*.txt result_jamnone/Log.txt; do
    nf=$((nf + 1))
    if ! cmp -s "$f" "result_jamoff/$(basename "$f")"; then
        echo "FAIL: the flow with f_dwjam = 0 differs from the run without driftwood: $(basename "$f")" >&2
        rc=1
    fi
done
[ $rc -eq 0 ] && echo "=== f_dwjam = 0: the flow ($nf files of H, V and Log.txt) is bit-identical to the run without driftwood ==="

if [ $rc -eq 0 ]; then
    echo "=== driftwood verification PASS ==="
else
    echo "=== driftwood verification FAIL ===" >&2
fi
exit $rc
