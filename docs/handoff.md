# ENCflow 作業引き継ぎメモ(チャット移行用)

設計・規約・実バグの記録の正本は developer.md(§1〜§14)。
このメモは「現在進行中・未完了の項目」だけを書く。完了したら消してよい。

## 現在の到達点(要約)

- MPI 化は完了・検証済み: 帯分割+ハロ交換(案A)、確保縮小(第二段)、
  静的データの帯化(方式a・2点縮小)、m_record の点集約、決定的リダクション。
  検証の柱 =「np=1,2,4 が逐次 reference に ULP=0」+「-fcheck np>=2 を先に回す」。
- s%z(計算標高の動的状態化)導入済み。g%z = 入力地形(rank0 のみ全域保持)。
- 新モジュール: m_geomorph(重ね合わせ方式・calc_creep は未実装 par_stop)、
  m_gwflow(enc/stg 型の排他切替・バケツモデル実装済み)。
- m_output 分離、m_swflow の手続きポインタ成分化、list=読み込み専念の層契約。

## 未完了・検証待ち

1. **gwflow 導入コミットの検証(直近の宿題)**
   - fn_gwflow 未指定で全ケース既存 reference とビット一致(逐次・np=1,2,4)
   - バケツ疎通: wave 系 + f_gwvertical=1(旧 f_gwmodel。2026-08-05 改名)で
     S_total が14桁不動、np=1,2,4 ULP=0
   - -fcheck np=2、リスタート往復(save/restore 6成分化の確認)
   - 補記(2026-08-05): gfortran では gwflow 第2弾(下記 1b)の検証で
     無効時ビット一致・np=1,2,4 場一致・-fcheck np=2 を確認済み。
     残るは ifx での同確認とリスタート往復

1b. **gwflow 第2弾(Green-Ampt + パラメータ体系確定)の ifx 検証**
   (実装と gfortran 検証は 2026-08-05 完了。決定は developer.md §16、
    進捗は handoff_gwflow_tani.md §9)
   - 内容: f_gwmodel → f_gwvertical 改名+f_gwlateral 予約(0のみ受理)、
     geoinfo の sd(f_sdtype 3状態)/sy0、m_gwflow_greenampt 追加、
     モデル calc への実効時間刻み dts 供給(bucket の dt_gwflow>dt 時の
     実効浸透率 1/N を修正)
   - ifx で: 無効時ビット一致(wave/chichibu)、greenampt 疎通
     (S_total 14桁不動・np=1,2,4)、-fcheck 相当(-check all)np=2
   - 注意: 旧 param の f_gwmodel は namelist 読込エラーで検出される
     (互換入力なし。examples/List_samples/list_gwflow.txt 参照)

1d. **河道水理モデル(fn_channel: §17 堤防+§18 開口補正・サブグリッド
    河道幅)の残検証**(実装と gfortran/OpenMPI 検証は 2026-08-06 完了。
    設計正本は developer.md §17, §18。namelist は fn_channel /
    &list_channel に移行済み: fn_bank / bank0 / f_bank_datum /
    f_bank_aggr / f_bank_mode / f_bank_opening / fn_width /
    f_channel_advection。examples/List_samples/list_channel.txt 参照)
   - gfortran で確認済み: 無効時ビット一致(wave/chichibu、逐次+
     np=1,2,4)、-fcheck np=2(規律3。幅テーブルの帯上端バグを捕捉・
     修正済み)、bank0=一様分布ファイルとビット一致、opening=0 が
     厳密数学ビルドで移行前とビット一致、W≥面長で堤防のみとビット一致
     (退化性)、幅有効の np=1,2,4 ULP=0、自動ゼロ堤防の通知・動作
   - 残: ifx での同確認(無効時ビット一致・np=1,2,4)
   - 残: PREC=single ビルドの通し
   - 残: リスタート往復ビット一致(bank / width 有効ケース。新規状態は
     ないので既存機構で閉じるはずだが実証する)
   - 残: 等流ベンチマーク(矩形断面 Manning 解析解)との定量比較と
     恒常テストケース化(f_channel_advection の既定値もこの結果で確定)
   - 残: 実河川の幅データ(国土数値情報等)での実地検証、
     並列河道セル(角の2セル太り)検出警告の実装(§18 制約(6))
   - vv 正規化(u,v をセル方向別通水率 cwx/cwy で除算。§18)は実装・
     gfortran 検証済み 2026-08-06(-fcheck np=2、無効時ビット一致、
     W≥面長退化ビット一致、W=20m の np=2,4 ULP=0)。ifx 検証は上記に同梱
   - 河道内植生の抵抗は gv/bb の河道セル適用で表現可能と確認(§18。
     コード変更不要。粗度 rn との分担指針に注意)
   - 破堤(&list_channel_breach。§18)実装・gfortran 検証済み 2026-08-06:
     -fcheck np=2、無効時ビット一致(bank ケースは -O2 で前コミット一致)、
     f=1.0 固定が無破堤と同一バイナリでビット一致、破堤前区間の一致、
     MPI バイナリ内 np=1,2,4 完全一致、厳密数学で serial=MPI 一致。
     注意: -Ofast では serial/MPI の別ビルド間に fast-math 差(§9 の
     ULP=1 クラス)が出るようになった(bank_wall の submodule 化以降)。
     ifx 検証・恒常テスト化は 1d の残項目に同梱

