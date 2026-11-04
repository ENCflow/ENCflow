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
| [List_samples/](List_samples/) | 全 namelist の注釈付き見本(1 ファイル 1 グループ)。設定項目と既定値を引く辞書として使う(en/ に英語版) | 全機能 |
| [benchmark/](benchmark/) | 平面斜面・V 字流域・V 字谷の降雨流出 3 題を解析解と比べ、浅水流と降雨の基本的な精度を確かめる | 浅水流・降雨 |
| [vz_tani2023/](vz_tani2023/) | 谷(2023)の VZ 流出モデルの再現。斜面・ゼロ次谷・流域の全 7 事例の流出強度と圧力水頭を論文と比べる | 鉛直不飽和浸透(VZ)流出 fn_vz(柱の共有・土層厚の線形分布) |
| [badland/](badland/) | 台地と急崖への降雨で谷が刻まれるバッドランドの形成。谷の自己形成と谷間隔の選択則、鋭い稜線の発達を見る | 乾式斜面侵食 f_splash(spl_lc・spl_zbase) |
| [badland_storm/](badland_storm/) | 浸透能が低く豪雨時だけ表面流が現れる崖で、乾式侵食が止まるか、ガリー網に変わるかを見る(badland の対照) | f_splash + f_wash・f_suspend、Green-Ampt、降雨時系列 |
| [badland_round/](badland_round/) | 稜線が丸い膨潤粘土型のバッドランド。下刻とクリープの比が決める長さ尺度より低い丘からドーム状になることを見る | f_splash + f_creep(+ spl_strata)、Green-Ampt |
| [mesa/](mesa/) | キャップロックが平らな頂と垂直な崖を保ち、崖の平行後退で台地がメサ → ビュート → 尖塔へ縮む過程を見る | f_splash(spl_strata・spl_ksat)+ f_creep + f_rockfall(rf_rc・rf_fface)、Green-Ampt |
| [karst/](karst/) | 石灰岩台地のドリーネ群の形成。窪みに集まり吸込穴から地下へ消える水が、その場所を選択的に深める過程を見る | 石灰岩の溶食 f_dissol、管路連続体層(吸込穴)、Green-Ampt、周期強制 t_cycle_c |
| [tower_karst/](tower_karst/) | 平野に残る裸岩の塔(タワーカルスト)。平野と裾だけが溶けて塔の比高が増し、裾に堀と穴ができる過程を見る | 石灰岩の溶食 f_dissol(dissol_lat)、岩盤の崩落 f_rockfall、Green-Ampt の浸透能マップ、周期強制 |
| [stone_forest/](stone_forest/) | 石林: 節理の地図(可溶率 6 倍)で平らな石灰岩台地が柱と溝に分かれる。溝が深まり、壁が崩れて溝を埋め、崖錐が溶けて柱の高さが頭打ちになる | 石灰岩の溶食 f_dissol(fn_dissol の倍率)、基岩の崩落 f_rockfall(rf_bedrock)、崖錐の溶食、準定常強制 |
| [ashfall_lahar/](ashfall_lahar/) | 降灰で浸透能が下がった斜面の雨が灰を削って泥流になり、扇状地に堆積する過程と、砂防堰堤の効果を見る | 土石流 f_debris(地下水計算と併用する間隙水 f_dbwet=2)、Green-Ampt の浸透能、降雨、砂防堰堤(地形)、4 近傍化 p_diagratio |
| [landslide_tsunami/](landslide_tsunami/) | 陸上崩壊・海底地滑り・土石流が水域に突入して起こす津波の発生と伝播を、4 パターンと非静水圧版で比べる | 動く底層 f_bedslide、非静水圧補正 |
| [tsunami_fault/](tsunami_fault/) | 断層パラメータから海底変位を作って津波を起こし、静水圧・瞬時変位・非静水圧の違いと座標指定を比べる | 規定底面運動 fn_bedmotion、utils/fault2disp |
| [tsunami_coast/](tsunami_coast/) | 断層運動による沿岸の沈降・隆起と沖からの津波の到達の時間差が、沈降した湾奥平野の浸水をどう変えるかを見る | 規定底面運動 fn_bedmotion |
| [levee_breach/](levee_breach/) | 洪水が堤防の低い所を越水して破堤し、堤内地の氾濫で家屋が押し流される過程と、二線堤の効果を見る | 規定底面運動 fn_bedmotion(解像堤防の破堤)、家屋破壊 fn_bldgdebris(流体力判定)、建物空隙率 fn_gv、河道の破堤 &list_channel_breach(補足) |
| [estuary_barrage/](estuary_barrage/) | 感潮河川を遡上する塩水くさびと、河床から周辺の帯水層への塩水侵入に、河口堰の有無が与える影響を見る | 淡塩2層 fn_salt(地表の塩水層・地下の塩水 zone・交換の淡塩配分 f_salt_exch)、潮位、Green-Ampt、地下水の側方流、河床交換能 f_gwbed |
| [nest_reflect/](nest_reflect/) | 比 3・5 の双方向ネスト格子の界面をガウス波が横切るときの誤差と反射率を、一様細格子と比べて確かめる | ネスティング fn_nest(docs/users_guide/nest.md) |
| [tsunami_town/](tsunami_town/) | 津波で木造家屋が壊れ、瓦礫が内陸へ運ばれて積もり、引き波で海へ出る過程と、防潮堤かさ上げの効果を見る | 家屋破壊・瓦礫 fn_bldgdebris(浸水深判定・空隙率への帰還)、建物空隙率 fn_gv、潮位 fn_tide、流木 fn_driftwood(補足) |
| [timberyard/](timberyard/) | 高潮で貯木場の材木が流れ出し、防潮壁を越えて市街地へ入る過程(伊勢湾台風型)と、流出対策の効果を見る | 流木 fn_driftwood(水理的流失・堆積・再流動)、建物空隙率 fn_gv、潮位 fn_tide |
| [sewer_hybrid/](sewer_hybrid/) | 幹線 1 本と枝管網を同じ管路連続体層で表し、都市の雨水が下水道を流れて噴出・排水される様子を見る模式実験 | 管路連続体層 f_gwconduit |
| [qanat/](qanat/) | 山麓の扇状地の地下水を集めるカナート(横坑)の湧出と、近くの揚水井でそれが細り枯れる過程を見る | 管路連続体層 f_gwconduit(交換能のマップ fn_gwc_leak・開放の吐口 fn_gwc_outfall)、層2 f_gwlayer2、井戸揚水 f_gwpump |
| [catchment_metal/](catchment_metal/) | 流域の重金属(鉱山の排水と農地の負荷)の行き先と川の濃度を、地表水・地下水の流れ・吸着の遅れ・ため池・粒子態・蒸発散の順に機構を一つずつ加えて比べ、ため池が溶存態と粒子態に効くか、蒸発散(土の乾き具合による抑制の有無)で乾季の川がどう変わるかを見る | 水質 fn_wq(点源・面源・浸透同伴・遅延化係数 wq_rg・沈降 wq_vs・再懸濁 wq_wash_kf・海への流出の台帳)、Green-Ampt、地下水の側方流、サブグリッド河道幅、海域マスク、蒸発散 fn_evap(evap_hglim) |
| [meander/](meander/) | 氾濫原の正弦波状の河道が蛇行を発達させる過程。外岸の後退、内岸砂州の成長・定着と氾濫原化を見る | 掃流砂の方向補正 fluv_slope・f_secflow、側岸侵食 f_berode、安息角崩落 f_repose、定着 f_fixation、給砂 |
| [meander_cutoff/](meander_cutoff/) | 蛇行ループが、出水で陸を越える流れや河岸の後退だけで短絡(ショートカット)し、旧河道が滞水域になって埋まり始める過程を見る | 同上 + 崩落土塊 f_rockfall、区間流入の時系列 |
| [delta/](delta/) | 給砂河川が海盆に突入して作る河口デルタ。波のない河口から始めて、砂泥比・出水と植生・斜めの波・波浪場・潮汐を一つずつ加え、デルタの型ごとに要る機構と形の違いを見る | 海は通常セル+初期水位、容量給砂 fluv_bcfeed、浮遊泥 inflow_cs + f_bedfines、fluv_slope、f_repose、f_fixation(fix_tdec・fix_ctau_bank)、沿岸漂砂 fn_wave、沿岸の波浪場 fn_wavefield(f_wfsed・f_wfswash)、潮位 fn_tide |
| [bedrock_cover/](bedrock_cover/) | 山地渓流の岩盤河道で、給砂の量・時期・初期の被覆が下刻を促すか妨げるか(道具と被覆の効果)を見る | 流水による岩盤下刻 f_rockinc(剥離・被覆・研磨)、掃流砂 f_fluvial、区間流入の給砂 inflow_qb |
| [mountain_valley/](mountain_valley/) | 隆起する山地の V 字谷で、風化・クリープの斜面と岩盤下刻の渓流を同時に動かし、定常の谷の形を見る | 風化 f_wthr(fn_wthr)、深さ依存クリープ creep_hstar、流水による岩盤下刻 f_rockinc、掃流砂 f_fluvial、分布隆起 fn_uplift |
| [debris_bedrock/](debris_bedrock/) | 渓流に流した土石流が岩盤をどこでどれだけ削るか、土石流の頻度が渓流の定常勾配をどう変えるかを見る | 土石流 f_debris(高橋・中川、クーロン + Manning)、土石流による岩盤侵食 f_rockinc の rock_kdb |
| [shield_volcano/](shield_volcano/) | 火口の位置と噴出量を変えた断続的な噴火で溶岩流が重なり、楯状火山が育つ過程と、形を決めるのが降伏応力であることを見る。補足に粘い溶岩の溶岩ドームを解析解と比べる | 溶岩流 fn_lavaflow(複数噴火口 lv_cell・lv_val、Bingham 降伏応力 lv_tauy、固化 lv_wsol・lv_vsol) |
| [stratovolcano/](stratovolcano/) | 溶岩流 → 降灰 → 豪雨の侵食 を 10 回繰り返して、溶岩と灰の層が重なった成層火山を作る。噴火の仕方(溶岩と灰の割合)と侵食で、形と内部の層がどう変わるかを見る。最後に、育った山の地形に温度を考慮した 1 回の溶岩流を流し、流路が地形の凹凸で決まる様子と冷えて止まる様子を見る | 溶岩流 fn_lavaflow(固化した溶岩の下の土層を埋める。最後の段は温度モード f_lvtemp)、降灰は前処理、Green-Ampt、掃流砂 f_fluvial + morfac、段ごとの計算をつなぐドライバ |
| [glacier_valley/](glacier_valley/) | 川の V 字谷と支谷に寒冷な気候で氷河を育て、6000 年の侵食がどこに集まり、どのくらいの速さで進むかを見る(既定の値では谷の形の変化は数十 m)。補足に侵食係数 10 倍(6 万年分の侵食)の計算と湖の段を加え、閉じた凹地と湖・懸谷の段ができる一方で、侵食が涵養域を低くして氷河を短くすることを見る | 氷河 fn_glacier(質量収支・雪崩 f_glava・SIA 流動 f_glflow・滑動 f_glslide・侵食 f_glero と侵食の結合長 gl_lc)、気温減率と降水の標高補正、積雪、時間加速 gl_morfac、段の間で地盤高を渡す前処理 |

