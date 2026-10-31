# ENCflow アーキテクチャの地図 (architecture.md)

初めてこのコードベースに触れる開発者(人間・AI とも)が、最初の
1 時間で全体像をつかむための案内図です。**設計判断の理由と経緯の
正本は developer.md**、**変更時の検証規律は CLAUDE.md** にあり、
この文書は「何がどこにあり、どの順で動くか」だけを一枚にまとめます。
記述が食い違う場合はコードと developer.md が正です。

## 1. レイヤ構造(どのモジュールがどの層か)

```
main.f90 ─ m_main.f90(組み立て・時間ループ・終了処理。複数インスタンス encs(:) と
  │          ネスト系の時間進行 nest_advance。§71・§72)
  ├─ m_nest(多段ネスティング: 格子木・幾何・親の窓の写し・子の帯の Dirichlet。
  │          状態は持たず各格子の t_encflow を参照して交換する。fn_nest で有効化。§72。
  │          BMI では格子 = grid id、変数名の object 部に ~grid<id>。§73)
  ├─ 物理プロセス層(fn_* で個別に有効化。無効ならコスト・メモリゼロ)
  │    m_swflow      浅水流の切替器(排他: m_swflow_enc / m_swflow_stg)
  │      m_swflow_enc + submodule: _adv(移流) _bc(境界) _channel(河道・堤防) _diff(拡散)
  │                     _nh(1 層非静水圧補正。f_nonhydrostatic。静水圧ステップを predictor に
  │                         した射影。活性集合・砕波スイッチ・底面勾配項・動く底面の加速度項
  │                         f_nh_bottom を含む。状態・ソルバ・診断は submodule 私有。§69)
  │    m_gwflow      地下水の切替器(鉛直は排他: bucket / greenampt。
  │                  加算: lateral / layer2 / conduit(管路連続体層)/
  │                  pump(井戸揚水シンク)/ frost(凍土の浸透抑制)/
  │                  bed(河床交換能 = 河道セルと地下水の交換の上限。§16.5))
  │    m_vzflow      鉛直不飽和浸透(VZ)流出(谷 2023。少数の共有参照柱の 1 次元
  │                  Richards = m_vzflow_column を全ランク冗長に解き、区画番号ラスタの
  │                  各セルの土層厚の深さで流束を読み出して区画で集約、出口セルか系外へ
  │                  直接排水。VZ 貯留は hg と別物。fn_vz。§87)
  │    m_geomorph    土砂・地形変化(加算: creep / fluvial / suspend / wash / splash / debris /
  │                  bedslide / bank(側岸侵食) / fines(河床細粒分の帳簿) / fixation(植生定着)/
  │                  rockfall(崩落と崖錐)/ wave(波浪による沿岸漂砂。fn_wave)/ wthr・uplift /
  │                  dissol / rockinc(流水による岩盤下刻)/ wfsed(沿岸の波浪場による掃流砂・
  │                  浮遊砂の攪拌と、Euler 平均流速・岸向きの速度での輸送。f_wfsed。§90)/
  │                  wfswash(遡上域の輸送 = 汀線の面の経験式。f_wfswash。§90.21)。
  │                  debris は土石流・地滑り・火山流動の抵抗則/E-D 切替を含む。
  │                  bedslide は z・sd の内数として動く底層 hb = 地滑り津波の移動海底源。
  │                  dissol は石灰岩の溶食 = 土砂を出さない z 低下。rockinc は岩盤面 z − sd を
  │                  下げ剥離物を sd へ(§89)。creep は既定で z の線形拡散、creep_hstar > 0 で
  │                  土層だけが動く深さ依存クリープ(§89.8))
  │    m_driftwood   流木(材積のラスタ場3台帳: 立木 wst → 流動 s%hd → 堆積 s%wd。
  │                  発生・停止・再流動を担う。移流は swflow_enc の advect_scalar)
  │    m_bldgdebris  家屋破壊・瓦礫(家屋ストック wbs → 流動 s%hbd → 堆積 s%wbd。
  │                  破壊判定(浸水深/荷重に流木・瓦礫を算入)・停止・再流動と
  │                  空隙率 s%gv への帰還。移流は advect_scalar。§63)
  │    m_glacier     氷河(加算: 質量収支(常時)/ flow / slide / ero / ava)
  │    m_lavaflow    溶岩流(噴火口ソース+Bingham 粘性重力流+固化→z。等温)
  │    m_bedmotion   規定底面運動(地盤変位の時刻歴 → z の増分。断層津波の発生。入力は
  │                  スナップショット表+累積変位ラスタ〔窓付き可〕、私有は前後 2 枚と
  │                  適用済み変位のみ。断層パラメータ→変位は前処理 utils/fault2disp。§70)
  │    m_intercept   降雨遮断(排他: fixed / initloss)
  │    m_precip      降水    m_evap  蒸発散    m_snow  積雪・融雪
  │    m_tide        潮位(海域マスクの海セルに z = η − hsea0・h = hsea0 を強制。§47)
  │    m_wavefield   沿岸の波浪場(代表周波数・方向ビンの位相平均エネルギー平衡。空間は 2 リンク
  │                  分解の風上法、方向空間は陰的な屈折。非定常/準定常の 2 モードを 1 つの Jacobi
  │                  型の核で。状態 E_m(f_wf_current = 1 では作用量 N_m)は私有、共有状態へは
  │                  診断量と、wf_flow >= 1 なら流れへの作用(外力・Stokes 輸送・波・流れの
  │                  摩擦の速さ。ローラーのエネルギー平衡を含む)を書く。浅水流は calc_kth_flux
  │                  でそれを読む(段 W2)。f_wf_current = 1 なら浅水流の流速を読んでドップラー・
  │                  流れによる屈折・阻止を入れる(段 W3)。geomorph の f_wfsed = 1(要求 s%wv_sed)
  │                  なら土砂への書き出し(平均波向・軌道の振幅・岸向きの速度 u_a)も書き、
  │                  掃流砂・浮遊砂がそれを読む(段 W4・W5)。swflow の wf_break_visc > 0
  │                  (要求 s%wv_visc)なら砕波による渦動粘性 ν_w を書き拡散項が足す、geomorph の
  │                  f_wfsed_turb = 1(要求 s%wv_turb)なら攪拌の速さに砕波の乱れを含める。
  │                  geomorph の f_wfswash = 1(要求 s%wv_swash)なら入射波の波高・周期を毎ステップ
  │                  その時刻の与件から渡し(時刻の関数 = 保存なし)、波高 wvh のハロも埋める。
  │                  fn_wavefield。§90)
  │    m_wq          水質    m_meteo 気象強制場・暦
  │    m_saltwater   淡塩2層(鋭利界面。地表塩水層+地下塩水 zone+海側境界)
  │    m_swi         土壌雨量指数(地上雨量を読むだけの純診断。物理場に書かない)
  │    m_boundary    境界条件族(辺・流入・水位・ソース)+ m_boundary_structure(ポンプ・カルバート・分水・ダム)
  │
  ├─ 共有状態・入出力層
  │    m_sysparam (p)  実行制御パラメータ      m_geoinfo (g)  地形・物性・マスク
  │    m_state (s)     時間発展する場の正本、save/restore、統計・画面表示
  │    m_record (r)    プローブ・フラックス測線  m_output      分布ファイル出力
  │
  ├─ namelist 読み込み層: list_*(ファイルを「読むだけ」。解釈・検証・
  │    導出は各 m_*_init が行う。developer.md §12 の層契約)
  │
  ├─ 並列層: m_parallel_serial / m_parallel_mpi
  │    (公開インターフェースは完全同一。#ifdef なし、Makefile が択一
  │     リンク。逐次版は同名手続きの no-op/直結実装。§2)
  │
  └─ 基盤層(どこからでも使う道具)
       m_fileio(text/bil 行列 I/O・RLE) m_restart(save/restore の集約+RLE。§83)
       m_geotiff + _codec + _inflate(自前 GeoTIFF)
       m_georef(座標参照)  m_ffactor(摩擦テーブル)  m_util / m_sysdep_util
       user_geoinfo / user_initial(理想化実験用フック)
```

