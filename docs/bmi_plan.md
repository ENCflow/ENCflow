# bmi_plan.md — CSDMS BMI 対応の実現可能性検討メモ

対象: ENCflow を CSDMS Basic Model Interface (BMI) 2.0 に対応させる
ことの実現可能性・工事規模・推奨構成の見通し。
経緯: 2026-08-28 の検討として起草。同日中に段1(ライフサイクル化 =
developer.md §53)・段2(bmi/ アダプタ = §54)・bind(c)+Python
(§55)・set_value(§56 降水・§57 z/h)・段3(MPI 対応 = §58)まで
実装済み。実装済み事項の正本は developer.md の各 § で、本書は検討の
経緯と全体計画の記録。残る将来枠は段4のみ(§6)。

参考: BMI 2.0 仕様 <https://bmi.csdms.io/>、Fortran binding
<https://github.com/csdms/bmi-fortran>(MIT)。

---

## 1. BMI とは(要点のみ)

数値モデルに `initialize / update / update_until / get_value /
set_value / finalize` と時間・格子・変数の問い合わせ群からなる
**統一された操作口**を付ける薄い API 規格。計算アルゴリズムには
一切関与しない。BMI 化すると、Python(PyMT 等)からの制御、
他モデルとの結合、データ同化・パラメータ探索の外部駆動が
共通の方法でできるようになる。noninvasive が設計原則で、
BMI 化してもモデル本体は BMI に依存しない(standalone 実行は不変)。

## 2. 結論(総括)

**導入は十分可能。しかも ENCflow の現行構造は BMI 化に有利な部類**。
工事の中心は「計算物理コード」ではなく **m_main のライフサイクル化**
(初期化・1ステップ・終了処理の分離)であり、m_swflow 等の計算本体には
一行も触れずに済む見通し。

| 項目 | 評価 | 根拠 |
| --- | --- | --- |
| serial 版 BMI | 容易〜中 | main.f90 は `m_main_all()` 1行。時間ループの1回分が run_main 内で明確に閉じている |
| 状態量の公開 | 容易 | t_state に h,u,v,e,z,pre,hg,hs,swe,hi,hl… が集約済み |
| 格子情報の公開 | 容易 | g%nx/ny/dx/dy + t_georef(xul,yul,EPSG)で uniform_rectilinear を記述できる |
| MPI 版 get/set_value | 容易 | par_gather_to / par_scatter_cell が既存(BMI 用の集約を新設計する必要がない) |
| MPI 版 update | 相性良好 | 1ステップ内で halo・allreduce が完結し「全ランクが同一判定」規約が既にある(§5) |
| MPI 版 get_value_ptr | 非対応とする | 全域配列は単一メモリとして存在しない → BMI_FAILURE(仕様上許容) |
| 外部 coupler との MPI 共存 | 小改修 | par_init/par_finalize の所有権ガード(MPI_Initialized)を足す |
| 方針 §0 との整合 | 要・方針追記 | 方針10(外部ライブラリ不使用)との関係を先に整理する(§4) |

## 3. 現行構造の適合性(コード実査)

BMI 化で最も難しいとされるのは monolithic な時間積分コードの
initialize-run-finalize 分解だが、ENCflow では実質済んでいる。

1. **エントリが薄い**: `main.f90` は `call m_main_all()` のみ。
   `src/Makefile` は main.o 以外を既に `libencflow.a` に分離しており、
   「libencflow のもう一つの入口」として BMI を足せる。
2. **ライフサイクルが既に3分割の形**: `m_main_all` は
   par_init → 各 init → `run_main`(時間ループ)→ 各 dispose →
   par_finalize と一直線。`run_main` の `do it = s%it0+1, p%nt` の
   ループ本体1回分がそのまま BMI の `update()` に対応する。
3. **状態の集約**: 交換候補の物理量は t_state にほぼ集約されている。
   変数名マッピング(CSDMS Standard Names ↔ s%h 等)は BMI 層の
   select case で済み、内部変数名の変更は不要。
4. **時間軸が単純**: 絶対時刻1本(s%t = t0 + dt*it、§7)。
   get_current_time / get_start_time / get_end_time / get_time_step は
   p%t0, p%dt, p%nt から素直に出せる。
5. **並列の抽象化**: m_parallel が serial/MPI 同一インターフェース
   (§2)で、halo・reduce・gather/scatter が一箇所に集約されている。

## 4. 方針 §0 との整合(実装前に決着させる論点)

### 4.1 方針10(外部ライブラリ不使用)と bmi-fortran

CSDMS 公式の Fortran binding(bmif_2_0 抽象型、MIT)にリンクして
初めて「公式 BMI 準拠」になる。これは方針10 の「計算本体は外部
ライブラリ不使用」に触れ得るため、**黙って例外を作らず、次のどちらかを
方針の追記として先に合意する**(§0 の運用規律)。

- 案A: BMI アダプタを `bmi/` として**計算本体の外**に置き、optional
  ビルド(`make bmi`)とし、bmi-fortran は利用者が外部インストール
  (conda-forge か CMake ビルド)して `-I/-L` でリンクする。`make` で
  作る encflow / encflow_mpi / libencflow.a は従来どおり依存ゼロの
  まま。方針10 の精密化に「BMI 等の外部連携アダプタは test/ の検証
  スクリプト同様、計算本体の外であり本項の対象外」と明記する。
- 案B(推奨): 同じく `bmi/` の optional ビルドとした上で、bmif_2_0
  モジュール(仕様定義のみの単一 Fortran ソース。§4.3)を NOTICE
  表示の上で `bmi/vendor/` に同梱する。**追加ツールなし・make だけで
  自己完結**する。「外部由来コードの同梱」という初の例外になるため、
  方針10 への注記(仕様定義ファイルの同梱は可、実装コードは不可、等)
  を合わせて合意する。

いずれでも本体(src/)は BMI を知らない。当初は案Aを想定したが、
§4.3 の実態(仕様は依存ゼロの1ファイル)を確認した結果、ENCflow の
「絶対的ポータビリティ」には案Bの方が合うため、本メモは案Bを推す。

> **合意記録(2026-08-28)**: 案Bで合意。方針10 への注記(外部連携
> アダプタは計算本体の外・仕様定義ファイルの同梱は NOTICE 表示の上で
> 可・実装コードの同梱は不可)を developer.md §0 方針10 に追記した。

### 4.3 ビルド要件の実態(外部コード・追加ツールは何が要るか)

「BMI 対応 = CMake 等の重いツールチェーンが必要」ではない。実物を
確認した結果(2026-08-28、csdms/bmi-fortran master):

- **BMI 準拠に必要な外部コードは `bmi.f90` 1ファイルだけ**(約750行、
  MIT)。内容は抽象派生型 + deferred 手続き + 定数(BMI_SUCCESS 等)の
  **純仕様**で、実装コードも `use` 依存も一切ない。
  `gfortran -c bmi.f90` だけで `bmif_2_0.mod` が得られる。
