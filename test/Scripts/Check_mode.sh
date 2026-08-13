#!/bin/bash
# =====================================================================
# ビルドモード整合性チェック
#   使い方(各テストディレクトリの Run スクリプトから):
#     ../Scripts/Check_mode.sh serial || exit 1
#     ../Scripts/Check_mode.sh mpi    || exit 1
#
#   実行ファイルはモードごとに別名(serial: encflow / mpi: encflow_mpi)
#   なので、名前の段階でモード取り違えは起こらない。ここで確認するのは
#     1. 実行ファイル(リンク)の存在。bin/ に実体があればリンクを
#        自動作成する
#     2. src の直近ビルドが同モードの場合の、MPI 実装(module 環境)・
#        PREC の一致と install 忘れ
#   スタンプは .mode_<MODE>_<MPIID>_<PREC> 形式(MPIID は MPI ラッパーの
#   -show 出力のハッシュ)。期待スタンプ名は src/Makefile の
#   print-stamp ターゲットに計算させるため、ハッシュのロジックは
#   Makefile 側に一元化されている。
#   直近ビルドが別モードのとき(bin/ で両モードを共存させる運用)は、
#   bin/ の実行ファイルは過去のビルド物であり検証材料がないため、
#   名前がモードを保証することを頼りにそのまま通す。
# =====================================================================
if [ $# -lt 1 ]; then
    echo "usage: Check_mode.sh {serial|mpi}" >&2
    echo "  (received $# args: '$*')" >&2
    exit 2
fi

want=$1
srcdir=../../src
if [ "$want" = mpi ]; then
    exe=encflow_mpi
else
    exe=encflow
fi
bin=../../bin/$exe

# 実行ファイル(シンボリックリンク)の確認。bin/ に実体があれば
# 自動でリンクを張る(リンク切れも -e で検出され張り直される)
if [ ! -e "./$exe" ]; then
    if [ -e "$bin" ]; then
        ln -sf "$bin" "./$exe"
    else
        echo "ERROR: $bin がありません。先に src で make MODE=$want install を実行してください。" >&2
        exit 1
    fi
fi

# 現在の環境(make.inc + module)での期待スタンプ名を make に計算させる
expected=$(make -s -C "$srcdir" print-stamp MODE="$want" 2>/dev/null)
if [ -z "$expected" ]; then
    echo "ERROR: 期待スタンプ名を取得できません" >&2
    echo "  (src/Makefile に print-stamp ターゲットはありますか)" >&2
    exit 1
fi
stamp=$srcdir/$expected

if [ -e "$stamp" ]; then
    # 直近ビルドが現環境と一致: install 忘れの検出
    # (bin の実行ファイルがモード切替時刻より古ければエラー)
    if [ "$bin" -ot "$stamp" ]; then
        echo "ERROR: $bin が $expected より古く、install 忘れの可能性があります。" >&2
        echo "  cd $srcdir && make install の実行をお勧めします。" >&2
        exit 1
    fi
else
    actual=$(cd "$srcdir" && ls .mode_"${want}"_* 2>/dev/null | sed 's/^\.mode_//')
    if [ -n "$actual" ]; then
        # 同モードなのにスタンプが違う = MPI 実装(module 環境)か
        # PREC が現環境とズレている。bin の実行ファイルも同じズレを
        # 持つ可能性が高いので停止する
        echo "ERROR: src のビルドが現環境と一致しません" >&2
        echo "  要求(現環境): ${expected#.mode_}" >&2
        echo "  src のビルド : $actual" >&2
        echo "  対処: cd $srcdir && make MODE=$want install" >&2
        echo "  (module 環境がビルド時と同じかどうかも確認してください)" >&2
        exit 1
    fi
    # 直近ビルドは別モード(共存運用)。$bin は過去のビルド物で、
    # 実行ファイル名がモードを保証するのでそのまま使う
fi

exit 0
