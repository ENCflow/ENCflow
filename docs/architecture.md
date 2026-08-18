# ENCflow アーキテクチャの地図 (architecture.md)

初めてこのコードベースに触れる開発者(人間・AI とも)が、最初の
1 時間で全体像をつかむための案内図です。**設計判断の理由と経緯の
正本は developer.md**、**変更時の検証規律は CLAUDE.md** にあり、
この文書は「何がどこにあり、どの順で動くか」だけを一枚にまとめます。
記述が食い違う場合はコードと developer.md が正です。

## 1. レイヤ構造(どのモジュールがどの層か)

```
main.f90 ─ m_main.f90(組み立て・時間ループ・終了処理)
  │
  ├─ 物理プロセス層(fn_* で個別に有効化。無効ならコスト・メモリゼロ)
  │    m_swflow      浅水流の切替器(排他: m_swflow_enc / m_swflow_stg)
  │      m_swflow_enc + submodule: _adv(移流) _bc(境界) _channel(河道・堤防) _diff(拡散)
  │    m_gwflow      地下水の切替器(鉛直は排他: bucket / greenampt。
  │                  加算: lateral / layer2 / conduit(管路連続体層)/
  │                  pump(井戸揚水シンク)/ frost(凍土の浸透抑制))
  │    m_geomorph    土砂・地形変化(加算: creep / fluvial / suspend / wash / debris。
  │                  debris は土石流・地滑り・火山流動の抵抗則/E-D 切替を含む)
  │    m_glacier     氷河(加算: 質量収支(常時)/ flow / slide / ero / ava)
  │    m_intercept   降雨遮断(排他: fixed / initloss)
  │    m_precip      降水    m_evap  蒸発散    m_snow  積雪・融雪
  │    m_tide        潮位    m_wq    水質      m_meteo 気象強制場・暦
  │    m_saltwater   淡塩2層(鋭利界面。地表塩水層+地下塩水 zone+海側境界)
  │    m_boundary    境界条件族(辺・流入・水位・ソース)+ m_boundary_structure(ポンプ・カルバート・分水・ダム)
  │
  ├─ 共有状態・入出力層
  │    m_sysparam (p)  実行制御パラメータ      m_geoinfo (g)  地形・物性・マスク
  │    m_state (s)     時間発展する場の正本、save/restore、統計・画面表示
  │    m_record (r)    プローブ・フラックス測線  m_output      分布ファイル出力
  │
  ├─ namelist 読み込み層: list_*(ファイルを「読むだけ」。解釈・検証・
  │    導出は各 m_*_init が行う。developer.md §12 の層契約)
  │
  ├─ 並列層: m_parallel_serial / m_parallel_mpi
  │    (公開インターフェースは完全同一。#ifdef なし、Makefile が択一
  │     リンク。逐次版は同名手続きの no-op/直結実装。§2)
  │
  └─ 基盤層(どこからでも使う道具)
       m_fileio(text/bil 行列 I/O) m_geotiff + _codec + _inflate(自前 GeoTIFF)
       m_georef(座標参照)  m_ffactor(摩擦テーブル)  m_util / m_sysdep_util
       user_geoinfo / user_initial(理想化実験用フック)
```

依存の向きは常に「上から下」です。物理プロセス層どうしは互いを
use せず、共有状態 s・g・p を介してだけ結合します(結合点は §3)。

## 2. 実行の流れ

### 2.1 初期化(m_main_all。順序に依存があるものは矢印で明記)

```
par_init → sysparam → geoinfo(全域読込・全域前処理)
  → par_decomp_init(セル数重み付き帯分割)
  → geoinfo_scatter_coeffs(物性係数を rank0 から帯+ハロへ配布)
  → boundary → state(← geoinfo, boundary より後)
  → wq → record → precip → intercept → geomorph → gwflow
  → tide → swflow → meteo → evap(← meteo より後) → snow
  → glacier(← meteo・snow より後: 気温と涵養源が必須)
  → output_init → geoinfo_band_shrink(マスク類・z を帯に縮小)
  → run_main(時間ループ)
```