1c. **gwflow 第3弾(側方流動 Boussinesq)の残検証**
   (実装と gfortran 検証は 2026-08-05 完了。決定は developer.md §16.1、
    進捗と検証内容は handoff_gwflow_tani.md §9 の 2〜5)
   - ifx で: 無効時ビット一致、側方有効時の逐次 vs np=1,2,4 全場出力
     ビット一致(gfortran では一様sd・拘束的分布sd・薄層飽和の3ケースで
     確認済み)、-check all np=2
   - **解析解のある Boussinesq 拡散問題との定量比較(1Dベンチマーク)は
     未実施**(§9 の 2 の残)。恒常テストケース化(test/ 配下)も未着手
   - 側方有効時のリスタート往復ビット一致の確認(私有状態なしの想定の
     実証。s%hg は m_state 経由)
   - 谷型シナリオテスト(§9 の 6)はこれから
2. **developer.md への gwflow/geomorph の項の追記**(検証完了後)
   - 切替器 vs 重ね合わせの使い分け原則、s%hg 柱状換算契約、S 台帳、
     モデル実装5箇条(m_gwflow_bucket ヘッダが正本)
3. developer.md の日付プレースホルダ(2026-xx)の実日付化(残があれば)
4. **降雨遮断モジュール(m_intercept)の残検証**
   (無効時ビット一致と wave 疎通((1-α) 倍・np=1,2,4 ULP=0)は確認済み
    2026-08-04)
   - prtype=3 かつ dt_prupdate < dt_maplist の設定で二重減衰しないこと
     (updated ガードの検証。Pr 出力が分布更新のたびに一定率か目視)
   - developer.md への追記(gwflow/geomorph の項と併せて。上記2参照)
   - **第2弾(分布ファイル+初期損失モデル。2026-08-06)の検証**:
     - 無効時ビット一致の再確認(fn_intercept 未指定で全ケース。
       run_main に m_intercept_step の毎ステップ呼び出しが増えたため)
     - 固定率+一様値が第1弾と同値のままであること(乗算値は同一なので
       ビット一致のはず。wave 一発で可)
     - 固定率+分布: 一様値と同値を敷き詰めたマップで一様指定と
       ビット一致(np=1,2,4)
     - 初期損失の疎通: wave 一定雨+一様 smax で、遮断総量が
       Σ smax(有効セル)に飽和し、飽和後は S の入力勾配が素通しに
       復帰すること(相対 1e-14 程度は乗除の端数。契約D)。np=1,2,4 一致
     - 初期損失のリスタート: save → restore → save で
       intercept_initloss.dat がビット一致(st の往復)。
       restore 時に保存ファイルが無い場合の par_stop も確認
     - -fcheck np>=2(帯確保の新配列 st/pr0/prh0/マップ類)
5. **初期化の方式2・第1段(係数の rank0 化+scatter)の検証**
   - **確保に触れる変更なので -fcheck=all の np>=2 を最適化ビルドより先に**
     (静的データを使う chichibu で。規律3)
   - 逐次で既存 reference とビット一致(scatter_band は逐次 no-op 経路)
   - np=1, 2, 4 が逐次 reference に ULP=0(chichibu: 実地形+粗度+河道)
   - user フックありのケース(wave 系の f_user_routine_id>0)で np=1,2,4
     ビット一致(フックの rank0 実行+マスク再 bcast 経路の検証)
   - f_rntype=2(lu2rn 変換)のケースがあれば併せて確認(read_rn の
     rank0 経路)

