# 他シミュレーションソフトウェアとの比較 (comparison.md)

2026-08-10 時点の調査(以後随時更新。出典の確認日を併記)。ENCflow の機能実装
状況(浅水+河道+構造物+流出+蒸発散+2層地下水+土砂+水質+
buildup-washoff+積雪+長期地形変動まで完了)を前提とする。
ライセンス・配布形態は変わりうるので、引用時は各公式サイトで再確認すること。

## 1. 提供形態の比較

| モデル | 開発元 | 費用 | コード | 備考 |
|---|---|---|---|---|
| **ENCflow** | (本プロジェクト) | 無償(方針) | 全公開(方針) | 基本方針は developer.md §0。AI エージェント向け整備を同梱(§3) |
| RRI | ICHARM/土研 | 無償 | 公開(独自条件) | 著作権表示義務・商用は許可制。iRIC 版ソルバも公開 |
| iRIC (Nays2DFlood 等) | iRIC 団体 | 無償 | 主要ソルバ公開 | GUI+ソルバ群の基盤 |
| Morpho2DH | 竹林(京大防災研)/iRIC | 無償 | 非公開(iRIC 経由配布) | Morpho2D(平面2次元河床変動)+土石流・泥流。砂防堰堤等の構造物考慮 |
| HEC-RAS 2D | 米陸軍 USACE | 無償 | 非公開 | 実務標準の一つ。流域水文は HEC-HMS が分担 |
| LISFLOOD-FP 8 | Bristol 大 | 無償 | 公開(GPL) | サブグリッド河道・GPU |
| CAESAR-Lisflood | 英大学系 | 無償 | 公開(GPL) | LISFLOOD-FP 水理+地形進化(時間〜千年) |
| TELEMAC-2D (+GAIA) | EDF 主導 | 無償 | 公開(GPLv3) | 非構造 FE/FV。土砂は GAIA。流域水文なし |
| Delft3D FM | Deltares | カーネル無償 | カーネル公開(GPLv3) | GUI は無償配布だがライセンス管理あり |
| MIKE 21 / MIKE SHE | DHI | 有償 | 非公開 | 統合水文(SHE)は積雪含め最も網羅的 |
| TUFLOW | BMT | 有償 | 非公開 | 無償デモは 10 万セル・10 分制限 |
| Iber | UPC/GEAMA 等 | 無償 | 非公開(EULA・再配布禁止) | 水質・生息場・GPU 版 |
| BASEMENT | ETH Zürich | 無償(商用可) | 非公開(バイナリ配布) | 河床変動に強い |
| GSSHA | USACE ERDC | 無償 | 公開 | 分布型水文+2D 地表流+地下水+積雪 |
| SHETRAN | Newcastle 大 | 無償 | 公開(GitHub) | 物理ベース 3D 地下水+積雪 |
| ParFlow | CSM・LLNL・Bonn 大等 | 無償 | 公開(LGPL) | 3D 変飽和地下水(Richards)+地表流+陸面過程(CLM)の統合水文。MPI・GPU。依存多数(Hypre・HDF5・NetCDF 等) |
| r.avaflow | Mergili & Pudasaini | 無償 | 公開(GRASS GIS モジュール) | 多相質量流(土石流・雪崩・ラハール・GLOF)。質量流どうしの連鎖に対応(v4, 2025) |
| CSDMS(Landlab・pymt) | 米 NSF/コロラド大 | 無償 | 公開 | 単一モデルではなくコミュニティ基盤: 200+ モデルの登録庫と BMI 結合枠組み(§3 参照) |
| ANUGA | ANU/GA | 無償 | 公開 | Python の SWE。氾濫・津波 |
| GeoClaw | Clawpack 団体 | 無償 | 公開(BSD) | 津波の発生〜伝播〜遡上(AMR)。津波特化 |

