# test/splashsat — 凹地形増幅の飽和(spl_ksat)の解析検証

[English](en/README.md)

乾式斜面侵食 `f_splash` の凹地形増幅 1 + c κ の κ を有効曲率
κ̃ = κ / (1 + κ/κ_s) に置き換える **飽和形** `spl_ksat`(developer.md §48.6)の
解析検証です。x 方向に一様な放物線の谷 z = 0.05 (y − ly/2)²(ユーザールーチン
`parabolic_trough`。曲率 κ = 2a = 0.1 1/m が全セルで一定 — 2 次式の 5 点差分は
厳密)に一様降雨 30 mm/h、Green-Ampt 72 mm/h(全時間 h = 0)を与え、リル項を切って
(`spl_kt = 0`)雨滴項だけに増幅 `spl_ca = 10` m を掛けます。

| 量 | 値 |
|---|---|
| κ / κ_s / κ̃ | 0.1 / 0.1 / 0.05 1/m |
| Φ_A = 1 + ca κ̃ | 1.5(飽和なしなら 2.0) |
| Δz = P kr Φ_A T_geo | 8.333e-6 × 0.004 × 1.5 × 18,000 = **0.9 mm**(飽和なしなら 1.2 mm) |

境界行(j = 1, ny)は鏡像で κ が半分になるため、解析対象は内部行です。

```bash
make
./Run.sh                   # Log.txt(水の台帳)を reference と比較(ULP = 0)
python3 Check_analytic.py  # Sd0000 − Sd9998 の内部行を 0.9 mm と照合(PASS/FAIL)
./Run_MPI.sh 2; ./Run_MPI.sh 4
```

Check_analytic.py は内部行の全セルで理論値に機械精度で一致します。reference
(Log.txt)は水の台帳で、解析一致を根拠に確定しています。

## 関連

- [test/splash](../splash/)(増幅なしの解析検証)、[test/splashlc](../splashlc/)(波長選択)
- 動く実例: [examples/mesa](../../examples/mesa/)(崖の基部の段を残す)
