# test/dbrock — 土石流による岩盤侵食の検定

[English](en/README.md)

土石流のイベント計算(`f_debris = 1`)で、流れる混合体が岩盤を削る過程の検証ケースです。
岩盤下刻 `f_rockinc` の土石流の項(`rock_kdb`。
[ユーザーガイドの地形変化の章](../../docs/users_guide/geomorph.md#土石流による岩盤侵食rock_kdb)、
式は [解説](../../docs/users_guide/sediment.md#流水による岩盤下刻f_rockinc))を扱います
(docs/mountain_stream_plan.md §12、developer.md §88.18)。裸岩の低下速度は、準静的な
駆動応力の超過形

  E_d0 = f_r k_d max(τ_d/τ_cd − 1, 0)^m_d、 τ_d = ρ(1 + sC) g_e h_t tanθ

です。働くのは、濃い混合体(C ≥ db_cmin)が流れている(|V| ≥ db_vstop)セルだけです。
生成物は 1:1 で可動層 sd に入り(z は不変)、露出率 exp(−sd/H*) で自己被覆します。
reference は持たず、解析解・保存則・バイト一致・停止の表示で判定します。

## 構成

構成 db1・db3 の水路: 乾いた高い地盤(+2 m)に挟まれた幅 1 セルの直線水路(3 × 60 セル、
Δx = 1 m、南向きに勾配 0.2、n = 0.05)。北端から清水 0.5 m³/s と濃度 h_s/h = 0.5(C = 1/3)の
土砂を流し、南辺は自由流出です。交換なし(`f_dbed = 0`)・Manning 抵抗の混合体は約 60 s で
定常になるので、最初の地形更新を t = 100 s に置き、すべての更新が同じ定常の水理を見るように
します。k_d = 1e-3 m/s、τ_cd = 300 Pa(定常の τ_d ≈ 660 Pa)、m_d = 1.5、H* = 0.05 m です。
初期の被覆(0・0.02・0.04・0.06 m の繰り返し)と侵食性倍率(0〜2。9 行周期でずれる)は
行ごとに変えます。

| 構成 | ファイル | 内容 | 判定 |
|---|---|---|---|
| DB1 解析解 | `param_db1.txt` | 交換なしなので生成物はその場に溜まり、z も流れも変わらない。600 s で 6 回の更新 | 行 11〜50 の各セルで e^{H/H*} − e^{H0/H*} = E_d0 T/H* と相対 1e-9。倍率 0 の行は Ri = 0 で sd 不変。水路の z が不変 |
| DB1 更新間隔 | `param_db1_dtg.txt` | 更新間隔を 2 倍(200 s ごとに 3 回) | db1 と sd が相対 1e-12 |
| DB3 濃度の門 | `param_db3_cmin.txt` | db_cmin = 0.5 > C | どのセルも Ri = 0、sd 不変 |
| DB3 速度の門 | `param_db3_vstop.txt` | db_vstop = 10 m/s > \|V\| | どのセルも Ri = 0、sd 不変 |
| DB2 保存 | `param_db2.txt` | 四周壁の 10 × 40 セル。勾配 0.4 の斜面(y < 25 m)と平坦部。北の帯の土層 0.5 m を t = 1 s に流動化し、厚さ 2 cm の被覆の上を流下させる(E-D は高橋型、クーロン + Manning、φ = 30°、低速凝集)。20 s | 全固体 Σh_s A + (1 − λ)Σ(z − z0)A が 1e-10 m³ 以内で 0。可動層の固体 Σh_s A + (1 − λ)Σ(sd − sd0)A が (1 − λ) × 台帳(土石流が削った岩盤のかさ体積)と相対 1e-7。(sd − sd0) − (z − z0) = Ri が 1e-12 m 以内。台帳 > 1e-3 m³ |
| DB7 入力の誤り | `param_db7_kp.txt` ほか 4 つ | 土石流の構成に流水の剥離 / 閾値なし / db_cmin = 0 / f_debris なしで rock_kdb / 岩盤を削る過程なし | 初期化でそれぞれの表示で停止 |

| ファイル | 内容 |
|---|---|
| `make_init.py` | db1・db3 の水路の地形・初期の被覆・侵食性倍率と、db2 の箱の地形・土層厚・崩壊深の生成(定数は `param*.txt`・`Check_dbrock.py` と対で保守) |
| `Check_dbrock.py db1 / db3 / db2 LOG` | 上の判定(h・h_s・z・sd は save の state.dat、Ri は geomorph_rockinc.dat から倍精度で読む。DB2 の台帳は Screen ログの終了時の表示) |
| `Run.sh` / `Run_MPI.sh N` | 全構成の実行と検定。MPI は逐次の save(`save_*_serial`)と state.dat・geomorph_rockinc.dat をバイト比較する |

## 実行

```bash
make
python3 make_init.py   # 入力の再生成(同梱。変更したときだけ)
./Run.sh            # 逐次(約 1 分)
./Run_MPI.sh 4      # MPI(Run.sh の後に。save_*_serial とバイト比較)
```

## 検証記録(2026-10-27。gfortran 13.3 / Open MPI 4.1、既定の -Ofast ビルド)

- DB1: 解析解との max 相対差 1.4e-15(許容 1e-9)。τ_d = 660.1〜660.2 Pa、C = 1/3。更新間隔を
  2 倍にした構成との sd の max 相対差 2.3e-16。倍率 0 の 5 行は Ri = 0。水路の z の変化 3.6e-15 m。
- DB3: 濃度・速度の門の外では Ri と sd の変化がともに 0。
- DB2: 全固体 5.1e-14 m³。可動層の固体と (1 − λ) × 台帳の相対差 4.9e-10(台帳の表示は 9 桁)。
  (sd − sd0) − (z − z0) − Ri の最大 1.9e-14 m。土石流が削った岩盤 0.74 m³(最大 Ri 6.0 mm)。
- DB7: 5 構成とも初期化で停止。
- MPI(DB4): -fcheck=all の np = 2 で実行時エラーなし。-O2 のビルドで逐次と np = 1, 2, 4 の
  state.dat・geomorph_rockinc.dat がバイト一致。既定の -Ofast でも Run_MPI.sh 2・4 が全構成で
  逐次とバイト一致。
