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
| [vz_tani2023/](vz_tani2023/) | 谷(2023)の VZ 流出モデルの再現: 論文の全 7 事例(小斜面の人工降雨 KIEX、ゼロ次谷 MREX・MR1、竜ノ口山 TY1・TY2、桐生 KI1・KI2)を同じ設定で再計算し、論文の計算流出強度・圧力水頭(HYDRUS-1D)と比べる。論文の数値は利用者が入手した PDF の図から取り出す(同梱しない) | 鉛直不飽和浸透(VZ)流出 fn_vz(柱の共有・土層厚の線形分布) |
| [badland/](badland/) | 台地と急崖への降雨で谷が刻まれるバッドランド型の地形発達。白色雑音からの谷の自己形成、谷間隔の選択則(spl_lc)、格子収束、深い谷と鋭い稜線の長期発達 | 乾式斜面侵食 f_splash(spl_lc・spl_zbase) |
| [badland_storm/](badland_storm/) | 浸透能を下げて豪雨時だけ表面流が現れる崖: 乾式侵食が止まるか、ガリー網に変わるか(badland の対照実験) | f_splash + f_wash・f_suspend、Green-Ampt、降雨時系列 |
| [badland_round/](badland_round/) | 稜線が丸く、低い丘ほどドーム状になるバッドランド(膨潤粘土型): 移流型の下刻とクリープ(拡散)の比が決める長さ尺度 L で、L より小さい丘から丸くなる(badland の「鋭い稜線」の対照)。水平層理の硬軟互層(spl_strata)で縞と段が出る対照も | f_splash + f_creep(+ spl_strata)、Green-Ampt |
| [mesa/](mesa/) | メサ・ビュートの形成: キャップロック(spl_strata)で平らな頂と垂直な崖の平行後退、台地の縮小 → 孤立丘 → 尖塔。層理なし・中間硬層・増幅の飽和・崩落と崖錐(窓版・支え方式 = 垂直な崖 + 段)の対照 | f_splash(spl_strata・spl_ksat)+ f_creep + f_rockfall(rf_rc・rf_fface)、Green-Ampt |
| [karst/](karst/) | 石灰岩台地のドリーネ群の形成: 代表豪雨の反復で、浸透水が面的に溶かし、窪みに集まった水が吸込穴から地下へ消える場所が選択的に深まる(カルスト地形の自己組織化と内陸排水) | 石灰岩の溶食 f_dissol、管路連続体層(吸込穴)、Green-Ampt、周期強制 t_cycle_c |
| [tower_karst/](tower_karst/) | 平野に残る裸岩の塔(タワーカルスト): 塔の雨が裾の平野で浸透して平野と裾だけが溶け、側方溶食と岩盤の崩落で壁が後退し、岩屑の裾野と堀ができる。取水が浸透能で頭打ちなので morfac を大きく取れる | 石灰岩の溶食 f_dissol(dissol_lat)、岩盤の崩落 f_rockfall、Green-Ampt の浸透能マップ、周期強制 |
| [ashfall_lahar/](ashfall_lahar/) | 降灰 → 降雨 → 灰層の侵食による泥流(ラハール)の発生と堆積 | 土石流 f_debris、降雨 |
| [landslide_tsunami/](landslide_tsunami/) | 地滑り・土石流の水域突入と津波。陸上崩壊と海底地滑りの 4 パターンと非静水圧版 | 動く底層 f_bedslide、非静水圧補正 |
| [tsunami_fault/](tsunami_fault/) | 断層パラメータから津波を発生させる。静水圧・瞬時変位・非静水圧の比較と座標指定の各パターン | 規定底面運動 fn_bedmotion、utils/fault2disp |
| [tsunami_coast/](tsunami_coast/) | 沿岸の沈降・隆起と沖の断層津波の時間差。沈降した湾奥平野の浸水 | 規定底面運動 fn_bedmotion |
| [levee_breach/](levee_breach/) | 高解像度 DEM の堤防(解像堤防)を規定底面運動で破堤させる。仮想壁面の &list_channel_breach との比較 | 規定底面運動 fn_bedmotion、河道の破堤 |
| [nest_reflect/](nest_reflect/) | 比 3・5 の双方向ネスト格子の界面を横切るガウス波。一様細格子との誤差・反射率 | ネスティング fn_nest(docs/users_guide/nest.md) |
| [tsunami_town/](tsunami_town/) | 津波の市街地遡上による木造家屋の破壊と瓦礫の流動・堆積 | 家屋破壊・瓦礫 fn_bldgdebris、潮位 |
| [timberyard/](timberyard/) | 高潮による貯木場からの材木流入(伊勢湾台風型) | 流木 fn_driftwood、潮位 |
| [sewer_hybrid/](sewer_hybrid/) | 幹線 1 本と枝管網を同じ管路連続体層で表す都市排水の模式実験 | 管路連続体層 f_gwconduit |
| [qanat/](qanat/) | カナート(横坑集水)の理想化ケース | 管路連続体層、地下水 |
| [meander/](meander/) | 氾濫原の中の正弦波状の河道の蛇行発達。外岸の後退と内岸砂州の成長、出水・低水の繰り返しによる砂州の定着、給砂による砂州の氾濫原化の 9 構成 | 掃流砂の方向補正 fluv_slope・f_secflow、側岸侵食 f_berode、安息角崩落 f_repose、定着 f_fixation、給砂 |
| [meander_cutoff/](meander_cutoff/) | 頸部の狭い蛇行ループが出水で短絡し、旧河道が滞水域になって出入口が埋まり始める | 同上 + 区間流入の時系列 |
| [delta/](delta/) | 給砂河川が静水の海盆に突入して作る河口デルタ。河口砂州 → 分岐 → ローブ成長 → 流路の乗り換え。砂泥比による扇状と鳥趾状、流量変動と定着(冠水減衰・河岸係数)による分流路の安定化の 5 構成(docs/delta_plan.md) | 海は通常セル+初期水位、容量給砂 fluv_bcfeed、浮遊泥 inflow_cs + f_bedfines、fluv_slope、f_repose、f_fixation(fix_tdec・fix_ctau_bank)、辺の長波放射 |
| [bedrock_cover/](bedrock_cover/) | 山地渓流の岩盤河道の被覆効果(道具と被覆): 給砂の量(定常の下刻速度の山形)、給砂の時期(同じ総量の一定給砂とパルス)、初期の被覆、段差(遷急点)の後退を、幅 1 セルの掘り込み水路を並べて比べる | 流水による岩盤下刻 f_rockinc(剥離・被覆・研磨)、掃流砂 f_fluvial、区間流入の給砂 inflow_qb |
| [mountain_valley/](mountain_valley/) | 隆起する山地の V 字谷で、斜面(風化による土層の生成・深さ依存クリープ)と渓流(岩盤下刻・被覆)を同時に動かす。定常の斜面と渓流の勾配を斜面だけ・渓流だけの予測と比べ、斜面の供給が渓流を急にし研磨を増やすこと、基準面の低下への渓流と斜面の応答の遅れを見る。後半は同じ平均の給砂を一定とパルスで与えた渓流の定常勾配(研磨が効くとパルスで急になる) | 風化 f_wthr(fn_wthr)、深さ依存クリープ creep_hstar、流水による岩盤下刻 f_rockinc、掃流砂 f_fluvial、分布隆起 fn_uplift |