出典(2026-08-10 確認):
[RRI](https://www.pwri.go.jp/icharm/research/rri/index.html) /
[RRI 利用条件](http://www.icharm.pwri.go.jp/research/rri/rri_contract_e.html) /
[BASEMENT](https://basement.ethz.ch/about.html)
([v3 論文](https://arxiv.org/pdf/2102.12862)) /
[Iber](https://iberaula.es/space/54/downloads) /
[GSSHA](https://en.wikipedia.org/wiki/GSSHA) /
[Delft3D FM](https://oss.deltares.nl/web/delft3dfm) /
[TUFLOW Licensing](https://wiki.tuflow.com/index.php?title=TUFLOW_Licensing) /
[CAESAR-Lisflood](https://sourceforge.net/projects/caesar-lisflood/) /
[Morpho2DH](https://i-ric.org/en/solvers/morpho2dh/)(2026-08-16 確認。
ソルバ本体のソース公開は確認できず = iRIC 経由のバイナリ配布) /
[ParFlow](https://github.com/parflow/parflow)(2026-08-26 確認) /
[r.avaflow v1 論文](https://gmd.copernicus.org/articles/10/553/2017/)・
[v4 論文](https://gmd.copernicus.org/articles/18/9879/2025/)
(2026-08-26 確認) /
[CSDMS 論文](https://gmd.copernicus.org/articles/15/1413/2022/)
(2026-08-26 確認)

## 2. プロセスカバレッジの比較(ENCflow 現況との対比)

| プロセス | ENCflow | 同等以上を持つ代表 | 備考 |
|---|---|---|---|
| 2D 浅水(力学波) | ○ 八近傍連結コロケート格子(ENC格子)・適応 RK | TELEMAC, Delft3D, HEC-RAS, TUFLOW, Iber, BASEMENT | ENC格子は独自(Tada, 2026, HRL 20(2), doi:10.3178/hrl.25-00052) |
| 高潮・津波の遡上(沿岸氾濫) | ○ 海域セル+潮位/水位時系列(m_tide)+乾湿処理 | TELEMAC, Delft3D, ANUGA, GeoClaw | 沖側の発生・伝播は外部(観測波形・大領域モデル)から水位で受ける。高潮×河川×豪雨の複合災害を単一モデルで扱えるのは統合設計の利点 |
| サブグリッド河道(σ断面・幅) | ○ | LISFLOOD-FP(サブグリッド河道), HEC-RAS(1D-2D) | 1セル1水位+σ(h) は独自色 |
| 構造物(破堤・ポンプ・カルバート・樋門・分水・ダム操作) | ○ | HEC-RAS, TUFLOW, MIKE, SOBEK 系 | 無償・公開勢では手薄な領域 |
| 降雨流出・遮断・蒸発散 | ○(樹冠・Hamon/Thornthwaite・減率) | RRI, GSSHA, MIKE SHE, SHETRAN | 水理特化勢は持たない |
| 地下水 | ○ 2層(土層 Boussinesq+風化基岩層)+井戸揚水シンク(2026-08-18) | MIKE SHE(3D), SHETRAN(3D), GSSHA, ParFlow(3D 変飽和 Richards+CLM) | 平面2次元モデルで2層は少数派。揚水はセル単位シンク(MODFLOW WEL の平面版)で、揚水誘引の海水浸入も淡塩2層との併用で扱える。ParFlow は物理精緻の極(§3) |
| 海水浸入・淡塩2層 | △ 鋭利界面 2 zone(SWI2 同型。Φs = η+εζ・海側規定水頭・地表塩水層。§47。2026-08-18 プロトタイプ) | MODFLOW+SWI2/SEAWAT, SUTRA, FEFLOW(変密度) | 変密度輸送(SEAWAT/SUTRA)は分散・混合まで解く専用領域。ENCflow は鋭利界面の準静的近似で地表氾濫・潮位と単一時間発展の点が独自(遡上海水の行き先まで一気通貫) |
| 都市排水・管路網 | △ 管路連続体層(等価被圧連続体・8方向異方通水・被圧サーチャージ・枡交換。§46。2026-08-18 プロトタイプ) | SWMM+2D 結合(TUFLOW, InfoWorks ICM, xpswmm 等の dual drainage) | 世界標準は地表 2D と管路 1D 網の別モデル結合。ENCflow は網を連続体化して単一時間発展で解く独自路線(適用限界の定量化が研究テーマ。gwconduit_plan.md §3)。制御構造物・幹線支配系は原理的に対象外で網モデル結合に譲る |
| 土砂・地形変化(掃流・浮遊・崩壊・土石流) | ○ MORFAC 付き | GAIA, Delft3D-MOR, BASEMENT, CAESAR-Lisflood, Morpho2DH | 土石流・泥流(地すべり起因の流動・堆積)の無償実務勢は Morpho2DH(iRIC)が代表。ENCflow は土石流を流域水文・洪水と同居させる点が異なる |
| 火山流動・雪崩(岩屑なだれ・dense 火砕流・ラハール・流れ型雪崩) | ○ 等価流体(Voellmy・一定停止応力・f_release。§28.8) | Titan2D, VolcFlow, RAMMS(雪崩), r.avaflow(多相・連鎖), LaharZ(経験則) | 専用勢と同じ SWE+粒状体抵抗則の水準。ENCflow は噴火→流下→堆積→天然ダム→決壊洪水→降雨二次泥流の連鎖を単一モデル・単一計算で追える点が独自(専用勢は概ね単プロセス。r.avaflow は Pudasaini 多相モデルで質量流どうしの連鎖 — 崩壊→湖水衝突→GLOF 等 — を扱う点で最も近いが、流域水文・洪水水理・水質との同居はない)。流れ型雪崩も同構成で対象(発生はシナリオ。走路の雪の速度比例連行 f_dbed=4 あり。users_guide/geomorph.md)。希薄系(サージ・噴煙・降灰輸送・煙型雪崩)は対象外と明言(debris_plan.md §5) |
| 溶岩流(噴火口からの湧き出し・停止・固化) | ○ 深さ平均 Bingham 粘性重力流(等温。η・τ_y 直接入力+速度閾値の固化→地形化。§51、lava_plan.md。2026-08-23) | MOLASSES・Q-LavHA(確率論/CA)、MAGFLOW・LavaSIM(温度結合)、VolcFlow(lava 版) | 実務標準は CA・確率論系(等温・経験則)と温度結合系に二分される。ENCflow の等温 Bingham 拡散はその中間の物理水準で、固化溶岩が地盤 z になり同一ランで降雨・洪水・土砂が新地形上を流れる連鎖(噴火→溶岩原→二次水文応答)が独自。冷却・温度依存粘度は将来枠(lava_plan.md §8)、溶岩と水の熱的相互作用は対象外と明言 |
| 流木(発生・輸送・堆積) | △ ラスタ場の概算(材積のオイラー輸送+水理的流失・侵食連行・接地堆積。§50。2026-08-21) | iRIC 系の流木個別要素モジュール、IberWood(いずれも個別剛体のラグランジュ追跡) | 世界の主流は個別流木追跡で、橋梁・スリットの幾何的閉塞まで解く(ENCflow はラスタ純化方針により対象外と明言)。ENCflow は流木量の面的ポテンシャル評価(到達・堆積マップ)を洪水・土石流・崩壊と単一時間発展で扱う点が独自(発生の侵食連行はどの侵食プロセスとも自動連動) |
| 水質(負荷流出・減衰・沈降・buildup-washoff・Kd 二相分配・地下水中輸送・貯水池完全混合) | ○ | MIKE ECO Lab, Delft3D-WAQ, Iber-WQ, GSSHA | 無償・公開で水文+水質+水理の同居は稀。地表・地下・貯水池を跨ぐ物質収支を単一コードで閉じる |
| 積雪・融雪 | ○ 度日法(§31)+凍土の浸透抑制(凍結指数。2026-08-18) | MIKE SHE・GSSHA・SHETRAN(同じく度日法系) | HEC-RAS は HMS 側。 |
| 氷河 | ○ 度日質量収支+SIA 流動+滑動+氷河侵食+雪崩再配分(§45。2026-08-16) | 汎用洪水モデルには皆無 | 精緻な氷力学は専用モデル(PISM, Elmer/Ice, OGGM)の領域。洪水水理・流域水文・地形変動と氷河を単一モデルで併走させる構成は他に例がない |
| 長期地形変動 | ○ 風化・隆起・周期強制(§32。2026-08-10) | CAESAR-Lisflood, Landlab, Badlands, FastScape | 実水理駆動では CAESAR-Lisflood と並ぶ。Landlab/Badlands/FastScape はプロセス則 LEM(水理簡略)で棲み分け |
| 並列化 | OpenMP+MPI。**ランク数によらずビット再現** | TELEMAC/Delft3D は MPI(ビット再現は保証せず) | 決定的リダクション(§11)が差別化点 |
| リスタート厳密性 | ○(モジュール私有 save 契約。§7) | 商用勢は概ね対応 | 公開勢で徹底例は少ない |

## 3. ポジショニング所見

- 無償・コード公開のクラスで「力学波 2D 水理+流域水文+構造物+土砂+
  水質+多層地下水」を単一コードで持つのは実質 GSSHA と SHETRAN のみで、
  両者は水文寄り(水理は拡散波・簡略河道)。逆に水理が強い公開勢
  (TELEMAC・Delft3D FM・LISFLOOD-FP)は流域水文・構造物運用が薄い。
  ENCflow は「洪水水理の精度で流域全プロセスを積む」中間帯 = 従来は
  商用の MIKE/TUFLOW が占めてきた領域に、無償・公開で入る位置。
- **ランク数任意のビット再現・リスタート厳密性・ULP=0 の検証規律**は
  商用含めて明示保証する製品がほぼなく、研究再現性の主張として強い。
- **外部ライブラリゼロ(標準規格 MPI/OpenMP のみ)・Fortran 単一・
  自前 GeoTIFF/inflate** の絶対的ポータビリティは他に例がない
  (TELEMAC は METIS 等、Delft3D は多数の依存、ANUGA は Python
  スタック前提)。教育利用(ノート PC)からベクトル機・スパコンまで
  同一ソースという間口は、TUFLOW デモ制限や商用 GUI 前提と対照的。
- **導入のしやすさ(独習可能性)**: 利用者向けの整備として、
  ユーザーガイド 20 章+全パラメータ索引(453 項目)、
  全機能の注釈付き namelist 見本(examples/List_samples)、実行して
  学ぶチュートリアル 2 件(最小例 wave・実地形 chichibu。実データの
  落とし穴 = 窪地除去・平坦区間由来の流量振動から、ParaView での
  3D 可視化までを教材化)、前後処理ユーティリティ群(utils/: 窪地
  除去 rmdepress_river・集水域 calc_catchmentarea・土地利用→マスク
  lu2mask・VTK 変換 out2vtk 等)を同梱する。導入コストの比較でも
  公開勢の上位に入る。利用者向け文書は日英ミラー
  (docs/en/・tutorials の en/)を整備済みで、英語弱点は開発者文書
  (developer.md 等は日本語のみ)に残るのみ。
- **AI エージェント指向**: 入出力が完全テキスト
  (GUI 非依存)であることに加え、「現象 → 機能 → パラメータ」を
  機械的に引ける文書体系(用途集・全パラメータ索引・注釈付き見本)と、
  リポジトリ同梱のエージェント向け整備(開発規約 CLAUDE.md、ケース
  作成の定型手順 /make-case、利用者向け docs/ai_guide.md 日英)を持つ。
  ビット再現と回帰基準は、エージェントが自分の作業を検証するループを
  成立させる基盤でもある。ENCflow 自体の開発・検証の多くが AI
  エージェントとの協働で行われており、実証を伴う。GUI 前提・
  コード非公開の各勢はエージェントが構造的に操作しにくく、公開勢でも
  リポジトリ水準のエージェント整備を持つ例は現時点で見当たらない
  (この差は各モデルの対応が進めば縮まりうる)。
- **ポジショニングの第三軸 — 分野横断の入口
  (gateway / screening)**: ENCflow の価値は「各分野の専用モデルより
  精密か」という軸だけでは測れない。同じ格子・同じ入力体系・同じ
  実行方法のまま隣接分野のプロセスを1つずつ足せるため、専門外の現象を
  「まず一度計算してみる」導入障壁が、別ソフト体系の習得を要する従来の
  組み合わせ運用より一段低い(例: 河川の研究者が地下水を、洪水の
  研究者が土砂・融雪・水質を、設定ファイル1枚の追加から試せる)。
  簡潔なモデルで感度(このプロセスは効くか)を見積もり、効くと
  分かってから専門モデルへ進むスクリーニング用途としての価値であり、
  専用モデルの**代替ではなく入口**という位置づけ。機能表(§2)とは
  別軸の優位で、教育(同じ状態の上にプロセスが積み上がる構造として
  学べる)および AI エージェント運用(構造が統一されているため、
  専門外プロセスへの入口を機械が案内できる)とも整合する。開発目的と
  しての明文化は developer.md §0 冒頭。なお「専門知識なしで正しい
  結果が得られる」の意ではない — 下げるのは試す障壁であって専門知識の
  障壁ではなく、利用者向け文書の表現もこの線を守る。
- **統合の2つの別路線との対比**:
  (a) **物理精緻の統合水文(ParFlow)** — 3D 変飽和 Richards+陸面
  過程(CLM)を密結合で解く公開勢の代表。物理の忠実さでは上位に
  あるが、HPC・依存スタック(Hypre・HDF5 等)前提で、構造物・土砂・
  水質・火山系は持たない。ENCflow は鉛直を抽象化した概算路線
  (developer.md §0 方針5)により、ノート PC からの間口とプロセスの
  幅で棲み分ける。
  (b) **結合枠組み(CSDMS: BMI・pymt・Landlab)** — 既存の専用
  モデル群を標準インターフェースで繋ぐコミュニティ路線。各分野の
  専用モデルをそのまま使える強みの一方、格子・時間刻み・I/O の整合と
  モデル間の結び付けは利用者側の作業になる。ENCflow は単一コード・
  単一時間発展の内製統合で、結合作業なしにプロセスを足せる代わりに、
  各プロセスは概算水準にとどめる — 相補的な関係にある。