依存の向きは常に「上から下」です。物理プロセス層どうしは互いを
use せず、共有状態 s・g・p を介してだけ結合します(結合点は §3)。

## 2. 実行の流れ

### 2.1 初期化(m_main_all。順序に依存があるものは矢印で明記)

```
par_init → sysparam → geoinfo(マスク全域読込 → 窓確定 → 実数ラスタの窓読み・前処理)
  → par_decomp_init(セル数重み付き帯分割)
  → geoinfo_scatter_coeffs(物性係数を rank0 から帯+ハロへ配布)
  → boundary → state(← geoinfo, boundary より後)
  → wq → record → precip → intercept → geomorph
  → driftwood(← geomorph より後: morfac 検査に s%geo_morfac を参照)
  → bldgdebris(← driftwood より後: s%dw_active・s%dw_sg を荷重の評価に参照)
  → gwflow
  → tide(← state より後・swflow より前)
  → saltwater(← gwflow より後: 層1側方の係数を参照。← tide より後: 海セルの
               初期塩水層を潮位適用後の h に揃える。§47.4)
  → swflow → meteo → evap(← meteo より後) → snow
  → glacier(← meteo・snow より後: 気温と涵養源が必須)
  → lavaflow(← geomorph より後: morfac=1 検査)
  → bedmotion(← state より後: restore 時刻の変位を適用済みとする)
  → swi(← 最後: 排他検査に他モジュールの fn_* を参照)
  → vzflow(← swi の後: 併用検査に他モジュールの fn_*、VZ セル・出口の検査に
            ゾーン2の全域マスクと境界の一覧を使う。土層厚は require_sd。§87)
  → wavefield(← swflow より後: 河道の幅・断面形の有無が確定。静的な波浪セルの判定に
               ゾーン2の全域マスク、地形時計に s%geo_morfac。STG・ネストは停止。
               wf_break_visc の要求 s%wv_visc と係数を読み ν_w の配列を確保する。
               ← geomorph より後: f_wfsed の要求 s%wv_sed と u_a の係数、f_wfsed_turb の
               要求 s%wv_turb、f_wfswash の要求 s%wv_swash を読み、土砂への書き出しの配列を
               確保する。§90)
  (ネスト時は子格子ごとに同じ列を繰り返し、nest_setup_child が親子の幾何・時間軸・
   再開の整合を検査する。§72)
  → output_init → geoinfo_band_shrink(マスク類・z を帯に縮小。g%gv/g%lm の帯は
                     state_init が s%gv/s%lm へ写した後なのでここで解放。§63.1)
  → run_main(時間ループ)
```