## 複数プロセスの連鎖の例

ENCflow の特徴である「複数プロセスを 1 つの計算で連鎖させる」設定の
見本です(章を読んだ後の参考に)。

- 津波 → 家屋破壊 → 瓦礫の運搬・堆積 → 引き波で海へ(防潮堤・開口部の閉鎖で変わる): [tsunami_town/](tsunami_town/)。
- 高潮 → 貯木場の材木の流出 → 市街地への流入・堆積(対策で変わる): [timberyard/](timberyard/)。
- 降灰 → 浸透能の低下 → 降雨 → 泥流 → 扇状地の堆積(砂防堰堤で捕捉): [ashfall_lahar/](ashfall_lahar/)。
- 降雨 → 乾式侵食 → 地形発達: [badland/](badland/)。
- 豪雨 → 浸透能を超えた表面流 → 崖の乾式侵食とガリー侵食の競合: [badland_storm/](badland_storm/)。
- 降雨 → 下刻とクリープの競合 → 丸い稜線・ドーム状の丘: [badland_round/](badland_round/)。
- 降雨 → 軟層の侵食 → キャップロックの崖の後退 → メサ → ビュート: [mesa/](mesa/)。
- 豪雨 → 湛水 → 吸込穴 → 溶食 → ドリーネ: [karst/](karst/)。
- 裸岩の塔 → 裾の溶食 → 崩落 → 塔の後退: [tower_karst/](tower_karst/)。節理に沿った溶解 → 溝 → 柱 → 壁の崩落: [stone_forest/](stone_forest/)。
- 給砂 → 被覆と道具 → 岩盤の下刻: [bedrock_cover/](bedrock_cover/)。
- 隆起 → 風化 → クリープ → 渓流の被覆と下刻 → 定常の谷: [mountain_valley/](mountain_valley/)。
- 土石流 → 堆積層の剥離 → 岩盤の侵食 → 頻度ごとの定常勾配: [debris_bedrock/](debris_bedrock/)。
- 断続的な噴火 → 溶岩流 → 停止・固化 → 地形の積み重ね → 楯状火山: [shield_volcano/](shield_volcano/)。
- 溶岩流 → 灰の埋没 → 降灰 → 豪雨の侵食 → 麓への再堆積 の繰り返し → 成層火山: [stratovolcano/](stratovolcano/)。
- 降雪 → 氷化 → 氷河の流動・滑動 → 氷河侵食 → (長い時間では)閉じた凹地と湖・懸谷の段、侵食による氷河の短縮: [glacier_valley/](glacier_valley/)。
- 断層 → 津波 → 浸水: [tsunami_fault/](tsunami_fault/)、[tsunami_coast/](tsunami_coast/)。
- 斜面崩壊 → 水域突入 → 津波: [landslide_tsunami/](landslide_tsunami/)。
- 洪水 → 越水 → 破堤 → 氾濫 → 家屋の流失(二線堤で止める): [levee_breach/](levee_breach/)。
- 潮汐 → 塩水くさびの遡上 → 河床からの浸透 → 岸の地盤の塩水化(河口堰で遮断): [estuary_barrage/](estuary_barrage/)。
- 給砂 → 河口砂州 → 分岐 → ローブ → 植生の定着・波の沿岸漂砂・潮汐でデルタの形が変わる: [delta/](delta/)。
- 降雨 → 下水道(管路)→ 噴出・排水: [sewer_hybrid/](sewer_hybrid/)。
- 山からの涵養 → 扇状地の地下水 → カナートの集水・湧出(揚水井で細る): [qanat/](qanat/)。
- 雨 → 地表流と浸透 → 地下水の流れ → 湧出(基底流)→ 川の重金属の濃度(吸着の遅れ・ため池・粒子態の沈降・蒸発散で変わる): [catchment_metal/](catchment_metal/)。
- 1 機能だけの解析解ベンチマーク: [benchmark/](benchmark/)。
- 格子の精緻化(ネスティング): [nest_reflect/](nest_reflect/)。

計算したい現象から機能の組み合わせを引くには
[用途集](../docs/users_guide/usecases.md)、各機能の設定は
[ユーザーガイド](../docs/users_guide.md) を参照してください。