- リポジトリの CMake / fpm は CSDMS の**配布用パッケージング**であって
  技術的必然ではない。案B(同梱)なら CMake・fpm・conda のいずれも
  不要で、既存の make 体系に .f90 を1つ足すのと同じ。仕様は BMI 2.0
  (2020〜)で凍結されており、同梱の追随負担は実質ない。
- 案Aの場合のみ、利用者側に conda-forge の `bmi-fortran` か CMake
  ビルドが必要になる(ENCflow 側の Makefile は make のままでよい)。

追加ツールの話が出るのは、その先の**Python から実際に使う段**:

- 公式ルート(babelizer → pymt component 化)は conda エコシステム
  前提で重い。babelizer は BMI 仕様の一部ではなく **CSDMS Workbench の
  パッケージ生成ツール**(bmi-fortran=仕様、bmi-tester=検証、
  babelizer=Python 化、pymt=結合枠組み、という道具立ての一つ)。
  bmif_2_0 準拠の Fortran 実装と設定ファイル(babel.toml)を入力に、
  **bind(c) 相互運用層(bmi_interoperability.f90)と Cython 層を定型
  生成する**(テンプレートに同名ファイルを確認。手書き不要)。生成物は
  ENCflow とは別リポジトリの Python パッケージ(pymt_encflow 相当。
  meson + Python packaging でビルド)であり、ENCflow リポジトリには
  何も持ち込まない(BMI 準拠の Fortran 層まで提供していれば babelize
  できる、が公式ルートの意味)。
- 軽量ルート: `bind(c)` の薄い C API を bmi/ に自前で書き、Python
  標準の ctypes から呼ぶ。追加ツール不要(共有ライブラリ化の
  -fPIC/-shared だけ)で、ENCflow の思想に合う。bind(c)/iso_c_binding
  は Fortran 2003 の言語標準機能でありツールではない。BMI 準拠の
  Fortran 層があれば C 層は機械的に書ける(babelizer が生成するものと
  同種の定型コードを自分で書く、という関係)。第1段の動作確認は
  こちらで十分。
  - **この bind(c) 層は ENCflow 側が書いて bmi/ に含めて提供する**
    (利用者に書かせない)。理由: (1) 実装側の内部知識(インスタンス
    管理・Fortran↔C の文字列規約・配列の所有権)に依存し、利用者が
    安全に書ける性質のコードではない、(2) 言語標準のみで書けるため
    依存ゼロの原則と衝突しない、(3) 一度書けば凍結仕様(BMI 2.0)と
    共に安定し保守負担が小さい、(4) これがないと軽量ルートは事実上
    存在しない(利用者側の残作業が ctypes 呼び出しだけになることに
    価値がある)。Python 側の最小 ctypes ラッパーは正式サポート物では
    なく**サンプル**として同梱する(test/ の検証スクリプトと同じ
    位置づけ = 方針10 の対象外)。babelizer ルートを選ぶ利用者には
    この層は不要(babelizer が自前の相互運用層を生成する)が、
    共存して害はない。
- ビルド上の注意: 共有ライブラリ(libencflow_bmi.so)を作るには
  -fPIC でのコンパイルが要り、既存 libencflow.a(非 PIC)とは
  オブジェクトを共有できない。`make bmi` は別フラグの再コンパイルに
  なるため、MODE/PREC のスタンプ機構(§1・§3)との整合(bmi 用の
  別ビルドディレクトリ等)を設計段階で決める。静的リンクの実行形式
  (bmi-tester 用 CLI 等)だけなら -fPIC も不要。

### 4.4 呼び出し側から見た利用形態(リンクの実態)

BMI 仕様はプロセス内 API の呼び出し規約(関数シグネチャの束)で
あって、**リンク形態を何も規定しない**。「BMI = 共有ライブラリ」
ではなく、形態は呼び出し側が何者かで決まる。

1. **Fortran → Fortran**: `bmi_encflow` 型を use して通常の静的リンク
   (libencflow.a + アダプタ .o)で完結する。.so も -fPIC も不要。
   CSDMS の bmi-example-fortran もこの形。**段1〜2(ライフサイクル化と
   Fortran 内での準拠確認)はこれで足りる**。
2. **別言語(実質 Python)→ Fortran**: Python は .mod を読めない
   ため、bind(c) で C 互換シンボルにした共有ライブラリを**実行時に
   ロード**する(正確にはリンクでなく dlopen)。ctypes/cffi で直接
   ロードする軽量ルートと、babelizer が C ラッパー+Python 拡張
   モジュールを生成する公式ルート(§4.3)のどちらも .so が前提で、
   -fPIC の注意(§4.3 末尾)はこの形態で初めて効く。
3. **リンクしない形態(参考)**: grpc4bmi(eWaterCycle。サード
   パーティ拡張)は、モデルを別プロセス(多くはコンテナ)で走らせ
   BMI 呼び出しを gRPC で中継する。呼び出し側は何もリンクしない。
   MPI 版への含意が大きい: 形態2では `mpiexec -n 8 python script.py`
   と Python ごと全ランクで走らせる必要があるのに対し、この形態なら
   `mpiexec` で立てたサーバプロセスに通常の Python から接続でき、
   **MPI 初期化の所有権問題(§6 段3〜4)が呼び出し側に波及しない**。
   段4(library モード)を検討する際の代替経路として記録しておく。

### 4.2 方針12(物理量は直接与える)と set_value

ENCflow の強制場(降水等)は fn_* ファイル駆動が正であり、外部からの
`set_value("precipitation", …)` は m_precip_makepre と**二重更新**に
なり得る。BMI 経由の強制供給を許すなら「その場の所有権」を設計で
決める必要がある(例: prtype に「外部供給」を追加し、BMI 駆動時のみ
makepre を素通しにする等)。これは工事全体で唯一、計算本体側の入力
経路に触れる可能性のある論点。**第1段では get_value(観測・結合の
読み出し)のみ対応し、set_value は後続段の設計課題とする**のが安全。

(整理 2026-08-28)逐次に限れば set_value の残課題は次の3つに
分解でき、設計判断の本丸は 1 のみ(2 は軽く、3 は問題なしを確認済み):

1. **所有権 = 生産者は変数ごとに一人**(設計判断)。
   - 強制場(pre): makepre・遮断・融雪の生産チェーンと競合するため、
     配列への即時書き込みでは次の makepre に上書きされ得る。設計案:
     set_value は**ステージングバッファへの格納**とし、次の update
     冒頭で makepre の代わりに適用する。許可条件は fn_precip 未指定
     (= 方針7 の fn_* 流儀: 外部供給はファイル強制の代替であり併用
     しない)。
   - 状態量(z, h): 所有権は分担ルールで単純に決まる — ENCflow 側の
     z 更新プロセス(geomorph 等)を有効化していなければ競合しない
     (§8.1 の Landlab 分担と同じ)。
