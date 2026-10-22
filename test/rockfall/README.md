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
2. 終端の 8 近傍の最大高さ差 ≤ H_c + 1e-3(緩和の幾何収束の残差 1e-4 程度を許す)
3. 崖錐の収支: 全セルで ht ≥ (z − z₀)⁺(正味の堆積は崖錐として記録される)、Σht > 0
4. 共動更新: max|(sd − sd₀) − (z − z₀)| < 1e-10

```bash
make
./Run.sh            # 逐次 + 検定(save/ を save_serial/ に複製)
./Run_MPI.sh 2      # MPI + 検定 + save/state.dat の逐次とのビット一致確認
./Run_MPI.sh 4
```

## 関連

- [test/repose](../repose/)(安息角崩落。同じ数値形)、developer.md §48.7・§84.4
- [docs/users_guide/geomorph.md](../../docs/users_guide/geomorph.md) — `f_rockfall`
- 動く実例: [examples/mesa](../../examples/mesa/)(キャップロックの崖の後退と崖錐)
