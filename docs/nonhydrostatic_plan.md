# ENCflow 非静水圧(1 層 NH)拡張の設計検討メモ(提案。実装前)

作成: 2026-10-05。対象コード: v2.0.0(2026-10-04)。

本書は、利用者から提示された 2 つの検討文書

- 「非静水圧モデル検討・実装引継ぎメモ — 保存形移流・RK 内移流固定版」
  (以下「引継ぎメモ」)
- 「非静水圧・分散モデル 実装設計プラン」(以下「設計プラン」)

を現行コード(m_swflow_enc の momentum / calc_kth_flux / continuous、
adv submodule、並列層)と developer.md §0 の方針に照らして検討し、
**実装の可否・見通し・計画案**をまとめたものである。実装は未着手。
採否は利用者の判断(§4 の議論事項)を待つ。

---

## 0. 結論(要約)

1. **実装は可能**。ただし引継ぎメモの第一候補「edge-local scalar
   implicit(エッジ局所の単一掃引)」は、線形解析の結果、**目標の
   1 層分散関係を再現できない**(§2)。NH が意味を持つ解像度
   (Δx ≲ H/2)では補正量の 1/3〜1/7 しか出ず、Δx < H/√2 では格子
   スケールで補正の符号が反転する。
2. **推奨方式はステップ末尾の射影(fractional step)**: 既存の静水圧
   ステップ(適応 RK・保存形移流を含む)をそのまま predictor とし、
   boundary_uvmn と continuous の間で、セルスカラー 1 個の楕円型方程式
   (I − βDG)φ = βD a* を**反復(Jacobi → CG)**で解いてエッジ流速・
   流量を補正する(§3)。恒等項が支配する作用素なので 10〜30 掃引で
   収束し、3 次元 NH モデルの圧力ポアソンとは別物である。
   **適応 RK と同じ「必要な場所だけ」も載せられる**(§3.7): 検出量
   χ ≈ (kH)²/4 で種セルを選び、数 H の縁をつけた活性集合だけで反復
   する。楕円型作用素の影響距離が H/2 で減衰するため、活性領域の
   内側は厳密解のまま、静水圧の領域にはコストが乗らない。
   **反復内の MPI 通信も回避できる**(§3.9): 掃引数を固定して
   Chebyshev 加速し、幅 m のハロを 1 回だけ交換すれば、反復ループ内の
   ハロ交換と collective はゼロ(Δx = H/2 で m ≈ 12)。
3. この方式なら **momentum / calc_kth_flux(RK)/ adv / continuous は
   無変更**、親モジュールへの hook は m_swflow_enc_calc の 1 箇所、
   NH OFF で配列確保・演算・通信ゼロ追加 = 既存 reference とビット一致、
   という設計プラン §4.2・§7・§8・§20 の要件を満たす。
4. **方針との関係で 2 点の改定議論が先に必要**(§4): (a) developer.md
   §0-5「水平は SWE が上限」に研究用の明示的例外を置くこと、(b) 設計
   プラン §21 が「全体反復ソルバが必要なら中止」としている条件を、
   「セルスカラー 1 個・決定的・NH OFF でゼロ追加」を満たす反復は可、
   に改めること。
5. 引継ぎメモの前提(保存形移流への変更、RK 段内の移流固定、
   Jameson–Baker 4 段)は**現行コードで既に成立している**(§1)。
   前提の実装作業は不要。
6. コストの支配要因はソルバではなく**空間解像度 Δx ≲ H/2** である
   (§2.3)。NH ケースは研究計算として深い水域を細かく切る前提で
   見積もる。
7. **先行研究の調査(2026-10-05。§3.10)**: 「静水圧 predictor + 射影 +
   判定領域だけの楕円型解」は Firdaus & Behrens(IJNMF 2026、arXiv
   2606.27562)が 1 次元・2 次元で実証済みで、NEOWAVE・SWASH も同じ
   predictor–corrector 構成。**本提案は実証済みの実用路線**であり、
   概念の新規性は主張しない。調査を踏まえた実務的な改訂は、(a) 通信
   回避ソルバ(§3.9)は既存ハロでの Jacobi で正しさを固めてから
   Phase 4c で入れる、(b) 検出量は分散型 χ を既定、振幅型を比較用、
   (c) 砕波スイッチは「なし」で先に検証し保険として残す、(d) 鉛直
   圧力分布は線形(β = h²/4)のまま、(e) 動く底面は Firdaus/Jeschke の
   定式を参照、の 5 点(§3.10)。

---

## 1. 現行コードの確認(引継ぎメモの前提との対応)

| 引継ぎメモの前提・仕様 | 現行コード(2026-10-05) | 判定 |
|---|---|---|
| 移流項を保存形へ変更する(§10, §35-1) | f_advection_scheme=3(S&D 運動量保存形+MUSCL)が既定(2026-10-03 昇格。§68.19) | 済 |
| 旧 Scaled advection は廃止(§11, §35-2) | f_advection_runge=1 として残存。評価済みで非推奨・除去候補(§68.19)。アフィン形(Picard)も試行のうえ revert(§68.23) | 済(整理で除去) |
| RK 4 段中は移流固定(§12, §35-3) | calc_kth_flux: `tae = tae0`(RK 段内不変) | 済 |
| Jameson–Baker 4 段(1/4, 1/3, 1/2, 1)(§9) | calc_kth_flux: `a(1:4) = [4,3,2,1]`, `dtl = dt/a(l)/lme`、uve1 = uve0 + (...)·dtl | 済 |
| 判定単位はエッジ。Euler → 比が f 倍で RK(§8) | calc_kth_momentum: mne1 と mne の比 p_adprunge_thresh で判定し再計算 | 済 |
| local RK 中は対象エッジの両セルの水深だけ更新(§28) | calc_kth_flux 内 block: hc, hn を無印 mn + 自エッジ mne1 で更新 | 済 |
| unique edge 計算(約 4 edge/cell)(§8) | momentum: 各セル k=1..4 | 済 |
| uv は低メモリの単一バッファ(§8, §35-5) | §7: uv は自エッジ read-then-write のみ。**ステップ頭の uv^n は momentum 後に失われる** | 済(NH は uv^n の複製が要る。§3.4) |
| g cos²θ 補正は別オプションとして残す(§32) | f_gravity_correction(Ni et al. 2019 の cos²θ) | 済 |
| 2-pass 構造(全エッジ Euler → 判定 → RK)(§23) | 単一パス(エッジ訪問時に Euler と RK を続けて行う) | **未。momentum の構造変更になる** |
| NH detector・NH エッジの RK 昇格(§6, §21) | なし | 未(§2 の結果により**不要**と判断) |

