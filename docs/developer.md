# ENCflow 開発者向けメモ (developer.md)

コードから読み取れない「なぜ」を記録する。形式は「決定事項+理由+落とし穴」。
設計判断をしたら、記憶が新しいうちにここへ追記すること。

---

## 1. 実数精度の方針

- **倍精度はソースでなくコンパイルフラグで指定する**(ifx `-r8` / gfortran
  `-fdefault-real-8 -fdefault-double-8` / nvfortran `-Mr8` / flang `-r8`)。
  理由: リテラル定数の精度落ち(`x = 0.1` が単精度になる罠)をクラスごと根絶
  できる。kind 方式では `_wp` の付け忘れが残る。
- 代償: `.mod`/ABI 互換のため、src と utils/rerecord 等は**必ず同一の FFLAGS**
  でビルドする(make.inc に一元化済み)。
- gfortran は `-fdefault-real-8` 単独だと double precision が16バイトに昇格する。
  **`-fdefault-double-8` を必ず併用**すること。
- フラグなしビルドは黙って単精度の結果を出す。README に前提を明記し、
  実行時アサーション(`kind(1.0) /= real64` なら error stop)で防御する。

## 2. 単一ソース MPI 方式

- serial(OpenMP)版と MPI 版は**別コードにしない**。並列層を `m_parallel`
  モジュールに隔離し、`m_parallel_serial.f90` / `m_parallel_mpi.f90` の
  2実装を Makefile(`MODE=serial|mpi`)で差し替える。
- **両ファイルの公開手続きインターフェースは常に一致させる**(保守ルール)。
  MPI_WP のような MPI 版固有の公開は例外的に許す(通信コードは MPI 版にしか
  書かれないため)。
- 通信の実数データ型は `MPI_REAL` でも `MPI_DOUBLE_PRECISION` でもなく
  **必ず `MPI_WP`(= MPI_REAL8)を使う**。-r8 昇格と MPI ライブラリの解釈の
  不整合は、エラーにならず値が化ける最悪の壊れ方をする。
- OpenMP 併用のため `MPI_Init_thread(MPI_THREAD_FUNNELED)`。MPI 呼び出しは
  マスタースレッドのみが前提。
- 実行コンテキスト(nrank, nproc, is_root, 領域分割情報 dcp)は m_parallel が
  **protected 属性で公開**する(他モジュールは読めるが書けない)。
- 初期化は二段階: par_init(MPI_Init、main 冒頭、引数解析より前)→
  格子サイズ確定後に **par_decomp_init(nx, ny)**(m_geoinfo_init の直後、
  collective)。par_init 時点では nx/ny が未知のため分割は決められない。

## 3. ビルドシステム

- `.mode_$(MODE)_$(MPIID)` スタンプ: MODE 切替と MPI 実装切替(ラッパーの
  -show 出力のハッシュ)を検出し、混成オブジェクトを防ぐため全再ビルドする。
- `$(OBJS): ../make.inc` の依存により、**make.inc の編集は自動で全再ビルド**
  される(-flto の付け外し等も手動 clean 不要)。
- **残る手動 clean は「serial モードでのコンパイラ本体切替(ifx⇄gfortran 等)」
  のみ**。非ラッパーは -show を持たず MPIID が一定値になるため検出できない。
- Run スクリプトは実行前に `make -s print-stamp MODE=...` で期待スタンプ名を
  問い合わせ、**モードと MPI 実装がビルド時と一致しているかを検証する**
  (Check_mode.sh。ハッシュのロジックは Makefile 側に一元化)。
  「module を切り替えたのに再ビルドし忘れ」を実行前に堰き止める。
- ビルドと実行の実装一致は `ldd a.out` でも事後確認できる(不一致だと
  MPICH バイナリ + mpirun.openmpi = 全ランクがシングルトン化し
  「全プロセスがランク0」になる等の症状)。
- 静的ライブラリのアーカイバはコンパイラと LTO の有無で自動選択(make.inc):
  ifx(-ipo)→ oneAPI の llvm-ar / gfortran+-flto → **gcc-ar**(llvm-ar 不可)/
  flang 系+-flto → llvm-ar / それ以外 → ar。
  間違えると「アーカイブは作れるがシンボル索引が空 → リンクで未解決」という
  沈黙型の失敗になる。