静的データは 3 ゾーンのライフサイクルを持ちます(§11):
初期化中は全域配列 → scatter/band_shrink を経て → 時間ループ中は
帯配列(rank0 のみ g%z の全域を出力・集約用に保持)。
「どの配列がどのゾーンで全域か」の正確な契約は §11 を参照。

### 2.2 1 タイムステップ(run_main。この順序が結合の正本)

```
updatetime                    時刻更新
precip_makepre                降水分布の更新(更新時のみ)
  └ intercept_calc            遮断による有効雨量化(降水更新時のみ)
intercept_step                貯留型遮断の毎ステップ処理
snow_calc                     降雪/融雪(swe ⇄ h)
glacier_calc                  氷河(毎ステップ: 氷面融解 hi → h。dt_glacier 間隔:
                                雪崩→氷化→SIA 流動→氷河侵食。侵食時は s%z, s%e の
                                更新と z のハロ交換まで済ませる)
boundary_makebdc              境界条件値の準備
tide_calc                     潮位(海域セルの水位強制)
swflow_calc                   ★浅水流本体(uv/mn 更新 → 連続式 → h,e,u,v,m,n 確定)
  └ par_allreduce_maxi(ierror) 発散検出の全ランク集約
gwflow_calc                   地下浸透・地下水(s%h から s%hg/s%hgc へ。冒頭で凍土係数の更新、末尾で井戸揚水シンク)
saltwater_calc                淡塩2層(地表重力流・地下塩水 zone・海側境界)
wq_calc                       水質(移流・沈降・負荷)
evap_calc                     蒸発散(h・遮断貯留・hg からの蒸発)
swflow_post                   ステップ確定処理(σ・河道幅有効時の u,v 正規化)
wq_derive                     導出濃度場の更新(確定 h に対して)
geomorph_calc                 地形変化(s%z, s%e 更新+z のハロ交換)
calcstat                      統計(S 台帳・max 類。決定的総和)
表示・ファイル出力・計測      (collective 判定は全ランク同一に)
エラー判定                    CFL 超過等。全ランクで同一判定・同時 exit
```

終了処理は各モジュールの dispose を初期化の逆順で呼びます。
**モジュール私有状態の save は dispose 内**で行うのが契約です
(m_state の save より先に走る。§7・契約5)。

## 3. 状態の所有(誰が何を書いてよいか)

| 記号 | 型 | 所有者 | 内容と規約 |
|---|---|---|---|
| p | t_sysparam | m_sysparam | 実行制御。init 後は全モジュール読み取り専用 |
| g | t_geoinfo | m_geoinfo | 地形 z(入力)・粗度 rn・マスク x/sw/rw・格子。原則不変(例外: なし。動的な標高は s%z) |
| s | t_state | m_state | **時間発展する場の正本**: h, e(=z+h), u, v, m, n, vv, s%z(計算標高), sd(土層厚), hg(地下貯留), hg2(風化基岩層), hgc(管路連続体層), hss/hgs(塩水層厚), hs(土砂), cq(輸送物質), swe(積雪), hi(氷河の氷厚), hrs(ため池)、最大値統計。save/restore は m_state が束ねる(hg2・swe・hi 等のモジュール私有 save は各 dispose。契約5) |
| sx | t_enc_status | m_swflow_enc 私有 | エッジ流速 uv・流量 mn(前ステップ確定)・mn1(更新中)。他モジュールから不可視 |
| r, b, … | 各 t_* | 各モジュール | モジュール私有。リスタートは各自の save ファイル(契約5) |

プロセス間の結合は「s のフィールドを決まった順序で読み書きする」
ことだけで成立しています。たとえば地下水と浅水流は互いを知らず、
gwflow_calc が swflow_calc の後に s%h を減らし s%hg を増やす、という
**実行順序が結合仕様**です(§2.2 の順序を変えることは物理の変更)。
s%h を変更するモジュールは同じループで s%e = s%z + s%h を回復する
こと(反対称適用・柱状換算などの契約 5 箇条は m_gwflow_bucket の
ヘッダが正本の見本)。