静的データは 3 ゾーンのライフサイクルを持ちます(§11):
初期化中はマスク類が全域配列・実数ラスタが窓形(領域マスクの窓±ハロ。
全域添字。§82)→ scatter/band_shrink を経て → 時間ループ中は帯配列。
「どの配列がどのゾーンで全域か」の正確な契約は §11 を参照。
時間変化しうる物性は「入力は g、時間ループの正本は s」の型で扱います
(標高 z と空隙率 gv・有効慣性係数 lm がその実例。gv を変えるのは
m_state_set_gv だけで、空隙面積基底の柱状量を再スケールして体積を
保存する。§63.1)。

### 2.2 1 タイムステップ(run_main。この順序が結合の正本)

```
updatetime                    時刻更新
BMI 外部状態の適用            set_value された z / h の一回適用(§57。陸セルのみ・e 回復・
                                z ハロ交換。運動量は触らない)、続いて hg / swe の一回適用
                                (§76。陸セルのみ。hg はハロ交換まで。所有モジュールの calc の前)、
                                続いて粗度 rn の一回適用(§77。P 区分 = 物性係数の外部上書き。
                                有効セル全体・g%rn のハロ交換まで。時間ループで g を書く唯一の箇所)
bedmotion_calc                規定底面運動(ステップ末尾時刻の変位を補間し増分を s%z へ。
                                h 不変・e 回復・z ハロ交換。上と同じ契約・同じ位置 = swflow
                                の前。無効なら no-op。§70)
precip_makepre                降水分布の更新(更新時のみ)
  └ intercept_calc            遮断による有効雨量化(降水更新時のみ)
intercept_step                貯留型遮断の毎ステップ処理
snow_calc                     降雪/融雪(swe ⇄ h)
swi_calc                      土壌雨量指数(遮断後の地上雨量 s%pre を読む純診断)
glacier_calc                  氷河(毎ステップ: 氷面融解 hi → h。dt_glacier 間隔:
                                雪崩→氷化→SIA 流動→氷河侵食。侵食時は s%z / s%sd の
                                更新と e 回復・z のハロ交換まで済ませる)
boundary_makebdc              境界条件値の準備
tide_calc                     潮位(海域セルの水位強制)
wavefield_calc                沿岸の波浪場(非定常は毎ステップ、準定常は dt_wave ごと。前ステップ
                                確定の s%h をハロ交換して読み、共有状態へ診断量 s%wvh・wvdir・
                                wvub・wvdw を書く。wf_flow >= 1 なら外力 s%wvfx・wvfy、Stokes 輸送
                                wvus・wvvs、ローラー wver と、毎ステップ摩擦の速さ wvsp(前ステップ
                                確定の u・v から)・立ち上げの係数 wv_ramp も。f_wf_current = 1 なら
                                更新ごとに前ステップ確定の u・v(ハロ交換)でビンごとの分散関係・
                                輸送の分解・屈折速度を求め直す。wf_break_visc > 0 なら更新ごとに
                                砕波による渦動粘性 s%wvnub(帯±ハロ)、f_wfsed_turb = 1 なら攪拌の
                                速さ s%wvub と u_rms・k_b(wvub0・wvkb)も。f_wfswash = 1 なら毎ステップ
                                入射波の s%wv_hinc・wv_tinc。swflow_calc より前。
                                無効なら no-op。§90)
swflow_calc                   ★浅水流本体(移流・拡散 → 運動方程式 → 境界強制 →
                                [nh_project: 1 層 NH 射影で全加速度を補正。NH ON のみ] →
                                連続式 → h,e,u,v,m,n 確定。§69)
  └ par_allreduce_maxi(ierror) 発散検出の全ランク集約
vzflow_calc                   VZ セルに入った雨(pre·dt/gv)を s%h から回収し、dt_vz ごとに
                                共有参照柱を進めて区画の排水を出口セルの s%h へ(e 回復まで)。
                                地下水と同じ「swflow の後に s%h から取る」結合。無効なら no-op。§87
gwflow_calc                   地下浸透・地下水(s%h から s%hg/s%hgc へ。冒頭で凍土係数の更新、末尾で井戸揚水シンク)
saltwater_calc                淡塩2層(地表—地下の交換の淡塩配分・地表重力流・地下塩水 zone・海側境界)
wq_calc                       水質(発生源・浸透/湧出/ため池の同伴・Kd 分配・沈降・
                              ダム完全混合プール。移流本体は swflow_calc・地下横輸送は
                              gwflow_calc 内)
evap_calc                     蒸発散(h・遮断貯留・hg からの蒸発)
swflow_post                   ステップ確定処理(σ・河道幅有効時の u,v 正規化)
wq_derive                     導出濃度場の更新(確定 h に対して)
geomorph_calc                 地形変化(s%z, s%e 更新+z のハロ交換)
driftwood_calc                流木(発生・停止・再流動・ダム捕捉。← geomorph の後 =
                                同一ステップの z 更新を見た侵食連行。移流自体は
                                swflow_calc 内の advect_scalar が hs/cq と同様に実行)
bldgdebris_calc               家屋破壊・瓦礫(破壊・停止・再流動・ダム捕捉・空隙率の
                                帰還+gv/lm のハロ交換。← driftwood の後 = 同一ステップの
                                hd を荷重に見る。移流は swflow_calc 内)
lavaflow_calc                 溶岩流(噴火口ソース→Bingham 拡散流動→固化。固化時は
                                s%z 更新と e 回復・ハロ交換まで。z 更新プロセスの末尾)
calcstat                      統計(S 台帳・max 類。決定的総和)
表示・ファイル出力・計測      (collective 判定は全ランク同一に)
エラー判定                    CFL 超過等。全ランクで同一判定・同時 exit
```