補足: 現行の「RK 中の移流固定」の時間精度は引継ぎメモ §15〜§16 の
とおり移流に関して Euler 相当であり、引継ぎメモの整理は現行コードの
記述として正しい。

---

## 2. 線形解析: 候補スキームの分散補正率

### 2.1 定式

引継ぎメモ §3・§18 の 1 層 NH を、ENC の離散勾配 G(セル → エッジ、
(φ_n − φ_c)/w8dr(k))と離散発散 D(エッジ → セル、continuous と同じ
重み l8(k)/(dx·dy))で書くと

    (I − β G D) a = b,   β_i = h_i² / 4

である(a: NH 補正後のエッジ加速度、b: 静水圧の全加速度)。1 次元・
一定水深 H・Fourier モード e^{ikx} では、C 格子の離散ラプラシアンの
固有値 Λ = 4 sin²(kΔx/2)/Δx² を使って、補正率 P = â/b̂ が

| 方式 | P(k) | 備考 |
|---|---|---|
| (c) 厳密解(目標) | 1 / (1 + βΛ) | 引継ぎメモ §4 の ω² = gHΛ/(1 + βΛ) を与える |
| (a) 陽的 1 項 a = b + βGDb | 1 − βΛ | Neumann 級数の 1 次打ち切り |
| (b) edge-local 単一掃引(引継ぎメモ §25) | (1 + ε cos kΔx) / (1 + ε)、ε = 2β/Δx² = H²/(2Δx²) | (I − βGD) に対する Jacobi 反復の 1 回目(初期値 = b)に等しい |

(b) の導出: 引継ぎメモ §25〜§26 の C_i = B_i − s_e b_e は「他エッジの
寄与を Euler predictor の b で固定」する操作で、これは Jacobi 法の
1 掃引そのもの(対角 1 + ε、非対角 ε/2 × 2)。引継ぎメモ §36 の課題
6・7(処理順序・対称掃引)が示唆するとおり、本質的に反復法の 1 回目で
ある。

### 2.2 数値

Δx/H を変えた補正率 P(kH = 0.5 / 1.0 / 2.0。各欄は 目標 / (b) / (a))。
kΔx > π のモードは n/a。

| Δx/H | ε | kH = 0.5 | kH = 1.0 | kH = 2.0 | 格子スケールの (b) |
|---:|---:|---|---|---|---:|
| 2.0 | 0.125 | 0.946 / 0.949 / 0.943 | 0.850 / 0.843 / 0.823 | n/a | +0.78 |
| 1.0 | 0.5 | 0.942 / 0.959 / 0.939 | 0.813 / 0.847 / 0.770 | 0.585 / 0.528 / 0.292 | +0.33 |
| 0.5 | 2.0 | 0.941 / 0.979 / 0.938 | 0.803 / 0.918 / 0.755 | 0.521 / 0.694 / 0.081 | −0.33 |
| 0.25 | 8.0 | 0.941 / 0.993 / 0.938 | 0.801 / 0.972 / 0.751 | 0.505 / 0.891 / 0.021 | −0.78 |

読み方: 長波極限で (b) は目標の補正 (1 − P) を **1/(1 + ε) 倍**にしか
出さない(Δx = H/2 で 1/3、H/4 で 1/9)。Δx < H/√2 では格子スケール
モードの加速度の符号が反転する(2Δx モードの不安定化要因)。(a) は
kH ≲ 1 では目標に近いが kH > 1 で過大、格子スケールで負(βΛ > 1)。
目標を再現するのは (c) だけである。

### 2.3 必要な空間解像度(NH の成立条件)

C 格子の長波展開 ω² = gHk²[1 − (kΔx)²/12 + …] と 1 層 NH の
ω² = gHk²[1 − (kH)²/4 + …] から、**空間の数値分散と物理分散は
Δx = √3·H ≈ 1.7 H で同じ大きさ**になる。物理分散を数値分散の 10 倍
以上にするには Δx ≲ 0.55 H。したがって

- Δx > 1.7 H の格子では NH を入れても数値分散に埋もれる(無意味)。
- NH の検証・実用は Δx ≈ H/2〜H/4 が前提。この解像度では ε = 2〜8
  で、(b) は機能しない(§2.2)。

深さ 10 m の河川遡上津波なら Δx ≈ 2.5〜5 m、dt ≈ 0.1〜0.3 s。10 km
× 1 km で 10⁵〜10⁶ セル・1 時間で 10⁴ ステップ規模(ノート PC〜
ワークステーション、必要なら MPI)。**コストはソルバよりこの解像度
要件で決まる**。

### 2.4 2 次元 ENC 作用素と反復の収束

ENC の 8 近傍ラプラシアン −DG の対角成分は Σ_k l8(k)/(dx·dy·w8dr(k))
= 2.83/Δx²(p_diagratio 既定。5 点なら 4.0/Δx²。長波極限で ∇² に
一致することは確認済み)。ε_2D = β·2.83/Δx² として

| Δx/H | ε_2D | Jacobi の長波誤差減衰率 ε/(1+ε) | 1e-4 までの掃引数 | CG の条件数 κ ≈ 1 + 2ε | √κ |
|---:|---:|---:|---:|---:|---:|
| 1.0 | 0.71 | 0.41 | 10 | 2.4 | 1.6 |
| 0.5 | 2.83 | 0.74 | 30 | 6.7 | 2.6 |
| 0.25 | 11.3 | 0.92 | 109 | 23.6 | 4.9 |

恒等項があるため条件数は格子数に依存せず、**CG なら 10 反復程度、
Jacobi でも 30 掃引程度**で収束する。3 次元 NH モデルの圧力ポアソン
(κ ∝ N²、マルチグリッド必須)とは性格が違い、設計プラン §21 が
懸念した「全体反復ソルバ」の重さはない。

### 2.5 引継ぎメモ 2-pass 構造の実装上の問題(参考)

