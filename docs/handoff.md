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
     並列河道セル(角の2セル太り)・必須斜めリンクの検出警告の実装
     (§18 制約(6)、channel_model.md §5 の 4)
   - 決定(2026-08-07): 蛇行係数・冗長性判定付き斜め除去・fn_length_rw は
     モデル・データの複雑化回避のため**導入見送り**。代わりに適用条件
     (「実河道はラスタより滑らか」な解像度で使う。セル内蛇行河川は
     流量・流速過大)を宣言。議論の解析と設計台帳は
     **docs/channel_model.md** に独立文書として保存
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

1e. **排水ポンプ(&list_struct_pump。§15/§22)の残検証**(実装と gfortran/
    OpenMPI 検証は 2026-08-07 完了。無効時ビット一致、閾値未達=無ポンプ
    一致、一定流量= source±Q 一致、np=1,2,4 一致、厳密数学 serial=MPI
    一致、-fcheck np=2)
   - ため池取水(rscap>0 セルは s%hrs から汲む。§15)実装・gfortran
     検証済み 2026-08-07: 無効時ビット一致、ため池なしポンプが従来と
     ビット一致、池のみ vs 池+ポンプの S 差=移送量、η基準×ため池
     代表セルの par_stop、np=1,2,4 一致、厳密数学 serial=MPI 一致、
     -fcheck np=2。あわせて rsh→hrs 改名(等価リファクタ。f_out_hrs /
     Hrs0001。旧 f_out_rsh は namelist エラーで検出)
   - 内部水理構造物族への移設(2026-08-07。§22): 設定は fn_structure の
     &list_struct_pump へ(パラメータ名は同じ)、実装は submodule
     m_boundary_structure へ。等価移設のビット一致検証済み(§22)
   - 残: ifx / PREC=single、実ケース(前池+排水機場)での適用検証
   - カルバート(&list_struct_culvert。族の第二号)実装・gfortran 検証済み
     2026-08-07(§22)。残: 実カルバート(既知の流量観測がある樋管等)
     との定量比較、水路実験式(道路土工要綱等)との突合、
     流入部形状別の損失係数プリセット
   - 樋管・樋門(カルバートのゲート拡張: culv_flap / culv_gate_rule)
     実装・gfortran 検証済み 2026-08-08(§22)
   - 分水(&list_struct_diversion。η rating+受動性ガード)実装・
     gfortran 検証済み 2026-08-08(§22)。残: 実分水施設との定量比較
   - 第2弾候補: 起動/停止ヒステリシス(履歴状態+save 対応)、
     吐口の到達遅れ、時系列との併用(運転スケジュール・ゲートの時刻
     開閉)、内部状態を持つ種別(ダム貯留・ゲート開閉速度。save 対応と
     併せて)、円形断面カルバート、開度→面積の非線形

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
1f. **再開時刻の継続化(2026-08-08 実装。仕様は developer.md §7)の残検証**
   - gfortran 逐次で確認済み: フレッシュラン全8ケース reference と一致、
     wave t=4 分割の往復ビット一致(Log・E/H 出力)、tt<=t1 の par_stop
   - 残: MPI(np=2)での往復ビット一致、ifx での同確認
   - 既知の制限(save 対象外のため再開で連続しない。要否は今後判断):
     最大値統計 hmax 系・qcum(意図的仕様。§7)、m_intercept の内部状態
     (貯留型遮断の途中状態)、prtype=3 で再開時に読み直すフレームの
     遮断適用は中断なしランと1回分タイミングが異なりうる(遮断併用時のみ)

1g. **潮位境界 m_tide(2026-08-08 実装。仕様は developer.md §23)の残検証**
   - gfortran で確認済み: 無効時に全8ケース reference とビット一致、
     test/tide(排水→上げ潮浸水)の疎通と np=1,2,4 一致、-fcheck np=2、
     潮位有効時のリスタート往復ビット一致(更新位相の途中 t=121 で分割し
     Log・E/H 出力が中断なしランと一致)
   - test/tide の reference はコミット済みだが**新規ケースのため要目視確認**
     (排水で S: 0.55→0.42 → 上げ潮で S→1.25。妥当なら消し込み、
      修正が必要なら ./Run.sh -u で更新)
   - 残: titype=3/4(分布系)の疎通、ifx・PREC=single、実地形ケースでの
     hsea0 感度(浸水方向の流量が hsea0 に依存する度合いの定量化)
   - 関連する将来課題: 海への段落ち(f_rivermouth_drop)の境界条件への
     移管、集水域外縁排水の「海」代用をやめて領域内 x=0 境界の排水条件を
     境界条件族に追加する件(§23.1)

