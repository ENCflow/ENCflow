# examples/ — 設定ファイルのサンプルと例題

[English](README.en.md)

ENCflow の使い方を学ぶための例題集です。各ディレクトリに README と
パラメータファイル、入力を作るスクリプト、図化スクリプトが入って
います。回帰テストの基準を持つ検証ケースは [test/](../test/README.md)、
手順を追って学ぶ教材は [tutorials/](../tutorials/) にあります。

実行の型はどの例題も同じです。

```bash
cd examples/<name>
make            # bin/ の実行ファイルへのリンクと入力の生成
./encflow param.txt
python3 plot_results.py   # 図化(用意されている例題のみ)
```

| ディレクトリ | 内容 | 主な機能 |
|---|---|---|
| [List_samples/](List_samples/) | 全 namelist の注釈付き見本(1 ファイル 1 グループ。en/ に英語版) | 全機能 |
| [benchmark/](benchmark/) | 解析解のある降雨流出ベンチマーク 3 題。平面斜面 h-plane、V 字流域 v-shaped、V 字谷 v-valley | 浅水流・降雨 |
| [badland/](badland/) | 台地と急崖への降雨で谷が刻まれるバッドランド型の地形発達 | 乾式斜面侵食 f_splash |
| [ashfall_lahar/](ashfall_lahar/) | 降灰 → 降雨 → 灰層の侵食による泥流(ラハール)の発生と堆積 | 土石流 f_debris、降雨 |
| [landslide_tsunami/](landslide_tsunami/) | 地滑り・土石流の水域突入と津波。陸上崩壊と海底地滑りの 4 パターンと非静水圧版 | 動く底層 f_bedslide、非静水圧補正 |
| [tsunami_fault/](tsunami_fault/) | 断層パラメータから津波を発生させる。静水圧・瞬時変位・非静水圧の比較と座標指定の各パターン | 規定底面運動 fn_bedmotion、utils/fault2disp |
| [tsunami_coast/](tsunami_coast/) | 沿岸の沈降・隆起と沖の断層津波の時間差。沈降した湾奥平野の浸水 | 規定底面運動 fn_bedmotion |
| [nest_reflect/](nest_reflect/) | 比 3・5 の双方向ネスト格子の界面を横切るガウス波。一様細格子との誤差・反射率 | ネスティング fn_nest(docs/users_guide/nest.md) |
| [tsunami_town/](tsunami_town/) | 津波の市街地遡上による木造家屋の破壊と瓦礫の流動・堆積 | 家屋破壊・瓦礫 fn_bldgdebris、潮位 |
| [timberyard/](timberyard/) | 高潮による貯木場からの材木流入(伊勢湾台風型) | 流木 fn_driftwood、潮位 |
| [sewer_hybrid/](sewer_hybrid/) | 幹線 1 本と枝管網を同じ管路連続体層で表す都市排水の模式実験 | 管路連続体層 f_gwconduit |
| [qanat/](qanat/) | カナート(横坑集水)の理想化ケース | 管路連続体層、地下水 |

計算したい現象から機能の組み合わせを引くには
[用途集](../docs/users_guide/usecases.md)、各機能の設定は
[ユーザーガイド](../docs/users_guide.md) を参照してください。