(b) を採る場合でも、引継ぎメモ §23 の Pass 1 で「B_i += s_ie b_e,
B_j += s_je b_e」と両セルへ散布加算する形は、OpenMP のセル並列では
隣接セルへの競合書き込みになり、atomic にすると総和順序が非決定に
なる(§8 違反)。continuous と同じ「セルループで 8 エッジを集める
gather」に書き換える必要がある。また Pass 1/Pass 2 の分離は momentum
の単一パス構造の変更で、設計プラン §21 の中止条件「momentum の loop
構造を全面変更」に当たる。§3 の方式はこの問題を持たない。

---

## 3. 推奨方式: ステップ末尾の射影(fractional step)

### 3.1 時間分割

1 グローバルステップを次の 3 段に分ける(SWASH・NEOWAVE 型の
predictor–corrector。参考文献は §7)。

1. **静水圧 predictor(現行のまま)**: momentum(適応 RK・保存形移流・
   摩擦・堤防・構造物)→ par_edge_merge → boundary_uvmn。結果を
   u*(sx%uv)、mn1*(sx%mn1)とする。
2. **NH 補正(新設 nh_project。NH ON のときだけ呼ぶ)**:
   - a*_e = (u*_e − u^n_e)/Δt(ステップの静水圧全加速度。移流・摩擦・
     RK の効果を含む = 引継ぎメモ §18「全加速度に作用させる」と同じ)。
   - セルスカラー φ_i = β_i (D a)_i について
     (I − β D G) φ = β D a* を反復で解く(§3.3)。
   - NH エッジで a_e = a*_e + (G φ)_e、u^{n+1}_e = u^n_e + Δt a_e、
     mn1_e = u^{n+1}_e · he。
   - par_edge_merge(uv, mn1)を再実行(界面行の補完)。
3. **continuous 以降(現行のまま)**: 補正後の mn1 で水深更新。質量
   保存は両セルが同じ mn1 を見るので現行どおり厳密。

線形(1 次元・平坦床)では、静水圧部を前進後退 Euler とすると
半離散の分散関係が ω² = gHΛ/(1 + βΛ) に**厳密に**一致する(時間
離散化誤差は現行と同程度)。NH 補正は加速度に 0 < P ≤ 1 の
フィルタを掛けるだけなので、新しい速い波を生まず CFL は変わらない
(引継ぎメモ §30 と同じ結論)。

### 3.2 離散式(ENC の重み規約で)

- (D a)_i = Σ_{k=1..8} sign_e(k) a(ke(k), i+die(k), j+dje(k)) · l8(k)/(dx·dy)
  (continuous の dh = mne·mn2dh(k) と同じ重み、Δt を除いたもの)。
- (G φ)_e = (φ_n − φ_c)/w8dr(k)(圧力項 tge と同じ差分)。
- β_i = (h_i^n)²/4(時刻 n で固定。引継ぎメモ §27)。
- 行列は対角 1/β_i + Σ_k l8/(A·w8dr)、非対角 −l8(k)/(A·w8dr(k)) の
  9 点。A/β_i を掛けた形で対称正定値(エッジ重みが両セルで同じ)なので
  CG が使える。
- V1 では gv・wfrac・frw/fwd・σ を NH の作用素に入れない。これらが
  有効なセル・エッジは NH マスク外(静水圧)とする(設計プラン §13)。

### 3.3 ソルバ(決定性・MPI)

- **Jacobi(第 1 実装)**: φ_old → φ_new の二重バッファ。1 掃引 =
  セルループ 1 回 + par_halo_cell(φ_new) 1 回。収束判定は残差の最大値を
  par_allreduce_max(順序不変なので §11 の規律内)。スレッド数・ランク数
  に依らずビット一致する。
- **CG(第 2 実装。性能が要るとき)**: 内積は行部分和 → par_sum_rows
  (決定的総和)。1 反復 = 行列ベクトル積 1 回(セルループ + halo)+
  内積 2 回。§2.4 のとおり 10 反復程度。
- 反復回数上限・許容残差は namelist(nh_itmax, nh_tol)。不収束は
  par_warn + 継続(研究機能。発散は既存の 250 m/s 判定に掛かる)。
- **実装順序(2026-10-05 改訂)**: まず本項の Jacobi(既存の幅 2 ハロ
  交換+収束判定の allreduce)で正しさと分散関係の再現を固める(並列層
  は無変更)。反復内の通信を回避する形(固定回数の Chebyshev 加速 +
  幅 m ハロ。§3.9)は、実ケースで通信が律速と計測されてから Phase 4c で
  入れる。CG は比較用。

### 3.4 必要な追加状態(NH ON のときだけ確保)

| 配列 | 形 | 用途 |
|---|---|---|
| uv0 | エッジ(1:4, 0:nx, jsh−1:jeh) | ステップ頭の u^n の複製(uv が単一バッファのため。§7) |
| phi, phi1 | セル(1:nx, jsh:jeh) | NH ポテンシャル(二重バッファ) |
| rhs | セル | βD a* |
| nhmask | 整数セル | NH 有効セル(0/1) |

合計はセルスカラー約 7 個分。NH OFF では allocate せず、呼び出しも
行わない(方針 8)。リスタート: V1 の NH 状態はすべてステップ内の
一時量で、保存対象なし(設計プラン §19 の「p_nh が診断量なら保存
しない」に該当)。砕波スイッチ(Phase 6)を入れる段階で eta_prev と
breaking マスクを私有 save に加える。

### 3.5 NH マスク(エッジを静水圧に退化させる条件)

セル: x > 0、sw = 0(海域マスクは潮位強制の対象。要検討)、h ≥ nh_hmin、
gv = 1、wfrac = 1(幅河道外)、sdep = 0(σ 非適用)、breaking = .false.
(Phase 6)。エッジ: 両セルが NH セル、かつ 堤防壁・海岸堤防・開辺境界
面・区間流入面・構造物面・skip8 でない。マスク外のセルは φ = 0
(Dirichlet)で、マスク境界のエッジは補正しない(設計プラン §12.7 の
M_NH,e = min(M_c, M_n) と同じ)。優先順位は設計プラン §12.10 のとおり
dry → h < nh_hmin → breaking → NH。

### 3.6 親モジュールへの変更(最小)

```fortran
  ! m_swflow_enc_calc(boundary_uvmn の後、continuous の前)
  if (nh_active) call nh_project(p, g, s, sx_mod)
```

