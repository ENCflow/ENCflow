# test/rockfall — 岩盤の崩落(f_rockfall)の検定

地形変化モジュールの岩盤の崩落(`&list_geomorph` の `f_rockfall = 1`、
[ユーザーガイドの地形変化の章](../../docs/users_guide/geomorph.md#岩盤の崩落f_rockfall))
の検証ケースです(developer.md §87、docs/karst_plan.md §2.6)。安息角崩落
`f_repose`(土層を隣へ移す)の岩盤版で、基岩面 z − sd が隣接セルの地表より
tanφ_rock × 距離を超えて高い分を、岩 → 岩屑(受け手の土層 sd。かさ比 bulk)
として落とします。

| 項目 | 値 |
|---|---|
| 領域・格子 | 42 × 42 m、21 × 21 セル(Δx = 2 m)、四周壁、水なし |
| 初期地形 | 平坦 0 m の中央 1 セルだけ 10 m の岩柱(`data_rockfall/zpillar.txt`)。土層は裸岩を表す sd0 = 1e-3 m |
| 崩落 | φ_rock = 45°、relax = 1、bulk = 1.5、dzmax = 100 m(クリップなし)。毎ステップ更新を 10 回(dt = 0.1 s、1 s) |
| 漸化式 | v_k = relax (zb − z_w − tanφ dist_k)/(1 + bulk)/8(方向 k = 1..8)。供給側 z −= Σv_k(sd 不変)、受け手 z += bulk v、sd += bulk v |

`Check_rockfall.py` が同じ漸化式を独立に実装して Z9998・Sd9998(bil、
float32)と比較し、岩の体積の保存(Σ sd の増分 = bulk × V、Σ Δz =
(bulk − 1) × V)を見ます。岩柱の頂は 10 回で 10 → 3.53 m に下がります。

```bash
make
./Run.sh            # 逐次: 漸化式の検定 + Log.txt の reference 比較(ULP = 1)
./Run_MPI.sh 4      # MPI: 検定 + 逐次 reference に ULP = 0(+ result_serial との bil 比較)
```

## 検証記録(2026-10-22。gfortran 13.3 / Open MPI、-O2)

- 漸化式: z・sd の全セルが独立実装と一致(最大誤差 7e-8 m = float32 の丸め)。
  岩の体積は dz と sd の両方から 25.894 m³ で一致。
- MPI: np = 1, 2, 4 が逐次と Log.txt で ULP = 0、bil がバイト一致。
  -Og -fcheck=all の np = 2, 4 で境界違反なし(岩柱が帯の境界に接する)。
- 無効時(f_rockfall なし): dissol・wave が既存 reference とビット一致。