6. **座標管理(m_georef / ESRI hdr)導入コミットの検証**
   (仕様と決定事項は docs/geotiff_plan.md §10)
   - gfortran 逐次では検証済み: wave/chichibu(txt 入力)がベースラインと
     全出力ビット一致、bil+hdr 入力が bil 単独入力と全出力ビット一致
     (hdr から nx,ny,dx,dy 補完)、矛盾指定の par_stop、出力 hdr の往復。
   - 経緯度格子(実データの hdr)も gfortran 逐次で検証済み: dx,dy 未指定の
     par_stop、概算との大差(100m 格子に 250m 指定)の par_stop、
     慣習的近似(100m 指定 vs 概算 100.2/123.3m)の受理と両値表示、
     度単位のままの出力 hdr 往復。
   - 残: ifx での全ケース既存 reference ビット一致(逐次・np=1,2,4。
     collective は追加していないが確認はする)
   - 残: PREC=single ビルドの通し(座標は real64 固定の設計確認)
   - 残: 出力 .hdr+.bil を QGIS / ArcGIS で開いて位置・値の目視確認
     (GDAL EHdr 互換キーで書いている。gdalinfo でも可)
   - 残: examples の param サンプルへの epsg / hdr 運用の説明追記
7. **GeoTIFF Phase 1〜3 完了(読み書きとも実用範囲は完成)**
   - 読み: m_geotiff + m_geotiff_codec + m_geotiff_inflate、f_input_mode=4
     (形式番号は出力のビット値と共通。3 は専用メッセージで停止)。
     書き: gtif_write(無圧縮単一 strip・Float32/Int32・GeoKey)、
     f_output_mode をビット和(1:text, 2:bil, 4:geotiff。3=従来互換)に変更。
     座標未管理で geotiff 出力指定は初期化時 par_stop。
     残るのは Phase 4(BigTIFF 読み・precip の multi-IFD・圧縮書き等、
     必要になってから)
   - gfortran で検証済み: test/gtif の 47 テスト PASS(往復 4 テスト含む。
     PREC=single でも PASS)、txt ケースの無効時ビット一致(wave/chichibu)、
     chichibu の GeoTIFF 入力(LZW / Deflate+pred3)が bil+hdr 入力と全出力
     ビット一致、mode=7 の tif 出力 118 ファイルが bil と画素ビット一致、
     gdalinfo が EPSG:2451/6668/6677 を正しく解決、mode=3 従来互換、
     epsg 不一致・座標未管理 gtif 出力の par_stop
   - 残: ifx ビルド・np=1,2,4 の無効時ビット一致(collective は増やして
     いないが確認する)。test/gtif の Run.sh は逐次専用
   - QGIS / ArcGIS Pro の実出力サンプル受領・組み込み済み(2026-08-01。
     test/gtif/data_user、16 テスト追加で計 39 PASS)。ArcGIS のタイル+
     GeoKey 併記(4612+2451)、QGIS の実数文字列 nodata、i8 型を実物で
     検証。QGIS 高圧縮(Deflate+pred2)も Phase 2 で読解済み。
     よく使う CRS は JGD2000 平面直角 9 系(EPSG:2451)
   - bil 読みの画素型対応(2026-08-01。geotiff_plan.md §10 項9): sidecar
     hdr の NBITS/PIXELTYPE で int8/int16/int32×符号有無を読み分け。
     gfortran で検証済み: GDAL EHdr の Byte/Int16/UInt16 マスク入力が
     int32 版と全出力ビット一致、hdr なし(生 int32)の従来経路ビット一致、
     Float64・型違い・格子数不一致の明示エラー、経緯度 hdr の probe 不変
   - 経緯度格子で CRS 未指定なら WGS84 を仮定(2026-08-01。表示つき。
     epsg 明示が優先、投影系は従来どおり CRS なし)。検証: 仮定時の tif が
     EPSG:4326、epsg=6668 明示時は JGD2011、メートル hdr は CRS なし、
     既存結果ビット一致
   - QGIS での目視確認済み(2026-08-01): wrk_*.tif の見た目 OK、
     実データ往復の wrk_d2451_real / wrk_d4326_real は位置も OK
     (便宜座標の wrk_* が架空位置に出るのは仕様。README 参照)。
     ArcGIS でも開けるかの確認は任意で残

8. **境界条件 Phase 0/1(境界正規化・辺境界・ソース再編)の残検証**
   (実装・gfortran/OpenMPI 検証済み 2026-08-02。記録は boundary_plan.md
   §8/§9、設計正本は developer.md §15)
   - ifx での無効時ビット一致(逐次・np=1,2,4。inflow_dist で
     par_allreduce_sumr の collective が増えた点に注意)
   - 開辺ケースの恒常テスト化(放射境界ベンチマーク新設時に合流)
   - PREC=single ビルドの通し確認(inflow_dist の重み共有を含む)

