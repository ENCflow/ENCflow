#!/bin/bash
# =====================================================================
# テストケース共通実行エンジン
#   使い方1(ラッパー経由・推奨):
#     各ケースの Run.sh / Run_MPI.sh から
#       exec ../Scripts/Run_case.sh serial "$@"
#       exec ../Scripts/Run_case.sh mpi    "$@"
#   使い方2(シンボリックリンク):
#     Run.sh / Run_MPI.sh という名前でこのファイルへリンクを張ると、
#     呼び出し名からモードを自動判別する(名前に MPI を含めば mpi)
#
#   引数:  [serial|mpi] [ランク数] [-u]   (順不同、すべて省略可)
#   環境変数(ラッパーや実行時に上書き可):
#     PARAM  : パラメータファイル (既定 param.txt)
#     FILES  : reference と比較するファイル。RESDIR 内のベース名で
#              指定する (既定 Log.txt = result/Log.txt を比較)
#     RESDIR : 計算結果ディレクトリ (既定 result)
#              画面出力の保存先は Screen.log(比較には使わない)
#     NP     : MPI ランク数の既定値 (既定 2)
#     RTOL   : 相対許容誤差 (既定 serial:0, mpi:1e-5)
#     MPIRUN_OPTS : mpirun 追加オプション (--oversubscribe 等)
# =====================================================================

# エンジン自身の場所(シンボリックリンク経由でも実体の場所を得る)
sdir=$(dirname "$(readlink -f "$0")")

# --- モード判定: 第1引数 > 呼び出し名 > 既定 serial ---
mode=
case $1 in
    serial|mpi) mode=$1; shift ;;
esac
if [ -z "$mode" ]; then
    case $(basename "$0") in
        *MPI*|*mpi*) mode=mpi ;;
        *)           mode=serial ;;
    esac
fi

# --- 残りの引数解析: 数値はランク数、-u は reference 更新 ---
NP=${NP:-2}
update=
for a in "$@"; do
    case $a in
        -u)          update=-u ;;
        *[!0-9]*|'') echo "usage: $(basename "$0") [serial|mpi] [ランク数] [-u]" >&2
                     exit 2 ;;
        *)           NP=$a ;;
    esac
done
if [ -n "$update" ] && [ "$mode" = serial ] && [ "$NP" != 2 ]; then
    : # (serial でランク数が指定されても無視するだけなので特に何もしない)
fi

PARAM=${PARAM:-param.txt}
FILES=${FILES:-Log.txt}

# --- ビルドモードの整合性確認 ---
"$sdir/Check_mode.sh" "$mode" || exit 1

# --- 実行(pipefail: tee でなく計算本体の終了コードを拾う) ---
set -o pipefail
if [ "$mode" = mpi ]; then
    time mpirun -np "$NP" $MPIRUN_OPTS ./a.out "$PARAM" | tee Screen.log
else
    time ./a.out "$PARAM" | tee Screen.log
fi
rc=$?
set +o pipefail

if [ $rc -ne 0 ]; then
    echo "ERROR: 実行が異常終了しました (rc=$rc)。回帰テストは行いません。" >&2
    exit $rc
fi
echo ""

# --- 回帰テスト ---
# MPI は逐次と丸め順序が異なるため、既定で「最終表示桁1つ分」の差を
# 許容する(ULP=1。それ以上の差は FAIL)。逐次は完全一致を要求。
if [ "$mode" = mpi ]; then
    export ULP=${ULP:-1}
    export RTOL=${RTOL:-0}
else
    export ULP=${ULP:-0}
    export RTOL=${RTOL:-0}
fi

"$sdir/Compare_ref.sh" $update $FILES
