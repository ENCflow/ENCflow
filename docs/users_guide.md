# ENCflow ユーザーガイド

ENCflow の設定と実行のリファレンスです。初めての方はまず
[チュートリアル](tutorial.md) で一度動かしてから戻ってくることを
勧めます。このページ(第I部)で ENCflow の全体像と入力の作法を説明し、
個別のテーマは章別のページへ分かれています。

検証の内容と実行手順は [testの一覧](../test/README.md)、
現象別の設定例は [examplesの一覧](../examples/README.md) を参照してください。
各章にも、その機能に対応する検証ケース・例題へのリンクを掲載しています。

## 目次

**第I部 全体像**(このページ)
- [ENCflow の骨格](#encflow-の骨格)
- [機能の有効化 — fn_\* の原則](#機能の有効化--fn_-の原則)
- [パラメータファイルの読み方](#パラメータファイルの読み方)
- [実行の流れ](#実行の流れ)
- [ユーザールーチン](#ユーザールーチン)
- [やりたいことから引く](#やりたいことから引く)

**第II部 横断機能**
- [時刻の管理](users_guide/time.md) — 時間軸・時間刻み・出力間隔・暦
- [座標系の管理](users_guide/coordinates.md) — 絶対座標とローカル座標・EPSG・経緯度格子
- [入出力の形式](users_guide/io.md) — テキスト/bil/GeoTIFF・出力ファイル体系
- [中断と再開](users_guide/restart.md) — 状態保存・時刻継続・初期条件としての利用
- [ネスティング(多段格子)](users_guide/nest.md)(fn_nest、&list_nest)— 親格子の中の子格子を同時に解く(多段・双方向・Flather 放射・非静水圧の帯)
- [並列実行](users_guide/parallel.md) — OpenMP・MPI・結果の再現性

**第III部 機能別リファレンス**
- [浅水流計算](users_guide/swflow.md)(&list_enc、数値パラメータ)— 方式選択・適応的ルンゲクッタ・数値定数
  - [ENC 格子と時間積分の解説](users_guide/encgrid.md) — 8 方向格子の通過幅・連続式・セル流速の再構成・圧力/摩擦/抗力項・適応的ルンゲクッタ・クーラン数・数値定数の根拠(浅水流計算の補足)
  - [移流項のスキーム](users_guide/advection.md) — 方程式・運動量保存形の検査体積・ステンシル・限定器(浅水流計算の補足)
  - [非静水圧補正の解説](users_guide/nonhydrostatic.md) — 1 層モデルの方程式・射影アルゴリズム・活性集合・砕波・動く底面・参考にした他モデル(浅水流計算の補足)
  - [拡散項の解説](users_guide/diffusion.md) — 渦動粘性モデル(定数・ゼロ方程式)・9 点ラプラシアン・安定条件(浅水流計算の補足)
- [地理情報](users_guide/geoinfo.md)(&list_geoinfo)— 格子・地形・粗度・マスク・海岸堤防
- [初期条件](users_guide/initial.md)(&list_initial)— 水深・水位・窪地充填
- [境界条件](users_guide/boundary.md)(&list_bound_edge/source/stage/inflow)— 辺境界・ソース・水位規定・区間流入
- [潮位・海面](users_guide/tide.md)(&list_tide)— 高潮・上げ潮浸水・排水
- [内部水理構造物](users_guide/structure.md)(&list_struct_pump/culvert/diversion/dam)— ポンプ・カルバート・分水・ダム・湖沼
- [河道](users_guide/channel.md)(&list_channel)— 堤防・河道幅・断面形・破堤
- [降雨・気象](users_guide/forcing.md)(&list_precip / intercept / meteo / evap / snow)— 降水・遮断・気温・蒸発散・積雪融雪
- [地下水](users_guide/gwflow.md)(&list_gwflow とモデル固有設定)— 浸透・側方流動・風化基岩層・管路連続体層(下水道網・岩盤亀裂網)
- [淡塩2層](users_guide/salt.md)(&list_salt)— 塩水くさび・海水浸入・淡水レンズ(鋭利界面近似)
- [土砂・地形変化](users_guide/geomorph.md)(&list_geomorph)— 掃流砂・浮遊砂・斜面浸食・土石流・長期地形発達
- [流木](users_guide/driftwood.md)(&list_driftwood)— 流木化(水理的流失・侵食連行)・輸送・堆積(ラスタ場の概算)
- [家屋破壊・瓦礫](users_guide/bldgdebris.md)(&list_bldgdebris)— 氾濫流・流木による木造家屋の破壊・瓦礫の輸送・堆積・空隙率への帰還(ラスタ場の概算)
- [氷河](users_guide/glacier.md)(&list_glacier)— 涵養・融解・氷体流動・氷河侵食・雪崩再配分
- [溶岩流](users_guide/lavaflow.md)(&list_lavaflow)— 噴火口からの湧き出し・Bingham 粘性流動・停止・固化(溶岩原の地形化)
- [規定底面運動](users_guide/bedmotion.md)(&list_bedmotion)— 地盤変位の時刻歴で z を強制(断層津波の発生)
- [水質](users_guide/wq.md)(&list_wq)— 負荷投入・輸送・減衰・洗い出し・Kd 二相分配・地下水経由・貯水池
- [土壌雨量指数](users_guide/swi.md)(&list_swi)— 土砂災害警戒の実務指標(気象庁3段タンク。専用ラン)
- [計測](users_guide/record.md)(&list_record)— プローブ・フラックス測線
- [用途集](users_guide/usecases.md)— 現象名から機能の組み合わせを引く(未対応の現象も明示)

**付録**
- [全パラメータ索引](users_guide/params_index.md) — 全 583 パラメータの名前→章の逆引き

---

## ENCflow の骨格

ENCflow は地表の水の流れを計算するモデルです。必要に応じて、降雨・
地下水・土砂などの計算を同じ格子上に追加できます。

## 機能の有効化 — fn_\* の原則

**必要な設定だけ書けば始められます。** 機能の設定で必須なのは
[地理情報](users_guide/geoinfo.md)（`fn_geoinfo`）だけです。それ以外は
書かなければ既定の動作になるか、その機能を使わない状態になります。
**`fn_XXX=""` を書き並べる必要はありません。**

初期条件や計算法を変えたいとき、降雨などの機能を追加したいときに、
その `fn_XXX` を `&list_sysparam` に書き足します。

- 設定を **同じファイル**に書くなら `fn_XXX="-"`
- **別ファイル**に書くなら `fn_XXX="ファイル名"`

![最小限の設定で始め、必要な機能を追加する](figs/config_structure.png)

*左は平坦な地形で始める最小例。右は降雨を追加する例。使わない機能の設定は書かなくてよい。*
[SVG](figs/config_structure.svg) · [生成コード](figs/guide/fig_config.py)

**指定しないときの動作**

| 設定 | 書かなかった場合 |
|---|---|
| 地理情報 `fn_geoinfo` | 同じファイルの `&list_geoinfo` を読む（地理情報の準備は必須） |
| [初期条件](users_guide/initial.md) `fn_initial` | 乾いた状態から開始 |
| [浅水流計算](users_guide/swflow.md) `fn_enc` | 既定の計算法で水の流れを計算 |
| [境界条件](users_guide/boundary.md) `fn_boundary` | 計算領域の4辺は不透過（水を通さない壁） |

これ以外の下表の追加機能は、`fn_XXX` を書かなければ有効になりません。

<details>
<summary>追加できる機能の一覧</summary>

| 機能 | 設定ファイルの指定 | namelist グループ |
|---|---|---|
| 潮位・海面 | `fn_tide` | &list_tide |
| 内部水理構造物 | `fn_structure` | &list_struct_pump / culvert / diversion / dam |
| ため池 | `fn_reservoir` | (地理情報と併用) |
| 河道 | `fn_channel` | &list_channel(+ breach) |
| [降水](users_guide/forcing.md) | `fn_precip` | &list_precip |
| 降雨遮断 | `fn_intercept` | &list_intercept(+ モデル固有) |
| 気象強制場(気温ほか) | `fn_meteo` | &list_meteo |
| 蒸発散 | `fn_evap` | &list_evap |
| 積雪・融雪 | `fn_snow` | &list_snow |
| 氷河 | `fn_glacier` | &list_glacier |
| 溶岩流 | `fn_lavaflow` | &list_lavaflow |
| 規定底面運動 | `fn_bedmotion` | &list_bedmotion |
| 地下水 | `fn_gwflow` | &list_gwflow(+ モデル固有) |
| 淡塩2層 | `fn_salt` | &list_salt |
| 土砂・地形変化 | `fn_geomorph` | &list_geomorph |
| 流木 | `fn_driftwood` | &list_driftwood |
| 家屋破壊・瓦礫 | `fn_bldgdebris` | &list_bldgdebris |
| 水質(負荷流出) | `fn_wq` | &list_wq |
| 土壌雨量指数 | `fn_swi` | &list_swi |
| 計測(プローブ・測線) | `fn_record` | &list_record |

</details>

書き方に迷ったら、[動く設定例（test/wave）](../test/wave/) や
[全設定の記述例](../examples/List_samples/list_sysparam.txt) を参考にしてください。

## パラメータファイルの読み方

パラメータファイルは Fortran の **namelist 形式**のテキストです。

```
&list_sysparam            ! グループの開始
  dt = 0.01               ! 「名前 = 値」を並べる。! 以降はコメント
  tt = 8.0
  fn_geoinfo = "-"        ! 文字列は引用符で囲む
/                         ! グループの終了
```

- 書く順序は自由で、書かなかったパラメータは既定値になります。
- 配列は `prval(:,1) = 0, 15` のように添字を付けて行ごとに書けます。
- **存在しない(綴りを間違えた)パラメータ名はエラーで停止します**。
  バージョン更新でパラメータが改名された場合も同じ仕組みで検出され、
  エラーメッセージが移行先を案内します。
- エラーメッセージ・実行時表示は英語です(世界中の利用者が検索・質問
  できることを優先しています。日本語の解説はドキュメントが担います)。

## 実行の流れ

```bash
./encflow param.txt
```

パラメータファイルを1つ与えて実行します。実行ファイルは計算したい
ディレクトリに `bin/encflow` へのリンクを張る(またはコピーする)
だけで、どこでも動きます
([インストールガイド 3.4 節](install.md#34-自分の計算はどこで実行してもよい))。画面には設定の読み込み
状況に続いて、時刻・保存量 S・ルンゲクッタ適用率・クーラン数などの
監視列が表示されます(列の読み方は
[チュートリアル Step 1](../tutorials/wave/README.md#実行)、
列の選択は f_disp_\* — [入出力の章](users_guide/io.md) 参照)。

結果は出力ディレクトリ(既定 `result/`)に、分布ファイル
(`H0001.txt` など)・計算ログ `Log.txt`・使用パラメータの控えとして
書き出されます。ファイル名の体系と形式は
[入出力の章](users_guide/io.md) にまとめてあります。

計算が途中で止まるときは、原因を特定したうえで**明示的にエラー停止**
します(黙って不正な値のまま進めることはしません)。メッセージには
原因のパラメータ名・ファイル名が含まれるので、まずそれを確認して
ください。

## ユーザールーチン

地形や初期条件を数式・コードで与えたいとき(理想化実験・ベンチマーク)
のために、名前で呼び出すユーザールーチンの仕組みがあります。

```
&list_initial
  f_user_routine = "wave_hump"   ! 登録済みルーチンの識別名
/
```

登録済みの識別名は `src/user_geoinfo.f90`(地形)・
`src/user_initial.f90`(初期条件)の冒頭に一覧があります。自作する
ときは各ファイル末尾の `template` を複製し、識別名を登録して
リビルドします。実データを使う通常の計算では使いません。

## やりたいことから引く

より詳しい一覧(現象名 → 機能の組み合わせ → 設定の要点。未対応の
現象も含む)は [用途集](users_guide/usecases.md) へ。

| やりたいこと | 使う機能(章) |
|---|---|
| 洪水氾濫の計算 | [地理情報](users_guide/geoinfo.md)+[境界条件](users_guide/boundary.md)(+河道・構造物) |
| ダム・ため池の決壊氾濫 | [河道](users_guide/channel.md)(堤防+破堤)+[用途集](users_guide/usecases.md) |
| 霞堤・遊水地・二線堤の治水効果 | [河道](users_guide/channel.md)(堤防・開口)+[構造物](users_guide/structure.md) |
| 干拓地・低平地の機場排水 | [構造物](users_guide/structure.md)(ポンプ)+[潮位・海面](users_guide/tide.md) |
| 高潮・津波の遡上 | [潮位・海面](users_guide/tide.md)+[境界条件](users_guide/boundary.md) |
| 地震(断層)による津波の発生〜伝播〜遡上、沿岸の隆起・沈降 | [規定底面運動](users_guide/bedmotion.md)(+utils/fault2disp)+[境界条件](users_guide/boundary.md)(放射) |
| 地滑り・山体崩壊・海底地滑りによる津波 | [土砂・地形変化](users_guide/geomorph.md)(動く底層)(+[浅水流計算](users_guide/swflow.md)の非静水圧補正) |
| 分散性のある津波・波(河川遡上津波のソリトン分裂・undular bore・孤立波) | [浅水流計算](users_guide/swflow.md)(非静水圧補正 f_nonhydrostatic) |
| 降雨流出(流域水文) | [降雨・気象](users_guide/forcing.md)(+地下水) |
| 都市の内水氾濫(下水道の排水・噴出) | [地下水](users_guide/gwflow.md)(管路連続体層)+[降雨・気象](users_guide/forcing.md) |
| 海水浸入・塩水くさび・淡水レンズ | [淡塩2層](users_guide/salt.md)+[潮位・海面](users_guide/tide.md) |
| 土砂輸送・土石流 | [土砂・地形変化](users_guide/geomorph.md) |
| 流木を伴う洪水・土石流 | [流木](users_guide/driftwood.md)(+土砂・地形変化) |
| 津波・高潮による家屋の破壊と瓦礫の流動・堆積 | [家屋破壊・瓦礫](users_guide/bldgdebris.md)(+流木・潮位) |
| 降雨で誘発される斜面崩壊・土石流 | [土砂・地形変化](users_guide/geomorph.md)+[地下水](users_guide/gwflow.md)(浸透→間隙水圧) |
| 貯水池の堆砂・排砂 | [土砂・地形変化](users_guide/geomorph.md)+[構造物](users_guide/structure.md) |
| 汚濁負荷・物質輸送 | [水質](users_guide/wq.md) |
| 融雪を含む計算 | [降雨・気象](users_guide/forcing.md)(積雪・融雪+気温減率) |
| 氷河の融解水・カール地形の形成 | [氷河](users_guide/glacier.md)(+降雨・気象、長期は中断と再開) |
| 氷河湖決壊洪水(GLOF) | [氷河](users_guide/glacier.md)+[河道](users_guide/channel.md)(破堤) |
| 観測点との比較・流量測線 | [計測](users_guide/record.md) |
| 長時間計算の分割・シナリオ分岐 | [中断と再開](users_guide/restart.md) |
| GIS データ(GeoTIFF 等)の入出力 | [座標系](users_guide/coordinates.md)+[入出力](users_guide/io.md) |
| 大規模計算・クラスタ実行 | [並列実行](users_guide/parallel.md) |