9. **乾床薄膜先端の「質量微増」— 原因特定済み(2026-08-03)。対処は要議論**
   - 結論: 質量は作られていない。全セルの Σh(負値込み)は注入量と
     機械精度で一致する(一時計装の台帳測定で 600 ステップ累積残差
     ~1e-16 m³)。見かけの +0.1% は S モニタの定義による集計アーティ
     ファクト: f_exflux_reduction=0 では前縁で dh > h の過大流出が
     h1 < 0 のセルを作るが、m_state の診断集約は h <= 0 を cycle する
     ため(m_state.f90 の hsum)、負水深の欠損が S から見えず
     |Σ min(h,0)| ぶん S が過大に見える。乾床注入 30s で
     S 超過 +1.407e-4 m³ ⇔ 負水深計 −1.408e-4 m³(湧き出し)、
     +2.9302e-4 ⇔ −2.9302e-4 m³(区間流入)と全桁一致。
   - 指紋: 台帳は t≈22.5s(最初の h1<0 発生)まで機械精度で厳密。
     f_exflux_reduction=1 にすると負水深がほぼ出ず超過も消える
     (+0.023% → +0.00007%)。適応 RK は無関係。dt/2 で微減。
   - 対処の選択肢(未決。実装前に議論):
     (a) 乾床前縁を扱う計算では f_exflux_reduction=1 を推奨する運用
         (本来この目的のフラグ。例題 param の既定も要検討)
     (b) S モニタの負水深の扱いを変える(負値も総和する、または
         負水深の総量を別枠で表示して見かけの超過をなくす)
     (c) 抑制 OFF でも負水深を許さない設計変更(挙動変更なので
         reference 更新を伴う。優先度低)

## 中期の道標(着手順は実測次第)

- セル数重み付き帯分割は実装済み(2026-08。developer.md §11)。残るは
  全国データでの実測(メモリ RES、ランク別時間)による残余不均衡の確認
  (乾湿の時間変動が支配的なら静的分割では捉えられない)
- geomorph: **F0(calc_creep + 加速係数 morfac)実装・検証済み 2026-08-07**
  (developer.md §19。解析解ベンチ test/creep 新設、無効時ビット一致・
  -fcheck np=2・np=1,2,4 ビット一致は gfortran/OpenMPI で確認済み。
  ifx での同確認は未)。s%z のハロは calc 末尾交換で解決(§11 TODO(1))。
  **F1a(s%sd 動的化+gwflow 読み替え+save 5成分化)も実装・検証済み
  2026-08-07**(developer.md §19.1。save_version = "2026-08-07" に更新。
  旧 save は版照合で停止する)。
  **F1b(掃流砂 Exner f_fluvial+sd 共動更新+gwflow 容量引き渡し)も
  実装・検証済み 2026-08-07**(developer.md §19.2。test/fluvial 新設。
  時間発展 z の出力は既存の f_out_z=1 で可能=§11 TODO(2) は解消)。
  **F2(浮遊砂 f_suspend: s%hs+swflow_enc ステップ内移流(汎用
  スカラーカーネル advect_scalar)+E-D 交換)も実装・検証済み
  2026-08-07**(developer.md §19.3。test/suspend 新設。save は
  6成分 "2026-08-07b")。
  **板倉・岸式(f_esform=2)実装・検証済み 2026-08-07**(典拠は
  実践河川水理学(iRIC)第4章。§19.3。test/suspend の param_ik で恒常検定)。
  **境界土砂供給・第1段(開境界の容量輸送+平衡給砂 fluv_bcfeed)
  実装・検証済み 2026-08-07**(§19.4。残: 浮遊砂の境界流入濃度、
  区間流入の Qs(t)。plan §2.7)。
  残: 等流×給砂平衡・定常巻き上げ沈降の解析解ベンチマーク(平衡給砂で
  上流条件は準備済み)、fluvial/suspend の morfac 等価性ベンチ、
  ifx での geomorph 一式(F0〜F2)の確認。
  **fn_width 併用対応は実装・検証済み 2026-08-07**(§19.2 追補。
  掃流=frw+河道底集中、浮遊=無修正整合、堤防エッジは掃流遮断)。
  **record への hs/sd 計測追加も実装・検証済み 2026-08-07**(プローブ
  8成分化・CSV 列追加。rerecord の z 確保漏れ修正を含む。§19.3)。
  **F3(斜面浸食 f_wash)実装・検証済み 2026-08-07**(developer.md §19.5。
  test/wash 新設。m_geomorph はプロセス別 submodule に分割済み)。
  F0〜F3 完了。残の主要項目: 解析解ベンチマーク(平衡勾配・巻き上げ
  沈降)、morfac 等価性ベンチ(fluvial/suspend)、浮遊砂の境界流入濃度・
  区間流入 Qs(t)(plan §2.7)、侵食係数の校正指針、混合粒径(F4)、
  ifx / PREC=single での geomorph 一式の確認。
  設計正本は docs/geomorph_plan.md(改訂3)
