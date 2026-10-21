# test/ — 検証ケースと回帰テスト

[English](README.en.md)

機能ごとの検証ケースです。回帰テストを兼ねていて、基準(reference)
との自動比較か、解析解・保存則の検定スクリプト(Check_*.py)のどちらか、
または両方を持ちます。使い方の教材は [tutorials/](../tutorials/)、
現象別の例題は [examples/](../examples/README.md) にあります。

## 実行の型

```bash
cd test/<name>
make              # bin/ の実行ファイルへのリンク(必要なら入力の生成)
./Run.sh          # 逐次(OpenMP)。reference があれば自動で比較
./Run_MPI.sh 4    # MPI 4 ランク。結果は逐次と一致するのが規律
python3 Check_*.py   # 解析解・保存則の検定(用意されているケース)
```

Run.sh と Run_MPI.sh は共通エンジン [Scripts/Run_case.sh](Scripts/Run_case.sh)
を呼び、Log.txt と記録 CSV を reference と比較します(Compare_ref.sh)。
reference の更新(`-u`)は結果の妥当性を人間が確認してから行い、
不一致は原因を特定して報告します(CLAUDE.md の絶対規律)。

## ケース一覧

表の「検証」は、ref = reference との自動比較、解析 = Check_*.py に
よる解析解・保存則の検定。

