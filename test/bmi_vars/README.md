# bmi_vars — 機能依存の BMI 変数と hg・swe の set の受け入れ試験

BMI の変数表は「その量を生産する機能が有効な格子にだけ載る」動的な表です
(developer.md §76、bmi/README.md「公開変数」)。本ケースはそれを 3 つの
構成で検査します。地形は平坦(z=0)・閉領域・一様降雨 36 mm/h・初期水深 5 cm。

| 構成 | 内容 | 検査 |
|---|---|---|
| param_none.txt | 機能なし | 地下貯留 hg・積雪 swe が変数表になく、get / set が BmiError。粗度 rn(常時存在。§77)は get = rn0、同値 set 受理・負値拒否 |
| param_full.txt | バケツ地下水(浸透能 10 mm/h)+ 気温 −5 ℃ + 積雪(初期 100 mm) | hg・swe が載る。値が解析値(毎ステップ一定増分)・分布出力(Hg/Sw/H)と一致。同値 set の不変性(Log 全行一致)。負値の set は BmiError |
| param_ga.txt | 同上だが Green-Ampt(土層厚 1 m) | hg・swe・sd が載る。hg の set は拒否(私有の累積浸透と不整合)、swe の set は受理 |

同一プロセスでの再 initialize(none → full → none)で表が作り直されることも検査します。

```sh
./Run.sh        # test_vars.py --set、静的ドライバ、bmi-tester(あれば)
```

MPI: `cd bmi && make clean && make MODE=mpi` の後、
`mpirun -np N ../../bmi/test_encflow_bmi_mpi param_full.txt` の result_full/Log.txt が
逐次の Log と一致すること。
