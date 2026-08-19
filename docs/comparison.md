# 他シミュレーションソフトウェアとの比較 (comparison.md)

2026-08-10 時点の調査(所見の追記は各項の日付)。ENCflow の機能実装
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
ソルバ本体のソース公開は確認できず = iRIC 経由のバイナリ配布)

## 2. プロセスカバレッジの比較(ENCflow 現況との対比)

| プロセス | ENCflow | 同等以上を持つ代表 | 備考 |
|---|---|---|---|
| 2D 浅水(力学波) | ○ 八近傍連結コロケート格子(ENC格子)・適応 RK | TELEMAC, Delft3D, HEC-RAS, TUFLOW, Iber, BASEMENT | ENC格子は独自(Tada, 2026, HRL 20(2), doi:10.3178/hrl.25-00052) |
| 高潮・津波の遡上(沿岸氾濫) | ○ 海域セル+潮位/水位時系列(m_tide)+乾湿処理 | TELEMAC, Delft3D, ANUGA, GeoClaw | 沖側の発生・伝播は外部(観測波形・大領域モデル)から水位で受ける。高潮×河川×豪雨の複合災害を単一モデルで扱えるのは統合設計の利点 |
| サブグリッド河道(σ断面・幅) | ○ | LISFLOOD-FP(サブグリッド河道), HEC-RAS(1D-2D) | 1セル1水位+σ(h) は独自色 |
| 構造物(破堤・ポンプ・カルバート・樋門・分水・ダム操作) | ○ | HEC-RAS, TUFLOW, MIKE, SOBEK 系 | 無償・公開勢では手薄な領域 |
| 降雨流出・遮断・蒸発散 | ○(樹冠・Hamon/Thornthwaite・減率) | RRI, GSSHA, MIKE SHE, SHETRAN | 水理特化勢は持たない |
| 地下水 | ○ 2層(土層 Boussinesq+風化基岩層)+井戸揚水シンク(2026-08-18) | MIKE SHE(3D), SHETRAN(3D), GSSHA | 平面2次元モデルで2層は少数派。揚水はセル単位シンク(MODFLOW WEL の平面版)で、揚水誘引の海水浸入も淡塩2層との併用で扱える |
| 海水浸入・淡塩2層 | △ 鋭利界面 2 zone(SWI2 同型。Φs = η+εζ・海側規定水頭・地表塩水層。§47。2026-08-18 プロトタイプ) | MODFLOW+SWI2/SEAWAT, SUTRA, FEFLOW(変密度) | 変密度輸送(SEAWAT/SUTRA)は分散・混合まで解く専用領域。ENCflow は鋭利界面の準静的近似で地表氾濫・潮位と単一時間発展の点が独自(遡上海水の行き先まで一気通貫) |
| 都市排水・管路網 | △ 管路連続体層(等価被圧連続体・8方向異方通水・被圧サーチャージ・枡交換。§46。2026-08-18 プロトタイプ) | SWMM+2D 結合(TUFLOW, InfoWorks ICM, xpswmm 等の dual drainage) | 世界標準は地表 2D と管路 1D 網の別モデル結合。ENCflow は網を連続体化して単一時間発展で解く独自路線(適用限界の定量化が研究テーマ。gwconduit_plan.md §3)。制御構造物・幹線支配系は原理的に対象外で網モデル結合に譲る |
| 土砂・地形変化(掃流・浮遊・崩壊・土石流) | ○ MORFAC 付き | GAIA, Delft3D-MOR, BASEMENT, CAESAR-Lisflood, Morpho2DH | 土石流・泥流(地すべり起因の流動・堆積)の無償実務勢は Morpho2DH(iRIC)が代表。ENCflow は土石流を流域水文・洪水と同居させる点が異なる |
| 火山流動(岩屑なだれ・dense 火砕流・ラハール) | ○ 等価流体(Voellmy・一定停止応力・f_release。§28.8) | Titan2D, VolcFlow, RAMMS(雪崩), LaharZ(経験則) | 専用勢と同じ SWE+粒状体抵抗則の水準。ENCflow は噴火→流下→堆積→天然ダム→決壊洪水→降雨二次泥流の連鎖を単一モデル・単一計算で追える点が独自(専用勢は単プロセス)。希薄系(サージ・噴煙・降灰輸送)は対象外と明言(debris_plan.md §5) |
| 水質(負荷流出・減衰・沈降・buildup-washoff) | ○ | MIKE ECO Lab, Delft3D-WAQ, Iber-WQ, GSSHA | 無償・公開で水文+水質+水理の同居は稀 |
| 積雪・融雪 | ○ 度日法(§31)+凍土の浸透抑制(凍結指数。2026-08-18) | MIKE SHE・GSSHA・SHETRAN(同じく度日法系) | HEC-RAS は HMS 側。 |
| 氷河 | ○ 度日質量収支+SIA 流動+滑動+氷河侵食+雪崩再配分(§45。2026-08-16) | 汎用洪水モデルには皆無 | 精緻な氷力学は専用モデル(PISM, Elmer/Ice, OGGM)の領域。洪水水理・流域水文・地形変動と氷河を単一モデルで併走させる構成は他に例がない |
| 長期地形変動 | ○ 風化・隆起・周期強制(§32。2026-08-10) | CAESAR-Lisflood, Landlab, Badlands, FastScape | 実水理駆動では CAESAR-Lisflood と並ぶ。§4 参照 |
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
- (追記 2026-08-14、2026-08-18 更新)機能面に加えて利用者向けの
  整備が一巡した: ユーザーガイド 20 章+全パラメータ索引(453 項目)、
  全機能の注釈付き namelist 見本(examples/List_samples)、実行して
  学ぶチュートリアル 2 件(最小例 wave・実地形 chichibu。実データの
  落とし穴 = 窪地除去・平坦区間由来の流量振動から、ParaView での
  3D 可視化までを教材化)。前後処理ユーティリティ群(utils/: 窪地
  除去 rmdepress_river・集水域 calc_catchmentarea・土地利用→マスク
  lu2mask・VTK 変換 out2vtk 等)も同梱し、導入コスト(独習可能性)の
  比較でも公開勢の上位に入る。利用者向け文書は日英ミラー
  (docs/en/・tutorials の en/)を整備済みで、英語弱点は開発者文書
  (developer.md 等は日本語のみ)に残るのみ。なお比較優位の大半は
  「無償・全公開」の確定(ライセンス表記の復元。§34.3)が前提で
  あることに注意。
