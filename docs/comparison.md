# 他シミュレーションソフトウェアとの比較 (comparison.md)

2026-08-10 時点の調査(以後随時更新。出典の確認日を併記)。ENCflow の機能実装
状況(浅水+河道+構造物+流出+蒸発散+2層地下水+土砂+水質+
buildup-washoff+積雪+長期地形変動+流木+家屋破壊・瓦礫+非静水圧
補正+規定底面運動(断層津波)+多段ネスティング+蛇行河道の発達+崩落と崖錐+
波浪による沿岸漂砂(段 1)+石灰岩の溶食(カルスト)+山地渓流の岩盤下刻と深さ依存クリープ+土石流による
岩盤侵食+沿岸の波浪場(段 W1〜W5)まで完了。
海域マスクの意味(解かない・水位を強制、系外への流出は台帳外)を全モジュールで揃えた
2026-10-22 の整合を含む。2026-10-28 更新)を前提とする。
ライセンス・配布形態は変わりうるので、引用時は各公式サイトで再確認すること。

## 1. 提供形態の比較

| モデル | 開発元 | 費用 | コード | 備考 |
|---|---|---|---|---|
| **ENCflow** | (本プロジェクト) | 無償 | 全公開 | 基本方針は developer.md §0。AI エージェント向け整備を同梱(§3)。CSDMS BMI 2.0 対応(bmi-tester 合格。optional アダプタで本体は依存ゼロのまま。2026-08-29) |
| RRI | ICHARM/土研 | 無償 | 公開(独自条件) | 著作権表示義務・商用は許可制。iRIC 版ソルバも公開 |
| iRIC (Nays2DFlood 等) | iRIC 団体 | 無償 | 主要ソルバ公開 | GUI+ソルバ群の基盤 |
| Morpho2DH | 竹林(京大防災研)/iRIC | 無償 | 非公開(iRIC 経由配布) | Morpho2D(平面2次元河床変動)+土石流・泥流。砂防堰堤等の構造物考慮 |
| HEC-RAS 2D | 米陸軍 USACE | 無償 | 非公開 | 実務標準の一つ。流域水文は HEC-HMS が分担 |
| LISFLOOD-FP 8 | Bristol 大 | 無償 | 公開(GPL) | サブグリッド河道・GPU |
| CAESAR-Lisflood | 英大学系 | 無償 | 公開(GPL) | LISFLOOD-FP 水理+地形進化(時間〜千年) |
| SFINCS | Deltares | 無償 | 公開(GPLv3。GitHub Deltares/SFINCS。Fortran) | 複合洪水(高潮・波・降雨・河川)向けの簡約浅水モデル。局所慣性方程式(移流項は任意)+サブグリッド地形+四分木格子、GPU(OpenACC)。HydroMT-SFINCS で入力を自動構築、Delft Dashboard・FloodAdapt と連携。Leijnse ら(2021)、van Ormondt ら(2025) |
| TELEMAC-2D (+GAIA) | EDF 主導 | 無償 | 公開(GPLv3) | 非構造 FE/FV。土砂は GAIA。流域水文なし |
| Delft3D FM | Deltares | カーネル無償 | カーネル公開(GPLv3) | GUI は無償配布だがライセンス管理あり。土砂 MOR・水質 WAQ を含む |
| MIKE 21 / MIKE SHE | DHI | 有償 | 非公開 | 統合水文(SHE)は積雪含め最も網羅的。水質は ECO Lab |
| TUFLOW | BMT | 有償 | 非公開 | 無償デモは 10 万セル・10 分制限 |
| Iber | UPC/GEAMA 等 | 無償 | 非公開(EULA・再配布禁止) | 水質・生息場・流木(IberWood)・GPU 版 |
| BASEMENT | ETH Zürich | 無償(商用可) | 非公開(バイナリ配布) | 河床変動に強い |
| GSSHA | USACE ERDC | 無償 | 公開 | 分布型水文+2D 地表流+地下水+積雪 |
| SHETRAN | Newcastle 大 | 無償 | 公開(GitHub) | 物理ベース 3D 地下水+積雪 |
| ParFlow | CSM・LLNL・Bonn 大等 | 無償 | 公開(LGPL) | 3D 変飽和地下水(Richards)+地表流+陸面過程(CLM)の統合水文。MPI・GPU。依存多数(Hypre・HDF5・NetCDF 等) |
| r.avaflow | Mergili & Pudasaini | 無償 | 公開(GRASS GIS モジュール) | 多相質量流(土石流・雪崩・ラハール・GLOF)。質量流どうしの連鎖に対応(v4, 2025) |
| OpenLISEM(Hazard 版) | Jetten・Bout 等(トゥエンテ大 ITC) | 無償 | 公開(GitHub) | 分布型の降雨・浸透・流出・土壌侵食に、Pudasaini 二相流(土石流)と斜面崩壊・連行を統合(Bout ら 2018)。降雨から土砂流の発生・流下・堆積までを一続きに解ける数少ない例 |
| FLO-2D | FLO-2D Software | 有償 | 非公開 | rain-on-grid の流出+泥流(O'Brien 二次式レオロジー)。実務標準。泥流の濃度は入力時系列で与える(侵食による濃度上昇は解かない) |
| LaharFlow | Woodhouse 等(Bristol 大) | 無償(Web 版) | 非公開 | ラハール専用の浅水層モデル。河床の侵食・堆積による bulking/dilution を解く。源流束を与える(降雨流出なし) |
| Kanako-2D / Kanako-LS | 中谷・里深・水山(砂防) | 無償 | 非公開 | 高橋系の侵食・堆積付き土石流(1D-2D)。砂防実務。上流端の土石流ハイドログラフが入力 |
| RAMMS(AVALANCHE / DEBRISFLOW) | WSL/SLF → RAMMS AG | 有償 | 非公開 | Voellmy 等価流体+曲率項+せん断応力型連行。雪崩・土石流の実務標準。ブロック放出かハイドログラフで発生 |
| Titan2D | バッファロー大 | 無償 | 公開 | Savage–Hutter 型粒状流(地形座標・土圧係数・AMR)、Pitman–Le 二相。火山流動の比較・不確実性評価の実績。発生はパイル・流量源 |
| CSDMS(Landlab・pymt) | 米 NSF/コロラド大 | 無償 | 公開 | 単一モデルではなくコミュニティ基盤: 200+ モデルの登録庫と BMI 結合枠組み(§3 参照) |
| ANUGA | ANU/GA | 無償 | 公開 | Python の SWE。氾濫・津波 |
| GeoClaw | Clawpack 団体 | 無償 | 公開(BSD) | 津波の発生〜伝播〜遡上(AMR)。時間依存の海底変形 dtopo、Boussinesq 版あり |
| COMCOT | Cornell 大(Liu)ほか | 無償 | 開発者経由配布 | 津波の発生〜遡上(ネスト格子)。Okada 変形・時間依存変形 |
| JAGURS | JAMSTEC・馬場ほか | 無償 | 公開(GitHub) | 津波(分散・地球の弾性応答)。並列。時間依存の海底変形 |
| TUNAMI | 東北大 | 無償 | 開発者経由配布 | 津波の伝播・遡上の標準コードの一つ。初期水位方式 |
| SWASH | TU Delft | 無償 | 公開(GPL) | 多層非静水圧の波浪・津波・沿岸 |
| FUNWAVE-TVD | Delaware 大 | 無償 | 公開(GitHub) | Boussinesq 型波浪(ソリトン分裂・砕波) |
| NHWAVE | Delaware 大 | 無償 | 公開(GitHub) | σ座標の 3D 非静水圧。地滑り津波の発生に実績 |
| NEOWAVE | Hawaii 大 | — | 非公開 | 1 層非静水圧の津波モデル(ENCflow と同じ 1 層近似) |
| VolcFlow | Clermont-Ferrand 大(Kelfoun) | 無償 | 開発者経由配布 | 火山質量流(岩屑なだれ・火砕流・溶岩)。二層版で地滑り津波 |
| SOBEK | Deltares | 有償 | 非公開 | 1D-2D 水理+構造物(Delft3D FM Suite へ統合) |
| SWMM | 米 EPA | 無償 | 公開(パブリックドメイン) | 都市排水の管路網(1D)。2D 地表との結合は各社製品が担う |
| InfoWorks ICM / xpswmm | Autodesk(旧 Innovyze) | 有償 | 非公開 | 管路網+2D 地表の dual drainage の実務標準 |
| MODFLOW(+SWI2 / SEAWAT) | USGS | 無償 | 公開 | 3D 地下水の標準。SWI2 で鋭利界面、SEAWAT で変密度 |
| SUTRA | USGS | 無償 | 公開 | 変密度・変飽和の地下水流動・輸送 |
| FEFLOW | DHI | 有償 | 非公開 | 3D 地下水・熱・物質輸送(変密度) |
| MOLASSES / Q-LavHA | USF / VUB | 無償 | 公開 | 溶岩流のセルオートマトン・確率論系 |
| MAGFLOW / LavaSIM | INGV / 日本(日高ほか) | — | 非公開(要確認) | 温度結合の溶岩流モデル |
| LAHARZ | USGS | 無償 | 公開 | ラハールの到達範囲の経験則(GIS) |
| Badlands / FastScape | Sydney 大 / GFZ | 無償 | 公開 | プロセス則の景観発達モデル(Landlab は CSDMS の行) |
| PISM / Elmer/Ice / OGGM | UAF・PIK / CSC / Innsbruck 大ほか | 無償 | 公開 | 氷床・氷河力学の専用モデル |

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
(2026-08-26 確認)。
GeoClaw 以降の行(COMCOT〜PISM)は §2 で言及するモデルを網羅する目的で
2026-10-06 に追加したもので、配布形態は一般的な知識によるもの。
引用前に各公式サイトで要確認。

ネスティングの出典(2026-10-10 確認):
[JAGURS の分散・ネスト並列化(PAGEOPH 2015)](https://link.springer.com/doi/10.1007/s00024-015-1049-2) /
[NEOWAVE の非静水圧ネスト(Yamazaki ら、IJNMF 2011。ファイル名は 2010)](https://uaf.edu/cfos/files/publications/kowalik/Yamazaki_et_al_2010-IJNMF-1.pdf) /
[GeoClaw-Bouss の陰的 AMR(Berger & LeVeque, SISC 2024)](https://faculty.washington.edu/rjl/pubs/mjb-rjl-implicit-2023/index.html) /
[FUNWAVE-TVD の多格子ネスト(GMD 2022)](https://gmd.copernicus.org/articles/15/5441/2022/) /
[ネスト Boussinesq(Zhou ら, NHESS 2011)](https://nhess.copernicus.org/articles/11/2677/2011/) /
[TUFLOW Multiple 2D Domains(Classic M2D と HPC Quadtree)](https://docs.tuflow.com/classic-hpc/manual/2026.0/TwoD2DLinking-2.html) /
[HEC-RAS 2D(ネスト不可・細密化領域)](https://therassolution.kleinschmidtgroup.com/the-ras-solution-forum/topic/reduce-grid-size-at-area-of-interest) /
[Delft3D 4 の domain decomposition による細密化(DDM29)](https://www.ddm.org/DD29/proceedings/ID104_pages.pdf) /
[MIKE 21 Classic の Multiple Grids](https://en.wikipedia.org/wiki/MIKE_21) /
[ROMS-AGRIF の二方向ネスト(Debreu ら, Ocean Modelling 2012)](https://memsic.ccsd.cnrs.fr/UNIV-GRENOBLE1/hal-00690731)。
COMCOT・TUNAMI-N2・MOST の接続法は docs/nesting_plan.md §2.1(ソース確認を含む)。

SFINCS の出典: [SFINCS documentation](https://sfincs.readthedocs.io/en/latest/)・
[GitHub Deltares/SFINCS](https://github.com/Deltares/SFINCS)(2026-10-20 追加。
作業環境から両サイトに到達できなかったため、内容は Leijnse ら 2021(Coastal
Engineering)・van Ormondt ら 2025(GMD)の知識によるもの。引用前に要確認)。

## 2. プロセスカバレッジの比較(ENCflow 現況との対比)

| プロセス | ENCflow | 同等以上を持つ代表 | 備考 |
|---|---|---|---|
| 2D 浅水(力学波) | ○ 八近傍連結コロケート格子(ENC 格子)・適応 RK・運動量保存形の移流(Stelling & Duinmeijer 型を 8 方向に拡張、MUSCL、斜め副格子モードの側方面結合) | TELEMAC, Delft3D, HEC-RAS, TUFLOW, Iber, BASEMENT | ENC 格子は独自(Tada, 2026, doi:10.3178/hrl.25-00052)。ENC 格子上の運動量保存形移流の設計・検証は未公表(docs/advection_design.md。段波 Stoker 解に 1 %、副格子モードの減衰 test/sublattice) |
| 高潮・津波の遡上(沿岸氾濫) | ○ 海域セル(解かない・水位を強制。境界・構造物・ネスト帯には置けず、統計からも除外)+潮位/水位時系列+乾湿処理。沖側を解くなら海底地形+f_htype=2 の「解く海」 | TELEMAC, Delft3D, ANUGA, GeoClaw, SFINCS(高潮+波+降雨+河川の複合洪水に特化。波は SnapWave の定常波解) | 沖側の発生・伝播は外部から水位で受ける(発生から解くなら断層津波の行)。高潮・河川・豪雨の複合災害を単一モデルで扱える |
| 地滑り津波(陸上崩壊の水域突入・海底地滑り) | △ 動く底層(慣性なし Voellmy・移動海底方式) | GeoClaw+地滑り源, VolcFlow, NHWAVE, r.avaflow | 発生→流下→造波→伝播→遡上を 1 方程式の底層で単一時間発展に収める。慣性は対象外の概算。近地の分散性は非静水圧補正で |
| 断層津波の発生(海底変位の時刻歴) | ○ 規定底面運動(変位の時刻歴を増分で z へ。前処理 utils/fault2disp) | GeoClaw, COMCOT, JAGURS, TUNAMI | 時間依存の変形を増分で与えるため、地震誘発の海底地滑りと同一ランに置ける。短い変位の Kajiura 効果は非静水圧補正で |
| 非静水圧・分散波(ソリトン分裂・undular bore・孤立波) | △ 1 層非静水圧補正(射影法。活性集合・砕波スイッチ) | SWASH, NEOWAVE, FUNWAVE, GeoClaw-Bouss | 専用モデルの精度は競わず、分散性が本質の区間だけ補正する(無効時はゼロ追加)。線形波・孤立波は 1 層理論に 1% 以内 |
| サブグリッド河道(σ断面・幅) | ○ | LISFLOOD-FP, HEC-RAS(1D-2D), SFINCS(セル内の地形分布から水深–体積・通水を表にするサブグリッド地形。河道に限らない) | 1 セル 1 水位+σ(h) は独自色 |
| 構造物(破堤・ポンプ・カルバート・樋門・分水・ダム操作) | ○ | HEC-RAS, TUFLOW, MIKE, SOBEK(SFINCS は薄い壁・堰・排水ポンプ・カルバートまで) | 無償・公開勢では手薄な領域 |
| 降雨流出・遮断・蒸発散 | ○ 樹冠・Hamon/Thornthwaite・減率 | RRI, GSSHA, MIKE SHE, SHETRAN | 水理特化勢は持たない(SFINCS は rain-on-grid+浸透(定数・CN・Green-Ampt・Horton)まで。遮断・蒸発散・地下水はない) |
| 地下水 | ○ 2 層(土層+風化基岩層)+井戸揚水シンク+河床交換能(MODFLOW RIV 相当の上限形) | MIKE SHE, SHETRAN, GSSHA, ParFlow | 平面 2 次元で 2 層は少数派。揚水と淡塩 2 層の併用で揚水誘引の海水浸入も扱える。河川と帯水層の交換は河道マスクのセル列で表し、別の河川パッケージを持たない |
| 鉛直不飽和浸透(Richards) | △ 共有参照柱の 1 次元 Richards(小杉式)を区画の土層厚で読み出し、出口へ直接排水(谷 2023 の VZ 流出モデル) | HYDRUS-1D(鉛直 1 次元の専用), MIKE SHE, SHETRAN, ParFlow | セルごとに鉛直格子を持たず、少数の参照柱が区画を代表する(状態は柱数×層数)。側方の遅れは解かない概算。初版は地下水(2 層)と同じ場所では併用不可 |
| 海水浸入・淡塩2層 | △ 鋭利界面(SWI2 同型)+地表塩水層 | MODFLOW+SWI2/SEAWAT, SUTRA, FEFLOW | 混合・分散まで解く変密度輸送は専用領域。地表氾濫・潮位と単一時間発展で遡上海水の行き先まで追う点が独自 |
| 都市排水・管路網 | △ 管路連続体層(等価被圧連続体・8 方向通水・サーチャージ) | SWMM+2D 結合(TUFLOW, InfoWorks ICM, xpswmm) | 世界標準は地表 2D と管路 1D 網の結合。網を連続体化する独自路線で、制御構造物・幹線支配系は網モデルに譲る |
| 土砂・地形変化(掃流・浮遊・崩壊・土石流) | ○ MORFAC 付き。崖の崩落と崖錐(f_rockfall。窓版の自由面高さ・海食崖の海への排出)も | GAIA, Delft3D-MOR, BASEMENT, CAESAR-Lisflood, Morpho2DH | 土石流を流域水文・洪水と同居させる点が異なる |
| 河口デルタの形成(河口砂州の分岐・ローブ成長・流路の乗り換え、砂泥比による扇状と鳥趾状、流量変動と定着による分流路の安定化) | ○ 設定のみ(海は通常セル+初期水位、容量給砂+浮遊泥+細粒分の帳簿+勾配補正+安息角+定着) | DeltaRCM(簡約。ランダムウォーク), Delft3D(物理ベース 2D/3D。Edmonds & Slingerland), CAESAR-Lisflood(局所慣性+側方侵食) | 砂泥比の効果(泥が多いほど分流路が少なく細長い)は三者と同じ向き。対称性の破れは乱数でなく分岐の不安定性。運動量保存形の流れで背水と噴流を解き、流量変動・潮位・流域水文と同じ格子で結合できる点が独自。波浪・潮汐流・プルームの浮力は未実装。docs/delta_plan.md |
| 蛇行河道の発達(湾曲部の流砂方向補正・側岸侵食・安息角崩落・内岸砂州の植生定着・頸部短絡・河床の細粒分の帳簿) | ○ ラスタ上の地形変化の帰結として(河岸線をベクトルで持たない。平衡二次流。非平衡二次流は計画) | Nays2DH(iRIC)、Delft3D-MOR、BASEMENT、CAESAR-Lisflood、自己発展河岸の研究モデル(Asahi ら 2013) | 専用勢は河岸線を追跡するか曲線座標で解く。ENCflow は河岸面を隣接セル間の段差として扱い、短絡・砂州の氾濫原化は乾湿処理と地形変化の帰結として現れる。流域水文・洪水と同じ時間発展に置ける点が独自(examples/meander・meander_cutoff) |
| 火山流動・雪崩(岩屑なだれ・火砕流・ラハール・流れ型雪崩) | ○ 等価流体(Voellmy・一定停止応力・曲率項) | Titan2D, VolcFlow, RAMMS, r.avaflow, LAHARZ | 抵抗則は専用勢と同水準。噴火→流下→堆積→天然ダム→決壊洪水→二次泥流の連鎖を単一計算で追える点が独自。希薄系(サージ・噴煙)は対象外 |
| 降灰後の降雨泥流(降灰 → 降雨 → 灰層の侵食・泥流化 → 堆積) | ○ 降灰厚を土層厚として与えるだけで発生源の指定なし | OpenLISEM(Hazard 版)。FLO-2D, Kanako-2D, Morpho2DH, LaharFlow, RAMMS, r.avaflow, HEC-RAS 6, LAHARZ は連鎖の一部 | 専用勢は降雨流出か土砂流の流下のどちらかで、他方は入力。同じ格子・時間ループに同居するので泥流が自然に立ち上がる。比較研究の相手は OpenLISEM |
| 溶岩流(湧き出し・停止・固化) | ○ 深さ平均 Bingham(等温)+固化→地形化 | MOLASSES, Q-LavHA(CA・確率論), MAGFLOW, LavaSIM(温度結合), VolcFlow | CA・確率論系と温度結合系の中間の物理水準。固化溶岩が地盤になり、同一ランで降雨・洪水・土砂が新地形上を流れる点が独自 |
| 流木(発生・輸送・堆積) | △ ラスタ場の概算(材積のオイラー輸送) | iRIC 系の流木モジュール, IberWood(個別剛体追跡) | 主流は個別流木追跡で閉塞の幾何まで解く。ENCflow は到達・堆積ポテンシャルの面的評価を洪水・土石流と単一時間発展で扱う |
| 家屋破壊・瓦礫(木造家屋の破壊、瓦礫の輸送・堆積) | △ ラスタ場の概算(被害関数型の破壊判定+瓦礫のオイラー輸送+空隙率の帰還) | 被害関数の後処理, DEM・粒子法の瓦礫個別追跡 | 実務標準は浸水深ベース被害関数の後処理。瓦礫の行方と流木・瓦礫による破壊力の増加を同じ時間発展で扱う点が独自 |
| 水質(負荷流出・減衰・沈降・buildup-washoff・Kd 分配・地下水輸送・貯水池完全混合) | ○ | MIKE ECO Lab, Delft3D-WAQ, Iber-WQ, GSSHA | 無償・公開で水文+水質+水理の同居は稀。地表・地下・貯水池を跨ぐ物質収支を単一コードで閉じる |
| 積雪・融雪 | ○ 度日法+凍土の浸透抑制 | MIKE SHE, GSSHA, SHETRAN | HEC-RAS は HMS 側 |
| 氷河 | ○ 度日質量収支+SIA 流動+滑動+氷河侵食+雪崩再配分 | 汎用洪水モデルには皆無。精緻な氷力学は PISM, Elmer/Ice, OGGM | 洪水水理・流域水文・地形変動と氷河を併走させる構成は他に例がない |
| 沿岸の波浪場(浅水変形・屈折・砕波・防波堤の陰) | △ 段 W1: 位相平均・代表周期 1 個・方向ビンのエネルギー平衡(2 リンク分解の風上法、非定常/準定常)。固定床で地形に作用しない | XBeach 定常モード, SnapWave(SFINCS と結合), HISWA, SWAN, CMS-Wave | 精度は専用勢と競わず、流域・河川・洪水・津波・土砂と同じ格子・同じ時間発展で動かす。過程の漂砂は段階的に(docs/wavefield_plan.md、§90)。回折・風による発達は持たない |
| 波による流れ(セットアップ・沿岸流・戻り流れ) | △ 段 W2: 放射応力(波+ローラー)の外力、深さ平均 GLM の Stokes 輸送、波・流れの底面摩擦(1.16 u_rms)、流れの側方 Neumann 境界(wf_flow)。砕波による水平混合(Battjes 1975 型の渦動粘性 wf_break_visc。既定なし) | XBeach(GLM・ローラー), Delft3D-FLOW+WAVE, SFINCS+SnapWave, ADCIRC+SWAN | XBeach の定常モードと同じ式の系統(ローラー・GLM・摩擦)を、河川・洪水・津波の浅水流の運動方程式に直接足す。検定は Bowen のセットアップと沿岸方向の運動量の釣り合い(test/wfcurrent、§90.5) |
| 流れによる波の変化(ドップラー効果・流れによる屈折・阻止) | △ 段 W3: 方向ビンごとのドップラーの分散関係、作用量の平衡(輸送 c_g + U・流れの勾配による屈折)、阻止(f_wf_current)。代表周期 1 個で阻止の点の反射はない | XBeach(wci), SWAN, HISWA, Delft3D-WAVE | 浅水流の流れ(河川・潮流・津波・波による沿岸流)をそのまま波に効かせ、波→流れと双方向に連成する。河口の噴流が波の遡上を止めることを分散関係の阻止として表す(fn_wave の wave_vmax のような打ち切りなし。test/wfdoppler、§90) |
| 波による漂砂(攪拌・沿岸漂砂・浜の侵食と回復) | △ 段 W4・W5: Soulsby(1997)の波・流れのせん断による掃流砂・浮遊砂の攪拌、Euler 平均流速と波の歪度・非対称の岸向きの速度 u_a(Ruessink ら 2012)による輸送(f_wfsed)。砕波の乱れによる攪拌(XBeach の turb の形 f_wfsed_turb。既定なし)。遡上域の輸送はない | XBeach, Delft3D(FLOW+WAVE+MOR), MIKE 21 ST, CMS | 流域・河川の土砂供給と同じ格子・同じ時間発展で、波による沿岸漂砂と岸沖の輸送を加える(デルタ・河口・浜の変化)。直線海岸の沿岸漂砂は CERC と同じ桁(test/wfsed、§90) |
| 波浪による沿岸漂砂(汀線の平滑化・砂嘴・弧状デルタ) | △ 波を解かず汀線帯の CERC 型概算(f_wave_longshore。沖波の H₀・T・方向を与件に、汀線方位の平滑化・局所勾配項・河口の流速規則。攪拌と遮蔽の精緻化は計画) | Delft3D-MOR+WAVE(SWAN)、XBeach、CEM(Ashton & Murray の一線汀線モデル) | 汀線の一線モデルと同じ CERC 則を 2 次元の地形変化の上で動かす点が独自(examples/delta の波浪ケース、§84.15)。波の伝播は上の行の波浪場(段階実装中) |
| 長期地形変動 | ○ 風化・隆起・周期強制・石灰岩の溶食(涵養比例の化学的削剥+吸込穴の集中項 = ドリーネ) | CAESAR-Lisflood, Landlab, Badlands, FastScape | 実水理駆動では CAESAR-Lisflood と並ぶ。他はプロセス則 LEM で棲み分け。溶食は管路連続体層(カルスト水文)と同一ランで動く概算で、洞窟網の幾何(speleogenesis モデル)は対象外 |
| 山地渓流の岩盤下刻(剥離・研磨・可動層の被覆・基準面)と斜面の土層供給 | ○ 超過せん断応力の剥離+運ばれる礫の研磨、被覆は可動層の厚さの露出率と掃流砂の利用可能率、分布隆起。土層だけが動く深さ依存クリープ(creep_hstar)。土石流による岩盤侵食(混合体の準静的な駆動応力の超過形。濃い混合体が流れるセルだけ)。混合粒径は採らない(developer.md §84.10 の決定) | Landlab(SPACE = stream power + 被覆、DepthDependentDiffuser、MassWastingRunout = 崩壊土砂の流下と土層の侵食。岩盤は削らない)、研究モデル(Sklar & Dietrich 2004 の saltation–abrasion、Zhang ら 2015 のマクロ粗度、Inoue ら 2016 の 2 次元の岩盤–沖積河道、Stock & Dietrich 2006 の土石流の慣性応力則、McGuire ら 2023 の流動深と勾配の則) | LEM の多くは stream power で流れを解かない。浅水流の底面せん断と掃流砂の容量で道具と被覆を 2 次元で結合し、洪水・流域水文と同じ時間発展に置ける点が独自。土石流による岩盤侵食も、単層混合体のイベント計算の中で被覆・生成物の取り込みを侵食・堆積式と結ぶ(巨礫の前縁は分けて表さない)。急勾配の等流で τ_b が大きく出る偏り(developer.md §89.4 の 1)は f_opening_dynamic = 3 で除ける(§68.41。既定は 2 のまま)。5 セル幅の水路で流れが格子の幅まで集まる性質(§89.4 の 3)は課題(examples/bedrock_cover、examples/mountain_valley = 斜面の風化・クリープと渓流の連成、test/dbrock、examples/debris_bedrock = 1 回の土石流の岩盤侵食と、出水との交互計算による頻度ごとの定常勾配、docs/mountain_stream_plan.md) |
| ネスティング(多段格子) | ○ 静的ネスト(任意の深さ・比 r と r_t は任意整数)。帯 Dirichlet / Flather 放射 / スポンジ、置換は面積平均・湿潤判定・保存修正。非静水圧の φ と追加の場(土砂・水質・地下貯留等)も交換 | 津波: COMCOT, TUNAMI, MOST, JAGURS, NEOWAVE, GeoClaw(AMR), FUNWAVE-TVD。構造格子の MIKE 21 Classic, TUFLOW Classic, Delft3D 4。海洋・気象(ROMS-AGRIF, WRF) | 洪水の公開勢は非構造・四分木で局所細密化しネストを持たない。分散波の接続は JAGURS・NEOWAVE・GeoClaw-Bouss・FUNWAVE の少数派(§3) |
| 並列化 | OpenMP+MPI。ランク数によらずビット再現 | TELEMAC, Delft3D(MPI。ビット再現は保証せず)、SFINCS(OpenMP+GPU/OpenACC) | 決定的リダクションが差別化点 |
| リスタート厳密性 | ○ モジュール私有 save 契約 | 商用勢は概ね対応 | 公開勢で徹底例は少ない |

各行の定式・検証値・実装時期の詳細は developer.md の該当 § と
users_guide の各章にある(本表には書かない)。

## 3. ポジショニング所見

- 無償・コード公開のクラスで「力学波 2D 水理+流域水文+構造物+土砂+
  水質+多層地下水」を単一コードで持つのは実質 GSSHA と SHETRAN のみで、
  そこに流木と家屋破壊・瓦礫(被害関数型の破壊判定+瓦礫のラスタ輸送+
  空隙率の帰還。§2)を同じ時間発展で載せる例は公開・商用を通じて
  見当たらない(被害想定は浸水深→被害率の後処理が実務標準)。
  両者は水文寄り(水理は拡散波・簡略河道)。逆に水理が強い公開勢
  (TELEMAC・Delft3D FM・LISFLOOD-FP)は流域水文・構造物運用が薄い。
  ENCflow は「洪水水理の精度で流域全プロセスを積む」中間帯 = 従来は
  商用の MIKE/TUFLOW が占めてきた領域に、無償・公開で入る位置。
- **SFINCS との対比(最も近い公開勢)**: Deltares の SFINCS は、無償・コード公開・
  Fortran・ラスタ格子・入出力が単純、という提供形態が ENCflow に最も近く、
  同じ時間発展の中で高潮・波・降雨・河川流入・構造物を扱う「複合洪水」志向も
  共通する。違いは方程式と守備範囲にある。SFINCS は既定で局所慣性方程式
  (移流項なし)+サブグリッド地形+四分木で**沿岸低平地の高速計算**に特化し
  (GPU 対応、全球規模の複合洪水評価に実績)、流域水文は rain-on-grid と浸透
  までで、地下水・土砂・水質・火山系は持たない。ENCflow は力学波(運動量保存形の
  移流)を既定にして山地流域の急勾配河道まで扱い、流域水文から土砂・地形変動
  までを同居させる。移流項を省いた局所慣性方程式が急な実地形で解像度依存を
  強く持つことは tutorials/chichibu の補足(結果 3)に示したとおりで、両者の
  棲み分けは「沿岸低平地の広域・高速(SFINCS)」と「山地〜沿岸の多プロセス
  (ENCflow)」になる。SFINCS の四分木・サブグリッド地形・GPU は ENCflow が
  持たない要素で、ラスタ純化の方針(developer.md §0)の下でどこまで取り込むかは
  中期の検討対象(ネストは §2 のとおり静的ネストで代替)。
- **河口デルタ(DeltaRCM との対比)**: DeltaRCM は水の経路をランダムウォーク、
  砂・泥を粒子の規則で置く簡約モデルで、様式の探索と長期統計に向く。ENCflow は
  同じ様式(砂州の分岐、砂泥比による扇状と鳥趾状、流路の乗り換え)を浅水方程式と
  輸送式から出し(docs/delta_plan.md)、対称性の破れを乱数でなく分岐の不安定性が
  担う。力学的な部分の割合は流れで明確に大きく、土砂は他の物理ベース 2 次元モデル
  (Delft3D・CAESAR-Lisflood)と同階層の経験式、定着は現象論的、という三層。利点に
  なるのは流れの力学が効く問題(背水・噴流・流量変動との結合・他過程との同居)と
  係数の移転性で、様式の探索や多数実現の統計では簡約モデルが適する。計算コストは
  桁で重い(dx 2.5 m・4000 h の地形時間で 4 スレッド 7 時間)。
- **降雨流出と土砂流の同居**: 降灰後の降雨泥流(examples/ashfall_lahar)の
  ように「流出の計算が侵食の駆動になり、侵食が流れの性質(濃度・抵抗)を
  変える」連鎖は、流出モデルと質量流モデルが同じ格子・同じ時間ループに
  いて初めて発生源なしに立ち上がる。公開・商用を通じて一続きに解けるのは
  OpenLISEM(Hazard 版)がほぼ唯一で、他は片方を入力として受け取る
  (§2 のラハールの行)。
- **ネスティング(多段格子)の位置づけ**: 津波モデルでは入れ子格子が標準装備
  (COMCOT・TUNAMI・MOST・JAGURS・NEOWAVE・GeoClaw の AMR)だが、分散波
  (非静水圧・Boussinesq)まで界面で接続するのは JAGURS(Baba ら 2015)・
  NEOWAVE(Yamazaki ら 2011。非静水圧圧力の Dirichlet)・GeoClaw-Bouss
  (Berger & LeVeque 2024。SGN を AMR で、楕円型方程式を段ごとに陰解)・
  FUNWAVE-TVD(Choi ら 2022。二方向)に限られる。ENCflow の帯の φ(NEOWAVE
  型)はこの少数派に入り、比 1:1 の自己ネストで子の内部が親と 2e-13 m で一致する
  検証(test/nest_identity)を持つ。津波以外では、洪水・河川の公開勢は非構造格子・
  四分木・非一様格子(TELEMAC・Delft3D FM・HEC-RAS・TUFLOW HPC Quadtree・
  LISFLOOD-FP 8.1)で局所細密化するためネストを持たず、構造格子時代の
  MIKE 21 Classic(Multiple Grids)・TUFLOW Classic(M2D)・Delft3D 4(domain
  decomposition)が入れ子・多領域に対応していた(いずれも後継は非構造へ)。
  海洋・気象(ROMS-AGRIF/CROCO・WRF)ではネストが標準で、ENCflow の Flather
  放射・reflux はその系譜。ENCflow が独自なのは、**ラスタ純化を保ったまま
  静的ネストで局所細密化し、浅水の h・u だけでなく浮遊砂・水質・流木・瓦礫・
  塩水・地下貯留まで同じ帯と置換で交換する**点で、流域水文・地下水まで入れ子に
  する例は公開・商用を通じて見当たらない(統合水文の MIKE SHE・GSSHA・ParFlow は
  単一格子)。
- **ランク数任意のビット再現・リスタート厳密性・ULP=0 の検証規律**は
  商用含めて明示保証する製品がほぼなく、研究再現性の主張として強い。
- **外部ライブラリゼロ(標準規格 MPI/OpenMP のみ)・Fortran 単一・
  自前 GeoTIFF/inflate** の絶対的ポータビリティは他に例がない
  (TELEMAC は METIS 等、Delft3D は多数の依存、ANUGA は Python
  スタック前提)。教育利用(ノート PC)からベクトル機・スパコンまで
  同一ソースという間口は、TUFLOW デモ制限や商用 GUI 前提と対照的。
- **導入のしやすさ(独習可能性)**: 利用者向けの整備として、
  ユーザーガイド 26 章+全パラメータ索引(583 項目)、
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
  研究者が土砂・融雪・水質を、津波の研究者が流木や家屋破壊・瓦礫を、
  設定ファイル1枚の追加から試せる)。
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
  幅で棲み分ける(例外として、鉛直不飽和浸透の応答そのものを扱う
  谷の VZ 流出モデルに限り、少数の共有参照柱で Richards 式を解く。
  セルごとの鉛直格子は持たない。developer.md §87)。
  (b) **結合枠組み(CSDMS: BMI・pymt・Landlab)** — 既存の専用
  モデル群を標準インターフェースで繋ぐコミュニティ路線。各分野の
  専用モデルをそのまま使える強みの一方、格子・時間刻み・I/O の整合と
  モデル間の結び付けは利用者側の作業になる。ENCflow は単一コード・
  単一時間発展の内製統合で、結合作業なしにプロセスを足せる代わりに、
  各プロセスは概算水準にとどめる — 相補的な関係にある。
  (2026-08-29 追記)この相補は実際に接続可能になった: ENCflow 自身が
  BMI 2.0 component として振る舞える(bmi-tester 合格。bmi/)ため、
  内製統合のプロセス連鎖を一括で持つ component として CSDMS 側の
  結合(Landlab・pymt・GLOFRIM 型チェーン)へそのまま差し出せる。
  「内製統合 vs 結合枠組み」は二者択一ではなく、前者を後者の部品に
  できる関係になっている(経緯は docs/bmi_plan.md)。