2. **従属状態の整合**(所有権ではない付随処理。§7 論点9): z / h を
   set したら e = z + h の回復が必要(m_geomorph が z 更新後に行う
   契約と同じ)。逐次ではハロ交換が no-op のため実質これだけ。
   加えて h >= 0 等の入力検査。
3. **診断への波及**(確認済み・対処不要): m_state_calcstat は状態の
   集計のみで、外部注入で破綻する厳密な収支閉合台帳は持たない。
   S 列は注入分だけ動くが、それは正しい表示である。

受け入れ試験も自然に決まる: **同じ降雨を fn_precip で与えた場合と
set_value で与えた場合の結果一致**(強制の等価性テスト)。MPI 対応で
増えるのは scatter・ハロ交換・z の帯下限問題(§54)のみで、所有権の
設計は逐次と共通。

> **実装記録(2026-08-28)**: 上記 1(降水)を逐次で実装(正本は
> **developer.md §56**)。受け入れ試験 bmi/python/test_set_value.py で
> ファイル強制と set_value 強制の Log 全行一致を確認(誤用検査込み)。
> 続けて z・h の set も設計合意の上で実装(正本は **§57**。z = 生産者
> 一人ルール+海セル除外、h = DA 型置換。同値 set 不変性テストで
> wave・chichibu とも Log 全行一致)。機能無効時は逐次・MPI・BMI 経由
> ともビット一致 PASS。

## 5. 推奨構成

ENCflow 全体を **1つの BMI component** として公開する(rainfall /
SWE / gwflow… をコンポーネント分割しない)。単一格子・単一時間発展で
プロセス連鎖を解くという ENCflow の核心(§0 目的1)と、BMI の
「component の粒度は設計者が決める」原則は両立する。

```text
main.f90 ── encflow / encflow_mpi     bmi/bmi_encflow.f90 ── libencflow_bmi
     │      (従来どおり・依存ゼロ)           │ (optional。bmi-fortran 依存)
     └──────────────┬─────────────────────────┘
                    ▼
        m_main の公開ライフサイクル API
        (m_main_initialize / _update / _finalize / _get_… / 既存 m_main_all)
                    │
        private :: t_encflow(全 t_xxx を束ねる派生型。singleton)
                    │
        既存の各モジュール(m_state / m_swflow / … / m_parallel)— 無変更
```

- `t_encflow` は m_main の private 型とし、外部(BMI 含む)には公開
  手続きだけを見せる。t_state 等の内部構造も BMI 層に見せない。
- 従来の `m_main_all` は initialize → do while → finalize の合成に
  書き換える(main.f90 は不変)。CLI と BMI が同一の内部 API を共有。
- MPI では singleton が各ランクに1個ずつ存在し、`update()` を
  全ランク collective に呼ぶ規約とする。BMI に見せる格子は常に
  **論理全域格子**(nx×ny)。帯分割・ハロはランク内部の実装詳細。
- 同一プロセス内の複数インスタンスは当面非対応(必要になったら
  型を公開せず handle 方式に拡張できる)。

## 6. 段階的な工事計画と検証

> **実装記録(2026-08-28)**: 段1・段2 実装済み。正本は **developer.md
> §53(段1: ライフサイクル API)・§54(段2: bmi/ アダプタ)**。
> 段1 = t_encflow は m_main private の singleton、公開は
> m_main_initialize/update/finished/finalize。逐次 wave/chichibu
> ビット一致、MPI wave np=1,2,4・chichibu np=2,4 identical PASS。
> 段2 = bmi/(vendor/bmi.f90 同梱・bmi_encflow.f90・test_bmi.f90)+
> m_main アクセサ4つ。BMI 経由の完走で wave・chichibu(非正方形)の
> Log.txt が reference と identical。公開変数は h, z, pre の3出力。
> 段2.5(同日・§55)= bind(c) 層 + libencflow_bmi.so + Python ctypes
> ラッパー(bmi/python/encflow.py)+ ライブ表示サンプル(live_view.py。
> §8 の利用イメージが実際に動く)。§4.3 軽量ルート実装済み。
> 判明事項: 内部 j は北→南。当初は Landlab 連携で行反転が必要と
> 記したが、§7-5 案A(BMI 層で行順を標準形 = 要素0が南西に正規化。
> 同日実装)により**連結相手側の反転は不要**になった。
> **段3(同日・§58)実装済み** = MPI 対応: owns_mpi ガード
> (MPI_Initialized 検査。ライブラリモードでは finalize しない)、
> set_value の scatter 化(src は rank0 のみ有効・値検査は allreduce で
> 全ランク同一判定)、MPI 実行規約(全ランク collective・rank0 有効)。
> §54 の「z の帯下限問題」は誤解と判明(s%z は帯確保の通常配列。
> 全域保持は g%z)— 規律3 の -fcheck=all np=2 が検証で実効。
> 残る将来枠は段4(par_comm 抽象化・par_stop の return code 化・
> MPI 版 .so、複数インスタンス)のみ。

| 段 | 内容 | 規模感 | 検証 |
| --- | --- | --- | --- |
| 1 | m_main のライフサイクル化(t_encflow 導入、run_main のループ1回分を update に抽出、ループ前後の初期出力・最終出力を initialize 末尾 / finalize 先頭へ移設) | 中。m_main.f90 中心の等価リファクタ | **絶対規律2がそのまま使える**: 逐次ビット一致 + MPI np=1,2,4 ULP=0。既存 reference 不変 |
| 2 | serial BMI アダプタ(bmi/bmi_encflow.f90 + Makefile)。initialize/update/update_until/finalize/time/grid/get_value 中心 | 中。定型コードが大半(BMI は約40関数だが多くは数行。非対応は BMI_FAILURE 可) | 本体無変更 → 既存回帰は自明に不変。BMI 側は CSDMS bmi-tester。非正方形格子(nx≠ny)で flatten 順序を確認 |
| 3 | MPI BMI(get_value=par_gather_to、set_value=par_scatter_cell、get_value_ptr=BMI_FAILURE)+ par_init/par_finalize の MPI_Initialized / owns_mpi ガード | 小 | 同上 + mpi4py 共存の煙試験 |
| 4 | (将来枠)MPI_COMM_WORLD → par_comm 抽象化、par_stop のエラー伝播化(library モード)、set_value による強制供給、複数インスタンス | 未定 | 必要になってから設計 |

段1は BMI を使わなくても価値がある(Python 制御・単体試験・
アンサンブル・データ同化がやりやすくなる)。段2以降は本体に触れない。

## 7. 主要な設計論点(次の設計段階で決める)

1. **update() の切り出し境界**: run_main のループ前ブロック
   (makepre・初期出力・番号0スロット)とループ後ブロック
   (output_state 9998 / output_summary 9999 / record_summary)の
   置き場所。standalone 実行のビット一致を保つ移設位置の確定。