- IPO/LTO 相当: ifx `-ipo`、gfortran `-flto=auto`、AOCC flang `-flto`。
  **nvfortran には相当機能がない**(-Mipa は HPC SDK 23.3 で無効化)。
  submodule 境界を跨ぐホットコール(adv_edge 等)のインライン化は nvfortran
  だけ効かない点に注意。
- `-g` は最適化ビルドにも常時付ける(性能への害なし。バックトレースと
  プロファイルに必須)。ただし **nvfortran は `-g` 単独で -O0 を暗黙適用する
  歴史があるため `-gopt` を使う**。

## 4. エラー処理・メッセージ出力

- 4分類のラッパー(m_parallel)を使う。生の print は使わない:
  - `par_info` : 進捗・情報。ランク0のみ、stdout。
  - `par_warn` : 局所警告。検出ランクがランク番号付き、stderr、停止しない。
  - `par_stop` : **決定的エラー**(設定不正など全ランクが同時に検出するもの)。
    **collective — 必ず全ランクが揃って呼ぶこと**。一部ランクだけが呼ぶと
    Barrier でデッドロックする。ランク0が表示し finalize を通して stop 1。
  - `par_abort`: 局所的な致命的エラー。検出ランクだけが呼んでよい。MPI_Abort。
- エラー・警告は stderr に出す(意図的)。`tee` で作る Screen.log や
  result/Log.txt(回帰テストの比較対象)にエラー文言を混ぜないため。
- namelist の read は `iostat=` `iomsg=` で捕捉し par_stop に渡す。
  ランタイム任せにすると全ランクがメッセージを出す。ファイル open も同様
  (m_fileio に集約済みのため、入口数箇所の iostat 化で全読み込みに効く)。
- 時間ループのエラー処理: **判定は全ランクで同一に行い、exit は全ランクが
  同時に実行する**。print だけ is_root。ランク0だけが exit すると他ランクが
  回り続け finalize で整合しなくなる。`error stop` は dispose/par_finalize を
  素通りするので使わない — ierror を返し、finalize 後に stop 1。
- 領域分割後の集約対象(判定・出力の直前に allreduce/gather が要るもの):
  **ierror(swflow の発散検出はランク局所値になる)、s%cnmax、
  s%hmean(二段総和の行部分和)、s%sp の各成分(表示区間内最大値)**。
  m_record の水収支 ss/ss0 も実装時は総和として同リストに入る。

## 5. is_root ガードの規約

- **出力専用ルーチンは入口で自衛する**(`if (.not. is_root) return`)。
  run_main 層に is_root を書かない。呼び出し側の is_root ブロックは
  「後から collective 呼び出しが紛れ込む」デッドロックの温床になる。
- ガード節が許されるのは**副作用(ファイル・画面出力)しか持たないルーチン
  だけ**。out 引数や関数値で結果を返すルーチンに付けると、ランク0以外で
  未定義値が返る時限爆弾になる。
- **collective(par_stop)を is_root ガードの内側で呼ばない**。ランク0だけが
  Barrier に入り、他ランクが永久待ちになる(m_record init で発見した違反 →
  par_abort に変更済み)。ガード内のエラー停止には par_abort を使う。
- init/dispose は対にする(init がランク0限定なら dispose も。未割付
  deallocate 防止)。

## 6. 文字列・メッセージの組み立て

- 固定長バッファへの**代入**は黙って切り詰める(write と違いエラーにならない)。
- 規約: 連結で組めるものは `character(:), allocatable`。数値入りは
  m_util の `itoa`/`rtoa` で連結(`call par_stop("... "//itoa(n))`)を優先。
  write が必要なら作業バッファは `character(len=1024)`(ケチらない)+ trim。
  itoa 方式は contained 手続きの msg シャドーイング警告(fortls)も根治する。