- gwflow: RRI 型・鉛直浸透重視型の追加(m_gwflow_bucket を複製して契約に従う)
- intercept: 初期損失モデルと分布ファイル対応は実装済み(2026-08-06。
  貯留型の3点セット=step 口・原雨量私有保管・st の save/restore を含む。
  貯留型の実装契約は m_intercept_initloss ヘッダが正本)。残るは
  キャノピー貯留(蒸発回復あり)・Gash の追加(m_intercept_initloss を
  複製して契約に従う)と、土地利用からの構築(lu2rn 同型。
  m_intercept_fixed ヘッダ契約5)
- NEC SDK 実機検証(mpinfort -show の可否確認 → スタンプ機構の対応判断)
- **初期化メモリピーク対策・第2段(ゾーン2の rank0 化)**。第1段
  (物性係数の rank0 化+scatter。2026-07-31 実装)で非 root の一過性
  ピークから係数6配列を削減済み。残るのは z, x, sw, rw(全ランク全域)と
  ts(m_state の全域一時)。第2段の候補:
  (a) m_state の全域初期化(set_h / fill_depression / user_initial)を
      rank0 実行にして ts を rank0 のみ確保 → par_scatter_cell で帯配布
  (b) record / boundary の位置検証を「帯所有ランクが検証+allreduce」方式に
  (c) precip prtype3 の冗長読みを rank0 読み+scatter に
  (d) 最後に band_shrink を scatter 化して非 root の全域確保をゼロに
  (b) は §11「冗長計算=配布機構」原則の改定を伴うため実装前に議論する。
- **save/restore のメモリスケーラビリティ**(全国 100m 級への障壁)。
  エッジ復元(swflow_enc の uv/mn。最大コスト)は par_scatter_edge で
  scatter 化済み(2026-08-04。非 root は全域一時を持たない)。残り:
  (1) セル成分(m_state)の restore は ts(全域一時)経由の bcast のまま。
      ts は新規初期化も使うため、初期化第2段(a)= ts の rank0 化と
      同時に scatter 化する(単独でやってもメモリは減らない)
  (2) rank0 の全域一時は残る(RLE が先頭からの逐次展開のため。
      250m エッジ1本 1.7GB、100m で 11GB)。rank0 を太いノードに
      置けば成立。解消するなら「RLE を展開しながら j 順に帯を送る」
      ストリーミング配布(save 側も対称に可能)。RLE の逐次性とは
      整合するので MPI-IO・形式変更なしで実現できる。
      m_fileio の読み書き口の再設計を伴うため 100m 運用が
      現実になった段階で着手
- **t_state の診断・最大値記録系のオプション確保化**(逐次実行の
  メモリ削減の最大の残り札。2026-08-05 の検討より)。
  hmax/hmaxt/vvmax/qqmax/qqdir/qdir/qqt/qcum/fr/cn の10本+ddir1/ddir8 は
  純粋な出力用途で、250m 全国(~4.7e7 セル)の逐次実行 21GB のうち
  倍精度 ~4.5GB(単精度でも ~2.2GB)を常時占める。出力有効時のみ
  確保するオプション化は「機能追加=無効時ビット一致」で検証でき規約と
  整合する。なお同検討で、geoinfo 実数の real32 固定(~1.2GB)と
  マスク類の int8 化(~0.7GB)は不採用と決定: 両方でも 16GB 機の
  目標に届かず、倍精度ビルドの結果が変わり(全 reference 更新)、
  §1 のフラグ精度方針に混合 kind を持ち込み、PREC=single では無意味の
  ため。16GB 機での動作確認用途は PREC=single ビルド(定常 ~10.5GB)で
  足りており、本項の着手は「倍精度のまま 16GB」等の需要が出てから

- 作業対象の**現行ファイルを都度アップロード**(AI 側のファイルは残らない)
- 等価リファクタ=逐次ビット一致、機能追加=無効時ビット一致、が合否判定
- 等価変換とバグ修正・挙動変更はコミットを分ける
- 確保範囲を変える変更は、最適化ビルドより先に -fcheck np>=2
- 過去の議論の詳細は「以前のチャットで◯◯をどう決めたか検索して」と
  頼めば AI が過去会話から掘り返せる