に加えて init の `call nh_init(p, g, s)`、dispose の `call nh_dispose()`、
ステップ頭(halo 交換直後)の `if (nh_active) call nh_prepare(sx_mod)`
(uv0 の複製)の 4 箇所。interface は設計プラン §7.1 の型。NH の式・
状態・ソルバはすべて submodule m_swflow_enc_nh に閉じる。

mn1 の再計算に使うエッジ水深 he は calc_kth_flux の局所変数で、
hcap・dry_head_cap・σ の分岐を含む。流速比 mn1 = mn1*·(u^{n+1}/u*)
で済ませると u* ≈ 0 のエッジで破綻するため、**he の評価を純関数
edge_depth() に切り出す等価リファクタ(ULP=0 のコミット)を先に行い、
両者で共有する**(Phase 2)。

### 3.7 活性集合による適応化(適応 RK と同じ発想で「必要な場所だけ」)

§3.1〜§3.6 の射影は NH マスク内の全セルで解く。これに、適応 RK と
同じ「必要な場所だけ」を載せる。

**なぜ単位がエッジでなくセル集合か**: 適応 RK がエッジ単位で済むのは、
RK の作用が自エッジと両側 2 セルに閉じているため。NH 補正
(1 − β∇²)φ = s は楕円型で 1 点の補正が近傍に同時に効くが、影響範囲は
有限で、Green 関数は exp(−r/√β) = exp(−2r/H)、すなわち **e 倍減衰距離
H/2** である。数水深より遠くは事実上無関係なので、適応化の単位は
「検出セル+数 H の縁」の連結領域になる(Δx = H/2 なら縁 4〜6 セル)。
引継ぎメモの edge-local 案(§2.2 の (b))は、この縁が隣 1 セルぶんしか
ない(反復の 1 回目)ことが不足の正体でもある。

**手順**(nh_project の中。静水圧 predictor の後):

1. 検出: 全セルで 1 パスの gather により
   χ_i = |β_i (D a*)_i| / (ā*_i + |β_i (D a*)_i| + ε)
   を求める。ā*_i は 8 エッジの |a*| の RMS(引継ぎメモ §36-4 の
   「RMS 正規化」。単一エッジ正規化との比較は検証項目)。長波では
   χ ≈ (kH)²/4 = z で、引継ぎメモ §5・§6 の z/(1+z) と同じ量になる。
2. 活性集合: χ_i > χ_on のセルを種とし、縁幅 nh_margin セル(既定は
   2H/Δx 程度 = 減衰距離の 4 倍)だけ 8 近傍で膨張させる。前ステップに
   活性だったセルは χ_i > χ_off で継続(ヒステリシス。初期候補は
   引継ぎメモの χ_on ≈ 0.06 / χ_off ≈ 0.04)。活性集合は §3.5 の
   NH マスクとの積。膨張はセルループを nh_margin 回(各回 halo 交換
   1 回)。
3. 反復は活性セルだけで解く(非活性は φ = 0 の Dirichlet、演算ゼロ)。
   補正は両セルが活性なエッジだけ。コストは活性セルの割合に比例する。
4. 決定性: χ は時刻 n と predictor の量だけから決まり、膨張は 8 近傍の
   論理和なので、走査順・スレッド数に依らない。MPI では**反復回数と
   収束判定(allreduce)を全ランクが同じ回数呼ぶ**。活性セルのない
   ランクも collective にだけ参加する(developer.md §5)。活性マスクは
   膨張ごとに halo 交換するのでランク境界で連結が切れない。

**効果**: 長波・氾濫・斜面流・河道の定常流では χ ≈ 0 で活性化せず、
NH ON のケースでも静水圧の領域にはコストが乗らない。活性領域の内側は
§3.3 の厳密解のままで、近似は縁の φ = 0 による exp(−2·縁幅/H) 程度の
切り捨てだけである。設計プラン §21 が懸念した「全格子の反復」では
なく「検出した小領域の反復」になる。

**実装例・先行研究(2026-10-05 調査。要文献照合 = 本文未読)**:

- **Firdaus, K. & Behrens, J.(ハンブルク大)** Locally Adaptive
  Non-Hydrostatic Shallow Water Extension for Moving Bottom-Generated
  Waves. IJNMF 2026(arXiv 2505.17025、1 次元)/ Two-Dimensional Locally
  Adaptive Non-Hydrostatic Extension of Shallow Water Equations. arXiv
  2606.27562(2026-06、2 次元)。**本節と同じ発想の最も近い先行研究**:
  静水圧 SWE を predictor にし、射影法で楕円型問題を判定領域だけで
  解き、砕波は Froude 数で局所的に SWE へ切り替える。2 次元で計算量
  約 40% 削減。判定量は静水圧 predictor の |η/d| と流速の大きさで
  閾値 0.001、判定領域を 1 要素広げる。離散化は RK-DG + 局所 DG、
  鉛直圧力は 2 次分布(Jeschke et al. 2017)。MPI は検索で確認できず。
- Berger, M.J. & LeVeque, R.J. (2024) Implicit adaptive mesh refinement
  for dispersive tsunami propagation. SIAM J. Sci. Comput. 46:B554
  (GeoClaw-Bouss。SGN の楕円型系を AMR のレベルごとに陰的に解く。
  領域を限る発想は細分化パッチ経由)。
- Yamazaki, Cheung & Kowalik (2011) NEOWAVE: ネスト格子内で NH、外側は
  粗い格子。
- 分散項を局所的に**切る**方向の切替は多数(Tonelli & Petti 2009 の
  hybrid Boussinesq/NSWE、Tissier et al. 2012、Kazolea & Ricchiuto 2018、
  FUNWAVE-TVD(Shi et al. 2012)、SWASH の砕波スイッチ)。機構(マスク
  境界で φ = 0 として静水圧に落とす)は ON 方向にも同じ。Kazolea &
  Ricchiuto は H/NH 切替の安定性と格子依存を主要な難点として報告。

**検出量の既定(2026-10-05 改訂)**: nh_detector で切り替える。

| nh_detector | 検出量 | 性質 | 位置づけ |
|---|---|---|---|
| 1(既定) | χ_i = |β_i (D a*)_i| / (ā*_i + |β_i (D a*)_i| + ε)、長波で χ ≈ (kH)²/4 | 振幅に依らず「分散が効く場所」を測る。長波・定常流・一様流で 0 | ENCflow の主対象(背景流のある河川、洪水波と津波の重なり)で河川全体が常時活性にならない、という**実用上の理由**で既定 |
| 2 | Firdaus & Behrens 型: |η̃/d| > k_nh または |ũ| > k_nh(k_nh = 0.001) | 振幅検出。静水と乾燥地以外はほぼ活性 | 海の津波には実用的。比較用(Phase 4b) |