- 幅なし `i` 書式は ifx 拡張で規格外(gfortran はエラー)。`i0` を使う。
  並び出力 `write(msg,*)` は空白が処理系依存なので比較対象の出力に使わない。

## 7. 状態変数の時刻規約(m_swflow_enc)

- **無印 = 時刻 n(ステップ中は読み取り専用)、接尾辞 1 = 時刻 n+1 の
  書き込み先、ステップ末尾でコミット**(h/h1 が模範)。
- 例外: uv は自エッジの read-then-write のみで他エッジの旧値を参照しないため
  単一バッファで安全(この理由をコード側にもコメント)。
- mn は現状 in-place 更新 + RK 用旧値コピー mn0。安全性は「自エッジ
  read-before-write」「エッジ書き手一意」「フェーズ分離」の3性質に依存
  している(2026-xx 精査で逐次等価を確認済み)。MPI 分割前に mn1 方式へ
  リファクタリング予定(等価変換なので逐次ビット一致で検証できる)。
- リスタート(save_state/restore_state)の保存対象は **s%h, u, v と
  sx%uv, mn(エッジ状態)**。エッジ状態を含むため力学状態は厳密に復元される。
  最大値統計(hmax 系)・qcum・sp(表示区間統計)は対象外で、リスタート後
  ゼロから再集計される(意図的な仕様)。保存形式を変更する場合は既存
  save_state.dat との互換に注意。

## 8. OpenMP の決定性

- **RK の他エッジ参照は必ず mn0(前ステップ値)を読む**。更新中の mn を読むと
  スレッドタイミング依存のデータ競合になる(2026-xx に修正した実バグ)。
- scatter 型の書き込み(atomic/critical で隣接セルへ加算)は使わない。
  エッジは所有セルが一意に書く gather 型を維持する。
- 自動配列を部分初期化のまま参照しない(ulm/vlm の実バグ)。
  **`-finit-real=snan` は派生型成分には効かない**ので検出を過信しない。
- 総和リダクションはスレッドの終了順で結合順が変わり、同一条件でも最終ビット
  が揺れる(S 列の ULP=1)。決定化したい診断量は「行ごと部分和 → 逐次固定順
  結合」の二段総和にする(calcstat の hsum_j で実装済み)。max/min は順序
  不変なので reduction のままでよい。
- 現状の到達点: 同一バイナリならスレッド数・実行によらず S 以外はビット一致。
- ThreadSanitizer は libgomp 非対応のため OpenMP コードに偽陽性を量産する。
  本気の競合検査は LLVM 系(libomp/Archer)で。valgrind --track-origins は
  未初期化読みに有効(逐次・短縮ケースで)。

## 9. コンパイラ間の既知の差(仕様であってバグではない)

- fast-math(-Ofast / -fp-model fast / AOCC も同類)の下では、定数除算の逆数
  乗算化や FMA 縮約がコンパイラごとに異なり、**閾値判定(適応 RK トリガ)の
  境界すれすれで判定が反転**する。Runge 列(事象カウント)はその最鋭敏な
  検出器で、コンパイラ間比較では ULP=2 程度揺れる → SKIPCOLS=4 で除外。
  トリガの除算は maglim_inv の乗算に置換済み(完全解ではない)。
- 書式出力の「ちょうど半分」の丸め(6.25 → 6.2/6.3)は処理系定義。
  ログは書式の RN(round='nearest' 相当)で統一済み。
- 回帰テストの規準: **同一バイナリ=完全一致(ULP=0)、コンパイラ・マシン・
  ランク数跨ぎ= ULP=1**。ULP は印字の最終桁を単位とした許容誤差で、列ごとの
  書式から自動決定される(Compare_ref.sh)。

## 10. 回帰テスト運用

- reference は環境依存(ビット一致基準)なので gitignore。**make clean では
  消さない**(clean 後の初回実行が未検証の結果を黙って新基準にする事故を防ぐ)。
  更新は明示的に `./Run.sh -u`。作成・更新時に env/BUILDINFO.txt へ実行環境
  (ホスト・module・ldd・ビルドモード)を自動記録する。
