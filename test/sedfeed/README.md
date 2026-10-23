# test/sedfeed — 区間流入への給砂

[English](en/README.md)

掃流砂・浮遊砂の給砂 3 方式(developer.md §84.9、docs/meander_plan.md §3.6a)の検定。

## 設定

幅 5 セルの直線水路(Δx = 1 m、長さ 300 m、勾配 0.002、n = 0.03、両岸は +2 m の
乾いた地盤、土層厚 2 m で全域可動、`f_opening_dynamic = 2` で等流は Manning に
一致)。西端の区間流入 Q = 2.35 m³/s(等流水深 0.5 m)、東辺は自由流出(qb 構成は
壁)。d50 = 3 mm、morfac = 10(cseq は浮遊砂 0.2 mm、morfac = 1)。

| 構成 | 設定 | 役割 |
|---|---|---|
| nofeed | fluv_bcfeed = 0 | 無給砂。上流端から河床低下波 |
| feed1 | fluv_bcfeed = 1、fluv_bcfeed_fac = 1 | 容量給砂。流入面の供給 = 流入セルの正味流出 → 入口の河床が固定 |
| feed05 | 倍率 0.5 | 入口の低下が減る(比例はしない。入口に穴ができると正味流出が減り供給も減る) |
| qb | inflow_qb = 0.0005 m³/s(東辺は壁) | 掃流砂流砂量の源泉。台帳 (1 − λ) Σ(z − z0) A = ∫Qb dt × morfac |
| cseq | f_suspend = 1、inflow_cs_eq = 1 | 浮遊砂の平衡濃度給砂。流入濃度 = 流入セルの C_eq |

## 検定項目(Check_sedfeed.py)

1. 無給砂: 入口セルの Δz < −0.2 m。
2. 容量給砂(倍率 1): 入口セルの |Δz| < 1e-9(save の z で確認。供給 = 正味流出
   なので厳密に 0)、上流区間 x = 20〜120 m の平均 |Δz| < 0.03 m(無給砂 0.075)。
3. 倍率 0.5: 入口セルの低下が無給砂より小さい。
4. inflow_qb の台帳が相対 1e-9 で閉じる(save_qb/state.dat の z)。
5. 平衡濃度給砂: 流入列の hs/h が、流入セルの τ* から同じ式で評価した C_eq に
   ±1 % で一致。

Run_MPI.sh は同じ検定を MPI で行い、save_*_serial とのビット一致を見る
(厳密フラグで逐次・MPI を作って比較する。§28.3)。

## 使い方

```
make
./Run.sh            # 逐次(5 本で約 4 分)
./Run_MPI.sh 2      # MPI
```
