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

- 案A(推奨): BMI アダプタを `bmi/` として**計算本体の外**に置き、
  optional ビルド(`make bmi`)とする。`make` で作る encflow /
  encflow_mpi / libencflow.a は従来どおり依存ゼロのまま。方針10 の
  精密化に「BMI 等の外部連携アダプタは test/ の検証スクリプト同様、
  計算本体の外であり本項の対象外」と明記する。
- 案B: bmif_2_0 モジュール(仕様定義のみの短い Fortran ソース、MIT)を
  NOTICE 表示の上で bmi/ に同梱する。ビルドは自己完結するが
  「外部由来コードの同梱」という別の例外になる。

いずれでも本体(src/)は BMI を知らない。この検討メモでは案Aを推す。

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

## 8. 位置づけへの影響

対応した場合、docs/comparison.md の「提供形態」に BMI(PyMT /
NextGen 系エコシステムとの相互運用)を追記する節目になる。
「専門の隣の現象をまず試す」(§0 目的3)導線として、Python から
`initialize → update → get_value` で回せることは導入障壁の低減にも
合致する。
