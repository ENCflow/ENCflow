#!/bin/bash
# =====================================================================
# 回帰テスト: reference の作成・比較
#   使い方(各テストディレクトリの Run スクリプトから、実行成功後に):
#     ../Compare_ref.sh Log.txt              比較(なければ作成)
#     ../Compare_ref.sh -u Log.txt           reference を今回の結果で更新
#     RTOL=1e-8 ../Compare_ref.sh Log.txt    許容誤差付き比較(MPI版など)
#
#   カレントディレクトリの param.txt と指定ファイル群を ./reference と
#   比較する。param.txt が不一致なら比較不能として報告する。
#
#   環境変数:
#     RTOL : 数値の相対許容誤差 (既定 0 = 完全一致を要求)
#     ATOL : 数値の絶対許容誤差 (既定 0)
#
#   戻り値: 0=PASS または reference 作成/更新, 1=FAIL, 2=比較不能
# =====================================================================
refdir=reference
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

# --- 更新モード ---
if [ $update -eq 1 ]; then
    rm -rf "$refdir"
    mkdir -p "$refdir"
    cp -p "$param" "$@" "$refdir"/
    echo "=== REFERENCE UPDATED: 今回の結果を新しい基準として保存しました ==="
    echo "    (結果の妥当性をプロット等で確認してから信頼してください)"
    exit 0
fi

# --- 初回: reference 作成 ---
if [ ! -d "$refdir" ]; then
    mkdir -p "$refdir"
    cp -p "$param" "$@" "$refdir"/
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
status=0
for f in "$@"; do
    if [ ! -e "$refdir/$f" ]; then
        echo "FAIL: $f (reference 内に存在しません)"
        status=1
        continue
    fi

    if cmp -s "$f" "$refdir/$f"; then
        echo "PASS: $f (完全一致)"
        continue
    fi

    # 完全一致でない場合: トークン単位の数値比較(許容誤差付き)
    awk -v rtol="${RTOL:-0}" -v atol="${ATOL:-0}" '
        function abs(x) { return x < 0 ? -x : x }
        function isnum(s) {
            return (s ~ /^[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eEdD][+-]?[0-9]+)?$/)
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
                a = ref[FNR, i]; b = t[i]
                ga = a; gb = b
                sub(/%$/, "", ga); sub(/%$/, "", gb)
                if (isnum(ga) && isnum(gb)) {
                    gsub(/[dD]/, "e", ga); gsub(/[dD]/, "e", gb)
                    x = ga + 0; y = gb + 0
                    d = abs(x - y)
                    s = (abs(x) > abs(y) ? abs(x) : abs(y))
                    if (d > atol + rtol * s) {
                        nbad++
                        rd = (s > 0 ? d / s : 0)
                        if (rd >= maxrd) {
                            maxrd = rd
                            msg = "行 " FNR " 列 " i ": " a " vs " b
                        }
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
                exit 1
            }
            exit 0
        }
    ' "$refdir/$f" "$f"

    if [ $? -eq 0 ]; then
        echo "PASS: $f (許容誤差内: RTOL=${RTOL:-0} ATOL=${ATOL:-0})"
    else
        echo "FAIL: $f"
        status=1
    fi
done

if [ $status -eq 0 ]; then
    echo "=== 回帰テスト PASS ==="
else
    echo "=== 回帰テスト FAIL: 意図した変更なら ./Run.sh -u で reference を更新してください ==="
fi
exit $status
