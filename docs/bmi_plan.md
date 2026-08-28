# bmi_plan.md — CSDMS BMI 対応の実現可能性検討メモ

対象: ENCflow を CSDMS Basic Model Interface (BMI) 2.0 に対応させる
ことの実現可能性・工事規模・推奨構成の見通し。
経緯: 2026-08-28 の検討。**まだ検討段階であり、設計・実装は未着手**。
具体的な設計(関数一覧・変数名マッピング・コード案)は次の段階で行う。

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
5. **変数名マッピング表**: CSDMS Standard Names ↔ t_state 成分の
   対応表と単位(内部は SI が基本)。PREC=double|single は
   get_var_type / get_var_itemsize で実精度を報告する。
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
  (y の向き = j の増加方向の規約合わせのみ §7-5 のマッピング設計で確認)。
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
