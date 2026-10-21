# test/berode — 側岸侵食(f_berode)

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
| 掃流砂 | 芦田・道上式、d50 = 1 mm、土層 10 m(bankface と同じ) |
| 時間 | dt = 0.05 s、60 s |

| ファイル | 内容 |
|---|---|
| `Check_berode.py` | (1) 体積保存 |Σ(z − z₀)| < 1e-9、(2) 水路に接する河岸 2 列(120 セル)がすべて Δz < 0 で、接しない河岸は厳密に 0、(3) 河岸の損失体積の比 loss(2K_b)/loss(K_b) = 2 ± 2%(侵食則の線形性)、(4) 共動更新の恒等、(5) 定着の河岸係数: fix0 の z は kb1 と厳密一致、fix1 の河岸損失は kb1 の 5 % 未満 |

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

## 関連文書

- developer.md §84.4、docs/meander_plan.md §3.3
- [docs/users_guide/geomorph.md](../../docs/users_guide/geomorph.md) — `f_berode`、`berode_kb`、`berode_tausc`、`berode_m`