| ディレクトリ | 内容 | 主な機能 | 検証 |
|---|---|---|---|
| **浅水流・河道** | | | |
| [wave/](wave/) | 静水に立てた水の山が広がる最小例。チュートリアル 1 の題材 | 浅水流 | ref |
| [chichibu/](chichibu/) | 秩父の実地形流域に降る雨。チュートリアル 2 の題材。解像度・スキーム・堤防の多数の派生ケース | 浅水流・河道・降雨・計測 | ref |
| [chichibu_icmap/](chichibu_icmap/) | 秩父に固定遮断率の勾配マップ。領域マスクの窓が原点から始まらないケースで分布ファイルの帯配布がずれないことの回帰(§82) | 浅水流・降雨・遮断 | ref |
| [dambreak/](dambreak/) | 湿潤床のダム破壊。Stoker 解析解による移流スキームの検証 | 浅水流 | ref・解析 |
| [hillslope/](hillslope/) | 斜面流の移流スキーム比較。解析解と格子収束 | 浅水流・降雨 | 解析(スクリプト) |
| [bendloss/](bendloss/) | 1 セル幅水路の 90° 屈曲で生じる人工的な損失の切り分け | 河道・移流スキーム | 解析 |
| [diffusion/](diffusion/) | 運動方程式の拡散項のガウス形ジェット・ベンチマーク(解析解・格子収束) | 浅水流 f_diffusion_term | 解析 |
| **非静水圧補正** | | | |
| [nhwave/](nhwave/) | 閉じた水槽の定在波。静水圧 ENC の数値分散の計測 | 浅水流 | ref |
| [nhwave_nh/](nhwave_nh/) | 同じ水槽に 1 層非静水圧補正を掛けた定在波 | 非静水圧 | ref |
| [nhsolitary/](nhsolitary/) | 孤立波の伝播(非線形の検証) | 非静水圧 | ref |
| [nhcurrent/](nhcurrent/) | 一様流上の線形波の分散関係 | 非静水圧・区間流入・放射境界 | ref |
| [nhshelf/](nhshelf/) | 棚に乗り上げる孤立波のソリトン分裂。底面勾配項の検証 | 非静水圧 f_nh_slope | ref |
| [nhbore/](nhbore/) | 長波の段差から分裂する undular bore | 非静水圧 | ref |
| [nhbreak/](nhbreak/) | 砕波性孤立波の海浜遡上。砕波スイッチ・渦粘性・乾湿退化 | 非静水圧 f_nh_breaking | ref |
| [nhbottom/](nhbottom/) | 動く底面の加速度項。規定隆起の厳密解、海底地滑りとの結合、規定底面運動 | 非静水圧 f_nh_bottom、fn_bedmotion | ref |
| **沿岸・潮位** | | | |
| [tide/](tide/) | 潮位境界の疎通テスト | 潮位 | ref |
| [coastal_drain/](coastal_drain/) | 海抜下ポルダーの排水(吐口・機場) | 管路連続体層・潮位 | ref |
| [culvert/](culvert/) | カルバート流量則の 3 レジーム通過(排水試験。復元流量の単調性) | 構造物 | ref・解析 |
| [salt/](salt/) | 淡塩 2 層の模式実験(ロック交換の終状態、海側境界) | 淡塩 2 層 | ref |
| **地下水・都市排水** | | | |
| [gwdefault/](gwdefault/) | 地下水各モデルの最小入力と既定値の表示 | 地下水 | 画面出力 |
| [pump/](pump/) | 井戸揚水シンクの線形水位低下(解析検証) | 地下水 | ref |
| [frost/](frost/) | 凍土による浸透抑制の線形低減(解析検証) | 地下水・積雪 | ref |
| [conduit/](conduit/) | 管路連続体層の模式実験(一様・解析平衡) | 管路連続体層 | ref |
| [sewer_wq/](sewer_wq/) | 下水噴出の衛生リスク(水質 × 管路連続体層) | 管路連続体層・水質 | ref |
| **降雨・遮断・土壌雨量指数** | | | |
| [icevap/](icevap/) | 遮断・蒸発散の各モデルの最小入力と既定値の表示 | 遮断・蒸発散 | 画面出力 |
| [swi/](swi/) | 土壌雨量指数(気象庁 3 段タンク)の解析参照解 | 土壌雨量指数 | 解析 |
| **土砂・地形変化** | | | |
| [creep/](creep/) | 斜面クリープ(線形拡散)のガウス丘ベンチマーク | 土砂 f_creep | 解析 |
| [fluvial/](fluvial/) | 掃流砂 Exner の疎通・保存則(閉領域ダムブレイク型) | 土砂 f_fluvial | 解析 |
| [bankface/](bankface/) | 乾いた河岸をもつ水路のダム破壊流。河岸面の掃流遮断(乾いた河岸は不変)と薄い土層での供給量制限(体積保存) | 掃流砂 | 解析 |
| [bendsed/](bendsed/) | 90° 湾曲水路の流砂方向補正。外岸洗掘・内岸堆積の向き、left/right の鏡像対称、補正なしとの対照 | 掃流砂 fluv_slope・f_secflow | 解析 |
| [berode/](berode/) | 乾いた河岸をもつ水路の側岸侵食。水路に接する河岸だけが後退し、損失体積が K_b に比例、土砂保存 | 掃流砂 f_berode | 解析 |
| [repose/](repose/) | 乾いた 45° の砂山が安息角 30° まで崩れる。終端勾配と体積保存 | f_repose | 解析 |
| [fixation/](fixation/) | 低水で露出した砂州の定着。成長則の解析解、定着した砂州は出水で削られない、累積浸食によるリセット、粗度増加で砂州上の流速が下がり断面流量は保存、浮遊砂の給砂が定着砂州に積もる、リスタート往復 | 掃流砂・浮遊砂 f_fixation、fix_cn | 解析・自己検証 |
| [bedfines/](bedfines/) | 河床の細粒分の帳簿。細粒 100 % は無効時とビット一致、掃流砂+浮遊砂で 0 ≤ sf ≤ sd と固体総量・細粒分の保存が機械精度、粗粒だけの河床は浮遊砂を出さない、粗粒の水路に給砂した細粒分の在庫が堆積に厳密に等しい、容量給砂が入口の河床高と在庫を固定、リスタート往復 | 掃流砂・浮遊砂 f_bedfines、fines_la、fines_frac0 | 解析・自己検証 |
| [sedfeed/](sedfeed/) | 直線水路の区間流入への給砂。無給砂の河床低下波、容量給砂(倍率 1)で入口の河床が厳密に固定、inflow_qb の台帳が機械精度、浮遊砂の平衡濃度給砂が流入セルの C_eq に一致 | 掃流砂 fluv_bcfeed・fluv_bcfeed_fac、inflow_qb、inflow_cs_eq | 解析・自己検証 |
| [uniflow/](uniflow/) | 乾いた地盤に挟まれた幅 1・5 セルの直線水路の等流。f_opening_dynamic = 2 で Manning に一致、振り替えなしでは河岸行の流量不足(既知の性質を記録) | ENC の通水能、f_opening_dynamic | 解析 |
| [suspend/](suspend/) | 浮遊砂(移流+浸食・沈降)の疎通・保存則 | 土砂 f_suspend | 解析 |
| [wash/](wash/) | 斜面浸食(雨滴+面状)の疎通・保存則 | 土砂 f_wash | 保存則(Log) |
| [splash/](splash/) | 乾式斜面侵食の解析検証 | 土砂 f_splash | ref |
| [splashslide/](splashslide/) | 固結崖と崩壊崖の対照(乾式侵食と斜面崩壊の併用) | f_splash・f_slide | 解析 |
| [splashlc/](splashlc/) | 曲率の相関長 spl_lc による谷の波長選択(2 波長擾乱の成長比の対照) | f_splash(spl_lc・spl_zbase) | 解析 |
| [splashstrata/](splashstrata/) | 水平層理の侵食性倍率 spl_strata(3 層: キャップロック 0 / 0.5 / 1)の解析検証 | f_splash(spl_strata) | ref + 解析 |
| [sedinflow/](sedinflow/) | 区間流入の土砂濃度時系列の台帳検定 | 境界・土砂 | 解析 |
| **土石流・崩壊・火山流動・雪崩** | | | |
| [debris/](debris/) | 土石流(侵食起動型)の疎通・保存則。高橋型・江頭型 | 土石流 f_debris | 解析 |
| [slide/](slide/) | 瞬時流動化(地滑り型)の疎通・保存則。安定判定 | 斜面崩壊 f_release・f_slide | 解析 |
| [volcano/](volcano/) | 火山流動の Voellmy 定常等流ベンチマーク(岩屑なだれ・火砕流) | 等価流体 | 解析 |
| [curvature/](curvature/) | 曲率項(遠心加速度)の有無の対照 | 等価流体 f_dbcurv | 解析 |
| [avalanche/](avalanche/) | 流れ型雪崩(等価流体+速度比例連行)の疎通・保存則 | 等価流体・積雪 | 解析 |
| [bedslide/](bedslide/) | 動く底層。岩屑なだれの湖突入と津波、海底地滑り、土石流からの引き渡し | 動く底層 f_bedslide | 解析 |
| **流木・家屋破壊** | | | |
| [driftwood/](driftwood/) | 土石流+流木の混合流れ、洪水による流失、再流動 | 流木 fn_driftwood | 解析 |
| [bldgdebris/](bldgdebris/) | 氾濫流による家屋破壊と瓦礫の疎通・保存則。流木との併用、空隙率の帰還 | 家屋破壊 fn_bldgdebris | 解析 |
| [gvchange/](gvchange/) | 空隙率変更手続きの単体検定(体積保存。時間ループは回さない) | m_state_set_gv | 単体テスト |
| **水質** | | | |
| [damwq/](damwq/) | ダム完全混合放流とため池同伴の恒常検定 | 水質・ダム | ref・解析 |
| [tracer/](tracer/) | スカラー輸送(1 次風上)の数値拡散の計測。清水前線の広がり(縦断)と定常プルームの横断分散を修正方程式の理論値と比較 | 水質(スカラー移流) | ref・解析 |
| [gwseep/](gwseep/) | 地下横輸送と湧出還元の恒常検定 | 水質・地下水 | ref・解析 |
| [kdpart/](kdpart/) | Kd 平衡二相分配の恒常検定 | 水質・浮遊砂 | ref・解析 |
| **氷河・溶岩** | | | |
| [glacier/](glacier/) | SIA 氷体流動の Halfar ドーム、カール形成 | 氷河 | 解析 |
| [lava/](lava/) | Bingham 溶岩流の Huppert 相似解、最小入力 | 溶岩流 | 解析 |
| **ネスティング・BMI** | | | |
| [nest_twin/](nest_twin/) | 2 ケースの交互実行が単独実行と一致(複数インスタンス化の基盤) | m_main の複数インスタンス | 一致(スクリプト) |
| [nest_identity/](nest_identity/) | 比 1:1 自己ネストの恒等(子の内部 == 親、双方向はルート == 単独)。restart・保存修正・地下水 | ネスティング fn_nest | 一致(ドライバ) |
| [bmi_nest/](bmi_nest/) | BMI の多格子公開(grid id・修飾名)。Python からの恒等・再 initialize・同値 set、bmi-tester | BMI・ネスティング | 一致(Python)・bmi-tester |
| **入出力** | | | |
| [gtif/](gtif/) | GeoTIFF リーダーの読みテスト資産(圧縮・座標系の各種) | GeoTIFF | 単体テスト |
| Scripts/ | 共通の実行エンジンと比較スクリプト | — | — |

MPI の規律(np=1, 2, 4 が逐次と一致)や確保範囲の検査(gfortran
-fcheck=all)の手順は [CLAUDE.md](../CLAUDE.md) と
[docs/developer.md](../docs/developer.md) §3・§11 を参照してください。
