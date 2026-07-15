#!/bin/bash
# =====================================================================
# 回帰テスト: reference の作成・比較
#   計算結果ディレクトリ($resdir)内のファイルを ./reference と比較する。
#
#   使い方(各テストディレクトリの Run スクリプトから、実行成功後に):
#     ../Scripts/Compare_ref.sh Log.txt        result/Log.txt を比較(なければ作成)
#     ../Scripts/Compare_ref.sh -u Log.txt     reference を今回の結果で更新
#     ULP=1 ../Scripts/Compare_ref.sh Log.txt  最終表示桁1つ分まで許容
#
#   ファイル名はベース名で指定する(resdir 内のパスとして解釈される)。
#   カレントディレクトリの param.txt が reference と不一致の場合は
#   比較不能として報告する。
#
#   環境変数:
#     RESDIR : 計算結果ディレクトリ (既定 result。param の dir_result に合わせる)
#     許容誤差 = ATOL + RTOL*max(|a|,|b|) + ULP*量子
#     RTOL : 相対許容誤差 (既定 0)
#     ATOL : 絶対許容誤差 (既定 0)
#     ULP  : 印字の最終桁を単位とした許容誤差 (既定 0)
#            量子は各数値の表示形式から自動決定する
#            (例: 12.1298 → 1e-4, 0.0050462962963 → 1e-13, 98.6 → 0.1)
#            並列数・コンパイラ・マシン間の比較では ULP=1 を推奨
#     SKIPCOLS : 比較から除外する列番号(空白区切りトークンの番号)。
#            カンマ区切りで複数指定可 (例: SKIPCOLS=4 → Runge列を除外)。
#            事象カウント系など閾値に敏感な列を外し、他の列の
#            チェック精度(ULP=0等)を保つために使う
#
#   戻り値: 0=PASS または reference 作成/更新, 1=FAIL, 2=比較不能
# =====================================================================
refdir=reference
resdir=${RESDIR:-result}
param=param.txt

update=0
if [ "$1" = "-u" ]; then
    update=1
    shift
fi

