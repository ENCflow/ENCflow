# test/dissol — 石灰岩の溶食(f_dissol)の解析検証とリスタート往復

[English](en/README.md)

地形変化モジュールの石灰岩の溶食(`&list_geomorph` の `f_dissol = 1`、
[ユーザーガイドの地形変化の章](../../docs/users_guide/geomorph.md#石灰岩の溶食f_dissol))
の検証ケースです(developer.md §86、docs/karst_plan.md §3)。溶食は
「岩に入る水の量 × k_d(= c_eq/ρ_r)× morfac」だけ z を下げる局所・線形の
更新なので、水量が解析的に決まる構成(A〜G)で終了時の地盤高を検定します。

| 構成 | ファイル | 水量の源 | 解析値 |
|---|---|---|---|
| A 面的溶食 | `param.txt` | バケツ浸透 36 mm/h(= 1e-5 m/s)を 100 s → I = 1e-3 m。dt_geomorph = 5 s(100 ステップの積算)、morfac = 1e4、残渣率 0.25 | w = 4e-5 × 1e-3 × 1e4 = 4e-4 m → Δz = −3e-4 m、Δsd = +1e-4 m |
| B 集中溶食(ドリーネ項) | `param_sink.txt` | [test/conduit](../conduit/) の模式実験 A(一様枡密度の管路層へ湛水が落ちて平衡)に、中心 5×5 だけ可溶(`data_dissol/sol.txt`)の吸込穴項を重ねる。dt_geomorph = tt(最終ステップに 1 回)、f_sink = 0.5 | Δz(中心) = −4e-5 × 0.5 × hgc(150 s) × 1e4 = −0.2 × Hgc0003、Δz(外側) = 0 |
| C 降雨源 | `param_rain.txt` | 地下水なし、一様降雨 30 mm/h を 3600 s(dissol_src = 2)。morfac = 1000 | Δz = −4e-5 × 0.03 × 1000 = −1.2e-3 m |
| D 側方溶食 | `param_lat.txt` | 平坦 0 m の中央 3×3 だけ −1 m の窪み(`data_dissol/zpit.txt`)に水位 −0.5 m の湛水(f_htype = 2)。バケツ浸透で窪みの 9 セルに W = 4e-4 m の溶解能、dissol_lat = 0.4 | 床 (1−p)W、周囲 16 セルの壁 pW·L_k/ΣL(軸 1・斜め 2/(2+√2)。karst_plan §2.5)。総和 9W |
| F 表面流源 | `param_surf.txt` | 裸岩(sd0 = 1e-3 m)に一様降雨 30 mm/h を 1 時間、バケツ浸透 10 mm/h、dissol_src = 3(fsurf = 0.3、sdsurf = 0.1)。morfac = 1000 | Δz = −k_d (I + fsurf·fb·(P − I)) morfac = −4e-5 × 0.01594 × 1000 = −6.376e-4 m(全セル)。rt1 → rt2 の往復も検定 |
| G 安全弁 | `param_clip.txt` | A と同じ浸透(溶食 2e-5 m/更新)に dissol_dzmax = 1e-5 | Δz = −20 × 1e-5 = −2e-4 m(全セル。超過分の溶解能は捨てる) |
| E 自動配分 | `param_lata.txt` | D と同じ窪みに、微小な一様降雨 0.36 mm/h を降雨源として全セルに W = 4e-4 m、dissol_lat = −1(濡れ面の面積比) | 窪みセルごとに p = hΣL/(hΣL + Δx²)(h = 0.5 m、Δx = 2 m)。乾いたセルは床に W。総和 441W(相対 1e-4) |
| リスタート往復 | `param_rt1.txt` → `param_rt2.txt` | A を 52 s(更新間隔 5 s の途中)で save し 100 s まで継続 | 通し計算(`save_all`・`result`)と state.dat・geomorph_dissol.dat・Z9998.bil がバイト一致 |

k_d = c_eq/ρ_r = (100 mg/L)/(2500 kg/m³) = 4e-5 m/m は `param*.txt` と
`Check_analytic.py` の両方に書かれています。変えるときは同時に変えてください。
bil 出力(float32)を読むので `f_output_mode = 3` が必要です。

| ファイル | 内容 |
|---|---|
| `param.txt` / `param_sink.txt` / `param_rain.txt` / `param_lat.txt` / `param_lata.txt` / `param_surf.txt` / `param_clip.txt` | 構成 A / B / C / D / E / F / G |
| `param_rt1.txt` / `param_rt2.txt` | A のリスタート分割(前半 0→52 s、後半 52→100 s) |
| `param_surf_rt1.txt` / `param_surf_rt2.txt` | F のリスタート分割(1830 s = 更新間隔の途中で保存。降雨積算 frn の私有 save の検定) |
| `data_dissol/sol.txt` | B の可溶率マップ(中心 5×5 = 1、他 0) |
| `data_dissol/zpit.txt` | D の地形(中央 3×3 = −1 m、他 0) |
| `Check_analytic.py` | Z9998(・Sd9998・Hgc0003)の bil を読んで解析値と比較(相対誤差 1e-6。D の総和は float32 の丸めのため 1e-3) |
| `Run.sh` / `Run_MPI.sh N` | 全構成の実行 + 解析検定 + 往復検定(+ A の Log.txt の reference 比較) |

## 実行

```bash
make
./Run.sh            # 逐次: A〜G・往復を実行し解析検定と往復検定。A の Log.txt は reference と比較(ULP = 1)
./Run_MPI.sh 4      # MPI: A〜G を実行し解析検定。Log.txt は逐次 reference に ULP = 0。
                    # 逐次の result* を result*_serial に複製しておくと bil のバイト比較も行う
```

## 検証記録(2026-10-21。gfortran 13.3 / Open MPI、-O2)

- 解析検定: A・B・C とも bil の全セルが解析値に一致(最大相対誤差 6e-8 以下
  = float32 の丸め)。D(2026-10-22)は床・壁の全セルが配分式に一致し、
  総溶解能 9W が保存(float32 の丸め内)。np = 4 では窪みが帯をまたぐ。
  E(自動配分)も同様に一致(p の相対誤差 1e-4 以内 = 降雨による h の変化分)。
  F(表面流源)は全セルが解析値に一致し、更新間隔の途中で save する往復が
  バイト一致(降雨積算の私有 save)。
- リスタート往復: 更新間隔の途中(52 s)の save → 継続が通し計算と
  state.dat・geomorph_dissol.dat・Z9998.bil でバイト一致(記録場の私有
  ファイルの検証)。
- MPI: np = 1, 2, 4 が逐次と Log.txt で ULP = 0、全 bil がバイト一致。
  -Og -fcheck=all の np = 2 で境界違反なし。
- 無効時(f_dissol なし): wave・conduit・chichibu・creep・splash が既存
  reference とビット一致。