2. **エラー経路**: ierror は既に run_main → m_main_all へ return-code
   的に伝わるため update の BMI_FAILURE 化と相性が良い。一方
   par_stop は MPI_Finalize + stop 1 で**ホストプロセスごと落とす**。
   初期段では「initialize の入力不正は stop で許容」とし、library
   モード化は段4へ。
3. **update_until の時刻端数**: ENCflow は固定 dt。dt の整数倍のみ
   受け付ける(端数は BMI_FAILURE か直近ステップへの切り下げ)。
4. **ENC 配置(staggered)量の公開**: セル中心量(h,e,z,pre,hg,…)を
   grid 0 で公開。エッジ配置の u,v,m,n は当面非公開とするか、別
   grid id とするかを決める(第1段はセル量のみで十分)。
   → **多格子(2026-10-10)**: ネスト系(fn_nest)は grid id で格子を区別
   (grid 0 = ルート、k = 一覧の k+1 行目)、非ルート格子の変数は object 部に
   `~grid<k>`。developer.md §73。
5. **変数名マッピング表**: CSDMS Standard Names ↔ t_state 成分の
   対応表と単位(内部は SI が基本)。PREC=double|single は
   get_var_type / get_var_itemsize で実精度を報告する。
   - **y の向き(行順)の検討(2026-08-28)**: 反転が要るか否かは
     連結相手の行順規約次第(上から描く表示系なら不要、Landlab の
     左下原点なら必要)— は事実だが、BMI には「相手次第」で済ませない
     道がある: 格子は origin/spacing/shape で自己記述されるので、
     **配列の並びとメタデータが整合していれば相手は規約を推測しなくて
     よい**。現在の実装は origin に左下隅(y_ll)を返しつつ配列は
     北始まり(内部 j=1 = 北)で、consumer が origin + index×spacing で
     座標復元すると南北が逆になる(厳密には不整合)。選択肢:
     - 案A(推奨): BMI 層の get_value / set_value で行反転し、
       「index 0 = 南西隅・dy 正・origin = 左下」の標準形に正規化する。
       内部は不変、コピー時の flip のみ(コスト僅少)。Landlab とも
       無反転で一致し、pymt 等の自動処理でも南北が正しく出る。
     - 案B: 北始まりのまま origin を北西にし dy を負で返す(非標準。
       多くの consumer が想定しない)。
     - 案C: 現状のまま注記運用(ad-hoc 連携では動くが自動処理で
       南北逆のリスクを相手に残す)。
     - **決定(2026-08-28)**: 案Aを採用し実装済み。流向の扱いも同じ
       原則で解決(2026-08-29・§60): 角度を生で出さず、流速成分に
       合成して y 成分を標準形へ符号変換する。get のコピー時に
       行反転(将来の set も同様)。検証: chichibu の DEM 入力
       (1行目=北)と BMI 取得 z の照合で「要素0行=南」を確認、
       wave/chichibu の Log は reference と identical のまま。
6. **save/restore との関係**: initialize が restore を内包する現行
   仕様のままでよいか(BMI の initialize(config) に自然に載る見込み)。
7. **再 initialize**: finalize 後の再 initialize(同一プロセス内)を
   許すなら、t_encflow 成分のデフォルト初期化(§13)への依存を確認。
8. **MPI 時の get_value の返り値の意味論**: 全域配列は rank0 のみ
   有効とするか(gather 先が rank0 のため自然)、全ランクへ bcast
   するか。呼び出しは全ランク collective とし、有効値の所在だけを
   規約化する(§8 の利用イメージ参照)。
9. **set_value 後の整合処理**: 変数によっては配列コピーで済まない
   (例: z の更新は e 回復・ハロ交換を伴う。m_geomorph が z 更新後に
   済ませている契約と同じ処理を set_value 側も負う)。変数ごとに
   「set 可否と付随処理」をマッピング表(論点5)に含める。
   → **解決(2026-08-28)**: z・h の set を実装(developer.md §57)。
   z は z 更新プロセス無効時のみ受理・海セル除外で tide と共存、
   h は DA 型の状態置換として常時受理・運動量非更新。適用は update
   冒頭で e = z + h 一括回復+ z ハロ交換(geomorph と同一契約)。
   同値 set の不変性テストで wave・chichibu(河道セル含む)とも
   Log 全行一致を確認。

## 8. 利用イメージ(Python サンプル。設計スケッチ)

BMI 化後に利用者側がどう書けるかのイメージ(**未実装につきこのままでは
動かない**。`ENCflow` クラスは bmi/python/encflow.py に置く予定の
ctypes 最小ラッパー、変数名は仮)。実験条件(tt, dt)を Python 側で
定義し、水深分布とハイドログラフを matplotlib で描く例:

```python
import numpy as np
import matplotlib.pyplot as plt
from encflow import ENCflow          # bmi/python/encflow.py(ctypes ラッパー)

# ---- 1. 実験条件は Python 側で定義する ----
dt      = 0.05        # 数値時間刻み (s)
tt      = 8.0         # 計算終了時刻 (s)
dt_plot = 0.1         # Python 側の取得・描画間隔 (s)
ip, jp  = 50, 2       # ハイドログラフを取るセル(1始まり。Fortran と同じ)

# 数値条件はパラメータファイルが正(方針12)なので、Python からは
# namelist を生成してから initialize に渡す(set_value で dt は変えない)
base = open("param_base.txt").read()          # dt = <DT>, tt = <TT> の雛形
open("param_run.txt", "w").write(
    base.replace("<DT>", str(dt)).replace("<TT>", str(tt)))

# ---- 2. BMI で初期化し、格子情報はモデルに問い合わせる ----
model  = ENCflow("param_run.txt")             # initialize
nx, ny = model.grid_shape("surface_water__depth")
dx, dy = model.grid_spacing("surface_water__depth")

# ---- 3. Python が時間を進め、都度 状態を取得する ----
times, hp = [], []
while model.time() < tt:
    model.update_until(min(model.time() + dt_plot, tt))
    h = model.get("surface_water__depth").reshape(ny, nx)   # 1D→2D(行=j)
    times.append(model.time())
    hp.append(h[jp - 1, ip - 1])
model.finalize()

# ---- 4. matplotlib で描画 ----
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
im = ax1.imshow(np.where(h > 1e-3, h, np.nan), origin="lower",
                extent=(0, nx * dx, 0, ny * dy))
fig.colorbar(im, ax=ax1, label="h (m)")
ax1.set_title(f"water depth at t = {times[-1]:.1f} s")
ax2.plot(times, hp)
ax2.set_xlabel("t (s)"); ax2.set_ylabel("h (m)")
ax2.set_title(f"hydrograph at cell ({ip}, {jp})")
fig.savefig("result.png", dpi=150)
```

このサンプルが示す設計上の分担(重要):

- **進行制御は Python が握る**: どこまで進めるか(update_until)・
  どの間隔で状態を取るか(dt_plot)は完全に Python 側の自由。既存の
  dt_file / dt_recrd の出力も並行して生きる(BMI は加算的な操作口)。
