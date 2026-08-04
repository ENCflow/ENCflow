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
   - バケツ疎通: wave 系 + f_gwmodel=1 で S_total が14桁不動、np=1,2,4 ULP=0
   - -fcheck np=2、リスタート往復(save/restore 6成分化の確認)
2. **developer.md への gwflow/geomorph の項の追記**(検証完了後)
   - 切替器 vs 重ね合わせの使い分け原則、s%hg 柱状換算契約、S 台帳、
     モデル実装5箇条(m_gwflow_bucket ヘッダが正本)
3. developer.md の日付プレースホルダ(2026-xx)の実日付化(残があれば)
4. **診断集約の real64 固定化(hsum 系・par_sum_rows)の検証**
   - PREC=double で全ケース既存 reference とビット一致(逐次・np=1,2,4。
     real64=既定 real なので等価のはず)
   - PREC=single は Log のモニタ値(貯留高 S 等)のみ改善方向に変化しうる
     (single の reference は無いので同一バイナリのビット再現のみ確認)
5. **降雨遮断モジュール(m_intercept / 固定遮断率モデル)の検証**
   - fn_intercept 未指定で全ケース既存 reference とビット一致
     (機能追加の合否判定。makepre の updated 引数追加も無効時等価)
   - 疎通: wave 系 + f_icmodel=1, ic_alpha=0.3 で総降雨(S への入力)が
     ちょうど (1-α) 倍になること。np=1, 2, 4 で ULP=0
   - prtype=3 かつ dt_prupdate < dt_maplist の設定で二重減衰しないこと
     (updated ガードの検証。Pr 出力が分布更新のたびに一定率か目視)
   - developer.md への追記(gwflow/geomorph の項と併せて。上記2参照)
6. **初期化の方式2・第1段(係数の rank0 化+scatter)の検証**
   - **確保に触れる変更なので -fcheck=all の np>=2 を最適化ビルドより先に**
     (静的データを使う chichibu で。規律3)
   - 逐次で既存 reference とビット一致(scatter_band は逐次 no-op 経路)
   - np=1, 2, 4 が逐次 reference に ULP=0(chichibu: 実地形+粗度+河道)
   - user フックありのケース(wave 系の f_user_routine_id>0)で np=1,2,4
     ビット一致(フックの rank0 実行+マスク再 bcast 経路の検証)
   - f_rntype=2(lu2rn 変換)のケースがあれば併せて確認(read_rn の
     rank0 経路)

7. **座標管理(m_georef / ESRI hdr)導入コミットの検証**
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
8. **GeoTIFF Phase 1〜3 完了(読み書きとも実用範囲は完成)**
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

9. **境界条件 Phase 0/1(境界正規化・辺境界・ソース再編)の残検証**
   (実装・gfortran/OpenMPI 検証済み 2026-08-02。記録は boundary_plan.md
   §8/§9、設計正本は developer.md §15)
   - ifx での無効時ビット一致(逐次・np=1,2,4。inflow_dist で
     par_allreduce_sumr の collective が増えた点に注意)
   - 開辺ケースの恒常テスト化(放射境界ベンチマーク新設時に合流)
   - PREC=single ビルドの通し確認(inflow_dist の重み共有を含む)

10. **乾床薄膜先端の「質量微増」— 原因特定済み(2026-08-03)。対処は要議論**
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
- geomorph: calc_creep 実装(ガウス丘の解析解ベンチマークを先に作る)。
  浸食有効化時は par_halo_cell(s%z) をステップ頭へ(§11 の TODO 参照)
- gwflow: RRI 型・鉛直浸透重視型の追加(m_gwflow_bucket を複製して契約に従う)
- intercept: 貯留型モデル(初期損失・キャノピー貯留・Gash)の追加。
  固定率と違い貯留状態が毎ステップ発展するため、(1) makepre 直後の
  適用口に加えて毎ステップの更新口を切替器に追加、(2) 原雨量のモデル私有
  保管(適用が破壊的なため)、(3) 内部状態の save/restore
  (intercept_<モデル名>.dat。m_gwflow_bucket 契約5)が必要。
  遮断率・貯留容量の分布ファイル/土地利用からの構築(lu2rn 同型)は
  固定率モデルの init 拡張でも可(m_intercept_fixed ヘッダ契約5)
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

## 作業の流儀(新チャットでも同じ)

- 作業対象の**現行ファイルを都度アップロード**(AI 側のファイルは残らない)
- 等価リファクタ=逐次ビット一致、機能追加=無効時ビット一致、が合否判定
- 等価変換とバグ修正・挙動変更はコミットを分ける
- 確保範囲を変える変更は、最適化ビルドより先に -fcheck np>=2
- 過去の議論の詳細は「以前のチャットで◯◯をどう決めたか検索して」と
  頼めば AI が過去会話から掘り返せる
