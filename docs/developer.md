# ENCflow 開発者向けメモ (developer.md)

コードから読み取れない「なぜ」を記録する。形式は「決定事項+理由+落とし穴」。
設計判断をしたら、記憶が新しいうちに記録すること。

本書は開発記録の目次で、§1 以降の本文は節ごとに docs/developer/NNN.md に置く(NNN は節番号を
3 桁にしたもの。§68 なら [developer/068.md](developer/068.md))。プロジェクト基本方針(旧 §0)は
[policy.md](policy.md) に独立している。記録は全体を通して読むものではない。下の「テーマ別の索引」で
「現行」から読み、経緯は必要なときだけ読む。

---

## 0. プロジェクト基本方針(docs/policy.md へ移した)

基本方針(開発目的と 13 箇条)は [docs/policy.md](policy.md) にある(英訳は
[docs/en/policy.md](en/policy.md))。「developer.md §0」「§0 方針 N」という引用は、policy.md の
方針 N を指す。

## 引用と記録のしかた

- **節番号は恒久の識別子**。他の文書・ソースのコメントからは「developer.md §N」「developer.md §N.M」の形で
  引用する(§N の本文は docs/developer/NNN.md、§N.M はその中の見出し「### N.M」)。番号は付け直さない。
  節の中から他の節を指すときは「§N」だけでよい。
- **節の新設**: いまの最後の番号の次の番号で docs/developer/NNN.md を起こす。1 行目は「## N. 題名(日付 …)」。
  下の「全節の一覧」に同じ題名で 1 行足し、「テーマ別の索引」の該当するテーマの「記録」に番号を足す
  (既定や設計を変えたら「現行」も直す)。本書に節の本文を書かない。
- **既存の節への追記**: その節のファイルの末尾に小節(### N.M)を足す。ほかの節のファイルに書かない。
- **大きさの目安**: 1 つの節のファイルが 200 KB を超えたら、そこへは追記せず新しい節を起こし、元の節から
  参照する。GitHub が Markdown を表示できるのは約 500 KB までで、CI はリポジトリ内の 400 KB を超える
  Markdown を不合格にする。
- **検査**: tools/devdocs/check.py(CI の i18n.yml)が、目次とファイル名・見出しの一致、引用の解決、
  Markdown の大きさを照合する。
- **分割前の履歴**: 本書は 2026-11-22 まで 1 ファイル(約 2.8 MB)だった。分割前の最後の版はコミット
  619cb1f の docs/developer.md で、行ごとの履歴は `git blame 619cb1f -- docs/developer.md`、変更の履歴は
  `git log 619cb1f -- docs/developer.md` でたどる(分割の記録は [§116](developer/116.md))。

## テーマ別の索引

テーマごとに、まず読むところ(現行)と、設計と経緯の記録を並べる。「現行」は、いまの仕様を書いた
利用者ガイドの章と、現在の既定・設計を決めた節(小節)。経緯は必要なときだけ読めばよい。記録は
番号順で、1 つの節が複数のテーマに出ることがある。§N.M のリンク先は §N のファイル(小節は見出しで探す)。

### 規約・基盤(コードを変える前に読む)

- 現行: [§1](developer/001.md)〜[§14](developer/014.md)(実数精度・単一ソース MPI・ビルド・エラー処理・is_root・文字列・状態変数の時刻と save/restore・OpenMP の決定性・コンパイラ間の差・回帰テスト・MPI 化の原則・モジュール設計・Fortran の落とし穴・性能)。要点は CLAUDE.md の「頻出の規約」にある
- 記録: [§42](developer/042.md)(全域スケール自動配列のヒープ化)・[§71](developer/071.md)(私有状態の所有の明示)・[§83](developer/083.md)(save/restore のストリーミング)

### 並列化と配列の確保範囲(帯分割・窓)

- 現行: [§11](developer/011.md)(分割実装の基準)と [§79](developer/079.md)〜[§83](developer/083.md)(行窓・列の確保範囲・全域配列の窓化・入力の窓読み・save/restore)。利用者向けは [並列実行](users_guide/parallel.md)
- 記録: [§2](developer/002.md)・[§8](developer/008.md)・[§11](developer/011.md)・[§42](developer/042.md)・[§79](developer/079.md)・[§80](developer/080.md)・[§81](developer/081.md)・[§82](developer/082.md)・[§83](developer/083.md)・[§128](developer/128.md)(実効平面積率 af のハロ)

### 浅水流の数値: ENC 格子・時間刻み・乾湿・エッジ水深

- 現行: [ENC 格子と時間積分の解説](users_guide/encgrid.md)・[クーラン数と時間刻みの決め方](users_guide/courant.md)・[時間刻みの設計方針](users_guide/timestep_policy.md)・[高い地盤へ登るエッジ水深の頭打ち](users_guide/dry_head_cap.md)。エッジ水深の頭打ちの既定 f_dry_head_cap = 4 は [§114](developer/114.md)(値の定義は [§113](developer/113.md))、上流側の決め方 f_hcap_upwind は [§95](developer/095.md)、CFL による停止 f_check_cfl = 1 は [§37](developer/037.md)
- 記録: [§7](developer/007.md)・[§20](developer/020.md)(拡散項)・[§37](developer/037.md)・[§52](developer/052.md)(通過幅ゼロのエッジ)・[§68.7](developer/068.md)・[§68.16](developer/068.md)(頭打ちの導入)・[§68.31](developer/068.md)・[§94](developer/094.md)(負の水深を防ぐ流出の抑制)・[§95](developer/095.md)・[§108](developer/108.md)(f_dry_head_cap = 2)・[§110.24](developer/110.md)(= 3)・[§113](developer/113.md)・[§114](developer/114.md)

### 通過幅(開口補正)と斜めの配分

- 現行: [通過幅の調整](users_guide/passage_width.md)・[斜めの配分比 d の決め方](users_guide/diagratio.md)・[斜めエッジの流束による数値拡散](users_guide/diagonal_diffusion.md)。塞がれた開口の動的振り替えの既定 f_opening_dynamic = 3 は [§68.41](developer/068.md)。塞がり率の水柱は、土砂流動の計算では流動深 h + hs([§130](developer/130.md))。振り替えなし(0)を使うのは V 字の沢を進む流れに限り、平らな谷底の谷では既定のまま([§130.11](developer/130.md))
- 記録: [§18](developer/018.md)(開口補正の導入)・[§52](developer/052.md)・[§68.10](developer/068.md)・[§68.11](developer/068.md)・[§68.13](developer/068.md)〜[§68.15](developer/068.md)・[§68.38](developer/068.md)(既定 2)・[§68.41](developer/068.md)・[§68.43](developer/068.md)〜[§68.45](developer/068.md)・[§96](developer/096.md)(拡散型プロセスの 9 点化)・[§98](developer/098.md)(地下水の層の通過幅)・[§99](developer/099.md)(氷河・溶岩流の 8 近傍化)・[§130](developer/130.md)(土砂流動の計算では塞がり率を流動深で測る。一様な V 字水路の厳密解との比較と検定 test/vchannel)・[§137](developer/137.md)(幅の極端に狭いサブグリッド河道のセルを、振り替えと通水率で計算の外と同じに数える。検定 test/sliver)

### 移流項

- 現行: [移流項のスキーム](users_guide/advection.md)・[1 セル幅の河道と移流項の風上供給元](users_guide/advection_donor.md)・[高い地盤へ登るエッジ水深の頭打ち](users_guide/dry_head_cap.md)。既定のスキーム f_advection_scheme = 3 は [§68.19](developer/068.md) の既定昇格、f_advection_donor = 4・f_advection_bend = 2・f_advection_lateral = 2・f_dry_head_cap = 4 は [§114](developer/114.md)、それぞれの値の定義は [§113](developer/113.md)
- 記録: [§21](developer/021.md)・[§68](developer/068.md)(2026-10-01〜11-03 の改良の全体)・[§78](developer/078.md)(スカラー輸送の MUSCL)・[§102](developer/102.md)(f_advection_donor = 2, 3)・[§110](developer/110.md)(屈曲直後の辺の慣性と側方面のブレーキ)・[§118](developer/118.md)(§110 の続き)・[§111](developer/111.md)(窪地処理の平坦区間の振動)・[§112](developer/112.md)(深くて遅い隣のセルの規則の試作)・[§113](developer/113.md)・[§114](developer/114.md)・[§131](developer/131.md)(解像した合流の損失の格子依存、側方面の扱いが仮想壁面を見ず濡れた堤内地が河道を減速させる件 §131.12。例題 confluence_backwater)・[§134](developer/134.md)(近傍の判定で仮想壁面の向こうのセルを数えない。§131.12 の修正。側方面の合流の判定の漏れ = §134.10)

### 急勾配の重力補正と斜面の勾配

- 現行: [急勾配の重力補正の解説](users_guide/steep_slope.md)。既定 f_gravity_correction = 2 は [§93](developer/093.md)、混合体流動の抵抗則は [§101](developer/101.md)
- 記録: [§91](developer/091.md)(cos²θ を勾配の大きさで)・[§92](developer/092.md)(slope8 の D∞)・[§93](developer/093.md)・[§100](developer/100.md)(= 3 の試作)・[§101](developer/101.md)

### 境界条件・潮位・海域

- 現行: [境界条件](users_guide/boundary.md)・[潮位・海面](users_guide/tide.md)。[§15](developer/015.md)・[§23](developer/023.md)・[§67](developer/067.md)(潮位の最小入力)
- 記録: [§15](developer/015.md)・[§23](developer/023.md)・[§67](developer/067.md)・[§68.30](developer/068.md)(自由流出面)・[§68.35](developer/068.md)(海セルに接するエッジ)・[§68.40](developer/068.md)(区間流入の外縁セル)・[§134.9](developer/134.md)(海岸堤防の仮想壁を移流項と開口の振り替えで見る)

### 非静水圧

- 現行: [非静水圧補正の解説](users_guide/nonhydrostatic.md)。設計の正本は docs/nonhydrostatic_plan.md、決定の記録は [§69](developer/069.md)
- 記録: [§69](developer/069.md)・[§75](developer/075.md)(ネスティングでの φ の帯)・[§124](developer/124.md)(段波の水理実験との比較。砕波スイッチと壁ぎわのセルの挙動)

### 河道

- 現行: [河道](users_guide/channel.md)・[河道の解説](users_guide/channel_models.md)。設計の文書は docs/channel_model.md
- 記録: [§18](developer/018.md)・[§26](developer/026.md)(断面形 σ)・[§38](developer/038.md)(rn0_rw)・[§68.8](developer/068.md)・[§68.9](developer/068.md)・[§68.12](developer/068.md)・[§68.24](developer/068.md)・[§68.26](developer/068.md)〜[§68.29](developer/068.md)・[§68.32](developer/068.md)・[§109](developer/109.md)(秩父の河道マスク)・[§111](developer/111.md)・[§128](developer/128.md)(堤防の越流の上限が読む af のハロ)・[§131](developer/131.md)(サブグリッド河道の支川の背水曲線、粗い格子の湾曲部の階段、セル幅の倍数でない川幅の表し方。§131.14 で粗い格子の河道マスクの作り方 3 通りと、利用者ガイドの作り方の節)・[§134](developer/134.md)(移流項が仮想壁面の向こうのセルを数えない)・[§135](developer/135.md)(粗い格子で川を表す表し方と通水の精度: 川幅・向き・屈曲・河道マスクの連結・占有率で作る河道マスクと下限。例題 coarse_channel)・[§137](developer/137.md)(占有率の細片を開口の振り替えと通水率で閉じた開口と数える)・[§138](developer/138.md)(河道のセルは堤内地を持たない: 氾濫原の水理への効き方と、占有率の下限と氾濫原の面積の兼ね合い)

### 内部水理構造物・堤防・家屋

- 現行: [内部水理構造物](users_guide/structure.md)・[構造物と境界の水理則の解説](users_guide/hydraulics.md)・[家屋破壊・瓦礫](users_guide/bldgdebris.md)・[家屋破壊・瓦礫モデルの解説](users_guide/bldgdebris_models.md)
- 記録: [§17](developer/017.md)(堤防)・[§22](developer/022.md)(構造物族)・[§63](developer/063.md)(家屋破壊・瓦礫)・[§68.25](developer/068.md)(堤防天端の下限)・[§103](developer/103.md)(fn_reservoir の廃止)・[§107](developer/107.md)(家屋の抗力項の次元の修正)・[§132](developer/132.md)(ダムの運転則の拡張: 実績の時系列・制限水位・洪水調節開始流量)・[§133](developer/133.md)(ダムの外部運転 = BMI の目標放流量)・[§134](developer/134.md)(堤防の仮想壁面の向こうのセルを移流項が数えない。海岸堤防も同じ = §134.9)

### 降雨・気象・蒸発散・雪氷

- 現行: [降雨・気象](users_guide/forcing.md)・[降雨・気象のモデルの解説](users_guide/forcing_models.md)・[氷河](users_guide/glacier.md)。既定値は [§65](developer/065.md)・[§66](developer/066.md)
- 記録: [§27](developer/027.md)(蒸発散)・[§29](developer/029.md)(気象強制場と暦)・[§31](developer/031.md)(積雪・融雪)・[§45](developer/045.md)(氷河)・[§65](developer/065.md)・[§66](developer/066.md)・[§88](developer/088.md)(降雨分布の時間の単位)・[§99](developer/099.md)(氷河の 8 近傍化)

### 地下水・淡塩

- 現行: [地下水](users_guide/gwflow.md)・[地下水モデルの解説](users_guide/gwflow_models.md)・[淡塩2層](users_guide/salt.md)。既定値は [§64](developer/064.md)
- 記録: [§16](developer/016.md)・[§46](developer/046.md)(管路層)・[§47](developer/047.md)(淡塩 2 層)・[§64](developer/064.md)・[§98](developer/098.md)・[§117](developer/117.md)(1 層の側方飽和透水係数の等価な値。例題 source_area)・[§125](developer/125.md)(管路層の 1 セル幅の幹線の通水能と、吐口の時間刻みごとの頭打ち。例題 coastal_compound_flood)

### 流出の指標と区画流出(土壌雨量指数・VZ・貯留関数法)

- 現行: [土壌雨量指数](users_guide/swi.md)・[鉛直不飽和浸透(VZ)流出](users_guide/vz.md)・[貯留関数法の区画流出](users_guide/sfm.md)。VZ の設計の正本は docs/vz_plan.md
- 記録: [§49](developer/049.md)・[§87](developer/087.md)・[§106](developer/106.md)(m_sfm と共通基盤 m_zonerunoff)・[§117](developer/117.md)(例題 source_area での VZ・貯留関数法との比べ)

### 田んぼダム(水田の貯留と落水口)

- 現行: [田んぼダム](users_guide/paddy.md)。設計の正本は docs/paddy_plan.md
- 記録: [§127](developer/127.md)(§127.9 は例題 paddy_dam、§127.10・§127.11 は水質・土砂との併用、§127.12 は双方向の
  水田でない面積の割合の下限、§127.13 は A の集水面積率 fn_pd_catch、§127.14 は例題 D の表現 A と B の差の切り分け、
  §127.15 は集水面積の雨を 3 × 3 の近傍のタンクへ配る形と例題の前処理、§127.16 は test/paddy の reference の確定と
  夜間の回帰への登録、§127.17 は main の取り込みで生じた混合粒径・有効掃流力との併用の停止、§127.18 はタンクのプールの沈降の
  検定、§127.19 は双方向のタンクへ入る水の二相分配の粒子態を田面に落とす形、§127.20 は B の減水深が
  二相分配の溶存態だけを運ぶ形、§127.21 は例題 paddy_dam で雨の前の湛水に溶けた物質の行方を表現 A と B で比べた結果)

### 土砂・地形変化

- 現行: [土砂・地形変化](users_guide/geomorph.md)・[土砂輸送と斜面・長期地形過程の解説](users_guide/sediment.md)・[土石流・斜面崩壊・動く底層の解説](users_guide/massflow.md)・[土砂・地形変化の適用例](users_guide/geomorph_applications.md)。既定値は [§62](developer/062.md)。混合粒径(f_bedmix。2026-11-22 合意、段 1 の掃流砂は 2026-11-23、段 2a の浮遊砂の結合・プローブの Dm・組成からの D84 と段 2b の崩落・クリープ・沿岸漂砂の組成は 2026-11-24、段 2c-1 の土石流との併用は 2026-11-27、段 2c-4 の土石流の式の侵食を動ける粒径階に限る選択子は 2026-11-28 に実装)の設計の正本は [docs/mixed_sediment_plan.md](mixed_sediment_plan.md)、採る範囲は policy.md 方針 6 の例外と [§84.19](developer/084.md)、実装の記録は [§119](developer/119.md)・[§122](developer/122.md)・[§123](developer/123.md)・[§139](developer/139.md)・[§143](developer/143.md)
- 記録: [§19](developer/019.md)・[§28](developer/028.md)(土石流・地滑り)・[§32](developer/032.md)(長期地形変動)・[§48](developer/048.md)(乾式斜面侵食)・[§61](developer/061.md)(動く底層)・[§62](developer/062.md)・[§84](developer/084.md)(蛇行・河岸侵食)・[§84.19](developer/084.md)(混合粒径を範囲を限って採る)・[§119](developer/119.md)(混合粒径の段 1 の実装)・[§120](developer/120.md)(例題 joganji_flume)・[§121](developer/121.md)(芦田・道上の有効掃流力 f_taupart = 2)・[§122](developer/122.md)(混合粒径の段 2a: 浮遊砂の結合・組成からの D84)・[§123](developer/123.md)(混合粒径の段 2b: 崩落・クリープ・沿岸漂砂)・[§126](developer/126.md)(雪崩の例題と設定の型の見直し: キャリアの授受・限界水深・連行の与え方)・[§129](developer/129.md)(Hungr の連行則 f_dbed = 5・連行する流動深の下限・取り込んだ質量の運動量 f_dbmom)・[§130](developer/130.md)(沢の向きへの依存の原因と修正、横断方向の応力の試作)・[§136](developer/136.md)(f_slide_noflow の既定を 1 に、1 の判定をそれまでの 2 に)・[§139](developer/139.md)(混合粒径の段 2c-1: 土石流との併用)・[§140](developer/140.md)(例題 debris_fan_flume。土石流扇状地の水路実験との比較・[§141](developer/141.md)(例題 debris_dam の粒度の幅を持つ堤体))・[§142](developer/142.md)(高橋・中川則の堆積の式が非正規化数の濃度でオーバーフローする不具合の修正)・[§143](developer/143.md)(混合粒径の段 2c-4: 土石流の式の侵食を動ける粒径階に限る選択子 f_dbsel)・[§144](developer/144.md)(例題 debris_fan_flume・debris_dam の f_dbsel のケース)・[§85](developer/085.md)(河口デルタ)・[§86](developer/086.md)(石灰岩の溶食)・[§89](developer/089.md)(山地渓流)・[§92](developer/092.md)・[§96](developer/096.md)・[§101](developer/101.md)

### 流木

- 現行: [流木](users_guide/driftwood.md)・[流木モデルの解説](users_guide/driftwood_models.md)
- 記録: [§50](developer/050.md)

### 溶岩流

- 現行: [溶岩流](users_guide/lavaflow.md)。既定値は [§66](developer/066.md)
- 記録: [§51](developer/051.md)・[§66](developer/066.md)・[§97](developer/097.md)(温度の移流の MUSCL)・[§99](developer/099.md)(流動の 8 近傍化)

### 沿岸の波浪場

- 現行: [沿岸の波浪場](users_guide/wavefield.md)・[沿岸の波浪場の解説](users_guide/wavefield_models.md)。設計の正本は docs/wavefield_plan.md
- 記録: [§84.15](developer/084.md)(波浪による沿岸漂砂)・[§90](developer/090.md)

### 規定底面運動

- 現行: [規定底面運動](users_guide/bedmotion.md)・[規定底面運動の解説](users_guide/bedmotion_models.md)
- 記録: [§70](developer/070.md)

### 水質とスカラー輸送

- 現行: [水質](users_guide/wq.md)・[水質モデルの解説](users_guide/wq_models.md)。スカラー輸送の既定 f_scalar_scheme = 3 は [§78](developer/078.md)、代表値の表は [§66](developer/066.md)
- 記録: [§30](developer/030.md)・[§66](developer/066.md)・[§78](developer/078.md)

### 計測・出力・可視化

- 現行: [計測](users_guide/record.md)・[入出力の形式](users_guide/io.md)
- 記録: [§24](developer/024.md)(フラックス測線の DDA 階段面)・[§25](developer/025.md)・[§33](developer/033.md)(画面・Log の表示列)・[§36](developer/036.md)(実座標指定)・[§39](developer/039.md)(貯水量の台帳 S)・[§43](developer/043.md)・[§44](developer/044.md)(out2vtk と X0000)・[§68.33](developer/068.md)・[§122](developer/122.md)(プローブの Dm の列)

### 入力と前処理

- 現行: policy.md の方針 11・12。[地理情報](users_guide/geoinfo.md)・[入出力の形式](users_guide/io.md)・[座標系の管理](users_guide/coordinates.md)。GeoTIFF の入出力と座標管理(m_geotiff・m_georef)の設計・決定・検証の記録は [docs/geotiff_plan.md](geotiff_plan.md) の §8〜§10 が正本(開発記録の節は持たない)
- 記録: [§40](developer/040.md)(土地利用からのマスク生成)・[§41](developer/041.md)(f_rntype = 2 の廃止と「物理量は直接与える」)・[§88](developer/088.md)

### ネスティング

- 現行: [ネスティング(多段格子)](users_guide/nest.md)・[ネスティングの解説](users_guide/nest_models.md)。設計の正本は docs/nesting_plan.md
- 記録: [§71](developer/071.md)・[§72](developer/072.md)・[§73](developer/073.md)・[§74](developer/074.md)・[§75](developer/075.md)

### BMI(外部連携)

- 現行: bmi/README.md。設計の文書は docs/bmi_plan.md
- 記録: [§53](developer/053.md)〜[§60](developer/060.md)・[§73](developer/073.md)・[§76](developer/076.md)・[§77](developer/077.md)・[§133](developer/133.md)(ダムの量の公開と外部運転)

### 公開・文書・言語

- 現行: docs/multilingual.md(多言語化の規約)・[§34](developer/034.md)(公開体制と言語方針)・[§35](developer/035.md)(利用者向け文書の構成)・本書の「引用と記録のしかた」と [§116](developer/116.md)(開発記録と引き継ぎメモの分割と書き方)
- 記録: [§34](developer/034.md)・[§35](developer/035.md)・[§105](developer/105.md)(浅水方程式の入門ページ)・[§116](developer/116.md)

### 例題・教材・データ

- 現行: examples/README.md・tutorials/
- 記録: [§104](developer/104.md)(examples/benchmark の再構築)・[§109](developer/109.md)・[§111](developer/111.md)・[§115](developer/115.md)・[§117](developer/117.md)(例題 source_area の作成と検討)・[§120](developer/120.md)(例題 joganji_flume。公開の実験データとの比較)・[§124](developer/124.md)(例題 tsunami_meander。論文の図から読んだ計測値との比較)・[§125](developer/125.md)(例題 coastal_compound_flood。沿岸の町の複合浸水)・[§126](developer/126.md)(例題 snow_avalanche。雪崩の設定の型の見直し)・[§131](developer/131.md)(例題 confluence_backwater。合流点の背水による支川の氾濫)・[§135](developer/135.md)(例題 coarse_channel。粗い格子で川を表す表し方の系統的な確かめ。§135.6 で占有率で作る河道マスクを中心に組み替え)・[§138](developer/138.md)(例題 coarse_channel の系列 fmin と、幅を使う例題の注記)・[§140](developer/140.md)(例題 debris_fan_flume。論文の図から読んだ値との比較・[§141](developer/141.md)(例題 debris_dam の粒度の幅を持つ堤体))・[§144](developer/144.md)(例題 debris_fan_flume・debris_dam に、侵食を動ける粒径階に限る f_dbsel のケース)
## 全節の一覧

- [§1](developer/001.md) 実数精度の方針
- [§2](developer/002.md) 単一ソース MPI 方式
- [§3](developer/003.md) ビルドシステム
- [§4](developer/004.md) エラー処理・メッセージ出力
- [§5](developer/005.md) is_root ガードの規約
- [§6](developer/006.md) 文字列・メッセージの組み立て
- [§7](developer/007.md) 状態変数の時刻規約(m_swflow_enc)
- [§8](developer/008.md) OpenMP の決定性
- [§9](developer/009.md) コンパイラ間の既知の差(仕様であってバグではない)
- [§10](developer/010.md) 回帰テスト運用
- [§11](developer/011.md) MPI 化の設計原則(分割実装の基準)
- [§12](developer/012.md) モジュール設計の規約
- [§13](developer/013.md) Fortran の落とし穴(実際に踏んだもの)
- [§14](developer/014.md) 性能に関するメモ
- [§15](developer/015.md) 境界条件(外縁4辺・内部ソース)
- [§16](developer/016.md) 地下水モジュール(m_gwflow)の設計(2026-08-05 決定)
- [§17](developer/017.md) 堤防(仮想壁面)モデルの設計(2026-08-06 決定)
- [§18](developer/018.md) 河道水理モデル(fn_channel: 開口補正・サブグリッド河道幅)の設計(2026-08-06 決定)
- [§19](developer/019.md) 地形変化モジュール(m_geomorph)の実装(2026-08-07)
- [§20](developer/020.md) 運動方程式の拡散項(f_diffusion_term。2026-08-07 実装)
- [§21](developer/021.md) 移流項 taxy の乾湿遷移時の古い値の除去(2026-08-07 挙動変更)
- [§22](developer/022.md) 内部水理構造物族(fn_structure: ポンプ・カルバート等)の設計(2026-08-07 決定)
- [§23](developer/023.md) 海域マスクと潮位境界(m_tide)の設計(2026-08-08 決定)
- [§24](developer/024.md) フラックス測線の計測方式(DDA 階段面。2026-08-08 変更)
- [§25](developer/025.md) 貯水量統計 S(領域平均貯留高)の定義変更(2026-08-08)
- [§26](developer/026.md) 河道断面形の一般化 σ(h) = (h/D)^m(2026-08-08 実装)
- [§27](developer/027.md) 蒸発散(&list_evap。2026-08-09 実装)
- [§28](developer/028.md) 土石流・地滑りモデル(f_debris / f_release / f_slide。2026-08-09 実装)
- [§29](developer/029.md) 気象強制場 m_meteo と暦の正本化(2026-08-09 分離)
- [§30](developer/030.md) 水質(負荷流出)モジュール m_wq(&list_wq。2026-08-09 実装)
- [§31](developer/031.md) 積雪・融雪モジュール m_snow(&list_snow。2026-08-10 実装)
- [§32](developer/032.md) 長期地形変動(LEM 化。2026-08-10 実装)
- [§33](developer/033.md) 画面・Log 表示列(f_disp_*。2026-08-13 実装)
- [§34](developer/034.md) 公開体制と言語方針(2026-08-13 決定)
- [§35](developer/035.md) ユーザー向けドキュメントの構成方針(2026-08-14 決定)
- [§36](developer/036.md) 計測の実座標指定(2026-08-14 決定・実装)
- [§37](developer/037.md) f_check_cfl の既定を 1 に変更(2026-08-14)
- [§38](developer/038.md) rn0_rw の適用条件の独立化(2026-08-14 変更)
- [§39](developer/039.md) S 台帳の乾燥セル hg 漏れ修正と閉流域の診断記録(2026-08-14)
- [§40](developer/040.md) 土地利用からのマスク生成は前処理ユーティリティで行う(2026-08-15 決定・実装)
- [§41](developer/041.md) f_rntype=2(土地利用から粗度)の廃止と「物理量は直接与える」原則(2026-08-15 決定・実装)
- [§42](developer/042.md) 全域スケール自動配列のヒープ化(2026-08-16)
- [§43](developer/043.md) ParaView 可視化は後処理ユーティリティ out2vtk で行う(2026-08-16 決定・実装)
- [§44](developer/044.md) 領域マスクの常時出力 X0000 と out2vtk の非表示対応(2026-08-16 決定・実装)
- [§45](developer/045.md) 氷河モジュール m_glacier(fn_glacier。2026-08-16 実装)
- [§46](developer/046.md) 管路連続体層 m_gwflow_conduit(f_gwconduit。2026-08-18 実装)
- [§47](developer/047.md) 淡塩2層(鋭利界面)モジュール m_saltwater(fn_salt。2026-08-18 実装)
- [§48](developer/048.md) 乾式斜面侵食 m_geomorph_splash(f_splash。2026-08-20 実装)
- [§49](developer/049.md) 土壌雨量指数 m_swi(fn_swi。2026-08-20 実装)
- [§50](developer/050.md) 流木モジュール m_driftwood(fn_driftwood。2026-08-21 設計合意)
- [§51](developer/051.md) 溶岩流モジュール m_lavaflow(fn_lavaflow。2026-08-23 実装)
- [§52](developer/052.md) 通過幅ゼロのエッジを運動方程式の対象外に(2026-08-24)
- [§53](developer/053.md) m_main のライフサイクル API 化(BMI 対応 段1。2026-08-28 実装)
- [§54](developer/054.md) BMI アダプタ bmi/(BMI 対応 段2。2026-08-28 実装)
- [§55](developer/055.md) BMI の C 相互運用層と Python サンプル(BMI 対応 段2.5。2026-08-28 実装)
- [§56](developer/056.md) BMI set_value による外部降水供給(逐次。2026-08-28 実装)
- [§57](developer/057.md) BMI set_value による z・h の外部設定(逐次。2026-08-28 設計合意・実装)
- [§58](developer/058.md) BMI の MPI 対応(段3。2026-08-28 実装)
- [§59](developer/059.md) bmi-tester 適合性確認と再 initialize 対応(2026-08-28 実施)
- [§60](developer/060.md) BMI 公開変数の第2弾: 常時確保のセル量(2026-08-29 実装)
- [§61](developer/061.md) 動く底層 f_bedslide(地滑り津波の移動海底源。2026-09-30 実装)
- [§62](developer/062.md) geomorph パラメータの既定値方針(2026-09-30 実装)
- [§63](developer/063.md) 家屋破壊・瓦礫モジュール m_bldgdebris と空隙率の状態化(2026-10-01 設計合意)
- [§64](developer/064.md) gwflow パラメータの既定値方針(2026-10-01 実装。§62 の展開)
- [§65](developer/065.md) snow・glacier パラメータの既定値方針(2026-10-01 実装。§62・§64 の展開)
- [§66](developer/066.md) intercept・evap・lavaflow の既定値と wq の代表値表(2026-10-01 実装。§62・§64 の展開)
- [§67](developer/067.md) 潮位・海面(m_tide)の最小入力(2026-10-01 実装。§62 の展開)
- [§68](developer/068.md) 移流項の改良: 現行スキームの評価と段階的方針(2026-10-01 設計合意)
- [§69](developer/069.md) 非静水圧(1 層 NH)拡張の設計決定(2026-10-05 合意。実装は段階的)
- [§70](developer/070.md) 規定底面運動 fn_bedmotion(地盤変位の時刻歴で z を強制。2026-10-06 実装)
- [§71](developer/071.md) 複数インスタンス化 Phase 0: 私有状態の「所有の明示」と等価性検証のフラグ(2026-10-09 実装)
- [§72](developer/072.md) 多段ネスティング Phase 1: 一方向・同一 dt の帯 Dirichlet(2026-10-09 実装)
- [§73](developer/073.md) 多段ネスティング Phase 5: BMI の多格子公開(2026-10-10 実装)
- [§74](developer/074.md) 多段ネスティング: Flather 放射 nest_bc = 3(2026-10-10 実装)
- [§75](developer/075.md) 多段ネスティング: 非静水圧の φ の帯(2026-10-10 実装)
- [§76](developer/076.md) BMI 公開変数の第3弾: 動的変数表と機能依存の状態量の get / set(2026-10-11 実装)
- [§77](developer/077.md) BMI set_value による粗度係数 rn の外部上書き: P 区分(パラメータ)の新設(2026-10-11 設計合意・実装)
- [§78](developer/078.md) スカラー輸送のリンクごとの MUSCL(f_scalar_scheme。2026-10-13 設計合意・実装)
- [§79](developer/079.md) 領域マスク外の計算負荷の削減: 行窓 wy のマスク化とエッジ流量・動的開口表の窓限定(2026-10-15 実装)
- [§80](developer/080.md) x 方向の確保範囲 dcp%ish/ieh(第二段 C。2026-10-16 設計合意・実装)
- [§81](developer/081.md) 第二段 (D1): 常駐の全域配列の窓化(2026-10-16 設計合意・実装)
- [§82](developer/082.md) 第二段 (D2): 入力の窓読みと初期化一時の窓形化(2026-10-16 実装)
- [§83](developer/083.md) 第二段 (D3): save/restore のストリーミング(2026-10-16 実装)
- [§84](developer/084.md) 蛇行・河岸侵食・流砂方向補正(段階計画の記録。2026-10-17 合意)
- [§85](developer/085.md) 河口デルタ形成の試行(2026-10-20〜21。記録は docs/delta_plan.md)
- [§86](developer/086.md) 石灰岩の溶食 f_dissol(カルスト地形。2026-10-21 実装)
- [§87](developer/087.md) 鉛直不飽和浸透(VZ)流出モデル m_vzflow(fn_vz。2026-10-26 設計合意)
- [§88](developer/088.md) 降雨分布の時間の単位(dt_mapunit・dt_maplist)の仕様と修正(2026-10-27)
- [§89](developer/089.md) 山地渓流の地形発達: 流水による岩盤下刻 f_rockinc(第 1 段)と深さ依存クリープ(第 2 段)(2026-10-27 合意・実装)
- [§90](developer/090.md) 沿岸の波浪場モデル m_wavefield(fn_wavefield。2026-10-27 設計合意)
- [§91](developer/091.md) 急勾配の重力補正の cos²θ を地盤の勾配の大きさで求める(格子の向きによる有効重力の偏りの修正。2026-11-04 挙動変更)
- [§92](developer/092.md) 斜面の最急勾配 slope8 を D∞(Tarboton 1997)で求める(8 方向の勾配の最大による格子の向きの偏りの修正。2026-11-04 挙動変更)
- [§93](developer/093.md) 斜面に沿う摩擦と流砂のせん断(f_gravity_correction = 2。2026-11-05 機能追加、同日に既定へ)
- [§94](developer/094.md) セルの流出の合計による過大な流出の抑制(辺ごとの抑制の取りこぼしによる負の水深の修正。2026-11-05 不具合修正)
- [§95](developer/095.md) エッジ水深の上流側を新しい流速の向きで決める(f_hcap_upwind。静止から流れ出す辺の頭打ちの抜けの修正。2026-11-05 挙動変更)
- [§96](developer/096.md) 拡散型プロセスの 4 近傍の異方性: クリープと乾式斜面侵食の曲率の 9 点化(2026-11-05 合意・段 1 を実装)
- [§97](developer/097.md) 溶岩の温度の移流の MUSCL(f_lvtemp_scheme。2026-11-05。§96 の段 2)
- [§98](developer/098.md) 地下水の層が共有する通過幅: 管路層の分離と斜めの配分の不一致の検出(2026-11-05)
- [§99](developer/099.md) 氷河の SIA・溶岩流の流動の 8 近傍化(lv_diagratio・gl_diagratio。案 A の動的な振り替え。2026-11-05。§96 の段 3)
- [§100](developer/100.md) 水面の勾配の項の可変の重力 g′(f_gravity_correction = 3。案 D + E の試作。2026-11-06)
- [§101](developer/101.md) 混合体流動の抵抗則を斜面に沿って評価する(f_gravity_correction ≥ 2。2026-11-06 挙動変更。案 A)
- [§102](developer/102.md) 運動量保存形移流の流入面の風上値を、面のセルへ実際に水を運ぶ全リンクの流量で重み付けする f_advection_donor = 2(逓減期のハイドログラフの跳ねの原因と対策。2026-11-06 設計合意・実装。2026-11-07 に後継の 3 を追加して 2 は廃止。同日 3 に側方面の乾湿判定の連続化を追加。2026-11-08 に 3 の流向面の判定を薄い供給元に限定。2026-11-09 に 3 を既定に)
- [§103](developer/103.md) fn_reservoir の廃止(2026-11-10 挙動変更。利用者の提案と「全て推奨で」)
- [§104](developer/104.md) examples/benchmark の再構築(2026-11-10。利用者の指示「完全に再構築」「STG を使わず ENC の p_diagratio で 4 近傍に」)
- [§105](developer/105.md) 浅水方程式の入門ページと `f_govequation = 1` の呼称(2026-11-11。利用者の依頼)
- [§106](developer/106.md) 貯留関数法の区画流出 m_sfm(fn_sfm。2026-11-11 合意・実装)と区画流出の共通基盤 m_zonerunoff
- [§107](developer/107.md) ENC の家屋の抗力項の次元の修正(係数に水深を掛けていた誤り。2026-11-12 不具合修正)
- [§108](developer/108.md) エッジ水深のエネルギー頭の頭打ちを、地盤が送り手の水位より高い濡れた受け手にも(f_dry_head_cap = 2。2026-11-13 機能追加、同日に既定を 2 に = §108.8、境目のつなぎ = §108.9)
- [§109](developer/109.md) 秩父のデータの河道マスクを、標高の落水線に載せ直す(2026-11-13。利用者の指摘と決定)
- [§110](developer/110.md) 河道の向きが変わる場所の移流項: 屈曲直後の辺の慣性の欠落と、越流する谷壁の辺による本流のブレーキ(50 m 格子の流況の切り替わりの原因。2026-11-14 発見。屈曲直後の辺の慣性は f_advection_bend で実装し、2026-11-15 から既定 1 = §110.10・§110.18。側方面のブレーキと合流の損失は f_advection_lateral = 1、河岸へのあふれ始めは f_dry_head_cap = 3 で実装し、2026-11-16 から既定 = §110.22〜§110.32)
- [§111](developer/111.md) 窪地処理でできた河道の平坦区間: 池の頭の自励振動(秩父 100 m 格子の測線 3)と、平坦区間の解消の検討(2026-11-17。調査と検討。計算本体・データは変えていない)
- [§112](developer/112.md) 移流項の設計のやり直し(深くて遅い隣のセルの扱い。handoff 00y): 理想化した検定での再現と、規則の候補の試作(2026-11-18〜19。調査と試作の記録。採る形は §112.11、計算本体への実装は §113)
- [§113](developer/113.md) 深くて遅い隣のセルの扱い: `f_advection_donor = 4`・`f_advection_bend = 2`・`f_advection_lateral = 2`・`f_dry_head_cap = 4`(2026-11-19。選択式の値として実装。既定は変えていない)
- [§114](developer/114.md) 既定の切り替え: `f_advection_donor` 3 → 4・`f_advection_bend` 1 → 2・`f_advection_lateral` 1 → 2・`f_dry_head_cap` 3 → 4(2026-11-21。利用者の決定。挙動が変わる)
- [§115](developer/115.md) 教材 tutorials/chichibu の単純化と、例題 examples/chichibu_flood の新設(2026-11-21。利用者の指示。計算本体は変えていない)
- [§116](developer/116.md) developer.md の分割: 基本方針の独立(docs/policy.md)と節ごとのファイル化(2026-11-22。利用者の依頼と、推奨案での合意)
- [§117](developer/117.md) 例題 examples/source_area: 山地流域の流出寄与域の発達と縮小(2026-11-10〜16。作成と検討の経過。handoff 00q から移した)
- [§118](developer/118.md) 河道の向きが変わる場所の移流項(§110)の続き: 200 KB を超えた §110 に代わる追記先(2026-11-22 から)
- [§119](developer/119.md) 混合粒径の段 1(f_bedmix。掃流砂の粒径階 × 交換層 1 枚・下層 1 枚)の実装(2026-11-23。§84.19 の合意と docs/mixed_sediment_plan.md §10 の決めごとに沿う。無効時はビット一致)
- [§120](developer/120.md) 例題 examples/joganji_flume: 国総研の常願寺川 1/100 移動床模型のケース 2-1 を混合粒径で計算し、計測と比べる(2026-11-23。混合粒径の段 3 の例題の部分)
- [§121](developer/121.md) 芦田・道上の有効掃流力(式 (11))を f_taupart = 2 として実装する(2026-11-24。§19.8 の今後の課題。既存の手続きの写しで、無効時はビット一致)
- [§122](developer/122.md) 混合粒径の段 2a: 浮遊砂を粒径階 1 と結び、プローブに Dm の列を足し、抵抗分割の D84 を組成から求める(2026-11-24。docs/mixed_sediment_plan.md の段 2 の最初。既存の手続きの写しで、無効時はビット一致)
- [§123](developer/123.md) 混合粒径の段 2b: 崩落と崖錐・深さ依存クリープ・沿岸漂砂を粒径階の組成で運ぶ(2026-11-24。遡上帯は前提の f_wfsed がないので見送り。無効時はビット一致)
- [§124](developer/124.md) 例題 examples/tsunami_meander: 蛇行水路を進む段波の水理実験(小林ら 2019・2021)を静水圧・非静水圧で計算し、計測と比べる(2026-11-25。計算本体は変えていない)
- [§125](developer/125.md) 例題 examples/coastal_compound_flood: 堤防を越えない沿岸の町の複合浸水(2026-11-25。利用者の依頼。計算本体は変えていない)
- [§126](developer/126.md) 例題 examples/snow_avalanche: 沢を下る流れ型雪崩(走路の雪の連行と誘導堤)と、雪崩の設定の型の見直し(2026-11-25。利用者の依頼。計算本体は変えていない)
- [§127](developer/127.md) 田んぼダムの評価機能 m_paddy(fn_paddy): 落水口の装置則とサブグリッドの水田タンク・区画の解像(2026-11-24 設計合意・段 1 実装、2026-11-25 段 2 実装・段 3 例題・段 4 水質と土砂・集水面積率)
- [§128](developer/128.md) 実効平面積率 af のハロの行の更新漏れ: 堤防の越流の追い越し上限が帯の境で古い値を読む(MPI の実バグ。2026-11-24 発見・修正)
- [§129](developer/129.md) 連行則の改良: Hungr の則(f_dbed = 5)・連行する流動深の下限(db_hent)・取り込んだ質量の運動量(f_dbmom)(2026-11-25。利用者の決定。既定は変えず、無効時はビット一致)
- [§130](developer/130.md) 沢の向きへの依存の原因と修正: 塞がれた開口の動的振り替えの塞がり率を、土砂流動の計算では流動深で測る(横断方向の応力の試作、一様な V 字水路の厳密解との比較、検定 test/vchannel、例題 snow_avalanche の再計算、例題 debris_fan での振り替えの有無の比較、土砂流動を使う例題 5 つの回し直し(§130.12〜§130.16)。2026-11-25〜27)
- [§131](developer/131.md) 例題 examples/confluence_backwater: 合流点の背水による支川の氾濫と、粗い格子・合流の形の確かめ(2026-11-26。利用者の依頼。計算本体は変えていない)
- [§132](developer/132.md) ダムの運転則の拡張: 実績の再生(放流量・貯水位の時系列)と、履歴を持たない実務の操作規則(制限水位・洪水調節開始流量・放流量の上限)(2026-11-26 設計合意・実装。無効時はビット一致)
- [§133](developer/133.md) ダムの量の BMI 公開と外部運転(f_dam_mode = 6): ダムの点の格子と目標放流量の set(2026-11-26 設計合意・実装。無効時はビット一致)
- [§134](developer/134.md) 移流項の近傍の判定に河道の堤防の仮想壁面を見せる: 壁の向こうの湛水が河道を減速させない(handoff 00al。2026-11-26 設計合意・実装。仮想壁面を使わない計算と、壁の向こうが乾いている計算はビット一致)
- [§135](developer/135.md) 例題 examples/coarse_channel: 粗い格子で川を表す表し方(川幅・向き・屈曲・河道マスクの連結・河道の脇の水)と通水の精度の系統的な確かめ(2026-11-26。利用者の依頼。計算本体は §134.10 の修正だけ)
- [§136](developer/136.md) f_slide_noflow の既定を 1 にし、1 の判定をそれまでの 2 に置き換える(薄い膜は下の層の判定を止めない。2026-11-26。利用者の決定)
- [§137](developer/137.md) 幅の極端に狭いサブグリッド河道のセルを、開口の動的振り替えと通水率で計算の外と同じに数える(占有率の細片。2026-11-27。利用者の依頼。挙動の変更)
- [§138](developer/138.md) 河道のセルは堤内地を持たない: 利用者ガイドと例題の注記、河道にする占有率の下限と氾濫原の面積(例題 coarse_channel の系列 fmin。2026-11-27。利用者の依頼。計算本体は変えていない)
- [§139](developer/139.md) 混合粒径の段 2c-1: 土石流(f_debris)との併用。流れの土砂を粒径階ごとの柱で受動的に運ぶ(2026-11-27。利用者の依頼と決定。方針 6 の例外に追記。併用しなければビット一致)
- [§140](developer/140.md) 例題 examples/debris_fan_flume: 混合粒径の材料の土石流扇状地の形成と、清水による侵食(高橋・中川・山敷 1991 の水路実験。2026-11-27。利用者の決定。計算本体は変えていない)
- [§141](developer/141.md) 例題 debris_dam に粒度の幅を持つ堤体のケースを足す(混合粒径と土石流の併用。決壊の流量は変わらず、決壊のあとは最も粗い粒径階が動くかどうかで分かれる。2026-11-27。利用者の決定。計算本体は変えていない)
- [§142](developer/142.md) 高橋・中川則の堆積の式が、非正規化数の濃度でオーバーフローする不具合と修正(境界検査つきのビルドだけで起こる。release の結果はビット一致。2026-11-28)
- [§143](developer/143.md) 混合粒径の段 2c-4: 土石流の式の侵食を動ける粒径階に限る選択子 f_dbsel(流動深と、掃流の領域の限界掃流力による判定。2026-11-28。利用者の依頼と決定。方針 6 の例外に追記。既定は選ばず、無効時はビット一致)
- [§144](developer/144.md) 例題 debris_fan_flume・debris_dam に、土石流の式の侵食を動ける粒径階に限る選択子 f_dbsel のケースを足す(決壊のあとの決壊口の低下はほぼ止まり、巨礫を含む堤体の決壊は遅れて判定の形に敏感、水路実験の薄い流れでは侵食が弱すぎる。2026-11-28。利用者の決定。計算本体は §143)
