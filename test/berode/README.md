# test/berode — 側岸侵食(f_berode)

[English](en/README.md)

水面より高い隣接セル(河岸面)を脚部セルの掃流力で後退させる側岸侵食
(developer.md §84.4。蛇行発達への拡張 docs/meander_plan.md の段 2)の検定です。
後退速度は超過掃流力型 E_b = K_b (τ*/τ*c,b − 1)^m、水没河岸高 h_w(脚部の
水深)× 通過幅の体積を河岸セルから脚部セルへ保存的に移します(以後の
掃流砂が運ぶ)。地形・流れは [test/bankface](../bankface/) と同じ
(幅 10 セルの直線水路、両岸 +2 m の乾いた河岸、閉領域のダム破壊流)。

## 構成

| 項目 | 値 |
|---|---|
| 地形・流れ | test/bankface と同一(`make_init.py` を共有) |
| 側岸侵食 | `f_berode = 1`、τ*c,b = 0.05、m = 1。`param_kb1.txt` K_b = 1e-5 m/s、`param_kb2.txt` K_b = 2e-5 m/s |
| 定着との結合 | `param_fix0.txt` kb1 + 定着(T_fix = 0.001 h、c_τ = 100)で `fix_ctau_bank = 0`、`param_fix1.txt` 同じ設定で既定(c_τ,b = c_τ)。developer.md §84.13 |
| 崩落土塊との結合 | `param_slump.txt` kb1 + 崩落と崖錐の河岸モード(`f_rockfall = 1`、`rf_bank = 1`、H_c = 1.5 m < 河岸 2 m、崖錐の安息角 35°)+ 遮蔽 `berode_hcover = 0.1 m`、`param_slump0.txt` 同じ設定で遮蔽なし。developer.md §84.17 |
| 掃流砂 | 芦田・道上式、d50 = 1 mm、土層 10 m(bankface と同じ) |
| 時間 | dt = 0.05 s、60 s |

| ファイル | 内容 |
|---|---|
| `Check_berode.py` | (1) 体積保存 |Σ(z − z₀)| < 1e-9、(2) 水路に接する河岸 2 列(120 セル)がすべて Δz < 0 で、接しない河岸は厳密に 0、(3) 河岸の損失体積の比 loss(2K_b)/loss(K_b) = 2 ± 2%(侵食則の線形性)、(4) 共動更新の恒等、(5) 定着の河岸係数: fix0 の z は kb1 と厳密一致、fix1 の河岸損失は kb1 の 5 % 未満、(6) 崩落土塊: slump / slump0 の体積保存・共動更新、崖錐 ht ≥ 0 で水路の行(脚部)にだけ積もる、(7) 遮蔽: slump の側岸侵食の台帳が slump0 の 0.1 倍未満、(8) 搬出: 終端の崖錐の総量が崩落の台帳より小さい(掃流砂が運び去った分)|

## 実行

```bash
make
./Run.sh          # 入力生成 → K_b, 2K_b → Check(数秒)
./Run_MPI.sh 4    # MPI。state.dat が逐次とバイト一致するのが規律
```

## 所見(2026-10-17)

| 検定 | K_b = 1e-5 | K_b = 2e-5 |
|---|---|---|
| Σ(z − z₀) | 4.6e-13 | −6.4e-13 |
| 河岸の損失体積 | 0.206 m·cell | 0.412 m·cell(比 1.998) |
| 接する河岸の最小 Δz | −3.4 mm | −6.9 mm |

- 脚部の掃流力が同じ間は後退量が K_b に比例する(比 1.998。2 倍で脚部に
  堆積する土砂が増え、わずかに非線形)。
- K_b に既定値はなく(校正値。文献の標準値を置かない)、明示指定が必要。
- MPI np = 2, 4 は逐次とバイト一致、-fcheck=all np=2 正常。

## 所見(2026-10-23。崩落土塊)

| 検定 | slump(h_cover = 0.1 m) | slump0(遮蔽なし) |
|---|---|---|
| 崩落の台帳(かさ) | 30.6 m³ | 30.4 m³ |
| 側岸侵食の台帳 | 0.002 m³ | 0.299 m³(kb1 単独は 0.367 m³·cell の河岸損失) |
| 終端の崖錐 Σht | 18.8 m³ | — |

- 河岸 2 m は H_c = 1.5 m を超えるので直ちに崩れ、崖錐 0.25 m が脚部(水路の両端の行)を
  覆う。遮蔽ありでは崖錐 ≥ h_cover の脚部で河岸面に掃流力が届かず、側岸侵食は 0.007 倍。
  崖錐は掃流砂の流出で 60 s に 12 m³ 減る(搬出)。
- MPI np = 2, 4 は state.dat と geomorph_rockfall.dat が逐次とバイト一致。

## 関連文書

- developer.md §84.4、docs/meander_plan.md §3.3
- [docs/users_guide/geomorph.md](../../docs/users_guide/geomorph.md) — `f_berode`、`berode_kb`、`berode_tausc`、`berode_m`
