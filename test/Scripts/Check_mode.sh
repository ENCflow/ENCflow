#!/bin/bash
# =====================================================================
# ビルドモード整合性チェック
#   使い方(各テストディレクトリの Run スクリプトから):
#     ../Scripts/Check_mode.sh serial || exit 1
#     ../Scripts/Check_mode.sh mpi    || exit 1
#
#   スタンプは .mode_<MODE>_<MPIID> 形式(MPIID は MPI ラッパーの
#   -show 出力のハッシュ)。期待スタンプ名は src/Makefile の
#   print-stamp ターゲットに計算させるため、ハッシュのロジックは
#   Makefile 側に一元化されている。
#   これにより、モード不一致だけでなく「module を切り替えたのに
#   再ビルドしていない」(MPI 実装の不一致)も検出できる。
# =====================================================================
if [ $# -lt 1 ]; then
    echo "usage: Check_mode.sh {serial|mpi}" >&2
    echo "  (received $# args: '$*')" >&2
    exit 2
fi

want=$1
srcdir=../../src
bin=../../bin/a.out

# a.out(シンボリックリンク)の存在確認。リンク切れも -e で検出される
if [ ! -e ./a.out ]; then
    echo "ERROR: ./a.out がありません。先に src で make install を実行してください。" >&2
    exit 1
fi

# 現在の環境(make.inc + module)での期待スタンプ名を make に計算させる
expected=$(make -s -C "$srcdir" print-stamp MODE="$want" 2>/dev/null)
if [ -z "$expected" ]; then
    echo "ERROR: 期待スタンプ名を取得できません" >&2
    echo "  (src/Makefile に print-stamp ターゲットはありますか)" >&2
    exit 1
fi
stamp=$srcdir/$expected

# ビルドモードと MPI 実装の確認
if [ ! -e "$stamp" ]; then
    actual=$(cd "$srcdir" && ls .mode_* 2>/dev/null | sed 's/^\.mode_//')
    echo "ERROR: ビルドモードまたは MPI 実装が一致しません" >&2
    echo "  要求(現環境): ${expected#.mode_}" >&2
    echo "  src のビルド : ${actual:-未ビルド}" >&2
    echo "  対処: cd $srcdir && make MODE=$want install" >&2
    echo "  (module 環境がビルド時と同じかどうかも確認してください)" >&2
    exit 1
fi

# install 忘れの検出: bin/a.out がモード切替時刻より古ければエラー
if [ "$bin" -ot "$stamp" ]; then
    echo "ERROR: $bin が $expected より古く、install 忘れの可能性があります。" >&2
    echo "  cd $srcdir && make install の実行をお勧めします。" >&2
    exit 1
fi

exit 0
