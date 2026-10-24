# test/splashstrata — 乾式斜面侵食の水平層理(spl_strata)の解析検証

[English](en/README.md)

乾式斜面侵食 `f_splash` に**水平層理の侵食性倍率** `spl_strata`(層の下端標高と
倍率の表。developer.md §48.5)を与えたときの解析検証です。
[test/splash](../splash/) と同じ遷緩点付き斜面(slope_break: z = 0.4(30 − x)、
x ≥ 30 m で平坦)・同じ降雨 30 mm/h・Green-Ampt 72 mm/h(全時間 h = 0)で、
増幅なしの係数(kr = 0.004、kt = 0.02)に 3 層の倍率を重ねます。

| 層 | 標高 | 倍率 | 該当する列 |
|---|---|---|---|
| 3 | z ≥ 10 m | 0(削れないキャップロック) | x ≤ 4.5 m |
| 2 | 6 ≤ z < 10 m | 0.5 | x = 5.5〜14.5 m |
| 1 | 0 ≤ z < 6 m | 1 | x = 15.5〜29.5 m の斜面と平坦部 |

侵食深(≤ 1.8 mm)は層境界までの余裕(≥ 0.2 m)より十分小さいので各列は同じ層に
留まり、侵食深は解析的に Δz = f(z)·P·(kr + kt S)·T_geo(T_geo = 18,000 s)です。
係数は Δz が Sd 出力の印字桁(1e-4 m)の整数倍になるように選んであります。

| 列クラス | S | 理論 Δz (mm) |
|---|---|---|
| 硬層(倍率 0) | 0.4 | 0 |
| 倍率 0.5 の層 | 0.4 | 0.9 |
| 倍率 1 の斜面 | 0.4 | 1.8 |
| 遷緩点の列(x = 29.5 m。最急降下で面の勾配) | 0.2 | 1.2 |
| 平坦部 | 0 | 0.6 |

## 実行

```bash
make
./Run.sh                   # Log.txt(水の台帳)を reference と比較(ULP = 0)
python3 Check_analytic.py  # Sd0000 − Sd9998 を列クラス別に解析値と照合(PASS/FAIL)
./Run_MPI.sh 2; ./Run_MPI.sh 4
```

Check_analytic.py は全列クラスで理論値に機械精度(最大誤差 4e-16 m)で一致します。
reference(Log.txt)は水の台帳で、層理の有無に依らず test/splash と同じ降雨・浸透の
系なので、解析一致を根拠に確定しています。

## 関連

- [test/splash](../splash/)(層理なしの解析検証)、developer.md §48・§48.5
- [docs/users_guide/geomorph.md](../../docs/users_guide/geomorph.md) — `spl_strata`
- 動く実例: [examples/badland_round](../../examples/badland_round/)(硬軟互層の縞)