終了処理は各モジュールの dispose を初期化の逆順で呼びます。
**モジュール私有状態の save は dispose 内**で行うのが契約です
(m_state の save より先に走る。§7・契約5)。

## 3. 状態の所有(誰が何を書いてよいか)

| 記号 | 型 | 所有者 | 内容と規約 |
|---|---|---|---|
| p | t_sysparam | m_sysparam | 実行制御。init 後は全モジュール読み取り専用 |
| g | t_geoinfo | m_geoinfo | 地形 z(入力)・粗度 rn・家屋 gv/bb/lm(入力)・マスク x/sw/rw・格子。原則不変(動的な標高は s%z、動的な空隙率は s%gv/s%lm。g%gv/g%lm の帯は band_shrink で解放)。例外は BMI の P 区分: set_value('rn') が g%rn の帯を上書きする(§77) |
| s | t_state | m_state | **時間発展する場の正本**: h, e(=z+h), u, v, m, n, vv, s%z(計算標高), sd(土層厚), hg(地下貯留), hg2(風化基岩層), hgc(管路連続体層), hss/hgs(塩水層厚), hs(土砂), hb(動く底層。z・sd の内数), sf(河床の細粒分の厚さ), fx(植生定着度), ht(崖錐の厚さ), cq/cg/crs(輸送物質の地表・地下・ため池プール), hd/wd(流動・堆積流木), hbd/wbd(流動・堆積瓦礫), gv/lm(空隙率と有効慣性係数。§63), swe(積雪), hi(氷河の氷厚), hl(溶岩厚), hrs(ため池), vzp/vzstore(VZ の台帳 = 回収済み未同期の雨と区画の VZ 貯留の総和。柱の状態 ψ は t_vzflow 私有。§87)、wvh/wvdir/wvub/wvdw(沿岸の波浪場の診断量 = 波高・平均波向・軌道流速・砕波散逸。方向ビンの状態 E_m(流れの作用ありは作用量 N_m)は t_wavefield 私有。§90)、wvfx/wvfy・wvus/wvvs・wvsp・wver(波→流れ = 外力・Stokes 輸送・波・流れの摩擦の速さ・ローラーのエネルギー。y 成分は流れと同じく南が正。wf_flow >= 1 のときだけ確保。§90)、wvex/wvey・wvae・wvua(波→土砂 = 平均波向の単位ベクトル・軌道の振幅・岸向きの速度。geomorph の f_wfsed = 1 の要求 wv_sed のときだけ m_wavefield が確保して帯±ハロを書く)・wvnub(砕波による渦動粘性 ν_w。swflow の wf_break_visc > 0 の要求 wv_visc のときだけ)・wvub0/wvkb(乱れを含まない u_rms と底面の乱れ k_b。geomorph の f_wfsed_turb = 1 の要求 wv_turb のときだけ。このとき wvub は攪拌の速さ)・sqbx/sqby・sqsx/sqsy(漂砂の推定。m_geomorph が帯に書く。§90)、最大値統計。save/restore は m_state が束ねる(hg2・swe・hi・hb・VZ の柱等のモジュール私有 save は各 dispose。契約5) |
| sx | t_enc_status | m_swflow_enc 私有 | エッジ流速 uv・流量 mn(前ステップ確定)・mn1(更新中)。他モジュールから不可視。NH の状態(圧力 φ・活性集合・砕波状態・zprev 等)も submodule 私有で、リスタート保存なし(φ は現在状態から再構築。f_nh_bottom の z̈ だけ再開直後の 1 ステップが異なる。§69) |
| r, b, … | 各 t_* | 各モジュール | モジュール私有。各過程の作業台帳・サブモデルの状態も `t_*` の成分として持つ(モジュール変数に状態を置くのは m_swflow_enc 系(7 つの変数群 opt/nhp/bcs/dbr/chn/sct/geo と submodule の私有状態)・m_ffactor・dcp だけで、これらは複数インスタンス時に `*_ctx_swap` で枠へ退避・復帰する。§71)。リスタートは各自の save ファイル(契約5)。例外: m_bedmotion は私有 save を持たず、再開時刻の変位を表から求めて「適用済み」とする(§70) |