追加パラメータ: f_nh_adaptive(0: マスク内全域、1: 活性集合)、
nh_detector、nh_chi_on、nh_chi_off、nh_margin(セル数。0 なら 2H/Δx
から導出)。f_nh_adaptive=0 は検証の基準(活性集合の切り捨て誤差を
測る比較対象)として残す。

### 3.8 設計プラン・引継ぎメモからの変更点

| 項目 | 文書の案 | 本提案 | 理由 |
|---|---|---|---|
| NH 補正の位置 | RK 各段(引継ぎメモ §24, §35-9) | ステップ末尾 1 回 | 反復解を段ごとに 4 回は不要・不可。段内 edge-local は §2 で不採用 |
| NH detector と RK 昇格 | χ^NH で判定、NH エッジは RK(§6, §21, §35-8) | detector は**セル単位の活性集合の種**に転用(§3.7)。RK 昇格は不要 | 楕円型の補正はエッジ単位に閉じない。適応 RK は静水圧 predictor 側でそのまま働く |
| edge-local scalar implicit | 第一候補(§25, §35-11) | 不採用(反復法の 1 回目に過ぎない) | §2.2 |
| 「NH ON は full RK」 | 設計プラン §14 | 不要。現行の適応 RK のまま | predictor の精度向上は補正と独立に効く |
| 全体反復ソルバ | 中止条件(設計プラン §21) | セルスカラー 1 個・決定的なら可 | §2.4。要改定 |
| パラメータ置き場 | list_enc(設計プラン §10) | 同じ(f_diffusion_term の前例) | 専用 fn_* は砕波等で項目が増えたら検討 |

---

### 3.9 通信の回避(固定回数 Chebyshev + 幅 m ハロ)

§3.3 の素朴な実装は 1 掃引ごとにハロ交換と収束判定の allreduce を
要する。作用素が恒等項支配で影響距離が H/2 しかないことを使うと、
**反復ループ内の通信を点対点・collective ともゼロ**にできる。

**(1) 固定回数 + 幅 m の一括ハロ**

- Jacobi を m 回掃引した結果は作用素の m 次多項式 = 半径 m の固定
  ステンシルを 1 回掛けたものと同じ。幅 m のハロを一括交換しておけば
  m 回の掃引は帯内で閉じる(1 掃引ごとに有効行が 1 行ずつ縮むだけ)。
- 収束判定の allreduce は使わず、掃引数 nh_nsweep を固定する。必要
  回数は ε(§2.4)から事前に決まる。残差は表示用に dt_disp ごとに
  1 回だけ集計する(par_allreduce_max。回帰比較の列には入れない)。
- 冗長計算は帯の両端 m 行(帯 200 行・m = 12 で約 1 割)。NH 専用の
  広ハロ配列(1:nx, js−m:je+m)は NH ON のときだけ確保する。
- 並列層に par_halo_edge(a, width) と同型の**幅指定つきセル交換**を
  1 本足す(逐次版は no-op。公開インターフェースは両版で一致。§2)。
  MPI に触れるので np=1,2,4 ULP=0 と -fcheck=all np≥2 を先に回す。
- m が帯幅に対して大きいときはハロ幅 w < m とし ceil(m/w) 回に分けて
  交換する(それでも collective はゼロ)。

**(2) Chebyshev 加速(内積なしで CG 並み)**

- CG は内積(allreduce)を毎反復に要するが、Chebyshev 半反復法は
  固有値の範囲だけ分かれば内積なしで同程度に収束する。対角スケール後の
  Jacobi 反復行列のスペクトル半径は ρ = ε/(1+ε) で、ε は水深から
  決まる既知量。漸近収束率は σ = ρ/(1+√(1−ρ²))。
- ρ は活性領域の最大水深から見積もる。過大評価しても収束するだけ
  なので、ステップごとの allreduce 1 回(活性セルの h の最大)、
  または初期の最大水深からの静的上限で足りる。

| Δx/H | ρ | Jacobi 掃引数(1e-4) | Chebyshev 掃引数(1e-4)= 必要ハロ幅 m |
|---:|---:|---:|---:|
| 1.0 | 0.41 | 10 | 7 |
| 0.5 | 0.74 | 30 | 12 |
| 0.25 | 0.92 | 109 | 24 |

**(3) 活性集合(§3.7)との組合せで通信相手も減らす**

- 活性セルが帯境界の 2m 行にない隣接ランク対は交換を省く。省くか
  どうかは両側が同じ情報(マスクのハロ)から対称に判定するので
  片側だけが待つことはない。
- collective がないので、活性セルのないランクは何もしない。必須の
  通信はステップ頭の活性フラグ(隣接ランクへ整数 1 個)だけ。

**(4) ステップあたりの通信量(まとめ)**

| 項目 | 素朴な実装(§3.3) | 本節 |
|---|---|---|
| 反復内のハロ交換 | m 回 | 0 回 |
| 反復内の allreduce | m 回 | 0 回 |
| ステップ頭の交換 | マスク・右辺・β を幅 1〜2 | 同じ 3 量を幅 m で 1 回(3 成分を 1 配列に詰めて 1 回にできる) |
| uv^n の複製 | 帯内コピー(通信なし) | 同じ |
| 補正後の界面行 | par_edge_merge 2 回(既存) | 同じ |
| 残差の表示 | 毎掃引 | dt_disp ごとに 1 回 |

避けられないのは「活性領域が帯境界をまたぐ以上、幅 m のハロ交換
1 回と界面行の merge は残る」こと。これは momentum が毎ステップ行う
幅 2 の交換と同じ種類・同じ回数で、反復の有無に依らない下限。

**(5) 第 2 段階の候補**

- 前ステップの φ からの warm start(掃引数 1/2〜1/3)。固定回数では
  結果が履歴に依存するので、リスタート往復のビット一致のために φ を
  私有 save に加える必要がある。まずは cold start(状態なし)。
- 帯分割は行を丸ごと持つので、x 方向の三重対角を厳密に解く
  line-Jacobi はランク内で閉じる。9 点ステンシルの扱いが複雑になる
  ため、Chebyshev で足りなければの候補。