- **数値条件(dt, tt)はパラメータファイルが正のまま**: BMI には
  dt を設定する標準口がない(get_time_step は照会のみ)ため、Python で
  決めた dt・tt は namelist 生成(テンプレート置換)で渡す。方針12
  (入力はファイル駆動)と衝突しない自然な形。
- **tt は上限として効く**: 現行設計では nt = tt/dt が確保・出力番号に
  効くため、BMI 化後も「nt を超える update は BMI_FAILURE」とするのが
  自然(§7-3 の端数問題と合わせて設計段階で確定)。
- **ハイドログラフを流量にする場合**は qq(線流量)等を同様に取得
  (変数名マッピングは §7-5)。既存の m_record プローブ CSV を使う
  選択肢も残る。
- **MPI 版で同じスクリプトを使う場合**は `mpiexec -n N python …` と
  なり、get_value の全域配列は rank0 のみ有効という規約になる見込み
  (描画・保存は rank0 で行う)。非 rank0 での get_value の返り値の
  意味論は §7 の設計論点に追加する。

### 8.0 交換間隔の指針(時間分割誤差と性能。2026-08-28 追記)

get/set によるコピー方式の結合コストは、モデル固有ではなく
**BMI 型連携一般に内在する性質**である(GLOFRIM も pymt も同じ)。
指針は「注記+適切な交換間隔」で足りる:

1. **間隔を決める第一の基準は物理**。結合間隔は交換する量の時間
   スケールで選ぶ(降雨強制なら分オーダー、地形進化との交換なら
   時間〜日)。数値 dt より細かい交換は物理的な意味を持たない。
   結合間隔は operator splitting の分割幅そのものであり、粗すぎれば
   時間分割誤差(§47 で記録した加算方式の dt 比例誤差と同種)、
   細かすぎれば無駄になる。
2. **これは ENCflow 内部の設計判断の外部版**である。dt_prupdate・
   dt_tiupdate・dt_gwflow 等の「プロセス更新間隔」は、まさに同じ
   トレードオフをモデル内部で解いている。外部結合でも同じ流儀で
   間隔を宣言的に決めればよい。
3. **性能の実態**: 交換1回のコストは場のコピー O(nx·ny)(set は
   ステージング+適用、get は集約+コピー。MPI ではさらに gather/
   scatter 通信)。1回あたりは数値解法1ステップより桁で安いが、
   Python ループで毎ステップ交換すると呼び出し・変換のオーバー
   ヘッドが積もる(chichibu 560×300 で1ステップ約 10 ms に対し
   交換は 1 ms 弱のオーダー)。物理基準で間隔を選べば自然に無視
   できる水準に収まる。
4. コピーが本当に効く場面のための BMI の逃げ道が get_value_ptr
   (参照渡し)だが、ENCflow は安全性と MPI 整合のため非対応の方針
   (§2・§7)。必要性が実測で示されたら逐次限定で再検討する。

### 8.1 Landlab との連携

BMI 化の具体的な効用の代表例。**可能で、しかも相性が良い**。ただし
BMI は通信規約であって自動結合ではなく、仲介するのは利用者の Python
スクリプト(または pymt)である。接続形態は3つ:

1. **素の Python ループ**(軽量ルートで成立): Landlab は Python
   ネイティブ(grid.at_node + run_one_step)でそのまま回せるため、
   **BMI が要るのは ENCflow 側だけ**。numpy 配列の受け渡しで繋がる。
2. **pymt 経由**(babelize 後): 時間同期・単位変換・格子マッピングの
   支援を得る公式ルート。
3. **BMI 同士に揃える**: Landlab component を `landlab.bmi.wrap_as_bmi`
   で BMI 化し、両者を同じ流儀で駆動する(枠組み統一が目的の場合)。

技術的な相性(確認済み):

- **配列の並びが一致する見込み**: Landlab の RasterModelGrid はノードを
  「左下起点・x 方向が最速」の 1D 配列で持つ。ENCflow h(nx,ny) の
  column-major flatten も x 最速で、reshape なしに 1:1 対応する
  (y の向きは §7-5 案Aの正規化で解決済み: BMI 層が「要素0=南西」の
  標準形で受け渡すため、Landlab 側の反転は不要)。
- **名前規約が同族**: Landlab のフィールド名(surface_water__depth,
  topographic__elevation 等)は CSDMS 流の二重アンダースコア規約
  そのもので、マッピング表が素直に書ける。
- **時間刻みの分担が自然**: ENCflow の小さい dt(水理)と Landlab の
  大きい dt(侵食・地形進化)は update_until による operator splitting
  でそのまま繋がる。

スケッチ(ENCflow の氾濫水理 × Landlab の斜面拡散。設計イメージ):

```python
from encflow import ENCflow
from landlab import RasterModelGrid
from landlab.components import LinearDiffuser

enc = ENCflow("param_run.txt")
nx, ny = enc.grid_shape("surface_water__depth")
dx, _  = enc.grid_spacing("surface_water__depth")

grid = RasterModelGrid((ny, nx), xy_spacing=dx)
z = grid.add_field("topographic__elevation",
                   enc.get("land_surface__elevation"), at="node")
diffuser = LinearDiffuser(grid, linear_diffusivity=0.01)

dt_couple = 3600.0
while enc.time() < tt:
    enc.update_until(enc.time() + dt_couple)   # 氾濫水理を進める
    grid.at_node["surface_water__depth"][:] = enc.get("surface_water__depth")
    diffuser.run_one_step(dt_couple)           # Landlab 側で地形を進める
    enc.set("land_surface__elevation", z)      # 更新地形を戻す(双方向)
```

注意点(設計論点への反映):

- **一方向(get のみ)なら第2段の範囲で可能**。双方向(z を戻す等)は
  set_value が必要で、§4.2 で後続段に回した課題そのもの。Landlab 連携は
  set_value を実装する具体的動機になる。
- **set_value は配列コピーでは済まない場合がある**: z の更新は e 回復・
  ハロ交換等の整合処理を伴う(m_geomorph が z 更新後に済ませている
  契約と同じ)。§7 に論点として追加(論点9)。
- **プロセスの所有権を決める**: ENCflow の geomorph と Landlab の侵食を
  同時に有効にすると二重計上になる。「Landlab に任せる場は ENCflow 側で
  有効化しない」(fn_* を作らない = 方針7 の流儀)が自然な分担。
- **同一格子が前提**。異格子は pymt の regridding か前処理で吸収。
- Landlab は serial Python のため、まずは **serial ENCflow との組合せ**が
  素直(MPI 版は rank0 規約で可能だが初期段の対象外)。

## 9. 連携候補の見取り図(エコシステム)

BMI 対応モデルのカタログは CSDMS model repository・pymt components・
周辺枠組み(NextGen, eWaterCycle, GLOFRIM, OpenDA)に集まっており、
重心は水文・地表過程 = ENCflow の領域と重なる。2026-08 時点の主な顔ぶれ:

**ENCflow 側から使いたくなる相手**(上流強制・境界・検証相手):

- 降雨流出・陸面(流量境界の供給元): NOAA **NextGen** のモジュール群
  (CFE, Noah-OWP, LSTM 等。NextGen は BMI 2.0 をモジュール規格に採用)、
  TopoFlow、PRMS、wflow、PCR-GLOBWB、HBV 系(eWaterCycle 経由)。
- 地下水: **MODFLOW 6**(公式に BMI/XMI を公開: libmf6 + xmipy)。
  ENCflow の簡便2層地下水の検証相手、または精緻側への置換相手。
- 流域からの水・土砂供給: HydroTrend(pymt)。
- 海岸・沿岸: XBeach、Delft3D FM(BMI あり)。高潮・波を潮位/境界
  水位強制として受ける。
- 雪氷・凍土: ECSimpleSnow、GIPL、Ku(permamodel。pymt)。
- 地形進化: Landlab(§8.1)、CHILD、Sedflux(pymt)。

**ENCflow と連携したくなりそうな側**(ENCflow が供給側に立つ文脈):

- **GLOFRIM** 型の「大域水文 → 局所氾濫」チェーン(openearth/glofrim。
  PCR-GLOBWB / wflow / CaMa-Flood と氾濫モデルを BMI で格子間結合)。
  現在その「局所氾濫エンジン」の座は LISFLOOD-FP / Delft3D FM で、
  ENCflow は同じ座に入れる上、氾濫+土砂+流木+地下水を1格子で持つ
  点が既存の座にない供給物になる。
- Landlab / pymt コミュニティ: Landlab 自前の OverlandFlow は
  de Almeida 近似であり、フル SWE+多プロセスの水理エンジンには
  需要がある(§8.1 の逆方向)。
- **eWaterCycle**: BMI 水文モデルの収集地(grpc4bmi+コンテナ。
  §4.4 形態3と適合)。
- **OpenDA** 等のデータ同化枠組み: BMI 対応モデルをそのまま同化対象に
  できる。
- NextGen: BMI 2.0 準拠モジュールとして原理的には参入可能
  (制度・運用面のハードルは別問題)。

**非対称性の見立て**: ENCflow が「受ける」ものの多くは時系列境界
(流量・水位)で、実はファイル渡し(既存の fn_boundary 体系)でも
済む。一方 ENCflow が「渡す」ものは 2D 場(水深・流速・地形変化)で、
こちらは BMI の価値が大きい。**ENCflow は BMI の供給側として特に
価値が出る**——これは §4.2 で「第1段は get_value まで」とした判断とも
整合する。

## 10. 位置づけへの影響

対応した場合、docs/comparison.md の「提供形態」に BMI(PyMT /
NextGen 系エコシステムとの相互運用)を追記する節目になる。
「専門の隣の現象をまず試す」(§0 目的3)導線として、Python から
`initialize → update → get_value` で回せることは導入障壁の低減にも
合致する。

### 10.1 認知経路(BMI 対応を各コミュニティに知らせる場所・方法)

労力の小さい順に。上の3つは対応完了とほぼ同時にできる:

1. **bmi-tester 合格の明示**: CSDMS 公式の適合性テスト(csdms/
   bmi-tester)に通し、合格を README・docs に記載する。準拠の客観的
   証明であり、以降のすべての経路の前提になる。
   → **達成(2026-08-28)**: 47 passed / 0 failed(developer.md §59。
   再現は bmi/python/check_bmi.sh)。bmi/README.md に記載済み。
2. **CSDMS Model Repository への登録**: CSDMS のモデル台帳
   (csdms.colorado.edu。数百モデル規模)にフォームで登録すると、
   メタデータ付きのモデルページができ DOI も付与される。エコシステム
   全体からの発見可能性はまずここで決まる。無料。既存の CITATION.cff・
   LICENSE がそのまま登録要件に使える。
3. **README/リポジトリ側の表示**: BMI 対応の節を README に設け、
   GitHub topics(basic-model-interface, csdms 等)を付ける。
   CSDMS の help-desk(GitHub)で対応を知らせるのも一手。
4. **連携実例の notebook を作って個別コミュニティへ**: 認知は登録より
   実例が効く。§8.1 の Landlab 連携 notebook を tutorials/ に置き
   Landlab コミュニティ(GitHub Discussions)へ、GLOFRIM には
   「ENCflow を局所氾濫エンジンとして追加できる」ことを issue で提案、
   eWaterCycle にはコンテナ+grpc4bmi のプラグイン追加を打診(§4.4
   形態3)。
5. **pymt 公式 component 化**: babelize して conda-forge に
   pymt_encflow を置くと、pymt のモデル一覧に載り「インストールして
   すぐ使える形」で露出する(§4.3 のとおり重いので、需要を見てから)。
6. **学術経路**: JOSS(研究ソフトウェア短報)か GMD(モデル記述論文)
   で BMI 対応を明記して引用可能にする。CSDMS Annual Meeting
   (毎年5月、Boulder)のクリニック・ポスターはエコシステム中心人物に
   直接届く場。AGU/EGU の model coupling セッションも同様。

## 11. 公開変数の拡張: 機能依存変数の get / set(2026-10-11 起案・同日合意・実装)

§60 で「機能有効時のみ確保される変数(hg・swe 等)は動的変数リストの
設計を決めてから」と保留し、§73 で拡張点(base_* と var_internal、
有効判定は m_main への問い合わせ口)を指摘した件の設計案。**§11.8 の
要合意事項は 2026-10-11 に全項合意し、§11.6 の段 0〜2 を同日実装した。
決定事項と検証記録の正本は developer.md §76**(本節は設計の経緯として保持)。

### 11.1 現状と課題

- 公開は出力 8・入力 3(§54・§60)で、いずれも m_state_init が無条件に
  確保するセル量。機能(fn_*)に依存する状態量は一つも公開していない。
- 名前の正本が散在している: `base_out / base_in`(表)、`var_internal`
  (Standard Name → 内部名)、`get_var_units`(単位)、`m_main_get_value /
  set_value` の `select case`(内部名の実装)、Python 定数 `VAR_*`、
  bmi/README.md・README.en.md の表。1 変数の追加で 6 箇所を触る。
- set は変数ごとに意味論・受理条件・適用処理が異なる(§56・§57)。
  追加のたびに個別設計になるので、区分を先に決めておく。

### 11.2 候補変数の棚卸し

t_state の成分(m_state.f90)と m_output の出力条件から。「存在」は
§11.3 の判定基準(= その量を生産するプロセスが有効)。Standard Name は
CSDMS の既存名を優先し、無いものは文法(object~adjective__quantity)内で
造語する(bmi-tester の名前検査は文法のみ。§73)。**名前は全て案**。