if [ $# -lt 1 ]; then
    echo "usage: Compare_ref.sh [-u] file1 [file2 ...]" >&2
    exit 2
fi

# --- 対象ファイルの存在確認 ---
for f in "$@"; do
    if [ ! -e "$resdir/$f" ]; then
        echo "ERROR: $resdir/$f がありません(dir_result と RESDIR は一致していますか)" >&2
        exit 2
    fi
done

# --- reference の作成(作成・更新の共通処理) ---
make_reference() {
    mkdir -p "$refdir"
    cp -p "$param" "$refdir"/
    for f in "$@"; do
        cp -p "$resdir/$f" "$refdir"/
    done

    # 環境記録(比較対象ではないので env/ に分離)
    local envdir=$refdir/env
    mkdir -p "$envdir"
    cp -p ./Screen.log "$envdir"/ 2>/dev/null
    cp -p ../../make.inc "$envdir"/ 2>/dev/null
    {
        echo "date      : $(date '+%Y-%m-%d %H:%M:%S')"
        echo "host      : $(hostname)"
        echo "user      : $USER"
        echo "pwd       : $PWD"
        echo "a.out     : $(readlink -f ./a.out 2>/dev/null)"
        echo "mode      : $(ls ../../src/.mode_* 2>/dev/null | sed 's/.*\.mode_//')"
        echo "modules   : ${LOADEDMODULES:-（module未使用）}"
        ldd "$(readlink -f ./a.out)" 2>/dev/null | grep -iE 'mpi|gfortran|ifcore|nvf' \
            | sed 's/^/lib       : /'
    } > "$envdir/BUILDINFO.txt"
}

# --- 更新モード ---
if [ $update -eq 1 ]; then
    rm -rf "$refdir"
    make_reference "$@"
    echo "=== REFERENCE UPDATED: 今回の結果を新しい基準として保存しました ==="
    echo "    (結果の妥当性をプロット等で確認してから信頼してください)"
    exit 0
fi

# --- 初回: reference 作成 ---
if [ ! -d "$refdir" ]; then
    make_reference "$@"
    echo "=== REFERENCE CREATED: 比較対象がないため今回の結果を基準として保存しました ==="
    echo "    (初回のため比較は行っていません。結果の妥当性を必ず確認してください)"
    exit 0
fi

# --- param.txt の一致確認(! コメントと空白を正規化して比較) ---
norm_param() {
    sed -e 's/!.*//' -e 's/[[:space:]]\{1,\}/ /g' -e 's/^ //' -e 's/ $//' "$1" \
    | grep -v '^$'
}
if ! diff <(norm_param "$param") <(norm_param "$refdir/$param") > /dev/null 2>&1; then
    echo "=== SKIP: param.txt が reference と異なるため比較できません ==="
    echo "    条件変更が意図したものなら ./Run.sh -u で reference を更新してください"
    exit 2
fi

# --- ファイルごとの比較 ---
if [ -n "$SKIPCOLS" ]; then
    echo "      (列 $SKIPCOLS は比較から除外)"
fi
status=0
for f in "$@"; do
    cf=$resdir/$f
    rf=$refdir/$(basename "$f")
    if [ ! -e "$rf" ]; then
        echo "FAIL: $f (reference 内に存在しません)"
        status=1
        continue
    fi

    if cmp -s "$cf" "$rf"; then
        echo "PASS: $cf (完全一致)"
        continue
    fi

    # 完全一致でない場合: トークン単位の数値比較(許容誤差付き)
    awk -v rtol="${RTOL:-0}" -v atol="${ATOL:-0}" -v ulp="${ULP:-0}" \
        -v skipcols="${SKIPCOLS:-}" '
        BEGIN {
            nsk = split(skipcols, sk, ",")
            for (m = 1; m <= nsk; m++) {
                c = sk[m] + 0
                if (c > 0) skipset[c] = 1
            }
        }
        function abs(x) { return x < 0 ? -x : x }
        function isnum(s) {
            return (s ~ /^[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eEdD][+-]?[0-9]+)?$/)
        }
        # 印字表現から「最終表示桁1つ分」の大きさ(量子)を求める
        #   12.1298 → 1e-4,  148225 → 1,  1.23e-05 → 1e-07(小数2桁+指数-5)
        function tokquantum(s,   t, epos, mant, ex, d) {
            t = s
            gsub(/[dD]/, "e", t)
            epos = index(t, "e")
            ex = 0
            mant = t
            if (epos > 0) {
                ex = substr(t, epos + 1) + 0
                mant = substr(t, 1, epos - 1)
            }
            d = 0
            if (index(mant, ".") > 0) d = length(mant) - index(mant, ".")
            return 10^(ex - d)
        }
        NR == FNR {
            nref_tok[FNR] = split($0, t)
            for (i = 1; i <= nref_tok[FNR]; i++) ref[FNR, i] = t[i]
            nref = FNR
            next
        }
        {
            ncur = FNR
            n = split($0, t)
            if (FNR > nref || n != nref_tok[FNR]) {
                nbad++
                if (msg == "") msg = "行 " FNR ": 行数または列数が不一致"
                next
            }
            for (i = 1; i <= n; i++) {
                if (i in skipset) continue
                a = ref[FNR, i]; b = t[i]
                ga = a; gb = b
                sub(/%$/, "", ga); sub(/%$/, "", gb)
                if (isnum(ga) && isnum(gb)) {
                    q = tokquantum(ga)
                    gsub(/[dD]/, "e", ga); gsub(/[dD]/, "e", gb)
                    x = ga + 0; y = gb + 0
                    d = abs(x - y)
                    s = (abs(x) > abs(y) ? abs(x) : abs(y))
                    tol = atol + rtol * s + ulp * q * 1.0001
                    if (d > tol) {
                        nbad++
                        rd = (s > 0 ? d / s : 0)
                        if (rd >= maxrd) {
                            maxrd = rd
                            msg = "行 " FNR " 列 " i ": " a " vs " b
                        }
                    } else if (d > 0) {
                        nflip++    # 許容内の微小差(最終桁ズレ等)を数える
                    }
                } else if (a != b) {
                    nbad++
                    if (msg == "") msg = "行 " FNR " 列 " i ": \"" a "\" vs \"" b "\""
                }
            }
        }
        END {
            if (ncur != nref) {
                nbad++
                if (msg == "") msg = "行数不一致 (ref:" nref " vs now:" ncur ")"
            }
            if (nbad > 0) {
                printf("      不一致 %d 箇所, 最大相対差 %.3e (%s)\n", nbad, maxrd, msg)
                if (nflip > 0) printf("      (ほかに許容内の微小差 %d 箇所)\n", nflip)
                exit 1
            }
            if (nflip > 0) printf("      許容内の微小差 %d 箇所 (ULP=%s RTOL=%s ATOL=%s)\n", nflip, ulp, rtol, atol)
            exit 0
        }
    ' "$rf" "$cf"

    if [ $? -eq 0 ]; then
        echo "PASS: $cf (許容誤差内)"
    else
        echo "FAIL: $cf"
        status=1
    fi
done

if [ $status -eq 0 ]; then
    echo "=== 回帰テスト PASS ==="
else
    echo "=== 回帰テスト FAIL: 意図した変更なら ./Run.sh -u で reference を更新してください ==="
fi
exit $status