- 補正の更新頻度低減(数ステップに 1 回)は分散項のサブサイクリングに
  なるので、精度の裏付けなしには採らない。

**位置づけ(2026-10-05 改訂)**: 本節は**性能段階(Phase 4c)**の
作業とする。まず §3.3 の Jacobi(既存の幅 2 ハロ+収束判定)で正しさを
固め、実ケース(河川遡上津波・地滑り津波)で通信が律速と計測されて
から、幅指定つきセル交換を並列層に足して固定回数 Chebyshev に移る。
ノート PC〜ワークステーション規模では不要な可能性が高い。移行時は
Jacobi 収束判定版との ULP 差(固定回数の切り捨て)を記録する。

### 3.10 調査結果を踏まえた方針の改訂(2026-10-05)

先行研究の調査(§3.7・§7)の結論: **骨格(ステップ末尾の射影 + 1 層
β = h²/4 + 活性集合 + 局所反復)は Firdaus & Behrens・NEOWAVE・SWASH が
実証済みの実用路線**で、変更しない。概念の新規性は主張しない(実用性
優先)。差別化しうるのは検出量 χ、減衰距離に基づく縁幅、通信回避の
固定回数 Chebyshev とビット再現性、ENC 格子と統合モデルへの組込み
だが、採否はいずれも実用性で決める。改訂は次の 5 点。

1. **通信回避ソルバは後回し**(§3.3・§3.9): 既存の並列層だけで
   Jacobi + 収束判定から始め、Phase 4c で計測してから入れる。
2. **検出量は χ(分散型)を既定、振幅型(Firdaus & Behrens 型)を
   比較用**(§3.7 の表)。理由は新規性でなく、背景流のある河川で
   河川全体が常時活性にならないこと。
3. **砕波スイッチは「なし」で先に検証する**(§5 Phase 6): ENCflow は
   運動量保存形移流(スキーム 3)で段波・跳水の速度を正しく出す。
   NEOWAVE も保存形移流で砕波を bore として扱う構成(明示的な砕波
   判定の要否は本文で要照合)。hybrid Boussinesq 系では H/NH 切替の
   安定性と格子依存が主要な難点と報告されているため、切替は「保存形
   移流 + NH で砕波が破綻する場合の保険」に格下げし、入れるなら SWASH
   型(∂η/∂t > α√(gh)。運用実績あり)。
4. **鉛直圧力分布は線形(β = h²/4)のまま**: 2 次分布(Jeschke et al.
   2017 / Firdaus)は Green–Naghdi 相当 ω² = gHk²/(1 + (kH)²/3) で
   O((kH)²) まで厳密だが、位相速度の誤差(厳密解 ω² = gk tanh kH
   との比)を概算すると

   | kH | 線形 1/(1+(kH)²/4) | 2 次 1/(1+(kH)²/3) |
   |---:|---:|---:|
   | 0.5 | +0.9% | −0.1% |
   | 1.0 | +2.5% | −0.1% |
   | 2.0 | +1.8% | −5.7% |
   | 3.0 | −3.7% | −13% |

   ソリトン分裂の後続波(kH 1〜2)では線形が劣らず、スカラー 1 個で
   済む。2 次分布は射影法で時間微分の曖昧さが出る(Firdaus et al.
   2025 が別形式で回避)ため、実用上の利点がない。
5. **動く底面(Phase 8)は Firdaus/Jeschke の定式を参照**: 彼らの主題が
   moving-bottom-generated waves なので、底面運動の源項
   w_b = ∂z_b/∂t + u·∇z_b の扱いは自前導出でなく彼らの式を ENC に移す。

**採らないもの**:

- 双曲型緩和(Escalante, Dumbser & Castro 2019; Muñoz-Moncayo &
  Ketcheson 2026): 反復も広いハロも不要で ENC の陽的構造に載るが、
  人工圧力波速で dt が 3〜10 分の 1 になり、統合モデルでは全プロセスが
  その dt を払う。活性領域だけサブサイクルすれば結局は反復法と同じ。
  引継ぎメモ §30 の判断と同じ。
- ネスト格子・AMR で NH 領域を限る(NEOWAVE・GeoClaw-Bouss): ENCflow は
  単一格子が方針(§0-2・§0-9)。活性集合がその代替。
- 引継ぎメモの RK 段内 NH・NH detector による RK 昇格・edge-local
  単一掃引: §2・§3.8 のとおり撤回のまま。

**変わらないこと**: §4 の D1(§0-5 の例外)と D2(反復ソルバの許容)は
依然として実装前に必要。D2 は既存ハロでの Jacobi から始めるので、
並列層の変更を伴わない形で判断できる。

## 4. 方針との整合と議論事項(実装前に決める)

- **D1. developer.md §0-5(水平は SWE+1 方程式拡散が上限)**: 1 層 NH は
  SWE に楕円型補正 1 本を加えるもので、上限を超える。研究用オプション
  として §0 に明示的な例外を追記する案:
  > 「分散性が本質の研究用途(河川遡上津波のソリトン分裂、地滑り津波の
  > 近地造波)に限り、SWE にセルスカラー 1 個の非静水圧補正(1 層。
  > 鉛直構造は β = h²/4 に抽象化)を重ねることを認める。既定は SWE、
  > 有効時以外はメモリ・CPU・通信ゼロ追加、無効時は既存 reference と
  > ビット一致を条件とする」
  鉛直を β に抽象化する点は方針 5 後半(鉛直は抽象化・概念化)と整合する。
- **D2. 反復ソルバの許容(設計プラン §21 の改定)**: 「MPI の全体反復
  ソルバが必要なら中止」を「セルスカラー 1 個、Jacobi/CG、決定的総和、
  NH OFF でゼロ追加、を満たす反復は可」に改める。活性集合(§3.7)を
  使えば反復の対象は「検出した小領域」で、§21 が懸念した全格子の
  反復ではない。これを認めない場合の
  代替は陽的 1 項補正 (a)(Δx ≈ H の粗い格子で kH ≲ 1 に限って使える
  部分補正)しかなく、§2.3 の解像度要件と両立しないため、**NH 機能
  自体を見送る**判断になる。
- **D3. 補正の時点**: ステップ末尾(本提案)で合意するか。RK 段内に
  入れる案は反復解と両立しない。