- param.txt は正規化(コメント除去)して比較し、不一致なら SKIP(比較不能)。
- 基準を更新したら、その結果の妥当性をプロットで一度は目視確認する。
- benchmark 系(解析解あり)はいずれ環境非依存の解析解ベーステストに昇格させ、
  CI に載せる(CI のランナーではローカル reference は使えない)。

## 11. MPI 化の設計原則(分割実装の基準)

- **静的データ(m_geoinfo: 標高・土地利用・粗度・マスク・窓)は全ランクが
  全域を恒久保持する。分割するのは動的状態(s, sx)だけ。**
  → m_geoinfo は MPI 化後も無変更。境界・湧き出し・プローブの位置解決は
  手元の全域情報で完結する。
- 数千ランク級で open 集中が問題化した場合の逃げ道は m_fileio の内側だけの
  改修(rank 0 が読んで Bcast。意味論は不変)。読み込みの入口は m_fileio に
  集約されているのでこれが単一差し替え点。ただし装置番号を外に出す un 系
  API は Bcast 化と相性が悪いので**新規利用を増やさない**。
- 初期化(namelist 含む)は全ランクで冗長実行。検証も全ランクで行い、
  報告だけランク0(par_stop)。構造体の配布ルーチンは書かない
  (書かないコードが一番バグらない)。
- **場を変更する処理は所有ランクがローカルに適用**(湧き出し、潮位境界)。
  **場を読むだけの診断・出力は gather して rank 0 で**(ファイル出力、
  プローブ、フラックス測線)。この二分法が判定基準。
  m_tide(未実装)は実装時に前者に該当する。分布ファイルは m_fileio 経由に。
- user_geoinfo / user_initial フックは「全域添字で書く」契約(全ランク冗長
  実行と整合)。動的状態を担当範囲のみ確保する段階に進んだら、user_initial
  は「全域一時配列に書かせて担当分を切り出す」方式を第一候補とする
  (フック側の単純さを保つため)。
- 同期は明示的に取らない。ハロ交換のデータ依存が必要な同期を内在する。
  MPI_Barrier は時間計測とデバッグの区切りにのみ使う(par_barrier)。
- 検証の柱: 冗長計算段階で「ランク数によらず逐次版とビット一致」を確認して
  から分割に進む。分割後はランク数不変性(1,2,4,8ランクで同一 reference に
  PASS)を回帰テストで担保する。
- FPE トラップと MPI: UCX は初期化・通信中に良性の invalid 演算を行うため、
  inv トラップと共存できない。nvfortran+HPC-X では `-Ktrap=divz,ovf` に
  落とすか、単一ノードでは `MPIRUN_OPTS="--mca pml ob1 --mca btl self,sm"`
  で UCX を回避する。
- ハイブリッド実行のバインド: OpenMPI は既定でコアにバインドするため、
  OMP スレッドが1コアに積み重なる。`--bind-to none` または
  `--map-by l3cache:pe=$OMP_NUM_THREADS` を指定。ランク数>コア数は
  `--oversubscribe`(MPICH は不要)。

## 12. モジュール設計の規約

- 状態の実体はモジュール変数として保持し(命名は `xx_mod` 等で引数と区別)、
  **プライベートルーチンは引数で受け取る**。依存が署名から読め、OpenMP の
  shared/private 判断が局所化し、複数インスタンス化にも開いた構造になる。
  直接参照してよいのは不変の小定数(die/dje 等)のみ。
- 例外: **実行コンテキスト(is_root, nrank, nproc, dcp)は use 直接参照して
  よい**(protected により書き込みはコンパイル時に禁止される)。ただし
  **dcp の直接参照はフェーズの入口まで。計算カーネルには範囲(js, je 等)を
  引数で渡す**(カーネルを「任意の部分範囲で動く一般手続き」に保つ)。
- 公開ルーチンは実体の受け渡しのみ、変更はプライベート側 — 同一実体の
  二重可視(エイリアシング)による未定義動作を規律で回避する。
