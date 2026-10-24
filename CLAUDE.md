# CLAUDE.md — ENCflow 作業ガイド

ENCflow: 浅水方程式による洪水シミュレーション(Fortran, OpenMP + MPI ハイブリッド)。
ENC 配置格子(独自スキーム)が主実装、STG は旧互換の比較用。

## プロジェクト基本方針(全設計判断の上位規範)

正文は **developer.md §0**(13箇条)。要点:
ラスタ純化(ベクトル表現を持ち込まない)/ 投影座標系スケールまで /
平面2次元で複数プロセスの同時概算(水平は SWE+1方程式拡散が上限、
鉛直は抽象化)/ 過度に複雑化せず徐々に精緻化 / 有効化は fn_* 作成
(不要なら「有効化しない」)/ 無効時はメモリ・CPU ゼロ追加 /
ノート PC〜スパコン単一ソース / 計算本体は Fortran のみ・全公開・
外部ライブラリ不使用(標準規格 OpenMP/MPI と言語標準のみ)/
入出力は単純形式・GUI 等は利用者側 / 計算で使う物理量は直接与える
(派生量の内部生成は明確な理由がある場合のみ。変換は前処理で)/
説明責任(モデル・基礎式・パラメータの出典を可能な限り明記し、独自の
簡略化はそう書く。理論解のある挙動は Check_*.py で verify。コード↔文書↔
翻訳↔テストの一貫性は CI が機械検査)。
**方針に反する実装は提案段階で止め、方針改定の議論を先に行うこと。**

## 正本ドキュメント(コード変更の前に必ず参照)

- **docs/architecture.md** — 全体像の案内図(レイヤ構造・実行順序・
  状態の所有・並列化の型)。初見のセッションはまずここを読む。
- **docs/developer.md** — 設計・規約・実バグ記録の正本(§0〜§30)。
  変更が既存の規約に触れるときは該当 § を読み、規約を変える場合は
  文書の更新までを同じ作業に含めること。
- **docs/multilingual.md** — 文書・教材・設定例の多言語化規約(正本・配置・
  更新と確認記録・検査)。翻訳、文書の移動、注釈付き入力の変更の前に参照する。
- **docs/handoff.md** — 未完了作業と中期の道標。作業完了時に消し込む。
- **docs/comparison.md** — 他モデルとの比較(提供形態・プロセス
  カバレッジ・ポジショニング)。機能追加の節目で更新する。

利用者としての作業(実験ケースの作成・実行・解析。コード変更なし)を
支援する場合は、本書の開発規約より先に **docs/ai_guide.md** と
`.claude/skills/make-case` の手順を参照すること(絶対規律は利用者
作業でも同様に適用される — 特に reference の不変更)。

## ビルドと検証

- ビルド: `src/` で `make`。コンパイラ・モード(release/debug)・MPI・
  実数精度(PREC=double|single)は `make.inc` で設定(詳細は developer.md
  §1, §3)。モード・精度切替の整合はスタンプ機構が検出する。
  **公開インターフェース(モジュールの引数等)を変えたらトップレベルで
  `make` を実行し utils/ の追随漏れを検出すること**(§10。utils は
  libencflow.a をリンクするため src だけのビルドでは漏れる)。
- 回帰テスト: 各ケース(`test/wave`, `test/chichibu` 等)で
  `./Run.sh`(逐次)/ `./Run_MPI.sh N`(N ランク)。
  reference との比較は自動(Compare_ref.sh)。

## 絶対規律(違反禁止)

1. **reference を更新(-u)しない**。回帰テストの不一致は、原因を特定して
   報告し、停止する。基準の更新は人間が結果の妥当性を目視確認してから行う。
2. **検証の合否判定**:
   - 等価リファクタ → 逐次ビット一致(ULP=0)
   - 機能追加 → 機能無効時に既存 reference とビット一致
   - MPI に触れる変更 → np=1, 2, 4 が逐次 reference に ULP=0
3. **確保範囲(jsh/jeh 等)に触れる変更は、最適化ビルドより先に
   gfortran -fcheck=all の np>=2 を実行する**(静的データを使うケースで。
   wave は固定値地形のため感度が低い)。
4. **等価変換とバグ修正・挙動変更はコミットを分ける**(検証の意味が
   逆になるため)。
