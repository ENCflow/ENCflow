#!/bin/sh
# =====================================================================
# ENCflow の BMI 適合性検査(CSDMS bmi-tester)を実行する
#
#   使い方(ケースディレクトリで。例: test/wave):
#     ../../bmi/python/check_bmi.sh [param.txt]
#
#   事前準備:
#     bmi/ で make(libencflow_bmi.so を生成)
#     pip install bmi-tester bmipy 'pytest<8'
#     pip install 'gimli.units==0.3.*'   # 任意: 単位の妥当性検査も有効化
#
#   注記: インストール版 bmi-tester の bmi-test CLI はステージごとに
#   pytest を起動するため、共有 conftest が rootdir の外になり fixture が
#   見つからない(上流の既知の粗)。ここでは rootdir をパッケージに固定
#   して全ステージを1セッションで直接実行する。
#   --ignore-unknown-dependency も同様に上流の依存名不一致への回避。
# =====================================================================
set -e
PARAM=${1:-param.txt}
BMIDIR=$(cd "$(dirname "$0")" && pwd)
TESTER=$(python3 -c "import bmi_tester, os; print(os.path.dirname(bmi_tester.__file__))")

export BMITEST_CLASS='encflow_bmi:EncflowBmi'
export BMITEST_INPUT_FILE="$PARAM"
export BMITEST_MANIFEST="$PARAM"
export BMI_VERSION_STRING=2.0
export PYTHONPATH="$BMIDIR${PYTHONPATH:+:$PYTHONPATH}"

exec python3 -m pytest -q -rs \
  --rootdir="$TESTER" --ignore-unknown-dependency \
  "$TESTER/_bootstrap" \
  "$TESTER/_tests/stage_1" "$TESTER/_tests/stage_2" "$TESTER/_tests/stage_3"