1h. **計測の実座標指定(§36。2026-08-14 実装)の残検証**
   - gfortran -Ofast で検証済み: 無効時 wave 回帰 PASS、プローブ・測線の
     ローカル/絶対(合成 bil+hdr)がセル番号指定と CSV 一致、斜め分割の
     加法性、1セル内測線の疎通、同一セル指定の par_abort、
     MPI np=1,2,4 バイト一致、-fcheck np=2 完走
   - 残: ifx / PREC=single での同確認。実データ(chichibu 等の hdr つき
     地形)での絶対座標の実地確認
   - 注意: セル境界ちょうどの座標はビルド間 ULP 差で帰属が変わりうる
     (§36.1 に記載。ガイドで「セル内部の座標を使う」ことを案内済み)
   - utils/rerecord の dcp 未初期化(計測全ゼロ)バグを整合確認で発見・
     修正済み(2026-08-14。§36 検証記録)。他の utils に m_record/dcp
     依存はないことを確認済み

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

1j. **土石流・地滑りモデル(f_debris/f_release/f_slide。2026-08-09 実装。
    developer.md §28、docs/debris_plan.md)の残作業**
   - **文献照合(2026-08-16 完了)**: 提供文献4本で主要な閉じ式は
     すべて確定・実装済み(debris_plan.md §1、developer.md §28.5-28.6):
     f_dbres=2/f_dbed=2(江頭系: 江頭1993・Morpho2DH manual)、
     f_dbres=3/f_dbed=3(高橋系: 高橋・中川1991 新砂防 44(3))。
     **残るのは f_dbed=1(簡易形)の慣用閾値のみ**(勾配3領域
     0.138/0.03・係数 6.7・上限 0.9C*・δe=0.0007 既定の出典 —
     未成熟土石流平衡濃度式の系譜。指針解説か高橋成書で確定可能。
     f_dbed=2/3 が文献照合済みのため優先度低)
   - **間隙水連行オプション f_dbwet(2026-08-16 実装済み)**:
     高橋・中川1991 式(5)の源泉 i{c*+(1−c*)s_b} の台帳
     (developer.md §28.7)。残るのは gwflow との両立(現状排他。
     不飽和侵食式(10)の飽和度結合と合わせて設計するのが自然)
   - **火山流動の等価流体モード(2026-08-16 実装済み)**: f_dbed=0 +
     f_dbres=4(Voellmy)/5(一定停止応力)+ test/volcano
     (developer.md §28.8、debris_plan.md §5)。残作業:
     (i) 火砕流の τ_y・μ の時間減衰則(ガス流動化の抜け。当面
     「有効化しない」と宣言済み)、(ii) 乾式流動の間隙流体密度
     抽象化(Phase 2 案b。クーロン項 sC/(1+sC) の s→∞ 極限の検証
     から)、(iii) 実事例(岩屑なだれの H/L、火砕流ランアウト)との
     突合、(iv) 融雪型泥流の連鎖(m_snow の SWE を火砕流の熱で
     融かす結合は抽象化未設計 — 当面は融雪水を境界・降雨入力で与える)
   - 高橋・中川1991 の未実装部(将来拡張): 不飽和床の侵食式(10)
     (gwflow の飽和度 hg/(sy0・sd) との結合が自然)、掃流状域の
     堆積式(28)(c_LS∞ の式が同論文にない)、粗粒・細粒の2成分化
   - 解析解・実験ベンチマーク: 斜面等流の平衡濃度、停止距離
     (高橋の実験式)、morfac なし版の検証階段(test/debris は疎通+
     保存則のみ)
   - ifx / nvfortran / AOCC でのビルド・検証(gfortran のみ実施済み)
   - S_grnd 表示が h=0 セルの hg を集計しない既存仕様の扱い
     (developer.md §28.4。直すなら m_state_calcstat の cycle 位置の
     変更 = 表示のみだが既存 Log との比較に影響 — 要議論)
   - Fs 分布の output_matrix 出力(f_out_fs)と record 計測の追加
   - f_wash と f_debris の併用(現状 wash は f_suspend 必須)、
     斜面崩壊の部分深さ化(現状は全層)、二相・二層モデルは将来
   - (解決 2026-08-16)マージ直後に観測した Run_MPI の過渡的な
     ビット不一致は -Ofast の fast-math ビルド間差と確定(§28.5。
     -O2 厳密数学 + make clean では両構成とも全一致)。debris/slide の
     Run_MPI.sh のビルド間比較は警告扱いに変更済み

## 既知の壊れている例題

