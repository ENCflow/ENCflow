# CSDMS モデルリポジトリ登録の準備メモ(2026-10-25)

CSDMS(Community Surface Dynamics Modeling System)のモデルリポジトリに
ENCflow を登録するための、申請対象版・記入内容・確認記録・残項目の控え。
開発者向けの作業メモ(英語ミラーは作らない。docs/multilingual.md の
plan 文書と同じ扱い)。登録が済んだら、申請内容の控えだけ残して整理してよい。

## 1. 申請対象版

| 項目 | 内容 |
|---|---|
| 版 | ENCflow v3.0.0(タグ `v3.0.0` = コミット `1aaf175`、2026-10-25 公開) |
| Release | https://github.com/ENCflow/ENCflow/releases/tag/v3.0.0(変更点・非互換変更・既知の問題を日英で記載) |
| 引用情報 | CITATION.cff(version 3.0.0 / date-released 2026-10-25) |
| DOI | Concept DOI(全版を代表): 10.5281/zenodo.22042847(README バッジ・CITATION.cff の doi)。**v3.0.0 の版 DOI: 10.5281/zenodo.23635011**(利用者確認 2026-10-25。CITATION.cff の identifiers に記載)。申請の Code DOI には版 DOI を書く |

v3.0.0 と main の先頭(`ef219ce`)の差は handoff/developer.md の文書更新のみで、
計算コードは同じ。申請では v3.0.0 を指定し、main の後続変更は含めない。

## 2. 申請フォームの記入案(英語)