- **格子幾何(nx, ny, dx, dy)の正本は g(t_geoinfo)**。p(t_sysparam)側は
  移行期間中の導出値(g からの単純転記。特に dx/dy の導出計算は m_geoinfo に
  限定し、実数のビット同値を保つ)。参照は触るついでに g へ漸進置換中で、
  参照ゼロになったら p から削除する。t_sysparam には最終的に実行制御と
  数値スキーム設定だけが残る。
- 表示用統計 sp は t_state に統合済み(モジュール変数から昇格。2026-xx)。
  成分は型定義のデフォルト初期化でゼロ保証。
- 実験機構は3段で使い分ける: 小さな変種は**実行時フラグ**(param で A/B 比較
  可能、回帰テストに条件が記録される)/ アルゴリズム単位の差し替えは
  **submodule ペア**(m_parallel と同じ「同一インターフェース+Makefile 選択」
  イディオム。内部状態を submodule に隠蔽できる)/ 骨格レベルの実験は
  ブランチ(マージか破棄で決着するもの)または _dev 全複製(同一バイナリで
  実行時 A/B が必要な場合のみ)。
- submodule のモジュール変数は単一インスタンスのグローバル状態。将来ネスト
  格子等で多重化する場合は派生型に包む改修が要る。

## 13. Fortran の落とし穴(実際に踏んだもの)

- **宣言時初期化(`integer :: n = 0`)は暗黙 SAVE**。block 構文内でも同じ。
  再入時に前回値から始まる。宣言と代入は分ける。
- 派生型の成分は `-finit-*` の対象外。早期 return 経路の初期化漏れは
  型定義のデフォルト初期化(`integer :: nsrcc = 0`)で型レベルで防ぐ
  (b%nsrcc 未初期化の実バグ: 最適化レベル・MPI 実装でゴミが変わり
  ランダムに segfault)。
- `open(newunit=un, ...)` に対して `close(1)` のような固定番号 close をしない。
- `use, intrinsic :: iso_fortran_env` は **only 句必須**(only なしだと
  NUMERIC_STORAGE_SIZE が取り込まれ、-fdefault-real-8 と矛盾する警告が出る)。
  only は他モジュールでも推奨(m_fileio の裸 use を only 化済み)。
- 標準出力の flush は `flush(output_unit)`(iso_fortran_env)。`flush(6)` は
  慣習依存、`call flush(6)` は規格外。nvfortran はパイプ先で行バッファしない
  ため、ラッパー内の明示 flush が診断可能性を保証する(「ハングに見えて
  出力滞留」の再発防止)。
- シェルのヒアドキュメントは `<< 'EOF'`(引用符付き)。裸の EOF は `$1` や
  `$var` が作成時に展開されて消える。

## 14. 性能に関するメモ

- 9960X(4ch DDR5, 4×CCD): 浅水陽解法は帯域律速で 15–20 スレッドで飽和。
  SMT 域の微増はレイテンシ隠蔽。chichibu 100m は L3(128MB)にほぼ載る
  キャッシュ常駐ケースなので、コンパイラ差が大きく見える(帯域律速の
  大ケースでは縮む)。性能結論は問題サイズ2点で確認する。
- コンパイラ比較(chichibu 100m, OpenMP 48スレッド, 9960X, 2026-xx):
  AOCC 10–11s < nvfortran 12–13s < ifx 15s。ただし ISA 指定(-xHost /
  -march=native)を揃える前の計測であり、揃えた再計測と大ケースでの確認が
  結論の前提。AOCC は Zen 系で有力なため本気の開発環境に採用(-flto 込み)。
- Core Ultra 285 は異種コア(8P+16E)+2ch メモリ。等分割 MPI とは相性が
  悪く、性能測定には使わない(機能・可搬性検証用)。
- 9960X は既定 UMA なので first touch 問題はない(BIOS の NPS/L3-as-NUMA を
  有効にした場合と、スパコンの多 NUMA ノードでは効く)。ハイブリッドで
  「1ランク=1 NUMA/CCD」に束縛すれば first touch への依存自体が減る。
- 出力による rank 0 の遅延は、ハロ交換導入後は全体を律速しうる。対処は
  測ってから: (1)気にしない → (2)非同期 gather / I/O スレッド → (3)MPI-IO。