- (追記 2026-08-19)**AI エージェント指向**: 入出力が完全テキスト
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

## 4. 残項目の実装勢と方向性

- **積雪・融雪**: 度日法で実装済み(§31。2026-08-10)。二重閾値の
  雨/雪分離+標高減率による雪線+融雪の h 直接投入。エネルギー収支法は
  m_meteo に放射・風速の枠を足してから(handoff 1m)。
- **氷河**: 実装済み(m_glacier。§45。2026-08-16)。度日質量収支
  (OGGM と同じ発想)+ SIA 氷体流動(非線形拡散 = 既存の保存形2ループの
  型)+ Weertman 滑動+滑動速度べき乗則の氷河侵食+雪崩再配分。カール等の
  氷河地形形成は代表年反復×MORFAC×リスタート連鎖で回す(§32.3 と同じ
  実行様式)。設計正本は docs/glacier_plan.md。精緻な氷力学(高次近似・
  氷温・カービング)は PISM/Elmer/Ice の領域として持ち込まない。
- **都市排水・管路網**: 管路連続体層のプロトタイプを実装済み
  (m_gwflow_conduit。§46。2026-08-18)。世界標準の二重排水
  (2D 地表+1D 管網の別モデル結合)に対し、網を等価被圧連続体へ
  均質化して単一時間発展で解く独自路線。今後の方向: (a) 連続体 vs
  (b) オンライン網結合(SWMM 参照解) vs (c) オフライン一方向の3段階
  比較で「セルサイズ×管網密度×降雨規模」の適用性マップを作る
  (研究計画は gwconduit_plan.md §3・§7)。残: 下水道 GIS からの
  前処理(4 成分エッジコンダクタンス集計)、幹線ハイブリッド
  (埋設河道)、CFPM2 型閾値切替則。制御構造物・幹線支配系は
  原理的に対象外(網モデル結合=確実層に譲る)。
- **長期地形変動**: 供給側(基岩風化=土層生成関数・隆起)と周期強制
  t_cycle を実装済み(§32。2026-08-10)。既存の輸送側(MORFAC 付き
  侵食・堆積・崩壊)と合わせ、CAESAR-Lisflood と同じ「実水理駆動の
  地形進化」をより精緻な水理で構成できる。実行様式は代表水文の反復×
  MORFAC×リスタート連鎖(§32.3)。残: 分布隆起・bulking・実証ラン
  (handoff 1n)。Landlab/Badlands/FastScape はプロセス則 LEM
  (水理簡略)で棲み分け。