## 4. 並列化の型(なぜランク数でビット一致するか)

- **j 方向の帯分割**。dcp%js/je = 担当帯、jsh/jeh = 確保範囲(帯±ハロ2)。
  計算は js..je、全域窓端の縮小は `max(js, jw1+1)..min(je, jw2-1)` 定型(§11)。
- ハロ交換は par_halo_cell(セル場)等。エッジ場はステップ頭に交換済みの
  前ステップ確定値(無印)だけを読む(§7・§8 のバッファ規約)。
- **総和は par_sum_rows**: 全域窓の行部分和を j 昇順に並べて一括総和する
  ため、ランク数・スレッド数によらず結果がビット一致します。max・整数和は
  順序不変なので allreduce 可(§11)。
- collective(gather/reduce/halo)の実行判定は必ず全ランクで同一に。
  is_root ガードの内側に collective を置かない(§5)。
- 帯確保の配列を渡すダミー引数は assumed-shape+下限指定
  (`a(1:, dcp%jsh:)`)。明示形状は行ずれ実バグの元(§12)。

## 5. 機能追加の型(新しいモジュールを書く人へ)

1. **有効化は fn_\* の有無**。"" = 無効(メモリ・CPU 追加ゼロ)、
   "-" = 同じパラメータファイルから読む、ファイル名 = 別ファイル。
2. 排他切替のモデル群(浅水流・地下水鉛直・遮断)は**切替器モジュール+
   手続きポインタ成分**(t_swflow の init/calc/post/dispose が見本)。
   加算的なプロセス群(geomorph の各過程)は**独立フラグの重ね合わせ**。
3. list_* には namelist を読むコードだけを書く。範囲検査・単位換算・
   導出は m_*_init で(§12)。
4. 実装契約(反対称フラックス・e の回復・owner-compute・柱状換算・
   私有 save)は m_gwflow_bucket のヘッダ 5 箇条に従う。
5. 検証は CLAUDE.md の規律で: 等価変換 = ULP=0、機能追加 = 無効時に
   既存 reference とビット一致、MPI に触れたら np=1,2,4 一致、確保に
   触れたら -fcheck=all np≥2 を先に。reference の更新は人間の目視後のみ。

## 6. データの流れ(単位・形式の約束)

- 入力: namelist パラメータファイル+ dir_data 下のラスタ
  (text / bil+hdr / GeoTIFF。読み書きとも自前実装で外部ライブラリなし)。
- 出力: result/ に分布(H0001 等+FILENUMBER.csv。領域マスク X0000 は
  常時出力 §44)、fluxes/・probes/ の CSV、Log.txt、パラメータ控え、
  save/(リスタート)。ParaView 可視化は後処理 utils/out2vtk(§43)。
- 座標・単位: 投影座標系のメートル、行順は北→南、セル番号は 1 スタート。
  計測の実座標指定は x 東向き・y 北向き(§36)。
- 物理量は SI(水深 m、流量 m³/s、降雨のみ慣用で mm/h)。

## 7. 迷子になったときの早見表

| 知りたいこと | 見る場所 |
|---|---|
| 設計判断の理由・経緯・実バグ | docs/developer.md(§0 方針 12 箇条から) |
| 変更時の検証手順・禁止事項 | CLAUDE.md |
| 未完了の作業・中期の道標 | docs/handoff.md |
| パラメータの意味(453 項目) | docs/users_guide/params_index.md と各章 |
| namelist の書き方の見本 | examples/List_samples/ |
| 使い方(利用者視点) | docs/users_guide.md・tutorials/ |
| 他モデルとの立ち位置 | docs/comparison.md |
| 個別機能の設計文書 | docs/*_plan.md(geomorph・debris・glacier・boundary・geotiff・gwconduit・swi〔実装済み〕)・channel_model.md |
| モジュール実装の作法 | src/m_gwflow_bucket.f90 のヘッダ |
| ビルドの仕組み | make.inc・docs/install.md・§1/§3 |