- **D4. パラメータ**: list_enc に f_nonhydrostatic(0/1)、nh_hmin(m)、
  nh_solver(1 Jacobi 収束判定(既定・Phase 4)/ 2 CG(比較用)/
  3 Chebyshev 固定回数(Phase 4c))、nh_itmax、nh_tol(1, 2 用)、
  nh_nsweep・nh_halo(3 用)、適応化の f_nh_adaptive、nh_detector、
  nh_chi_on、nh_chi_off、nh_margin(§3.7)。Phase 6 で
  f_nh_breaking、nh_break_alpha(0.6)、nh_break_beta(0.3)。既定値は
  "(default)" 表示(architecture.md §5-6)。
- **D5. Phase 1(静水圧 ENC の数値分散計測)を先に行う**(設計プラン
  §16・§22 Step 1)。NH の合否基準(位相速度誤差)の分母になり、
  §2.3 の解像度要件の実測根拠にもなる。コード変更は user_initial の
  ルーチン追加のみ。
- **D6. 海域マスク(sw)との関係**: 潮位強制セルを NH マスクに入れるか。
  V1 は除外(静水圧)を提案。地滑り津波の「解く海」(sw なし)は対象内。

---

## 5. 段階計画と合否基準

各段は CLAUDE.md の規律(reference 不更新、無効時ビット一致、MPI
np=1,2,4 ULP=0、確保に触れたら -fcheck=all np≥2 先行、等価変換と
挙動変更のコミット分離)で閉じる。

| 段 | 内容 | 合否基準 | 目安 |
|---|---|---|---|
| 0 | 本書の議論(D1〜D6)。developer.md §0 と本書の改定 | 合意 | — |
| 1 | **静水圧 ENC の数値分散計測**。test/nhwave: 閉じた正方水槽(平坦・無摩擦)の定在波。user_initial に "wave_standing"(モード (1,0) と (1,1) = 0° と 45° を壁の階段化なしに得る)。L 固定で h0 を変えて kH を走査(kΔx も変わる)。プローブ時系列から周期を測り c_num/c を kΔx・方向・dt・適応 RK・hcap 別に表にする。ENC 8 近傍の Λ(k_x, k_y) の閉形式を導出し比較 | 表と図(test/ 内の python。計算本体外)。reference は Log 列 | 1〜2 セッション |
| 2 | **等価リファクタ**: edge_depth() の切り出し(§3.6)。必要なら uv0 複製の置き場 | 全 reference ULP=0、np=1,2,4 | 0.5 |
| 3 | **骨組み**: m_swflow_enc_nh(nh_init/prepare/project/dispose の interface)、list_enc 項目、NH マスク、nh_project は a* の集計と φ=0 のまま(補正ゼロ)。**並列層は無変更** | f_nonhydrostatic=0 で全 13 reference ULP=0・np=1,2,4。-fcheck=all np=2 | 1 |
| 4 | **V1 ソルバ**: Jacobi(既存の幅 2 ハロ交換+収束判定 allreduce。§3.3)→ 補正 → merge。Test 1(静水中の定在波、Phase 1 と同じ水槽) | 周期が ω² = gHΛ_ENC/(1+βΛ_ENC) に対し kH = 0.3〜2(Δx = H/4〜H/2)で 1% 以内(目標値。Phase 1 の時間誤差を差し引く)。振幅減衰、反復回数。スレッド数・np=1,2,4 のビット一致(-O2 厳密) | 2〜3 |
| 4b | **活性集合の適応化**(§3.7): 検出 χ(既定)と振幅型(nh_detector=2)、ヒステリシス、縁の膨張、活性セルだけの反復 | f_nh_adaptive=0 と比べた位相速度・振幅の差が縁幅 nh_margin で指数的に減ること(定在波・孤立波)。χ と振幅型の活性率の比較(静水中の波・一様流上の波・背景流のある河川)。χ の単一エッジ正規化と RMS 正規化の比較。活性率と壁時計の比例。np=1,2,4・スレッド数でビット一致 | 1〜2 |
| 4c | **通信回避(性能段階。§3.9)**: 実ケースで通信が律速と計測された場合のみ。並列層の幅指定つきセル交換、固定回数 Chebyshev + 幅 m ハロ | 幅指定交換は既存の幅 2 交換と同値(ULP=0)。固定回数版と収束判定版の差が nh_nsweep で指数的に減ること。ハロ幅 w(1 回交換と分割交換)でビット一致。np 増加時の壁時計 | 1〜2(必要時) |
| 5 | **非線形**: Test 3 孤立波(1 層理論の波形・波速。長い閉水路)、Test 2 一様流上の線形波(区間流入+放射境界 f_bc=2 で可能か要確認)、ソリトン分裂(棚への入射。文献との定性比較) | 波速・波形保存・振幅減衰の表 | 2〜3 |
| 6 | **退化・砕波(2026-10-05 改訂: スイッチなしで先に検証)**: (i) nh_hmin の乾湿退化。(ii) 砕波を**スイッチなし**で検証: 斜面に入射する孤立波の砕波・bore 化を保存形移流(スキーム 3)+ NH のまま走らせ、砕波位置・bore 速度・遡上高・格子依存を見る(静水圧 bore は test/dambreak で確認済み)。(iii) 破綻する場合だけ保険として砕波スイッチ(設計プラン §12: SWASH 型 ∂η/∂t > α√(gh)、二閾値、二重バッファ、8 近傍伝播)を入れる | f_nh_breaking=0 で Phase 4 と ULP=0。前線が走査順・ランク境界に依らない。切替の格子依存(Kazolea & Ricchiuto 2018 の難点)を 2 解像度で確認 | 2 |
| 7 | **V2**: 底面勾配項(w_b = u·∇z_b、−(2q/h)∇z_b)、浅水化・遡上(Synolakis 型の非砕波遡上) | 遡上高の文献比較 | 3+ |
| 8 | **動く底面**(bedslide との時間同期。設計プラン §15)。底面運動の源項は Firdaus & Behrens / Jeschke et al. の定式を ENC に移す(§3.10-5) | 地滑り津波例題の近地波形。Firdaus & Behrens の moving-bottom テストケースとの比較 | 2+ |

文書更新: developer.md に新 §(設計決定と理由、§0 の改定)、
comparison.md(非静水圧の行)、users_guide/swflow.md と params_index、
handoff.md の消し込み。

---

## 6. 理論課題(引継ぎメモ §36 の更新)

1. 「前進後退 Euler/適応 RK の静水圧 predictor + ステップ末尾射影」の
   完全離散の増幅行列と CFL(1 次元・一定水深・平坦床)。
