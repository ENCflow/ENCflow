# bmi_dam — ダムの量の BMI 公開と外部運転の受け入れ試験

[English](en/README.md)

BMI でダム(`&list_struct_dam`)の水位・貯水量・流入・放流・スピルを読み、
外部運転(`f_dam_mode = 6`)と宣言したダムへ目標放流量を与えます
(developer.md §133、bmi/README.md「ダム」)。本ケースはそれを 4 つのダムで検査します。

領域は 24 × 10 セル(dx = dy = 10 m)。i = 2 の列に孤立した 1 セルの捕捉帯を
4 つ(j = 2, 4, 6, 8)置き、内部ソースで同じ三角形のハイドログラフ(基底 0.2 m³/s、
60 分に 1.7 m³/s、120 分に 0.2 m³/s へ戻る)を入れます。放流は i = 5〜24 の平坦な
閉じた池へ出します。HV は 4 つとも (100 m, 0) (105 m, 2.0×10⁴ m³) (112 m, 6.0×10⁴ m³)、
2 時間を dt = 1 s で計算します。

| ダム | 運転 | 検査 |
|---|---|---|
| 1 | 放流量の時系列(`f_dam_mode = 4`。段状 0.3 → 20 分に 0.6 → 60 分に 0.4 m³/s) | ダム 2 の比較の基準。外部運転ではないので、set した要素(999)は無視される |
| 2 | 外部運転(`dam_q0 = 0.3`)。Python が毎歩、ダム 1 と同じ段状の放流量を set する | ダム 1 の CSV と全行一致 |
| 3 | 外部運転(`dam_q0 = 0.2`)。見本の制御器 `bmi/python/dam_control.py`(貯水量を初期値へ戻す、上限 2 m³/s、目標の変化は 0.0004 m³/s/s 以内) | 目標の変化が毎歩その制限以内(洪水の流入の立ち上がりより遅いので、洪水の間は制限が効き続ける)、水位が 104 m ± 10 cm、実際の放流 = 目標 |
| 4 | 一定量放流方式 + 制限水位(`f_dam_mode = 1`、0.5 m³/s、`dam_hlim = 103`) | set した要素(999)は無視される |

そのほかに、変数表と格子(ダムの量 5 つと目標放流量。ダムの点の格子は
"unstructured" で、節点の座標は捕捉帯のセルの中心)、initialize 直後の値、
負の目標と長さの違う配列の拒否、get の値と同時刻のダム CSV の一致、閉じた系の
体積保存(Log の S)、外部運転のダムのない設定での再 initialize(目標放流量が
表になく、set は BmiError)を検査します(`bmi/python/test_dam.py`)。

```sh
./Run.sh        # test_dam.py、dam_control.py、静的ドライバ、bmi-tester(あれば)
```

`dam_control.py` はコマンドとしても実行し、外部運転のダム 2・3 を初期の貯水量に
保つこと(最終水位が 104 m ± 10 cm)を確かめます。静的ドライバ
`test_encflow_bmi` は、目標放流量が入力表にあると、各歩の前に貯水量を初期値へ
戻す決定的な制御を set しながら完走します。入力データ data_bmi_dam/ は
`python3 make_data.py` で作り直せます。

MPI: `cd bmi && make clean && make MODE=mpi` の後、
`mpirun -np N ../../bmi/test_encflow_bmi_mpi param.txt` の result/dams/*.csv と
result/Log.txt が、逐次の静的ドライバ(`../../bmi/test_encflow_bmi param.txt`)の
結果と一致すること。