プロセス間の結合は「s のフィールドを決まった順序で読み書きする」
ことだけで成立しています。たとえば地下水と浅水流は互いを知らず、
gwflow_calc が swflow_calc の後に s%h を減らし s%hg を増やす、という
**実行順序が結合仕様**です(§2.2 の順序を変えることは物理の変更)。
s%h を変更するモジュールは同じループで s%e = s%z + s%h を回復する
こと(反対称適用・柱状換算などの契約 5 箇条は m_gwflow_bucket の
ヘッダが正本の見本)。s%z を書くのは geomorph・glacier・lavaflow・
bedmotion と BMI の set_value('z') だけで、いずれも「h 不変で e を回復し
z のハロ交換まで済ませる」同じ契約に従います。増分で与える bedmotion は
他の z 更新と同じランで衝突しませんが、set_value('z') は bedmotion 有効時に
拒否します(z の外部生産者は一人。§70)。BMI の変数表は動的で、機能に依存する
状態量(hg・swe・sd・hs・cqc・hi・hl)は「その量を生産するプロセスが有効な
格子」にだけ載ります(m_main の var_state が正本。§76)。

**海域マスクの海セル(g%sw > 0)は「解かない・水位を強制する」セル**です(§23.1):
z は読み込みで 0 に強制され、fn_tide があれば m_tide が毎更新で z・h を書き、
なければ初期条件の h のまま動かない。浅水流・地下水・地形変化・各輸送は海セルを
計算対象から除き、海セルへ出た量(水・土砂・流木・瓦礫・水質)は系外へ消える
(台帳に列はない)。統計 S・最大値も海セルを除く。境界セル・構造物セル・ネストの
帯と置換対象には海セルを置けず、初期化で停止する。「解く海」は海域マスクを
使わず、海底地形と f_htype = 2 の通常セルで表す。河口・海岸堤防・機場の吐口の
海側の表し方は users_guide/tide.md と usecases.md。