CSDMS の提出手順は「ライセンスの選択 → モデル情報(質問票)の記入 →
ソースコードまたは公開先の連絡」(https://csdms.colorado.edu/wiki/Contribute_model)。
以下は質問票の主な項目に対する記入案。**項目名は過去の質問票の記憶に基づく
(本メモ作成時はネットワーク制約で CSDMS サイトに到達できなかった)。申請時に
実際のフォームの項目に合わせて取捨すること。**

| 項目 | 記入案 |
|---|---|
| Model name | ENCflow |
| Extended name | Eight-Neighborhood Connected collocated-grid flow model (shallow-water-based multi-process surface model) |
| Developers | Tsuyoshi Tada (National Defense Academy, Japan); So Kazama (Tohoku University, Japan) |
| Contact | Tsuyoshi Tada — tada@nda.ac.jp, tadadaze@gmail.com(利用者決定 2026-10-25)。質問の窓口として GitHub Discussions https://github.com/ENCflow/ENCflow/discussions も併記 |
| One-line description | A single-source Fortran program that solves overland water flow with the 2-D shallow water equations on an original eight-neighborhood connected collocated raster grid, and couples optional processes (channels and structures, rainfall–runoff, groundwater, fresh/salt two-layer flow, water quality, snow and glaciers, sediment transport and landscape evolution, lava, driftwood and debris) on the same grid. |
| Keywords | shallow water equations; flood inundation; overland flow; rainfall-runoff; groundwater; sediment transport; landscape evolution; tsunami; storm surge; non-hydrostatic; nesting; OpenMP; MPI; BMI |
| Model type | Single model (one BMI component; nested grids are exposed through grid ids) |
| Model domain | Hydrology; Terrestrial (surface water); Coastal; Geomorphology (landscape evolution) |
| Spatial dimensions | 2-D (plan view; vertical structure abstracted — up to 1-equation layers such as groundwater and salt layers; one-layer non-hydrostatic correction) |
| Spatial / temporal extent | Local to regional (raster grid, projected coordinates; up to tens of millions of cells with MPI). Event (minutes–days) to landscape (years) with the morphodynamic modules |
| Programming language | Fortran (2008). Optional Python wrapper for BMI (numpy only) |
| Platforms | Linux, macOS, Windows (gfortran, Intel ifx, NVIDIA nvfortran; OpenMP; MPI optional). No external libraries |
| Code license | Apache-2.0 |
| Source code | https://github.com/ENCflow/ENCflow (tag v3.0.0) |
| Code DOI | 10.5281/zenodo.23635011 (version DOI of v3.0.0). Concept DOI for all versions: 10.5281/zenodo.22042847 |
| Development status | Active |
| BMI | Yes — BMI 2.0 (Fortran adapter in `bmi/`; passes the CSDMS bmi-tester for a single grid and for a nested system) |
| Documentation | Install: docs/en/install.md. Tutorials: docs/en/tutorial.md, tutorials/bmi/en/README.md (BMI from Python). Users guide: docs/en/users_guide.md. BMI specification and limits: bmi/README.en.md |
| Verification / tests | test/README.en.md(回帰比較 ref と理論解・保存則 analytic を区別した一覧)。First run: `test/wave`(既知の問題は Release ノートの Compatibility notes) |
| Key references | Tada, T. (2026): An eight-neighborhood connected collocated grid scheme for overland flow simulation. Hydrological Research Letters 20(2), 113–118. doi:10.3178/hrl.25-00052(基礎スキーム)。ENCflow 全体のモデル記述論文は未刊行 |
| Input / output | Plain-text matrices, Fortran namelist parameter file, CSV records; GeoTIFF read/write for practice |

紹介文に書く「検証の範囲」は、次の区別を保つ(相談で指摘された点):

- Nightly は `REF_CASES` の 16 ケース(逐次・MPI np=1,2,4・-fcheck=all)と BMI
  ジョブであり、「リポジトリ内の全検証例を毎晩回している」のではない。
- 回帰比較(reference との一致)と、理論解・保存則の確認(Check_*.py)は別物
  (test/README.en.md の Check 列)。
- ビット一致の成立条件(docs/users_guide/parallel.md「結果の再現性とビルド条件」、
  非静水圧の OpenMP 複数スレッドの既知の問題、共有ライブラリ経由の BMI)。

## 3. v3.0.0 の BMI 試験記録

申請対象版そのものに対する確認(Nightly #42 は dec3ae1、#43 は 9d677ab が対象で、
v3.0.0 = 1aaf175 とは計算コードにも差があるため、タグを取り出して再実行した)。

| 項目 | 内容 |
|---|---|
| 対象 | タグ `v3.0.0` = `1aaf1752360b817aeace6e754cfcd9b498075bdd`(git worktree で取り出し) |
| 実行日 | 2026-10-25 |
| 環境 | Ubuntu 24.04.5 LTS(x86_64、2 コア)、GNU Fortran 13.3.0、make.inc 既定(MODE=serial、PREC=double、-Ofast -march=native -flto)、OMP_NUM_THREADS=2 |
| Python | 3.13.17、numpy 2.5.4、bmipy 2.0.1、bmi-tester 0.5.10、pytest<8、gimli.units 0.3(uv の venv) |
| ビルド | `make -C src install` → OK、`make -C bmi` → OK |

| # | 試験 | コマンド(ケース直下) | 結果 |
|---|---|---|---|
| 1 | test/wave 回帰(release 逐次、コミット済み reference と比較) | `./Run.sh` | PASS(Log.txt identical) |
| 2 | test/wave BMI 等価性: 静的ドライバで initialize→update×nt→finalize(同値 set 込み)が CLI 実行と ULP=0 | `../../bmi/test_encflow_bmi param.txt set` → `ULP=0 SKIPCOLS=4 ../Scripts/Compare_ref.sh Log.txt` | PASS(identical) |
| 3 | test/wave bmi-tester(CSDMS 公式適合性、単一格子) | `../../bmi/python/check_bmi.sh param.txt` | 128 passed, 11 skipped(skip は uniform_rectilinear 格子に無い face/edge 系と、bmi-tester 側が "too dangerous" とする set 試験) |
| 4 | test/bmi_nest(多格子公開: 格子情報・変数表・比 1:1 の恒等・再 initialize・同値 set、静的ドライバ root==single、bmi-tester) | `./Run.sh` | PASS(test_nest 全項目、static driver identical、bmi-tester 242 passed, 20 skipped) |
| 5 | test/bmi_vars(機能依存の公開変数: none/full/ga の変数表・get・再 initialize・同値 set・受理条件、静的ドライバ、bmi-tester) | `./Run.sh` | PASS(test_vars A〜F、static driver identical、bmi-tester 146 passed, 11 skipped) |
| 6 | test/wave set_value 等価性(ファイル強制 == set_value、h・z・rn の同値 set 不変) | `python3 ../../bmi/python/test_set_value.py` | PASS(3 項目) |

MPI 版の BMI ドライバ(`test_encflow_bmi_mpi`)はこの環境に MPI が無く未実行。
Nightly #42/#43 の full-mpi ジョブ(np=1,2,4)は通常実行の検証であり、BMI の
MPI 経路は bmi/README の手順で別途確認する(登録の前提にはしない)。
生ログは作業環境の scratchpad に残しただけで、リポジトリには入れていない。
この表を Release v3.0.0 の「検証」節に転記してもよい(人間の操作)。

## 4. 公開説明・引用情報の整合(2026-10-25 実施)

- README.ja.md / README.md: 「スレッド数・ランク数によらずビット一致」の無条件の
  断定を、規律+成立条件(ビルド条件・有効化機能)+参照先(parallel.md、
  リリースノートの既知の問題)の形に改めた。引用の節に「ソフトウェア版と
  HRL 論文の両方」「HRL 論文は基礎スキーム、全体のモデル論文は未刊行」
  「検証内容は test/README とユーザーガイド」を追記。
- CITATION.cff(利用者決定 2026-10-25): `preferred-citation` を外し、HRL 論文を
  `references:` に移した。これで GitHub の「Cite this repository」はソフトウェア
  (ENCflow、版・著者・DOI)を表示する。`doi` は Concept DOI のまま、`identifiers`
  に Concept DOI と v3.0.0 の版 DOI を列挙。`message` は「使用した版を引用し、
  references の論文も併せて引用」に改めた。リリース時の更新手順は developer.md
  §34.4(version / date-released に加え、版 DOI が付与されたら identifiers を
  更新する)。
- docs/users_guide/nonhydrostatic.md・parallel.md(日英): 「スレッド数によらず
  ビット同一」を、リリースノートと developer.md §71 に合わせて「単一スレッドなら
  ランク数によらず同一。複数スレッドでは reduction の順序が実行間で変わり最終桁が
  揺れる(既知の問題)」に改めた(利用者決定 2026-10-25)。

## 5. 残項目と確定事項

確定(2026-10-25、利用者): v3.0.0 の版 DOI = 10.5281/zenodo.23635011、HRL 論文は
CITATION.cff の references へ、非静水圧の再現性記述はリリースノート・developer.md
側に統一、連絡先は tada@nda.ac.jp と tadadaze@gmail.com、**所属機関の公開承認は
取得済み**。

残り:

1. **Nightly の緑の確認**: bmi ジョブに test/bmi_vars を追加した(§3 のローカル
   確認を根拠)。次回の Nightly が緑であることを確認する。
2. **GitHub の「Cite this repository」表示の確認**: preferred-citation を外した後、
   リポジトリページの表示がソフトウェア引用(ENCflow 3.0.0、両著者、DOI)に
   なっていること。
3. **Release v3.0.0 の「検証」節への転記**(任意): §3 の表(人間の操作)。
4. **CSDMS への提出**: アカウント作成、質問票への §2 の記入、ソース公開先
   (GitHub URL・版 DOI)の連絡。
5. 同梱データの再配布条件は本メモの対象外(整理済みであれば作業不要)。