- **examples/benchmark/h-plane の hp10x**: 実行中に FPE で停止する
  (-ffpe-trap 検知。f_rntype=2 廃止の等価変換(2026-08-15)以前からの
  既存問題。hp10 は正常)。原因未調査。
- examples/benchmark の mkdata/ ディレクトリに生成物(elev.txt,
  mask.txt)やビルド済みバイナリ(v-valley の tada)がコミットされて
  いる。掃除するか .gitignore の対象にするか要判断。

## 公開準備(方針の正本は developer.md §34)

- **GitHub Organization「ENCflow」作成・移管・URL 確定済み(2026-08-13)**。
  残: owner の複数化(両研究室の代表を追加)、リリース時の Zenodo DOI 付与。
- **README.en.md の作成**(公開の節目。機械翻訳+レビュー、
  「based on commit XXXX」刻印付き)。
- **実行時メッセージの英語化収斂**(触ったファイルから順に。
  Log 比較対象の文字列に触れる場合は reference への影響に注意)。
- 国際化の節目: docs/en/ ミラー+日英同期の CI チェック導入。
  コード内コメントの言語方針は海外コア開発者が現実になった時点で
  §34.2 を改定して決定(それまで日本語のまま)。
- 残ドキュメント: install.md は 2026-08-13、tutorial.md(目次)と
  wave チュートリアル本文 tutorials/wave/README.md(図の再生成は
  Fig_wave.sh)は 2026-08-14 作成済み。users_guide は構成方針を
  developer.md §35 に決定・記録し(precip/meteo 分離維持の決定を含む)、
  目次+第I部(docs/users_guide.md)と第II部5章(users_guide/ の
  time / coordinates / io / restart / parallel)を 2026-08-14 作成済み。
  第III部は地理情報(geoinfo.md)と降雨・気象(forcing.md)を
  2026-08-14 作成済み(コード照合: 格子の過剰指定検査、f_masktype=2 の
  生成規則、dt_mapunit の既定、evap/snow の par_stop 条件を確認済み)。
  初期条件(initial.md)・境界条件(boundary.md)・潮位(tide.md)も
  2026-08-14 作成済み(List_samples の注釈と §15/§23 を典拠に再構成)。
  構造物(structure.md)・河道(channel.md)も 2026-08-14 作成済み
  (List_samples の注釈が典拠。list_channel.txt の旧 &list_bound_pump
  参照の記述も修正)。
  浅水流(swflow.md)・地下水(gwflow.md)・計測(record.md)・
  水質(wq.md)・土砂地形(geomorph.md)も 2026-08-14 作成済みで
  **第III部の12章が完結**。付録の全パラメータ索引
  (params_index.md。370項目)も namelist 宣言からの機械抽出で
  2026-08-14 生成済み(生成スクリプトは使い捨て。§35.1。namelist
  変更時は再生成するか該当行を手修正)。残:
  付録の全パラメータ索引、List_samples の不足6件も 2026-08-14
  作成済み(sysparam は実行可能な最小例を兼ねる。initial / enc /
  record / geomorph は wave での読込動作を確認済み)。
  チュートリアル続編(実地形 chichibu)は 2026-08-14 作成済み
  (tutorials/chichibu/README.md。Step 1〜6 = 最小構成・GeoTIFF・
  計測・数値調整・遮断+バケツ・出口境界。図の再生成は
  Fig_chichibu.sh。流量振動の説明は §39.3 が典拠)。

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
  沈降)、morfac 等価性ベンチ(fluvial/suspend)、**区間流入の土砂濃度時系列
  (inflow_cs)実装・検証済み 2026-08-07**(§19.7。test/sedinflow で台帳
  閉合 2.6e-16)。**Qs(t) 直接指定(inflow_qs)も実装・検証済み 2026-08-07**(cs=Qs/Q の
  等価濃度還元。§19.7 追記)。残: 平衡濃度モード(plan §2.7 の 2 残)、
  侵食係数の校正指針、混合粒径(F4)、
  ifx / PREC=single での geomorph 一式の確認。
  基礎式の選択制は f_qbform / f_esform で対応済み(パラメータ共有+
  式固有係数のコード内固定で入力は複雑化しない。§19.8 に Nays2DH
  メニューとの対応を記録)。保留(文献確認待ち。新規パラメータゼロ):
  江頭式(係数は江頭ら 1997)、Lane-Kalinske(ppm 換算規約)、
  芦田・道上への有効掃流力 τ*e の導入(挙動変更)。
  設計正本は docs/geomorph_plan.md(改訂3)