## 複数プロセスの連鎖の例

ENCflow の特徴である「複数プロセスを 1 つの計算で連鎖させる」設定の
見本です(章を読んだ後の参考に)。

- 津波 → 家屋破壊 → 瓦礫: [tsunami_town/](tsunami_town/)。高潮 → 流木 → 市街地: [timberyard/](timberyard/)。
- 降灰 → 降雨 → 泥流: [ashfall_lahar/](ashfall_lahar/)。降雨 → 乾式侵食 → 地形発達: [badland/](badland/)。豪雨時だけ表面流が加わる崖: [badland_storm/](badland_storm/)。クリープで丸くなる丘: [badland_round/](badland_round/)。キャップロックのメサ → ビュート: [mesa/](mesa/)。豪雨 → 湛水 → 吸込穴 → 溶食 → ドリーネ: [karst/](karst/)。裸岩の塔 → 裾の溶食 → 崩落 → 塔の後退: [tower_karst/](tower_karst/)。給砂 → 被覆と道具 → 岩盤の下刻: [bedrock_cover/](bedrock_cover/)。隆起 → 風化 → クリープ → 渓流の被覆と下刻 → 定常の谷: [mountain_valley/](mountain_valley/)。
- 断層 → 津波 → 浸水: [tsunami_fault/](tsunami_fault/)、[tsunami_coast/](tsunami_coast/)。斜面崩壊 → 水域突入 → 津波: [landslide_tsunami/](landslide_tsunami/)。
- 洪水 → 破堤 → 氾濫: [levee_breach/](levee_breach/)。
- 降雨 → 下水道(管路)→ 噴出・排水: [sewer_hybrid/](sewer_hybrid/)。地下水 → 横坑集水: [qanat/](qanat/)。
- 1 機能だけの解析解ベンチマーク: [benchmark/](benchmark/)。格子の精緻化(ネスティング): [nest_reflect/](nest_reflect/)。

計算したい現象から機能の組み合わせを引くには
[用途集](../docs/users_guide/usecases.md)、各機能の設定は
[ユーザーガイド](../docs/users_guide.md) を参照してください。
