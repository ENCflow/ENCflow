# test/rockfall — 崩落と崖錐(f_rockfall)の検定

平地の上の四角い台地(一辺 20 m、高さ 10 m、垂直な自由面)に、水も降雨もなく
**崩落と崖錐** `f_rockfall`(developer.md §48.7)だけを働かせます。自由面 10 m が
限界高さ H_c = 4 m を超えるので縁が崩落し、落下した分が崖錐(安息角 35°)として
裾に広がります。

| 項目 | 値 |
|---|---|
| 領域・格子 | 41 × 41 m、Δx = 1 m(四周壁の閉領域) |
| 地形 | make_init.py: 台地 z = 10 m(|x|, |y| ≤ 10 m)、周囲 z = 0 |
| 崩落 | rf_hc = 4 m、rf_phi = 35°、rf_relax = 0.5、fluv_dzmax = 0.5 m |
| 時間 | dt = 0.1 s、60 s(地形更新 600 回、morfac = 1) |

検定(Check_rockfall.py。save/state.dat の z・sd と result/Ht9998.txt):

1. 土砂体積保存: |Σ(z − z₀)| < 1e-9(結果 1e-13)
2. 終端の 8 近傍の最大高さ差 ≤ H_c + 1e-3(緩和の幾何収束の残差 1e-4 程度を許す。窓版は 1e-2)
3. 崖錐の収支: 全セルで ht ≥ (z − z₀)⁺(正味の堆積は崖錐として記録される)、Σht > 0
4. 共動更新: max|(sd − sd₀) − (z − z₀)| < 1e-10

窓版(param_rc.txt、`rf_rc = 3 m`): 自由面の高さを 3 セルの正方形窓内の最低点との落差で
測る規則の検定。終端では、崖錐の安息角より急なエッジを持つセルの窓内落差が H_c 以下に
なります(Check_rockfall.py に `rc=3` を渡す)。Run.sh / Run_MPI.sh は両方を実行します。

支え方式(param_face.txt、`rf_fface = 0`、窓 `rf_rc = 3 m`): 崩落を「面の頂の柱が脚部まで
落ちる」柱の崩落にする規則の検定(乾式侵食なしなので倍率は使わない)。柱は 1 本ずつ落ち、
落ちた柱の岩盤は崖錐の上端の高さの棚として埋もれ、崖錐が厚くなって窓内落差が H_c 以下に
なると静止します(1500 更新で収束)。検定は (2) の対象を「上に H_c より高い段がない(始まり
うる)セル」に限り、(6) 崖錐のないセルに安息角より急な段差が残る(岩盤の面)を加えます
(`rc=3 face=1`)。MPI では state.dat に加えて私有 save geomorph_rockfall.dat(崖錐の厚さと
崩落中の柱のフラグ)も逐次と比較します。

海セル版(param_sea.txt、`make_init.py --sea`): 西側 x < 10 m を海セル(sw = 1、z = 0)にし、
台地の西壁が海に面する構成。海へ落ちた分は系外へ出るので、検定は (1) 陸の体積減少 =
台帳「rockfall exported to sea cells」、(5) 海セルの z 不変、に置き換わります。

```bash
make
./Run.sh            # 逐次 + 検定(save/ を save_serial/ に複製。窓版・支え方式・海セル版も)
./Run_MPI.sh 2      # MPI + 検定 + save/state.dat の逐次とのビット一致確認(窓版・支え方式・海セル版も)
./Run_MPI.sh 4
```

## 関連

- [test/repose](../repose/)(安息角崩落。同じ数値形)、developer.md §48.7・§84.4
- [docs/users_guide/geomorph.md](../../docs/users_guide/geomorph.md) — `f_rockfall`
- 動く実例: [examples/mesa](../../examples/mesa/)(キャップロックの崖の後退と崖錐)