| 内部名 | 内容 | 単位 | 確保 | 存在判定 | get | set 区分(§11.5) | Standard Name(案) |
|---|---|---|---|---|---|---|---|
| hg | 地下貯留(層1。柱状換算) | m | 常時 | gw%enabled | 第1弾 | S(bucket のみ受理) | soil_water__leq-depth |
| swe | 積雪水量 | m | fn_snow | allocated | 第1弾 | S | snowpack__liquid-equivalent_depth(既存) |
| sd | 土層厚 | m | fn_geomorph/fn_gwflow | allocated | 第1弾 | 不可(z−sd=岩盤面を動かす) | soil__thickness(既存) |
| hs | 浮遊砂柱状量 | m | 常時 | s%sed_active | 第1弾 | 不可(第2弾で検討) | surface_water_sediment~suspended__volume-per-area |
| cqc | 輸送物質濃度 | mg L-1 | fn_wq | s%wq_active | 第1弾 | 不可(導出量。cq は第2弾) | surface_water_solute__mass_concentration |
| hi | 氷厚 | m | fn_glacier | allocated | 第1弾 | 不可(z と共動) | glacier_ice__thickness(既存) |
| hl | 溶岩厚 | m | fn_lavaflow | allocated | 第1弾 | 不可(z と共動) | lava__thickness |
| hmax / vvmax / qqmax | 期間最大 | m, m s-1, m2 s-1 | 常時 | 常に存在 | 第1弾(低優先) | 不可(統計) | surface_water__time_max_of_depth 等 |
| hg2 / hgc | 層2・管路層の貯留 | m | f_gwlayer2 / f_gwconduit | allocated | 第2弾 | 不可 | bedrock~weathered_water__leq-depth 等 |
| hss / hgs | 地表・地下の塩水層厚 | m | fn_salt | allocated | 第2弾 | 不可 | — |
| swi | 土壌雨量指数 | mm | fn_swi | allocated | 第2弾 | 不可 | — |
| hd / wd, hbd / wbd | 流動・堆積の流木・瓦礫 | m | fn_driftwood / fn_bldgdebris | allocated | 第2弾 | 不可 | driftwood~floating__volume-per-area 等 |
| hb / vb, fs, frofac, bp | 動く底層・安全率・凍土係数・表面プール | — | 各フラグ | allocated | 需要待ち | 不可 | — |
| u, v, m, n | エッジ配置の流速・線流量 | — | 常時 | — | **非公開のまま**(§54) | — | — |
| prh, af, gv, lm, qdir, ddir* | 換算値・入力係数の写し・角度・整数フラグ | — | 常時 | — | 非公開(prh は pre の換算、qdir は §60 の方針で成分に合成済み) | — | — |
| rn | 粗度係数(g%rn。物性係数) | m-1/3 s | 常時 | 常に存在 | 実装済み(§77) | P(ENC 格子系のみ受理) | land_surface_water_flow__manning_n_parameter |

入力候補(強制。F 区分)の将来枝: 気温(m_meteo。tsrc に「外部」を
新設して受理)、ネスト境界の η_e・u_e(nesting_plan.md §15.6 の族)。
いずれも需要待ち(第3弾)。

### 11.3 論点1: 機能無効時の扱い(get)

| 案 | 内容 | 評価 |
|---|---|---|
| (a) **動的変数表** | 無効な機能の変数は input/output の表に載せない。表にない名前の get/set/get_var_* は未知名と同じ BMI_FAILURE | m_output の「allocated なら書く」と同じ基準。BMI の変数表の意味(この component が実際に交換する量)に一致。bmi-tester は表にある名前だけを検査するので、載せた変数は必ず get できる状態になる。無効時のコストはゼロ(表に無いだけ)。**推奨** |
| (b) 常時掲載・無効時はゼロ場 | 表は固定。無効なら 0 を返す | 「雪がない」と「雪モデルが無い」を consumer が区別できず、pymt 等の自動結合がゼロ場に黙って結合する。存在しない量を見せることになり、方針8 の精神に反する。却下 |
| (c) 常時掲載・無効時は get が FAILURE | 表は固定 | output_var_names にあるのに get できないのは BMI の契約違反(bmi-tester の get_output_values が落ちる)。却下 |

(a) の具体: 

- **存在判定の正本は m_main**。`m_main_has_value(iname)`(logical)を
  新設し、内部名ごとに「その量を生産するプロセスが有効か」を返す。
  判定材料は原則 `allocated(s%…)`(swe, hi, hl, sd, hg2, …)だが、
  **常時確保の hg・hs は確保ではなく有効フラグ**(gw%enabled、
  s%sed_active)で判定する(無効時のゼロ場は「存在しない」)。既存の
  8+3 変数は常に真(表は従来と同一になる = 後方互換)。判定材料は全
  ランクで同一(param 由来)なので collective 安全(§5)。
- `m_main_get_value / set_value` は、存在しない内部名に対して新しい
  ierr(=4「機能無効」)を返す(1「未知名」と区別して利用者へ説明可能に)。
- **ensure_items は格子ごとに判定する**(ネスト系は格子ごとに param が
  異なり、子だけ雪が有効、ということがあり得る): 格子 g を select →
  基本変数の順に `has_value` が真のものを並べる → ルートへ戻す。並びは
  「格子ごと・基本変数の順」(§73)のまま。
- **表の再生成は initialize ごと**にする。現状の「格子数が変わったら
  作り直す」では、同じ格子数で機能構成が違うケースを再 initialize した
  ときに古い表が残る。encflow_initialize で items を無効化(ng を 0 に
  戻す)してから ensure_items を呼ぶ。
- Python(encflow.py): `has(name)`(表にあるか)を追加。`VAR_*` 定数は
  新変数分を足す(表に無ければ get/set は従来どおり BmiError)。
  `__init__` の格子収集(output_var_names から)は無変更で動く。

### 11.4 論点2: 名前表の一元化(等価リファクタ。先行コミット)

bmi_encflow.f90 に 1 行 = 1 変数の表(派生型配列: Standard Name、
内部名、単位、入力可否)を置き、`base_out / base_in`・`var_internal`・
`get_var_units`・`ensure_items` をこの表から導く。変数追加は「表に 1 行
+ m_main に `case` 1 つ(+ has_value の 1 行)」になる。Python 定数と
README の表は利用者向け文書として残す(表との照合は test_nest.py 系の
受け入れ試験に 1 項目足せば機械検査できる)。既存 11 変数の並び・名前・
単位は不変で、BMI 経由のラン・bmi-tester の結果(92 passed)が同一である
ことが合否(規律4: 等価変換は追加と別コミット)。

### 11.5 論点3: set の方針

§56・§57 の 3 変数は実は 3 区分の見本になっている。区分ごとに受理条件・
適用位置・整合処理を固定し、新変数はどれかの区分に当てはめる(当てはまら
なければ公開しない):

