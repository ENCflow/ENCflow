# test/bmi_nest — BMI の多格子公開(ネスト系 = 1 component)の受け入れ試験

[English](en/README.md)

ネスト系をそのまま BMI の 1 つのモデルとして扱えること(bmi/README.md、
docs/users_guide/nest.md §BMI)を、test/nest_identity と同じ比 1:1 の自己ネスト
(wave 385²、子 121²、親セル 133..253、双方向 nest_fb = 2)で検査する。

```
./Run.sh          # 逐次のみ(Python 用の共有ライブラリは逐次ビルド)
```

1. bmi/ をビルド(libencflow_bmi.so と検証ドライバ test_encflow_bmi)。
2. `python3 ../../bmi/python/test_nest.py`(同一プロセスで順に initialize):
   - A: 単独ラン(param_single.txt)。t0 の水深を BMI で取り、子の足元を切り出して
     子の初期水深ファイル hinit_child.txt を書く。最終水深 hA と Log を保存。
   - B: ネスト(param_root.txt)。格子情報(`grids = [0, 1]`、形・刻み・原点。子の
     原点は親の原点 + 整列位置)、変数表(24 出力・8 入力、`~grid1` の修飾名)、
     var_grid を検査。毎ステップ、子の内部(帯の外)の水深と速さがルートの足元と
     ビット一致し、最終のルート水深が hA と一致し、Log が A と全行一致すること。
     誤用(存在しない格子・サイズ不一致・負の水深の set)が BmiError になること。
   - C: ネストを再度 initialize し、途中で子の h とルートの z を get してそのまま
     set(同値 set)。最終水深が hA と一致し Log が A と全行一致すること。
3. 静的ドライバ test_encflow_bmi でネストと単独を走らせ、Log が一致すること。
4. bmi-tester(インストール済みのとき)をネスト系に対して実行(check_bmi.sh)。

判定はすべて厳密一致(ULP 0)。恒等の構成図は test/nest_identity/figs/identity.png。