5. コミット前に `git diff` の全変更を要約して提示する。

## 頻出の規約(要点のみ。詳細は developer.md)

- 分割は j 方向の帯。`dcp%js/je` = 担当帯、`jsh/jeh` = 確保範囲(帯±ハロ2)。
  列の確保範囲は `dcp%ish/ieh`(マスクの列窓±ハロ。全ランク同一。§80)。
  計算は js..je と行ごとの `g%wx`、窓端の縮小は `max(js, jw1+1)..min(je, jw2-1)`
  定型(§11)。
- **帯確保の配列を渡すダミーは assumed-shape+下限指定**
  (`a(dcp%ish:, dcp%jsh:)`)。明示形状は並び結合で行がずれる実バグの元(§12)。
- **init に早期 return 経路がある派生型は全成分デフォルト初期化必須**(§13)。
- collective(gather/reduce/halo)の実行判定は全ランクで同一に。
  is_root ガードの内側に collective を置かない(§5)。
- 静的データは3ゾーンのライフサイクル(初期化=全域、時間ループ=帯)。
  物性係数の全域は rank0 のみが構築し scatter で帯配布(方式2)。
  全域前処理は m_geoinfo_init 内へ。ゾーン2で全域なのはマスク類 x, sw, rw のみ、
  z・係数・ts は窓形(窓±ハロ、全域添字。§11, §82)。
- list_* は namelist を読むだけ。解釈・検証・導出は各 m_* の init(§12)。
- save の write 並びと restore の read 並びは必ず同時に更新し、
  形式変更時は save_version(仕様変更日の日付)も更新(§7)。配列の
  save/restore は m_restart(restart_write/read_cell・_edge)経由(§83)。
- rank0 バッファは全域形 `(1:,1:)` と窓形 `(dcp%ish:, dcp%jwh1:)` の 2 系統。
  配布は par_scatter_cell(全域形)/ par_scatter_win(窓形)を取り違えない(§12)。
- 総和のリダクションは par_sum_rows(決定的)。max/整数和は allreduce 可(§11)。

## 作業の流儀

- **設計判断は実装前に議論する**。複数案があるときは比較と推奨を提示し、
  合意を得てから実装する。決定とその理由は developer.md に追記する。
- 単一ソース MPI: m_parallel_serial / _mpi は公開インターフェースを常に一致
  させる。#ifdef は使わない(§2)。
- 新しい物理モジュールの追加様式: 有効化は fn_* の有無(precip/record/
  geomorph/gwflow と同じ)。排他切替のモデル群は t_swflow 型の手続き
  ポインタ成分方式、加算的なプロセス群は独立フラグの重ね合わせ方式。
  実装契約の見本は m_gwflow_bucket のヘッダ。
- 新しいモデル・基礎式・既定値を入れる作業には、出典の記載(文献がなければ
  「独自」と明記)、解析解・保存則があれば test/<case>/Check_*.py の検定、
  users guide 該当章の更新(日英)を同じ作業に含める(§0 方針 13)。

## 文書・設定例の多言語化(詳細は docs/multilingual.md)

- 正本は日本語(例外: LICENSE と TRADEMARKS.md は英語正本。ルート README.md は
  英語ミラーで README.ja.md が正本)。英語版は `en/` ミラー(docs/en/、
  tutorials/<case>/en/、test/<case>/en/、examples/<case>/en/、List_samples/en/)で、冒頭に
  「English mirror of <正本パス>」を刻印する。既存の README.en.md は有効。
- 翻訳のために計算本体・データ・Run.sh・reference を複製・変更しない。設定例は
  コメントだけを翻訳し、値・識別子・ファイル参照・有効状態(コメントアウト例を
  含む)を保つ。実行場所は言語によらずケース直下(`./encflow en/param.txt`)。
- 利用者向け文書・教材・List_samples の正本を変えたら、同じ作業で英語版も更新する。
  更新後に `python3 tools/i18n/check.py audit --recorded-only --strict-recorded --links`
  (CI と同じ条件)を通し、原文と訳文を確認した組だけを `check.py record` で記録する
  (AI による確認は `--method assistant`。人間の確認と偽らない)。更新できない訳は
  `stale` のまま残し handoff.md に書く。既存の未確認ミラーを一括で記録しない。