- gwflow: RRI 型・鉛直浸透重視型の追加(m_gwflow_bucket を複製して契約に従う)
- intercept: 初期損失モデルと分布ファイル対応は実装済み(2026-08-06。
  貯留型の3点セット=step 口・原雨量私有保管・st の save/restore を含む。
  貯留型の実装契約は m_intercept_initloss ヘッダが正本)。残るは
  キャノピー貯留(蒸発回復あり)・Gash の追加(m_intercept_initloss を
  複製して契約に従う。遮断率の分布は §41 の原則どおり前処理で作成し
  ファイルで与える)
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

1h. **フラックス測線の DDA 階段面化(§24)の残項目**(実装・gfortran
    検証は 2026-08-08。斜め測線の角度安定性、縦横測線の旧方式一致、
    np=1,2 一致)
   - 一様流の解析解との突合(角度掃引 0〜90°)は簡易恒常テスト化が未着手
   - 実座標指定(flxytype=1)の廃止に伴う既存設定の移行確認
   - ダム流入計測への適用(貯留収支方式との併用・相互検証)

1i. **ダム(&list_struct_dam。族の第四号。§22)の残検証・第2弾**
   (実装・gfortran 検証は 2026-08-08。無効時ビット一致、モード別
    疎通、収支厳密性、リスタート往復、-fcheck np=2、np=1,2,4)
   - 残: 実ダム(公表の洪水調節図がある事例)との定量比較、
     ifx / PREC=single、√則(c)近似の自由水面遷移域の誤差評価
   - 第2弾候補: 予備放流・後期放流等の時系列運用(ゲート開閉速度)、
     捕捉帯直接降雨の同歩吸収、定量定率の複合運転、洪水期制限水位の
     運用(現状は初期水位のみ)

1j. **河道断面形の一般化 σ(h)=(h/D)^m(§26。2026-08-08 実装)の残項目**
   - gfortran 検証済み(実装コミット参照): 無効時ビット一致(全 reference)、
     ガード同値(bank のみ設定が実装前後で -O2 ビット一致)、変換の往復
     1ULP、σ 有効の疎通・リスタート往復、-fcheck np=2、np=1,2,4
   - 残: 台形/放物線断面の Manning 等流解析解との定量比較(恒常テスト化)、
     低水逓減の実河川検証、f_sect_rk=.false.(RK 矩形近似)とのコスト・
     精度差の実測、ifx / PREC=single
   - 第2弾候補: 幅 W と σ の合成の実河川検証、geomorph 河床変動との
     D 連動、浮遊砂濃度解釈(hs/vh)の geomorph 側整合

1k. **蒸発散(§27。2026-08-09 実装)の残項目**
   - gfortran 検証済み(実装コミット参照): 無効時ビット一致、一定速度の
     収支厳密性(wave)、式の Python 対照、統合(σ+遮断+日界+リスタート)、
     MPI np=1,2,4 / -fcheck np=2
   - 残: FAO Penman-Monteith 等の上位式(f_evmodel の追加枠)、
     分布気温×標高減率の併用(現状は排他)、土壌水分による蒸発抑制
     (現状は供給制限のみ)、evap.csv 累積の restore 継続、
     実河川の長期水収支検証(handoff 1j の低水逓減検証と併せて)
   - 気温分布ファイルの時間アンカーはシミュレーション時刻 t=0
     (date0_c の日界とはずれ得る。日単位運用なら実害なし)

1l. **水質(負荷流出)m_wq(§30。2026-08-09 実装)の残項目**
   - W2 実装済み範囲は §30 検証記録を参照
   - W3(次段): gwflow_lateral のセル間フラックス記録契約+飽和湧出の
     質量還元(cg→cq)+地下横輸送カーネル(cg の風上輸送)。
     ため池(rscap)吸収の質量同伴(吸収量の記録契約が必要)
   - 貯水池内混合(ダム放流濃度 M/V の完全混合池モデル)
   - 温度補正 k(T)=k20·θ^(T−20)(m_meteo の気温を水温プロキシに)
   - 粒子吸着系(Cs-137 等): Kd 分配で浮遊砂・E-D と結合(別ライン)
   - 2層 gwflow(風化基岩層)は f_gwlayer2 として実装済(2026-08-09。
     §16.2)。残: 層2の質量プール cg2(層1→2 浸透の濃度同伴+層2側方の
     cg2 輸送+湧出還元。逓減解析+トレーサ滞留時間でパラメータが分離
     同定できる)、d2/K2 の地質分布化(read_map_scatter 流用)、
     層2からの深部損失(系外)オプション