## 4. 並列化の型(なぜランク数でビット一致するか)

- **j 方向の帯分割**。dcp%js/je = 担当帯、jsh/jeh = 確保範囲(帯±ハロ2。
  逐次版も同じ規則で、帯 = 全域窓)。列は ish/ieh(§80)。
  計算は js..je、全域窓端の縮小は `max(js, jw1+1)..min(je, jw2-1)` 定型(§11)。
  全域窓 jw1/jw2(= g%wy)は領域マスクから求めた行範囲(有効セルの行±1)、
  行ごとの列範囲は g%wx。時間ループの走査・帯分割・総和はこの窓の中だけで、
  全域格子に小さなマスクを置いても毎ステップの負荷は窓の面積に比例する
  (§79。エッジ配列の行コピーや動的開口表の構築も窓に限る)。
- ハロ交換は par_halo_cell(セル場)等。エッジ場はステップ頭に交換済みの
  前ステップ確定値(無印)だけを読む(§7・§8 のバッファ規約)。
- **総和は par_sum_rows**: 全域窓の行部分和を j 昇順に並べて一括総和する
  ため、ランク数・スレッド数によらず結果がビット一致します。max・整数和は
  順序不変なので allreduce 可(§11)。
- collective(gather/reduce/halo)の実行判定は必ず全ランクで同一に。
  is_root ガードの内側に collective を置かない(§5)。
- 帯確保の配列を渡すダミー引数は assumed-shape+下限指定
  (`a(dcp%ish:, dcp%jsh:)`)。明示形状は行ずれ実バグの元(§12)。
- 列の確保範囲 `dcp%ish/ieh` = マスクの列窓±ハロ(x は分割しないので全ランク
  同一。番兵つき配列は ish−1..ieh+1、エッジ配列は ish−1..ieh)。全域バッファ
  (出力・save)との受け渡しは gather/scatter が窓形の一時で橋渡しする(§80)。

## 5. 機能追加の型(新しいモジュールを書く人へ)

1. **有効化は fn_\* の有無**。"" = 無効(メモリ・CPU 追加ゼロ)、
   "-" = 同じパラメータファイルから読む、ファイル名 = 別ファイル。
2. 排他切替のモデル群(浅水流・地下水鉛直・遮断)は**切替器モジュール+
   手続きポインタ成分**(t_swflow の init/calc/post/dispose が見本)。
   加算的なプロセス群(geomorph の各過程)は**独立フラグの重ね合わせ**。
3. list_* には namelist を読むコードだけを書く。範囲検査・単位換算・
   導出は m_*_init で(§12)。
4. 実装契約(反対称フラックス・e の回復・owner-compute・柱状換算・
   私有 save)は m_gwflow_bucket のヘッダ 5 箇条に従う。
5. 検証は CLAUDE.md の規律で: 等価変換 = ULP=0、機能追加 = 無効時に
   既存 reference とビット一致、MPI に触れたら np=1,2,4 一致、確保に
   触れたら -fcheck=all np≥2 を先に。reference の更新は人間の目視後のみ。
6. **物性・校正値には「とりあえず動かす」既定値を置き、採用した既定は
   実行開始時に "(default)" 付きで必ず表示する**(gm_param / dw_param /
   bd_param の型。§62・§50.6・§63.9)。与件そのもの(地形・崩壊深分布・
   建物の場所)は既定にしない。対になる閾値は「両方未指定で両方に既定、
   片方だけなら他方は無効」で明示を尊重する。

## 6. データの流れ(単位・形式の約束)

