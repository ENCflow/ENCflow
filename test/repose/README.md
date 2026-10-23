# test/repose — 安息角崩落(f_repose)

[English](en/README.md)

乾いた 45° の砂山(頂上 3 m、閉領域、水なし)が安息角 30° まで崩れる
検定です(developer.md §84.4。蛇行発達への拡張 docs/meander_plan.md の段 2)。
隣接セル間の勾配が tanφ_r を超えた分の高さ差を、1 更新に `repose_relax`/2/8
の割合で高い側から低い側へ移します(8 方向同時でも行き過ぎない保存形の
緩和。1 更新 1 スイープ)。

## 構成

| 項目 | 値 |
|---|---|
| 領域・格子 | 41 m × 41 m、41 × 41 セル(Δx = 1 m)、四周壁 |
| 地形 | 中央の円錐(側面勾配 1.0 = 45°、頂上 3 m)。`make_init.py` |
| 設定 | `f_repose = 1`、φ_r = 30°、relax = 0.5、変動上限 0.05 m、土層 10 m。掃流砂なし |
| 時間 | dt = 0.1 s、60 s(600 更新)。終了時に `save/state.dat` |

| ファイル | 内容 |
|---|---|
| `Check_repose.py <save>` | (1) 体積保存 |Σ(z − z₀)| < 1e-9、(2) 終端の最大勾配(軸・対角)≤ tan30° + 1e-4、(3) 頂上が 0.5 m 以上下がる、(4) 共動更新の恒等 |

## 実行

```bash
make
./Run.sh          # 入力生成 → 実行(1 秒)→ Check
./Run_MPI.sh 4    # MPI。state.dat が逐次とバイト一致するのが規律
```

## 所見(2026-10-17)

| 検定 | 値 |
|---|---|
| Σ(z − z₀) | 1.8e-14 m·cell |
| 最大勾配 | 0.577350(= tan30° に 1e-7 で収束) |
| 頂上 | 3.00 → 2.08 m(移動体積 7.9 m³) |
| 共動更新 | 2.1e-14 m |

中央行の断面は 0, 0.35, 0.93, 1.51, 2.08, 1.51, 0.93, 0.35, 0 m と、
対角方向も含めて 30° の円錐になります。MPI np = 2, 4 は逐次とバイト一致。

## 関連文書

- developer.md §84.4、docs/meander_plan.md §3.3
- [docs/users_guide/geomorph.md](../../docs/users_guide/geomorph.md) — `f_repose`、`repose_phi`、`repose_relax`
