# 他シミュレーションソフトウェアとの比較 (comparison.md)

2026-08-10 時点の調査。ENCflow の機能実装状況(浅水+河道+構造物+流出+
蒸発散+2層地下水+土砂+水質+buildup-washoff まで完了)を前提とする。
ライセンス・配布形態は変わりうるので、引用時は各公式サイトで再確認すること。

## 1. 提供形態の比較

| モデル | 開発元 | 費用 | コード | 備考 |
|---|---|---|---|---|
| **ENCflow** | (本プロジェクト) | 無償(方針) | 全公開(方針) | 基本方針は developer.md §0 |
| RRI | ICHARM/土研 | 無償 | 公開(独自条件) | 著作権表示義務・商用は許可制。iRIC 版ソルバも公開 |
| iRIC (Nays2DFlood 等) | iRIC 団体 | 無償 | 主要ソルバ公開 | GUI+ソルバ群の基盤 |
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
[CAESAR-Lisflood](https://sourceforge.net/projects/caesar-lisflood/)

## 2. プロセスカバレッジの比較(ENCflow 現況との対比)

| プロセス | ENCflow | 同等以上を持つ代表 | 備考 |
|---|---|---|---|
| 2D 浅水(力学波) | ○ ENC 8近傍・適応 RK | TELEMAC, Delft3D, HEC-RAS, TUFLOW, Iber, BASEMENT | ENC 配置格子は独自 |
| 高潮・津波の遡上(沿岸氾濫) | ○ 海域セル+潮位/水位時系列(m_tide)+乾湿処理 | TELEMAC, Delft3D, ANUGA, GeoClaw | 沖側の発生・伝播は外部(観測波形・大領域モデル)から水位で受ける。高潮×河川×豪雨の複合災害を単一モデルで扱えるのは統合設計の利点 |
| サブグリッド河道(σ断面・幅) | ○ | LISFLOOD-FP(サブグリッド河道), HEC-RAS(1D-2D) | 1セル1水位+σ(h) は独自色 |
| 構造物(破堤・ポンプ・カルバート・樋門・分水・ダム操作) | ○ | HEC-RAS, TUFLOW, MIKE, SOBEK 系 | 無償・公開勢では手薄な領域 |
| 降雨流出・遮断・蒸発散 | ○(樹冠・Hamon/Thornthwaite・減率) | RRI, GSSHA, MIKE SHE, SHETRAN | 水理特化勢は持たない |
| 地下水 | ○ 2層(土層 Boussinesq+風化基岩層) | MIKE SHE(3D), SHETRAN(3D), GSSHA | 平面2次元モデルで2層は少数派。RRI は1層 |
| 土砂・地形変化(掃流・浮遊・崩壊・土石流) | ○ MORFAC 付き | GAIA, Delft3D-MOR, BASEMENT, CAESAR-Lisflood | |
| 水質(負荷流出・減衰・沈降・buildup-washoff) | ○ | MIKE ECO Lab, Delft3D-WAQ, Iber-WQ, GSSHA | 無償・公開で水文+水質+水理の同居は稀 |
| 積雪・融雪 | ○ 度日法(§31。2026-08-10) | MIKE SHE・GSSHA・SHETRAN(同じく度日法系) | HEC-RAS は HMS 側。RRI 標準版になし |
| 氷河 | ×(SIA を将来枠に設計済み) | 汎用洪水モデルには皆無 | 専用モデル(PISM, Elmer/Ice, OGGM)の領域 |
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

## 4. 残項目の実装勢と方向性

- **積雪・融雪**: 度日法で実装済み(§31。2026-08-10)。二重閾値の
  雨/雪分離+標高減率による雪線+融雪の h 直接投入。エネルギー収支法は
  m_meteo に放射・風速の枠を足してから(handoff 1m)。
- **氷河**: 水文的には「涵養・消耗を持つ多年性スノーパック」として
  度日法の延長(OGGM と同じ発想)。氷体流動まで入れるなら SIA
  (浅氷近似)が浅水方程式と相似構造で、枠組みとの相性は良い。
- **長期地形変動**: 供給側(基岩風化=土層生成関数・隆起)と周期強制
  t_cycle を実装済み(§32。2026-08-10)。既存の輸送側(MORFAC 付き
  侵食・堆積・崩壊)と合わせ、CAESAR-Lisflood と同じ「実水理駆動の
  地形進化」をより精緻な水理で構成できる。実行様式は代表水文の反復×
  MORFAC×リスタート連鎖(§32.3)。残: 分布隆起・bulking・実証ラン
  (handoff 1n)。Landlab/Badlands/FastScape はプロセス則 LEM
  (水理簡略)で棲み分け。