- 入力: namelist パラメータファイル+ dir_data 下のラスタ
  (text / bil+hdr / GeoTIFF。読み書きとも自前実装で外部ライブラリなし)。
  時刻歴ラスタ(規定底面運動)は「時刻 ファイル名 [窓]」の表で与える。
- 前処理ユーティリティ utils/ は本体の層ではなく libencflow.a をリンクする
  独立プログラム(fault2disp: 断層パラメータ→地盤変位の時刻歴〔Okada、
  経緯度・地理参照〕、rmdepress_river・calc_catchmentarea・lu2mask など)。
  公開インターフェースを変えたらトップレベル make で追随漏れを検出(§10)。
- 出力: result/ に分布(H0001 等+FILENUMBER.csv。領域マスク X0000 は
  常時出力 §44)、fluxes/・probes/ の CSV、Log.txt、パラメータ控え、
  save/(リスタート)。ParaView 可視化は後処理 utils/out2vtk(§43)。
- 座標・単位: 投影座標系のメートル、行順は北→南、セル番号は 1 スタート。
  計測の実座標指定は x 東向き・y 北向き(§36)。
- 物理量は SI(水深 m、流量 m³/s、降雨のみ慣用で mm/h)。

## 7. 迷子になったときの早見表

| 知りたいこと | 見る場所 |
|---|---|
| 設計判断の理由・経緯・実バグ | docs/developer.md(§0 方針 13 箇条から) |
| 変更時の検証手順・禁止事項 | CLAUDE.md |
| 未完了の作業・中期の道標 | docs/handoff.md |
| パラメータの意味(646 項目) | docs/users_guide/params_index.md と各章 |
| namelist の書き方の見本 | examples/List_samples/ |
| 使い方(利用者視点) | docs/users_guide.md・tutorials/・users_guide/usecases.md(現象→機能) |
| 前処理・後処理の道具 | utils/*/README.md(fault2disp・out2vtk 等) |
| 他モデルとの立ち位置 | docs/comparison.md |
| 個別機能の設計文書 | docs/*_plan.md(geomorph・debris・splash・glacier・boundary・geotiff・gwconduit・swi・driftwood・lava・landslide_tsunami・nonhydrostatic・bedmotion・bmi〔実装済み。設計解説と実績の記録として保持〕、delta〔河口デルタ形成の試行の記録。構成法・結果・機構の議論・他モデルとの対応〕、lake・wq_metal・xwindow・meander・wave・vz・mountain_stream・wavefield・landslide_dam〔検討メモ。meander = 蛇行発達・側岸侵食・流砂方向補正の段階計画、wave = 波浪による沿岸漂砂と攪拌(弧状・カスプ状デルタ)、vz = 谷(2023)の鉛直不飽和浸透(VZ)流出モデル = 共有参照柱の 1 次元 Richards。2026-10-26 合意・段階実装中、mountain_stream = 山地渓流の地形発達(流水による岩盤下刻・被覆・研磨と深さ依存クリープの段階計画。2026-10-27 合意・段階実装中)、wavefield = 沿岸の波浪場(代表周波数・方向分割の位相平均の作用量平衡)と波・流れ・土砂の連成。2026-10-27 合意・段階実装中、landslide_dam = 天然ダム例題(豪雨→斜面崩壊→天然ダム→決壊洪水)に要る連成の点検と追加機構の下書き。2026-10-29 起案・未合意・中断中〕)・channel_model.md。家屋破壊・瓦礫は plan を消し込み済みで developer.md §63 が正本。非静水圧は developer.md §69、規定底面運動は §70 が規約の正本 |
| 「まず動かしてみる」最小入力と型別の推奨値 | users_guide/geomorph.md・driftwood.md・bldgdebris.md・gwflow.md・forcing.md(遮断・蒸発散・積雪)・glacier.md・lavaflow.md の各「パターン別の推奨値」、wq.md「物質別の代表値」(根拠は developer.md §62・§50.6・§63.9・§64〜§67。共通ヘルパは m_util の param_default)。既定値を置かない章(浅水流・河道・境界・潮位・初期条件・地理情報の粗度・淡塩・SWI・構造物・計測・降雨)にも「とりあえず動かしてみる」最小入力と型別の目安表がある |
| モジュール実装の作法 | src/m_gwflow_bucket.f90 のヘッダ |
| ビルドの仕組み | make.inc・docs/install.md・§1/§3 |