| 区分 | 意味論 | 受理条件 | 適用 | 既存 | 候補 |
|---|---|---|---|---|---|
| F 強制 | 持続(次の set まで) | 内部の生産者が無効 = 「外部」を宣言(pre は prtype=0 がその意味) | update 冒頭、内部の生成(makepre)の代わり | pre | 気温(tsrc=外部を新設)、境界 η_e・u_e |
| Q 準静的共有状態 | 一回置換。生産者は一人 | 内部の更新プロセスが全て無効 | update 冒頭、h 保存で e 回復、ハロ交換 | z | (sd は岩盤面を動かすので不可) |
| S DA 型状態置換 | 一回置換。常時受理 | 変数が存在(所有プロセス有効)+ 所有モデルが置換に整合できる + 非負 | update 冒頭、所有モジュールの calc の前 | h | hg、swe(第1弾)。hs・cq は第2弾で検討 |
| P パラメータ(2026-10-11 追加。developer.md §77) | 物性係数の外部上書き。一回適用で次の set まで持続。save されない | 変数が存在 + 更新が効く実装(ENC 格子系)+ 非負 | update 冒頭、swflow の前。g の係数を書き換えハロ交換 | rn | gv(減少方向 = 瓦礫の再構築の表現がないため見送り) |

原則:

1. **set 可能 ⟺ 表に存在**。入力表も動的(§11.3)。入力表に載る =
   「この量は外部から与え得る」であり、受理の可否(生産者規則・
   所有モデルの整合性)は set 時に判定する 2 層構造は現状(pre・z)と
   同じ。bmi-tester(0.5.10)は入力変数に対して set_value を**実行しない**
   (`test_set_input_values` が "too dangerous" で skip。stage_2/3 は
   in∪out の名前に対するメタデータ問い合わせのみ)ことを配布物で確認
   したので、入力表の掲載は適合性試験に影響しない。
2. **整合処理は所有モジュールの契約に従う**(h → e=z+h の回復と同型)。
   S 区分で置換してよいのは、所有モジュールが**その配列以外に私有の
   状態を持たない**(置換後に不整合が残らない)場合に限る:
   - hg: bucket(f_gwvertical=1)は私有状態なし → 受理。Green-Ampt
     (=2)は累積浸透の私有状態と不整合になる → 拒否(ierr=2)。層2・
     管路層は別変数(hg2・hgc)なので hg の置換は層1のみ。容量
     (sd·sy0)超過は拒否せず次ステップのモデル処理に任せる(bucket の
     溢流と同じ経路)— 実装時に bucket の契約を確認する。
   - swe: m_snow の私有は降水スナップショット(pr0)のみ → 受理。
   - hi・hl: z と共動(氷厚・溶岩厚は s%z に含まれる)ため置換は
     z の再構成を伴う → 見送り。hs・cq: swflow のステップ内移流と
     debris の運動量算入に関わる → 第2弾で個別検討。
3. **適用マスクは h と同じ**(x>0 かつ海セル除外。swe は init が
   海セルを 0 にしている契約に合わせる)。負値は ierr=3。NaN 検査は
   置かない(§56)。
4. **ステージングは当面「変数ごと」の現行様式を踏襲**(ext<name>_fresh +
   ext<name>(:,:)。初回 set 時にのみ確保 = 未使用ならメモリゼロ)。
   汎用化(名前付きステージの配列と適用ディスパッチャ)は set 変数が
   さらに 3 つ以上増える段で等価リファクタとして行う。適用順は固定:
   z → h → e 回復 → hg → swe → pre(現行の z → h → bedmotion → pre の
   間に S 区分を挿入)。
5. MPI は現行と同じ(全ランク collective、src は rank0 のみ有効、値検査は
   rank0 → allreduce で判定を揃える → scatter。§58)。再 initialize の
   残留リセット(init_instance)に新ステージを足す(§59)。
6. save/restore: 未適用のステージは save されない(現行と同じ。文書化)。
   ネスト系: 子格子への set はその格子の次のサブステップ冒頭で適用(§73)。

### 11.6 段取りと検証(合意後)

| 段 | 内容 | 合否(規律2) |
|---|---|---|
| 0 | 等価リファクタ: 名前表の一元化(§11.4)+ ensure_items の存在フィルタ基盤(`m_main_has_value`。既存変数は常に真)+ initialize ごとの表再生成 | BMI 経由 wave/chichibu が reference と identical。bmi-tester wave 92 passed・bmi_nest 170 passed 不変。test_set_value.py・test_nest.py PASS |
| 1 | get の追加(第1弾: hg, swe, sd, hs, cqc, hi, hl、任意で hmax/vvmax/qqmax) | 無効時: reference 全ケース PASS。有効時: get の場と m_output の同時刻の出力(Hg・Sw(×1000)・Sd・Hs・C・Hi・Hl)が一致。機能の多いケース(例: test/gwseep・test/frost・雪のケース)で bmi-tester を新たに回し passed / 0 failed。ネスト系で親子の機能構成が違うケースの変数表が格子ごとに正しい。MPI np=1,2,4 で BMI ドライバ identical |
| 2 | set 第1弾: hg(bucket)、swe | 同値 set の不変性(半分で get → set → 継続。Log 全行一致)を地下水・雪のケースで。誤用: Green-Ampt での hg set・無効時の set・負値が BmiError。無効時 reference 不変。MPI np=1,2,4 |
| 3 | 需要待ち: 気温の外部供給(F)、hs・cq の S、境界 η_e(F) | 各自 |

文書: bmi/README.md と README.en.md の変数表(存在条件の列を追加)、
developer.md に決定事項の新節、architecture.md の BMI 行(§2 の実行順序に
S 区分の適用、§3 の set_value の列挙)、handoff.md の保留項目の消し込み。

### 11.7 検討で分かったこと

- hg と hs は機能無効でも常時確保される(m_state_init)。「確保 = 存在」
  では無効時にゼロ場が公開されるので、存在判定は「確保」ではなく
  「生産プロセスの有効」で定義する必要がある(§11.3)。
- 現行の ensure_items は格子数だけをキーに表をキャッシュしている。機能
  依存の表にすると再 initialize で古い表が残り得るため、initialize ごとの
  再生成に変える(§11.3)。
- bmi-tester は set_value を実行しない(§11.5 原則1)。入力表の設計は
  適合性試験ではなく利用者への意味の正しさで決めてよい。

### 11.8 要合意事項

1. 無効時の扱いは (a) 動的変数表(§11.3)でよいか。
2. 存在判定の定義は「その量を生産するプロセスが有効」(hg・hs はフラグ、
   他は allocated)でよいか。
3. 第1弾 get の対象(§11.2 の「第1弾」行)。統計量(hmax 等)を含めるか。
4. set 第1弾は hg(bucket のみ受理)と swe の 2 つ。hi・hl・sd は不可、
   hs・cq は第2弾、でよいか。
5. ステージングの汎用化は見送り(変数ごとの現行様式)でよいか。
6. Standard Name の候補(CSDMS 既存名優先・文法内造語を許容)。
7. 段 0 の等価リファクタ(名前表の一元化)を先行コミットとして行うか。