1m. **積雪・融雪 m_snow(§31。2026-08-10 実装)の残項目**
   - ddf の季節正弦変化(HBV 流)、エネルギー収支法(m_meteo に放射・
     風速の枠が前提)、昇華、rain-on-snow の雪内保持・再凍結
   - 雪面沈着プール(降雪時の湿性沈着を SWE 内質量に持ち、融雪で
     同伴放出 = イオンパルス。buildup-washoff の枠を流用)
   - 氷河: **実装済み(2026-08-16。m_glacier / §45 / glacier_plan.md。
     残項目は 1q)**

1n. **長期地形変動(§32。2026-08-10 実装)の残項目**
   - 分布隆起 fn_uplift(断層ブロック・出口セル固定の基準面制御。
     read_map_scatter 流用)、風化の bulking(岩→土の体積膨張係数)
   - humped 型土層生成関数(薄い土層で最大の変種。必要が出たら)
   - 周期強制の対象拡張(prtype=3 分布降雨・気温分布 map・境界流入 —
     装置を順に読む構造のため要設計。当面はリスタート連鎖=1周期1ランで運用)
   - 長期実行の実証ラン(代表年×morfac×リスタート連鎖で 1 kyr 規模の
     平衡地形・土層厚分布の定常性確認)
   - 氷河地形: **実装済み(2026-08-16。SIA 氷体流動+滑動+氷河侵食則+
     雪崩再配分 = m_glacier。§45 / glacier_plan.md。残項目は 1q)**

1o. **海岸堤防(仮想壁面の海岸応用。§17.1。2026-08-10 実装)**
   - 実装済: 陸側セル持ち天端(fn_seawall/seawall0)+海側マスク
     fn_seaside(∪ sw)方式(&list_geoinfo)。当初の海側 sw セル持ち・
     &list_tide 案は津波(境界入射・sw なし)で機能しないため実装後に
     置換した(§17.1 に経緯)
   - 残: 越流の実験式検証(本間公式の海岸適用妥当性・胸壁形状補正)、
     海岸堤防の破堤(river breach 相当の時間発展開口)、
     消波工・粗度による越流低減係数

   - L-Q 式(流量依存負荷): 表面蓄積プール+洗い出し(buildup-washoff。
     wq_bd_*/wq_wash_*/f_wq_settle)として実装済(2026-08-09。§30)。
     土地利用別原単位は fn_wq_map、降雨中濃度(湿性沈着)は
     wq_rain_conc/series で実装済(同日)。残: 樹冠遮断分の沈着の地表還元
     (樹冠洗い落とし)、洗い出しの実流域 L-Q 再現検証(b>1・ヒステリシス
     の定量)、雨滴項の SWMM c2≠1 相当(べき化)が要るかの実データ確認

1p. **ParaView 可視化 utils/out2vtk(§43。2026-08-16 実装)の残項目**
   - 地形アニメーション: 地形変化計算で Z 系列があるとき、水面の高さは
     各時刻の Z で計算済みだが terrain.vts は Z0000 固定。terrain の
     時系列(terrain.pvd)化は必要が出たら。
   - 実データでの目視確認: ParaView 本体での表示・ドレープ・動画書き出し
     は実 GUI で未確認(公式 VTK ライブラリでの読解確認まで)。実ケースで
     README の手順どおりに通るか一度目視したい。
   - 大規模格子での txt 寸法プローブ(1行連結読み)の速度は未計測。
     遅ければ bil/GeoTIFF 出力の利用を README で促す(現状でも可能)。

1q. **氷河 m_glacier(§45。2026-08-16 実装)の残項目**
   - 実装済み範囲と検証は developer.md §45・glacier_plan.md §7 を参照
     (G1 涵養・消耗 / G2 SIA 流動 / G3 滑動+侵食 / G4 雪崩再配分+
     気象拡張 tempofs・f_prec_lapse。test/glacier の Halfar+カールスモーク、
     無効時ビット一致、-fcheck np=2、np=1,2,4 確認済み)
   - 残: ifx / PREC=single での同確認、リスタート往復ビット一致の実証
     (glacier.dat は snow.dat と同型なので既存機構で閉じるはずだが実証する)
   - 残: カール形成の長期実証ラン(理想山体×代表年×morfac×リスタート
     連鎖で 10^4 年スケールの圏谷形成を定量確認 → 恒常テストケース化)
   - 将来拡張(glacier_plan.md §7): 氷底ティル・モレーン(侵食物の系外
     排出を土砂プロセスへの引き渡しに置換)、雪崩の保持容量モデル
     (Gruber 型)、有効圧依存滑動、GLOF、cold-based 閾値、分布 A
   - ユーザーガイド: 氷河章(users_guide/glacier.md 日英)・params_index
     (+24 項目)・forcing 章の気象拡張・README 日英を整備済み
     (2026-08-16)