2. ENC 8 近傍の Λ(k_x, k_y) の閉形式と異方性(p_diagratio 依存)。
   Phase 1 の計測と突き合わせる。
3. 一様流 U₀ 上の離散分散関係 (ω − U₀k)² と、RK 内移流固定の位相誤差の
   定量化(引継ぎメモ §20)。
4. 変水深での β_i の非対称性の扱い(A/β_i を掛けた対称形で CG に
   載せる確認)と、NH マスク境界(φ = 0)での反射・不連続。
5. 砕波判定の Galilean 不変性(設計プラン §12.11〜12.12)。
6. Jacobi / 赤黒 SOR / CG の決定性とコストの比較(赤黒 SOR も色内で
   順序不変なので候補)。
7. V2 の底面勾配項の ENC 離散化と、g cos²θ 補正との二重計上回避。
8. 活性集合の縁(φ = 0 の Dirichlet)での切り捨て誤差の見積もり
   exp(−2·縁幅/H) の検証と、縁が波面を横切るときの反射の有無。
   検出量 χ の正規化(単一エッジ / RMS。引継ぎメモ §36-4 を継承)。
9. 固定回数 Chebyshev の ρ の見積もり(活性領域の最大水深からの
   上限)と、変水深で ε が場所により大きく違うときの収束の一様性。
   ハロ幅 w < m の分割交換が結果を変えないこと(理論上は同値)。
10. 線形圧力分布(1 + (kH)²/4)と 2 次分布(1 + (kH)²/3)の位相速度
    誤差の比較(§3.10-4 の表)を、ENC の離散 Λ を含めて再評価する。
    保存形移流 + NH で砕波を bore に移行させられる条件(スイッチなし
    の成立範囲)。

引継ぎメモ §36 の 5(混合 Euler/RK/RK+NH 界面)、6・7(処理順序・
対称掃引)は本提案では消え、4(detector の正規化)は上記 8 に移る。

---

## 7. 参考(要文献照合。§19.8 の原則)

- Stelling, G. & Zijlema, M. (2003) An accurate and efficient
  finite-difference algorithm for non-hydrostatic free-surface flow with
  application to wave propagation. IJNMF 43:1–23(Keller-box、1 層で
  ω² = gHk²/(1+(kH)²/4))。
- Zijlema, M., Stelling, G. & Smit, P. (2011) SWASH. Coastal Eng.
  58:992–1012。砕波の α = 0.6, β = 0.3(Smit et al. 2013 Coastal Eng.)。
- Yamazaki, Y., Kowalik, Z. & Cheung, K.F. (2009) Depth-integrated,
  non-hydrostatic model for wave breaking and run-up. IJNMF 61:473–497
  (NEOWAVE。1 層・スタガード・保存形移流+ステップ末尾の圧力補正
  = 本提案と同じ構成。ENC は 8 近傍である点が違う)。
- Yamazaki, Y., Cheung, K.F. & Kowalik, Z. (2011) Depth-integrated,
  non-hydrostatic model with grid nesting for tsunami generation,
  propagation, and run-up. IJNMF 67:2081–2107。
- Stelling, G.S. & Duinmeijer, S.P.A. (2003) IJNMF 43:1329(保存形移流。
  既に §68.6 で採用)。
- Berger, M.J. & LeVeque, R.J. (2024) Implicit adaptive mesh refinement for
  dispersive tsunami propagation. SIAM J. Sci. Comput.(GeoClaw-Bouss。
  §3.7 の「必要な領域だけ楕円型を解く」実装例)。
- Tonelli, M. & Petti, M. (2009) Hybrid finite volume – finite difference
  scheme for 2DH improved Boussinesq equations. Coastal Eng. 56:609–620
  (局所切替の hybrid Boussinesq/NSWE)。
- Kazolea, M., Delis, A.I. & Synolakis, C.E. (2014) Numerical treatment of
  wave breaking on unstructured finite volume approximations for extended
  Boussinesq-type equations. J. Comput. Phys. 271:281–305。
- Shi, F., Kirby, J.T., Harris, J.C., Geiman, J.D. & Grilli, S.T. (2012)
  A high-order adaptive time-stepping TVD solver for Boussinesq modeling
  of breaking waves and coastal inundation. Ocean Modelling 43–44:36–51
  (FUNWAVE-TVD)。
- Firdaus, K. & Behrens, J. (2026) Locally Adaptive Non-Hydrostatic
  Shallow Water Extension for Moving Bottom-Generated Waves. Int. J.
  Numer. Meth. Fluids, doi:10.1002/fld.70021(arXiv 2505.17025)。
- Firdaus, K. & Behrens, J. (2026) Two-Dimensional Locally Adaptive
  Non-Hydrostatic Extension of Shallow Water Equations. arXiv 2606.27562。
- Firdaus, K. et al. (2025) Non-Hydrostatic Model for Simulating Moving
  Bottom-Generated Waves: A Shallow Water Extension With Quadratic
  Vertical Pressure Profile. Int. J. Numer. Meth. Fluids,
  doi:10.1002/fld.5393。
- Jeschke, A., Pedersen, G.K., Vater, S. & Behrens, J. (2017)
  Depth-averaged non-hydrostatic extension for shallow water equations
  with quadratic vertical pressure profile: equivalence to
  Boussinesq-type equations. Int. J. Numer. Meth. Fluids 84:569–583。
- Kazolea, M. & Ricchiuto, M. (2018) On wave breaking for Boussinesq-type
  models. Ocean Modelling 123:16–39。
- Tissier, M., Bonneton, P., Marche, F., Chazel, F. & Lannes, D. (2012)
  A new approach to handle wave breaking in fully non-linear Boussinesq
  models. Coastal Eng. 67:54–66。
- Escalante, C., Dumbser, M. & Castro, M.J. (2019) An efficient hyperbolic
  relaxation system for dispersive non-hydrostatic water waves and its
  solution with high order discontinuous Galerkin schemes. J. Comput.
  Phys. 394:385–416(双曲型緩和。不採用の根拠 §3.10)。
- Muñoz-Moncayo, C. & Ketcheson, D.I. (2026) Adaptive, efficient, and
  scalable water wave modeling with dispersive hyperbolic systems. arXiv
  2606.12162(GeoClaw 上の双曲型緩和 + AMR。同上)。
