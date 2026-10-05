module m_swflow_enc
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo, zbank_min
  use m_boundary, only : t_boundary, e_struct_dam
  use m_state, only : t_state
  use m_ffactor, only : m_ffactor_init, m_ffactor_calc, m_ffactor_dispose
  use list_enc, only : t_list_enc, list_enc_read
  use list_channel, only : t_list_channel, list_channel_read
  use m_parallel, only : par_info, par_stop, dcp, is_root, &
                       par_halo_cell, par_halo_edge, par_edge_merge, &
                       par_gather_edge_to, par_scatter_edge, par_allreduce_sumi, &
                       par_gather_to, par_scatter_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_fileio, only : fileio_write_rle, fileio_read_rle
  use m_util, only : itoa
  implicit none
  private

  !--------------------------------------------------------------------
  ! パブリックルーチンとパブリック変数の宣言
  !--------------------------------------------------------------------
  public :: m_swflow_enc_init
  public :: m_swflow_enc_calc
  public :: m_swflow_enc_dispose
  public :: sblk                      ! 塞がり率(submodule の build_cwd が参照。同下)
  public :: is_wall                   ! 堤防壁の述語(submodule から参照。private だと
                                      !   gfortran の LTO でシンボル未解決になるため公開)
  public :: m_swflow_enc_set_debris   ! 土石流抵抗則の設定口(m_geomorph の
                                      ! init_debris が呼ぶ。swflow init より前)

  ! nvfortran の submodule バグ回避(TPR #27323 系)。修正され次第 private に戻す
  public :: f_advection_scheme
  public :: p_adv_upwind_index
  public :: n8x, n8y
  public :: have_width, have_frw, frw, wfrac   ! m_geomorph の掃流砂が読む(宣言部の注記参照)
  public :: have_fwd, fwd                      ! 同上(動的振り替えの表。§68.14)
  ! sect_* は submodule(enc_bc の水位規定変換)も呼ぶ。private のままだと
  ! gfortran がシンボルを局所化しリンク不能(§22 の実バグと同型)
  public :: sect_v, sect_hinv, sect_sigma
  public :: have_sect, sdep                    ! m_geomorph の浮遊砂 E-D が読む(濃度 hs/vh と湿潤幅率。§26)
  public :: m_swflow_enc_post            ! ステップ末尾の u,v 正規化パス(§26)
  public :: m_swflow_enc_sdep_update     ! 河床変動後の σ 遷移深さ D の更新(§26)
  public :: have_edge_flux, m_swflow_enc_edge_flux   ! 測線計測のエッジ流量の観測口
                                         ! (m_record 専用・読み取り専用。§24.1/§24.2)
  public :: swflow_vh                    ! 矩形換算水深 vh の照会(§26/§30。
                                         ! 水質の濃度換算 conc = cq/vh 用)
  public :: have_open_bc, bc_open_face         ! 開境界の面判定(m_geomorph の
                                               ! 開境界土砂フラックスが読む。読み取り専用)

  !--------------------------------------------------------------------
  ! モジュール内で共有される構造体と変数の宣言
  !--------------------------------------------------------------------
  ! 制御フラグとパラメータの宣言
  ! ---- システムのパラメータからセットする ---
  integer :: f_advection_term               ! 移流項の計算の有無
  integer :: f_pressure_term                ! 圧力項の計算の有無
  ! ---- ENCのパラメータファイルからセットする ---
  integer :: f_gravity_correction != 1       ! 重力の補正
  integer :: f_exflux_reduction != 1         ! reduction of excessive flux
  integer :: f_hcap_upwind != 1              ! セル境界水深 (0:両側平均, 1:上流側水深で頭打ち, 2:上流側水深)
  integer :: f_adaptive_runge != 1           ! 適応的ルンゲクッタ
  integer :: f_friction_fastmath != 0        ! 摩擦項計算の高速化
  integer :: f_advection_scheme             ! 移流項のスキーム (1: セル中心勾配 v1,
                                            !   2: 運動量保存形・1次風上, 3: 同+MUSCL。§68)
  integer :: f_rivermouth_drop              ! 河口から海へ段落ち強制
  integer :: f_opening_dynamic              ! 塞がれた開口の動的振り替え (0:なし, 1:河道
                                            !   セル間のエッジのみ, 2:全エッジ。§68.14)
  integer :: f_advection_donor              ! 運動量保存形移流の風上供給元の制限 (0:湿潤セル
                                            !   すべて, 1:河道セル間のエッジでは河道セルのみ。
                                            !   §68.18)
  integer :: f_dry_head_cap                 ! 乾燥セルへ向かうエッジ水深をエネルギー頭
                                            !   η + u_n²/2g − z_受け手 で頭打ち (0:なし, 1:有効。
                                            !   §68.16。水面+速度水頭より高い乾いた地盤へは
                                            !   流さず、流せないエッジの流速も 0 にする)
  integer :: f_bank_mode                    ! 堤防の水理モード(下の e_bank_*)
  integer :: f_diffusion_term               ! 拡散項の計算 (0:無効, 1:定数, 2:ゼロ方程式)
  ! 非静水圧(1 層 NH)補正(submodule m_swflow_enc_nh。docs/nonhydrostatic_plan.md)
  integer :: f_nonhydrostatic = 0           ! 0: 静水圧(既定), 1: 1 層 NH 補正
  real :: nh_hmin = 0.1                     ! NH を適用する最小水深 (m)
  integer :: nh_solver = 2                  ! 反復ソルバ (1: Jacobi, 2: CG(既定))
  integer :: nh_itmax = 500                 ! 反復回数の上限
  real :: nh_tol = 1.0e-6                   ! 相対収束判定
  integer :: f_nh_adaptive = 0              ! 活性集合 (0: マスク内全域, 1: 検出セル+縁)
  integer :: nh_detector = 1                ! 検出量 (1: 分散型 χ, 2: 絶対型 |βDa*|/g)
  real :: nh_chi_on = 0.06                  ! 検出の閾値
  integer :: nh_margin = 0                  ! 縁の幅(セル数。0: 2H/Δx から自動)
  real :: nh_amin = 1.0e-5                  ! 検出の下限 |βDa*| (m/s²)
  real :: nh_arel = 1.0e-3                  ! 検出の相対下限(領域最大の |βDa*| に対する比)
  integer :: f_nh_breaking = 0              ! 砕波スイッチ (0: なし, 1: ∂η/∂t > α√(gh) のセルを静水圧に)
  real :: nh_break_alpha = 0.6              ! 砕波開始の閾値 α
  real :: nh_break_beta = 0.3               ! 砕波前線の伝播の閾値 β
  integer :: nh_break_type = 3              ! 砕波の判定量 (1: ∂η/∂t, 2: フルード数, 3: 水面勾配)
  real :: nh_break_fr = 0.6                 ! フルード数判定の閾値
  real :: nh_break_slope = 0.3              ! 水面勾配判定の閾値
  integer :: nh_break_margin = 0            ! 砕波セルの縁の幅(セル数。0: 2H/Δx から自動)
  integer :: f_nh_slope = 0                 ! 底面勾配項 (0: Version 1 平坦床, 1: Version 2)
  logical :: nh_active = .false.            ! NH ON(init が f_nonhydrostatic から設定)
  real, allocatable :: nh_he(:,:,:)         ! momentum が面流束に使ったエッジ水深 he
                                            !   (1:4, 0:nx, jsh-1:jeh)。NH ON のときだけ確保。
                                            !   calc_kth_momentum が書き、nh_project が
                                            !   mn1 = uv·he の再構成に読む
  real :: p_diagratio != 2 / (2 + sqrt(2.))  ! ratio of diagonal component
  real :: p_adv_upwind_index != 0.0          ! upwind index of advection term
  real :: p_adprunge_thresh != 2.0           ! threshold of adaptive Runge-Kutta
  real :: p_diffusion_nu != 0.0              ! 拡散項の動粘性係数 (m2/s。モデル2では
                                            !   加算のバックグラウンド粘性)
  real :: p_diffusion_alpha != 0.41/6        ! ゼロ方程式モデルの係数 α (ν=ν0+α·u*·h)
  ! ---- 境界条件(t_boundary)からセットする ---
  ! 境界条件の私有状態(辺型・面型・基準水位等)は submodule
  ! m_swflow_enc_bc が保持する(bc_init が構築)。親には continuous /
  ! restore_uvmn のホットパスが読む判定フラグだけを置く
  logical :: have_open_bc = .false.         ! 開いた面(不透過でない)があるか
                                            !   (bc_init が設定。protected 不可:
                                            !   nvfortran は submodule のホスト結合を
                                            !   use 結合扱いし書き込みを拒否する。§13)

  ! 土石流モデルの結合(debris_plan.md §2.3-2.4)
  !   有効判定は s%debris_active(m_geomorph_init が設定)。パラメータは
  !   m_geomorph の init_debris が m_swflow_enc_set_debris で渡す
  !   (namelist の所有は list_geomorph。swflow init より前に呼ばれる契約)。
  !   運動量への hs 算入(重力・圧力項の水面 = z+h+hs、摩擦水深 = h+hs)は
  !   debris_active で常時、クーロン抵抗と降伏判定は db_res=1 のとき有効
  integer :: db_res = 0                     ! 抵抗則 (0:マニングのみ, 1:クーロン+マニング,
                                            !   2:江頭構成則, 3:高橋・中川1991,
                                            !   4:Voellmy, 5:一定停止応力)
  real :: db_tanphi = 0.0                   ! tan(内部摩擦角)
  real :: db_sgrav = 0.0                    ! 土粒子の水中比重 s
  real :: db_vstop = 0.0                    ! 降伏判定の速度閾値 (m/s)
  real :: db_cstar = 0.0                    ! 河床の充填濃度 C*(降伏応力の (C/C*)^{1/5})
  real :: db_cmin = 0.0                     ! 江頭層流則の濃度下限(未満はマニング)
  real :: db_d50v = 0.0                     ! 代表粒径 d (m)(層流則の (h/d)^{-2})
  real :: db_kcol = 0.0                     ! 前計算 k_d・(σ/ρ)・(1−e²)(層流則第2項)
  real :: db_mu = 0.0                       ! Voellmy 摩擦係数 μ(db_res=4)
  real :: db_xi = 0.0                       ! Voellmy 乱流係数 ξ (m/s²)(db_res=4)
  real :: db_tauy = 0.0                     ! 一定停止応力 τ_y (Pa)(db_res=5)
  real, parameter :: db_rhow = 1000.0       ! 清水密度 (kg/m³)(τ_y を加速度に落とす
                                            !   換算。混合密度 ρm = ρw(1+sC))
  ! 曲率項(developer.md §28.10。RAMMS: Fischer ら 2012 と同じ扱い)
  !   垂直応力に遠心加速度 a_c = uᵀHu/√(1+|∇z|²)(H = z の Hessian、u = セル
  !   流速ベクトル)を算入し、降伏項に倍率 max(0, 1 + a_c/g_n) を乗じる
  !   (g_n = 垂直方向の重力 = √(g・ge)。ge = g cos²θ の Ni 補正と整合)。
  !   凹(谷底・屈曲部外側)で減速、凸(遷急点・尾根)で摩擦低下。1+a_c/g_n<0
  !   (浮上条件)は 0 に切る。a_c はセルごとに時刻 n の u, v, z で前計算
  !   (curv_prepare。RK 内不変。hs と同じ近似)し、辺では両セルの平均。
  !   f_dbcurv=0 では配列未確保・パス未実行・aye 不変(ビット一致)
  integer :: db_curv = 0                    ! 曲率項の有無(f_dbcurv)
  real, allocatable :: acv(:,:)             ! セルの遠心加速度 a_c (m/s²)(1:nx, jsh:jeh)
  ! 江頭構成則の定数(原式固定。典拠: 江頭・芦田・矢島・高濱(1989)の
  ! 抵抗則 = 江頭(1993)講座 式(25)、Morpho2DH Solver Manual 式(17)(19)。
  ! k_f は 0.16〜0.25 の範囲が示されており Morpho2DH の 0.16 を採用)
  real, parameter :: db_kf = 0.16           ! 間隙流体の乱れの係数 k_f
  real, parameter :: db_kd = 0.0828         ! 粒子非弾性衝突の係数 k_d
  real, parameter :: db_yexp = 0.2          ! 降伏応力の指数 1/n(n=5。Morpho2DH 式(17))
  ! 高橋・中川(1991)新砂防 44(3) の定数(原式固定。db_res=3。式(22)-(25))
  real, parameter :: db_tana = 0.45         ! 石礫群の流動時の摩擦係数 tanα'
  real, parameter :: db_apr = 4.0           ! ダイラタント項の係数 A'
  real, parameter :: db_c49 = 0.49          ! 掃流状集合流動の抵抗係数(= 0.7²)
  real, parameter :: db_cbl = 0.4           ! 掃流状域の濃度閾値(C ≤ 0.4C*)
  real, parameter :: db_hdmud = 30.0        ! 泥流域の相対水深閾値(h/d ≥ 30 でマニング)

  ! 堤防(仮想壁面)モデル(developer.md §17)
  !   有効化は fn_channel の fn_bank / bank0 の有無(g%bank_active)。
  !   天端の絶対標高は geoinfo が河道セルごとに構築済み(g%zbank)。
  !   水理モード f_bank_mode は fn_channel の &list_channel から読む
  logical :: have_bank = .false.            ! 堤防天端が有効か
  ! セルの堤防壁エッジ本数(堰流量の追い越し禁止上限の分母。§68.29 (C')。
  ! have_bank のときだけ bank_init が帯+ハロで構築。状態は親、構築は submodule)
  integer, allocatable :: nwall(:,:)
  logical :: have_swall = .false.           ! 海岸堤防天端が有効か(§17 一般化)
  integer :: f_swall_mode = 0               ! 海岸堤防の水理モード(e_bank_* と同義)
  integer, parameter :: e_bank_weir = 0     ! 越流のみ(単純堤防): 双方向とも天端まで不透過
  integer, parameter :: e_bank_oneway = 1   ! 樋門(逆止弁): 堤内→河道のみ透過、逆は天端まで不透過
  integer, parameter :: e_bank_pump = 2     ! 強制排水: 堤内→河道は河道水位によらず常時段落ち

  ! 堤防時の開口補正(developer.md §18)
  !   壁で恒久的に塞がれた斜め開口の通過幅シェアを、同じ横断方向の
  !   河道—河道「法線」エッジ(成分2, 4)へ振り替える。直線の幅1セル
  !   河道で通過幅が法線開口(lp ≈ 0.414)に縮退する過小通水を治し、
  !   横断方向の開口合計は面全長で厳密に保存される。斜めエッジと
  !   壁エッジ(越流の敷幅)は不変。塞がりゼロのエッジは係数1で
  !   現行と厳密一致(退化性)。frw は init で構築する静的テーブルで、
  !   時間ループでは読み取り専用(w8mx 等の重み定数と同格の扱い)
  integer :: f_bank_opening                 ! 開口補正 (0:なし, 1:振り替え)
  logical :: have_bopen = .false.           ! 開口補正が有効か(have_bank との合成)

  ! サブグリッド河道幅(developer.md §18)
  !   河道幅 W(g%wrw。セル属性)から2つの静的補正を導く:
  !   (1) 通水: 河道—河道エッジの通過幅係数を min(W_e/面長, 1) 倍する
  !       (W_e = 両セルの正の幅の最小値。frw に開口補正と重畳)。
  !   (2) 貯留: セルの平面積率 wfrac = min(W·L_ch/(dx·dy), 1) で
  !       水深換算を除算補正する(gv と同じ意味論の水深依存なし版。
  !       L_ch = 河道隣接8近傍への半距離の総和)。
  !   W ≥ 面長・平面積率 1 のセルでは係数がちょうど 1 となり、
  !   解像河道(掘り込み+壁)の表現と厳密に一致する(退化性)。
  !   セル内の非河道部の貯留は表現しない(河道セルの水位=河道内水位)
  integer :: f_channel_advection            ! 河道セルを含むエッジの移流項 (1:通常, 0:落とす)
  ! have_width/have_frw/frw/wfrac は公開: m_geomorph の掃流砂が
  ! 「水と同じ開口・同じ貯留補正」で土砂を運ぶために読む(読み取り専用の
  ! 規約。書き手は本モジュールと submodule m_swflow_enc_channel のみ)。
  ! frw/wfrac に protected は付けられない: submodule 内の構築(allocate・
  ! 代入)を nvfortran がホスト結合でなく use 結合とみなし 0155 エラーに
  ! する(§13)。親モジュール本体だけが書く have_width/have_frw は
  ! protected を維持する
  logical, protected :: have_width = .false. ! サブグリッド河道幅が有効か(g%width_active)
  logical, protected :: have_frw = .false.  ! エッジ通過幅係数 frw が有効か
                                            !   (have_bopen または have_width)
  logical :: adv_drop_rw = .false.          ! 河道セルを含むエッジで移流項を落とすか
  real, allocatable :: frw(:,:,:)           ! エッジ別通過幅係数 (1:4, 0:nx, jsh-1:jeh)。
                                            !   開口補正は法線成分 2, 4 のみ、幅キャップは
                                            !   河道—河道の全成分に乗る
  real, allocatable :: wfrac(:,:)           ! セルの河道平面積率 (1:nx, jsh:jeh)。
                                            !   非河道・幅情報なしセルは 1
  ! 塞がれた開口の動的振り替え(developer.md §68.14)
  !   静的な frw(堤防壁)と同じ規則を、「隣接セルの地盤が水面より高い」
  !   ことで塞がれた開口に毎ステップ適用する。塞がり率
  !     s = clamp((z_n − z_c) / h_c, 0, 1)
  !   (z_n: 斜め先セルの地盤、z_c, h_c: 自セルの地盤と水深。領域外・無効
  !   セルは s = 1)は水位の連続関数で、平坦な開水面(z_n = z_c)では 0 =
  !   既存スキームと厳密一致。振り替え先は軸エッジ(成分 2, 4: lp → lp +
  !   nb·ld)と斜めエッジ(成分 1, 3: 自然幅 dx·dy/dr まで)で静的規則と同形。
  !   自然幅までの振り替えなので Σ w8mx·fw = 1 となり u, v の正規化は不要。
  !   表 fwd はステップ頭に h^n, z^n(ハロ幅 2)から各ランクが帯の必要
  !   エッジ行を冗長構築し、frw と同じ読取点で乗じる(frw と併用時は積。
  !   堤防壁で既に静的に振り替えた斜め先は数えない)。状態なし
  !   (リスタートでは復元した h から再構築 → restore_uvmn の u,v,m,n は
  !   保存時の値と最終桁で異なりうる。§68.14)
  logical :: have_fwd = .false.             ! 動的振り替えが有効か
  logical :: fwd_restored = .false.         ! 保存状態から fwd を復元したか(restore_state が設定)
  real, allocatable :: fwd(:,:,:)           ! 動的通過幅係数 (1:4, 0:nx, jsh-1:jeh)
  ! 破堤(developer.md §18。構築・更新は submodule m_swflow_enc_channel)
  !   サイト=セル対 (ic,jc)-(il,jl) で一意に決まるエッジ。実効天端を
  !   時系列 f(t)(1=天端高, 0=堤内地盤高)で変える:
  !     zeff(t) = zgnd0 + f(t)·(zcrest0 − zgnd0)
  !   f>=1 は zcrest0、f<=0 は zgnd0 に厳密固定=無破堤とのビット一致条件。
  !   履歴状態なし(t の純関数)のため save/restore 対象外。基準地盤
  !   zgnd0 は init 時の堤内地セルの s%z で静的(侵食に追従しない)。
  !   型と状態を親に置くのは frw/wfrac/cwx と同じ様式(submodule 内に
  !   置けない理由は §13 の classic flang 系不具合2件)
  logical :: have_breach = .false.          ! 破堤サイトがあるか(breach_init が設定)
  type t_breach
    integer :: ic = 0, jc = 0               ! 河道セル
    integer :: il = 0, jl = 0               ! 堤内地セル
    integer :: nval = 0                     ! 時系列データ数
    real, allocatable :: val(:,:)           ! 時系列 (1:2, 1:nval) = (s, 割合0〜1)
    real :: zcrest0 = 0.0                   ! 初期天端(セル対を帯内に持つランクのみ有効)
    real :: zgnd0 = 0.0                     ! 基準地盤(同上)
    real :: zeff = 0.0                      ! 現時刻の実効天端(breach_update が更新)
  end type
  integer :: nbr = 0                        ! 破堤サイト数
  type(t_breach), allocatable :: br(:)      ! サイトリスト(全ランク同一)
  ! 行バケット: 行 jc にあるサイトの並び ibrs(ibr0(jc):ibr1(jc))。
  ! bank_wall のゲート(サイトのない行は整数比較1回で素通り)
  integer, allocatable :: ibr0(:), ibr1(:)  ! (jsh:jeh)
  integer, allocatable :: ibrs(:)           ! 行順に整列したサイト番号

  ! 動的な通水率(壁なし幅モード = 幅 + 動的開口 fwd のとき。§68.32)。
  ! 非河道近傍のエッジを塞がり率 s(sblk。fwd と同じ)の重み (1 − s) で開口和に
  ! 入れる: 乾いて高い側方は壁と同値(除外)、湿った氾濫原は開いた面。静的
  ! cwx は乾いた側方を q = 1 で数えて希釈され、W < 自然幅のセル流速が過小に
  ! なっていた。ステップ頭に fwd と一緒に構築し、リスタート状態にも保存する
  ! (最終ステップの正規化が使った表を restore_uvmn が再現する条件)
  logical :: have_cwd = .false.
  logical :: cwd_restored = .false.
  real, allocatable :: cwxd(:,:), cwyd(:,:)   ! (1:nx, jsh:jeh)。使うのは js:je
  real, allocatable :: cwx(:,:), cwy(:,:)   ! セルの方向別通水率 (1:nx, js:je)。
                                            !   幅キャップによるセル開口の減衰率
                                            !   (キャップ後/キャップ前の開口和の比)。
                                            !   continuous / restore_uvmn が u,v を
                                            !   これで除算し、vv・摩擦・抗力・移流が
                                            !   河道内流速を見る。m,n は正規化しない
                                            !   (§18。フラックス測線の実流量の条件)

  ! ---- 河道断面形の一般化 σ(h) = (h/D)^m(§26)----
  ! sx%h1 は σ 有効時「矩形換算水深 vh = ∫σdh'」として運用する
  ! (真の体積 = vh×gv×wfrac×セル面積)。既存の加算式は無変更で、
  ! 変換は連続式開始時 sect_v とコミット時 sect_hinv に集約される。
  logical, parameter :: f_sect_rk = .true.  ! RK 内の仮水深更新で σ を再評価する
                                            !   (コンパイル時切替。.false. = RK 中は
                                            !    矩形近似=従来の加算式。コスト比較用。§26)
  logical :: have_sect = .false.            ! σ が有効か(p_sect_m>0 かつ遷移深さ源あり)
  logical, protected :: have_edge_flux = .false.  ! エッジ流量の観測口が使えるか
                                            ! (ENC の init 後 true。STG では false のまま。§24.2)
  real :: sect_m = 0.0                      ! 形状指数 m(0=矩形)
  real :: sect_mp1 = 1.0                    ! m+1(前計算)
  real :: sect_rmp1 = 1.0                   ! 1/(m+1)
  real :: sect_mfac = 0.0                   ! m/(m+1)
  real, parameter :: sect_sgmin = 0.01      ! σ の下限(乾燥近傍の感度増幅の抑制)
  ! σ 断面の天端標高(1:nx, jsh:jeh)。D(t) = screst − s%z(t) で、河床変動
  ! (geomorph・溶岩・外部 z)に D が追従する(§26 の 2026-10-04 改定)。静的
  ! データ(zbank または g%z + drw)から決まるため保存状態は不要(リスタート
  ! では build_sdep が復元した s%z から同じ D を再現)。非適用セルは screst_none
  real, allocatable :: screst(:,:)
  real, parameter :: screst_none = -1.0e30
  real, allocatable :: sdep(:,:)            ! 断面遷移深さ D (1:nx, jsh:jeh)。
                                            !   0 = σ 非適用セル(恒等写像)
  real, allocatable :: frw0(:,:,:)          ! 幅キャップ「前」の frw のコピー
                                            !   (σ 有効時のみ。cw_cell の h 依存
                                            !    再評価が静的 cwx/cwy と同じ比の
                                            !    分母・分子を作るための保存。§26)

  ! 状態変数の構造体の宣言と定義
  type t_enc_status
    real, allocatable :: uv(:,:,:)   ! セル境界での流速(符合は中心セルから近傍セルに向かい正)
    real, allocatable :: mn(:,:,:)   ! セル境界での流量(時刻n。ステップ中は読み取り専用)
    real, allocatable :: mn1(:,:,:)  ! セル境界での流量の書き込み先(時刻n+1。completeでmnへコミット)
    real, allocatable :: h1(:,:)     ! セル中心での計算済み水深
    real, allocatable :: hs1(:,:)    ! 浮遊砂柱状量の書き込み先(時刻n+1。completeでs%hsへ
                                     ! コミット。s%sed_active のときだけ確保)
    real, allocatable :: cq1(:,:)    ! 輸送物質柱状量の書き込み先(同上の意味論。
                                     ! s%wq_active のときだけ確保。§30)
    real, allocatable :: hss1(:,:)   ! 地表塩水層厚の書き込み先(同上の意味論。
                                     ! s%salt_active のときだけ確保。§47)
    real, allocatable :: hd1(:,:)    ! 流動流木柱状量の書き込み先(同上の意味論。
                                     ! s%dw_active のときだけ確保。§50)
    real, allocatable :: hbd1(:,:)   ! 流動瓦礫柱状量の書き込み先(同上の意味論。
                                     ! s%bd_active のときだけ確保。§63)
    logical :: initialized = .false.
  end type
  type(t_enc_status) :: sx_mod


  !--------------------------------------------------------------------
  ! モジュール内で共有される重み係数の定義
  !--------------------------------------------------------------------
  ! 中心セルから見たk近傍セルのインデックス
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]

  ! 中心セルから見たk近傍の境界フラックスのインデックス
  integer, parameter :: die(1:8) = [ -1,  0,  0, -1,  0, -1,  0,  0]
  integer, parameter :: dje(1:8) = [ -1, -1, -1,  0,  0,  0,  0,  0]

  ! 界面エッジ行の成分補完マスク(dje(1:4) = [-1,-1,-1,0] に対応)
  !   行 js-1: 南隣セル(j=js-1, dje=0)が書く成分 → k=4 を南から取る
  !   行 je  : 北隣セル(j=je+1, dje=-1)が書く成分 → k=1,2,3 を北から取る
  !   dje を変更する場合はここも必ず更新すること
  logical, parameter :: esync_s(1:4) = [.false., .false., .false., .true. ]
  logical, parameter :: esync_n(1:4) = [.true.,  .true.,  .true.,  .false.]

  ! 重み係数
  integer :: din2(1:8)           ! din(:)**2
  integer :: djn2(1:8)           ! djn(:)**2
  real :: w8x(1:8)               ! 勾配モデルの重み係数
  real :: w8y(1:8)               ! 勾配モデルの重み係数
  real :: w8dr(1:8)              ! 近傍セル中心までの距離
  real :: w8dr2(1:8)             ! 近傍セル中心までの距離の二乗
  real :: l8x(1:8)               ! k軸方向のフラックス通過幅の重み
  real :: l8y(1:8)               ! k軸方向のフラックス通過幅の重み
  real :: l8(1:8)                ! k軸方向のフラックス通過幅の重み
  logical :: skip8(1:8)          ! 通過幅ゼロのエッジ(p_diagratio=0/1 の対角・法線)
  real :: lpx, lpy, ldx, ldy     ! 通過幅シェア(法線 lp・斜め ld。開口補正が使う)
  real :: r8x(1:8)               ! din(:)/dx
  real :: r8y(1:8)               ! djn(:)/dy
  real :: n8x(1:8)               ! k軸の単位ベクトルのx方向成分
  real :: n8y(1:8)               ! k軸の単位ベクトルのy方向成分
  real :: w8mx(1:8)              ! k軸のフラックスからセル中心でのx方向平均量への寄与率
  real :: w8my(1:8)              ! k軸のフラックスからセル中心でのy方向平均量への寄与率
  real :: mn2dh(1:8)             ! k軸の単位幅流量から中心セルの水深減少量への変換係数


  interface
    module subroutine adv_init(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
    end subroutine
    module subroutine adv_prepare(p, g, s, sx)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
      type(t_enc_status), intent(in) :: sx
    end subroutine
    module function adv_edge(s, sx, i, j, k, in, jn, ie, je) result(ta)
      type(t_state), intent(in) :: s
      type(t_enc_status), intent(in) :: sx
      integer, intent(in) :: i, j, k, in, jn, ie, je
      real :: ta
    end function
    module subroutine adv_dispose()
    end subroutine
  end interface

  ! 拡散項の計算層(submodule m_swflow_enc_diff。developer.md §20)
  interface
    module subroutine diff_init(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
    end subroutine
    module subroutine diff_prepare(p, g, s)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
    end subroutine
    module function diff_edge(i, j, k, in, jn) result(td_e)
      integer, intent(in) :: i, j, k, in, jn
      real :: td_e
    end function
    module subroutine diff_dispose()
    end subroutine
  end interface

  ! 非静水圧補正 submodule(m_swflow_enc_nh)の分離インターフェース
  interface
    module subroutine nh_init(p, g, s)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
    end subroutine
    module subroutine nh_prepare(sx)
      type(t_enc_status), intent(in) :: sx
    end subroutine
    module subroutine nh_project(p, g, s, sx)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
      type(t_enc_status), intent(inout) :: sx
    end subroutine
    module subroutine nh_dispose()
    end subroutine
  end interface

  ! 境界条件の適用層(submodule m_swflow_enc_bc)
  interface
    module subroutine bc_init(p, g, b)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_boundary), intent(in) :: b
    end subroutine
    module subroutine boundary_h(p, g, b, s, sx)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_boundary), intent(in) :: b
      type(t_state), intent(inout) :: s
      type(t_enc_status), intent(inout) :: sx
    end subroutine
    module subroutine dam_apply(p, g, b, s, sx)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_boundary), intent(inout) :: b    ! ダム診断量を更新(§22)
      type(t_state), intent(inout) :: s
      type(t_enc_status), intent(inout) :: sx
    end subroutine
    module subroutine boundary_uvmn(p, g, b, s, sx)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_boundary), intent(in) :: b
      type(t_state), intent(in) :: s
      type(t_enc_status), intent(inout) :: sx
    end subroutine
    module function bc_open_face(in, jn) result(op)
      integer, intent(in) :: in, jn
      logical :: op
    end function
    module function bc_inflow_face(in, jn) result(r)
      integer, intent(in) :: in, jn
      logical :: r
    end function
    module subroutine bc_dispose()
    end subroutine
  end interface

  ! 河道水理モデルの構築・壁面適用層(submodule m_swflow_enc_channel)。
  ! 状態(frw/wfrac/cwx/cwy と有効フラグ)は親カーネルのホットパスが
  ! 読むため親に置き、submodule は構築と壁面上書きを担う(§18)
  interface
    module subroutine build_channel_frw(g)
      type(t_geoinfo), intent(in) :: g
    end subroutine
    module subroutine build_wfrac(g)
      type(t_geoinfo), intent(in) :: g
    end subroutine
    ! セル方向別通水率をスケール sig 付きで計算する(§26。sig=1 が静的
    ! cwx/cwy と厳密同値になるよう build_channel_frw と実装を共有)
    module subroutine build_cwd(g, s)
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
    end subroutine
    module subroutine cw_cell(g, i, j, sig, cx, cy)
      type(t_geoinfo), intent(in) :: g
      integer, intent(in) :: i, j
      real, intent(in) :: sig
      real, intent(out) :: cx, cy
    end subroutine
    module subroutine seawall_wall(p, g, s, i, j, in, jn, uve1, mne1)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
      integer, intent(in) :: i, j, in, jn
      real, intent(inout) :: uve1, mne1
    end subroutine

    module subroutine bank_wall(p, g, s, i, j, k, in, jn, uve1, mne1)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
      integer, intent(in) :: i, j, k, in, jn
      real, intent(inout) :: uve1, mne1
    end subroutine
    module subroutine bank_init(g)
      type(t_geoinfo), intent(in) :: g
    end subroutine
    module function chan_dir(g, i, j, ux, uy) result(ok)
      type(t_geoinfo), intent(in) :: g
      integer, intent(in) :: i, j
      real, intent(out) :: ux, uy
      logical :: ok
    end function
    module function bank_edge(g, s, i, j, in, jn) result(res)
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
      integer, intent(in) :: i, j, in, jn
      logical :: res
    end function
    module subroutine breach_init(p, g, s, ch)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
      type(t_list_channel), intent(in) :: ch
    end subroutine
    module subroutine breach_update(t)
      real, intent(in) :: t
    end subroutine
    module subroutine breach_dispose()
    end subroutine
  end interface

contains
 
!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! ENCの初期化
!----------------------------------------------------------------------
subroutine m_swflow_enc_init(p, g, b, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s
  type(t_list_enc) :: list
  type(t_list_channel) :: chlist



  ! ENCパラメータファイルを読み込む
  ! fn_enc 未指定なら既定値で続行(geoinfo/initial と異なり必須にしない)
  if (len_trim(p%fn_enc) > 0) call list_enc_read(p, list)

  f_gravity_correction = list%f_gravity_correction
  f_exflux_reduction = list%f_exflux_reduction
  f_hcap_upwind = list%f_hcap_upwind
  select case (f_hcap_upwind)
    case (0, 1)   ! なし / 上流側水深で頭打ち(既定)
    case (2)      ! 上流側水深そのもの(§68.7)
      call par_info("swflow_enc: f_hcap_upwind = 2 (edge depth = upwind cell depth)")
    case default
      call par_stop("list_enc: f_hcap_upwind must be 0(none), 1(cap by upwind depth) " // &
                    "or 2(upwind depth)")
  end select
  f_adaptive_runge = list%f_adaptive_runge
  f_friction_fastmath = list%f_friction_fastmath
  f_advection_scheme = list%f_advection_scheme
  f_opening_dynamic = list%f_opening_dynamic
  f_dry_head_cap = list%f_dry_head_cap
  f_advection_donor = list%f_advection_donor
  select case (f_advection_scheme)
    case (1)      ! セル中心勾配(v1。既定)
    case (2)      ! 運動量保存形(Stelling & Duinmeijer)・1次風上
      call par_info("swflow_enc: f_advection_scheme = 2 (momentum-conservative, 1st-order upwind)")
    case (3)      ! 運動量保存形+MUSCL(van Leer)
      call par_info("swflow_enc: f_advection_scheme = 3 (momentum-conservative, MUSCL van Leer)")
    case default
      call par_stop("list_enc: f_advection_scheme must be 1(cell-gradient), " // &
                    "2(momentum-conservative upwind) or 3(momentum-conservative MUSCL)")
  end select
  f_rivermouth_drop = list%f_rivermouth_drop
  f_diffusion_term = list%f_diffusion_term
  ! 河口の強制段落ちは潮位(fn_tide)と両立しない(高潮位時の背水を
  ! 無視して常時射流で流出させてしまう)。判定材料は namelist 由来で
  ! 全ランク同一(par_stop は collective 安全)
  if (f_rivermouth_drop > 0 .and. len_trim(p%fn_tide) > 0) then
    call par_stop("list_enc: f_rivermouth_drop cannot be used together with tide (fn_tide)")
  end if
  p_diagratio = list%p_diagratio
  p_adv_upwind_index = list%p_adv_upwind_index
  p_adprunge_thresh = list%p_adprunge_thresh
  p_diffusion_nu = list%p_diffusion_nu
  p_diffusion_alpha = list%p_diffusion_alpha
  f_nonhydrostatic = list%f_nonhydrostatic
  nh_hmin = list%nh_hmin
  nh_solver = list%nh_solver
  nh_itmax = list%nh_itmax
  nh_tol = list%nh_tol
  f_nh_adaptive = list%f_nh_adaptive
  nh_detector = list%nh_detector
  nh_chi_on = list%nh_chi_on
  nh_margin = list%nh_margin
  nh_amin = list%nh_amin
  nh_arel = list%nh_arel
  f_nh_breaking = list%f_nh_breaking
  nh_break_alpha = list%nh_break_alpha
  nh_break_beta = list%nh_break_beta
  nh_break_type = list%nh_break_type
  nh_break_fr = list%nh_break_fr
  nh_break_slope = list%nh_break_slope
  nh_break_margin = list%nh_break_margin
  f_nh_slope = list%f_nh_slope
  select case (f_diffusion_term)
    case (0)      ! 無効
    case (1)      ! 定数モデル
      if (p_diffusion_nu <= 0) then
        call par_stop("list_enc: f_diffusion_term=1 requires p_diffusion_nu > 0")
      end if
    case (2)      ! ゼロ方程式モデル
      if (p_diffusion_alpha <= 0 .and. p_diffusion_nu <= 0) then
        call par_stop("list_enc: f_diffusion_term=2 requires p_diffusion_alpha > 0 "// &
                      "(or p_diffusion_nu > 0)")
      end if
    case default
      call par_stop("list_enc: f_diffusion_term must be 0(off), 1(constant) or 2(zero-equation)")
  end select

  ! 河道条件ファイルから堤防の水理モードを読む(未指定ならデフォルト値)
  if (len_trim(p%fn_channel) > 0) call list_channel_read(p, chlist)
  f_bank_mode = chlist%f_bank_mode
  f_bank_opening = chlist%f_bank_opening
  f_channel_advection = chlist%f_channel_advection

  ! 堤防(仮想壁面)・河道幅の有効判定は geoinfo の構築結果に従う
  have_bank = g%bank_active
  if (have_bank) call bank_init(g)
  have_swall = g%swall_active
  f_swall_mode = g%f_swall_mode             ! 検証は geoinfo(setup_seawall)済み
  have_width = g%width_active
  ! 曲率項の作業配列(f_dbcurv=1 のみ。set_debris は geomorph init から
  ! swflow init より前に呼ばれる契約なので db_curv はここで確定済み)
  if (db_curv > 0) allocate(acv(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (f_bank_mode < e_bank_weir .or. f_bank_mode > e_bank_pump) then
    call par_stop("list_channel: f_bank_mode must be 0(overtopping only), " &
                  //"1(one-way sluice) or 2(forced drainage)")
  end if
  if (f_bank_opening < 0 .or. f_bank_opening > 1) then
    call par_stop("list_channel: f_bank_opening must be 0(none) or 1(reassign to normal edges)")
  end if
  if (f_channel_advection < 0 .or. f_channel_advection > 1) then
    call par_stop("list_channel: f_channel_advection must be 0(drop) or 1(normal)")
  end if
  ! 有効判定は namelist 由来+geoinfo の構築結果で全ランク同一
  have_bopen = have_bank .and. f_bank_opening > 0
  have_frw = have_bopen .or. have_width
  ! 塞がれた開口の動的振り替え(§68.14)。有効判定は namelist 由来で
  ! 全ランク同一。河道限定(1)は河道マスク(rw)が必須
  if (f_opening_dynamic < 0 .or. f_opening_dynamic > 2) then
    call par_stop("list_enc: f_opening_dynamic must be 0(off), 1(channel edges) or 2(all edges)")
  end if
  have_fwd = f_opening_dynamic > 0
  if (f_advection_donor < 0 .or. f_advection_donor > 1) then
    call par_stop("list_enc: f_advection_donor must be 0(all wet cells) or 1(channel cells on channel edges)")
  end if
  if (f_advection_donor == 1 .and. .not. any(g%rw > 0)) then
    call par_stop("list_enc: f_advection_donor=1 requires a channel mask (fn_rw in list_geoinfo)")
  end if
  if (f_advection_donor == 1 .and. f_advection_scheme < 2) then
    call par_info("swflow: f_advection_donor=1 has no effect with f_advection_scheme=1")
  end if
  if (f_dry_head_cap < 0 .or. f_dry_head_cap > 1) then
    call par_stop("list_enc: f_dry_head_cap must be 0(off) or 1(cap edge depth toward dry cells by energy head)")
  end if
  ! 河道限定(1。既定)は河道マスクがなければ対象エッジが存在しないので無効化
  ! (fwd を確保せず、メモリ・CPU とも追加なし。全エッジに効かせたい氾濫・
  ! ダム破壊は 2 を明示する。§68.19)
  if (f_opening_dynamic == 1 .and. .not. any(g%rw > 0)) then
    call par_info("swflow: f_opening_dynamic=1 has no channel mask (fn_rw); dynamic opening disabled")
    have_fwd = .false.
  end if
  if (have_fwd) then
    allocate(fwd(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 1.0)
    if (have_width) then
      have_cwd = .true.
      allocate(cwxd(1:g%nx, dcp%jsh:dcp%jeh), source = 1.0)
      allocate(cwyd(1:g%nx, dcp%jsh:dcp%jeh), source = 1.0)
    end if
    call par_info("swflow: dynamic opening reassignment enabled (f_opening_dynamic=" &
                  //itoa(f_opening_dynamic)//")")
  end if
  adv_drop_rw = have_bank .and. f_channel_advection == 0

  ! システムパラメータから継承するENCパラメータをセットする
  select case (p%f_govequation)
    case (0)      ! DynWE
      f_advection_term = 1
      f_pressure_term = 1
    case (1)      ! DifWE
      f_advection_term = 0
      f_pressure_term = 1
    case default  ! KinWE
      f_advection_term = 0
      f_pressure_term = 0
  end select

  ! 重み係数をセットする
  call init_weights(p, g)

  ! エッジ通過幅係数(開口補正+幅キャップ)とセル平面積率を構築する
  ! (通過幅シェア lp/ld を使うため init_weights より後。zbank / wrw は
  ! 帯+ハロ(scatter_coeffs 済み)、rw/sw/x はゾーン2で全域=
  ! 全ランクが自分の帯+ハロ行を冗長構築する)
  ! 断面形一般化 σ(h)(§26)の有効判定は build_channel_frw より前に行う
  ! (キャップ前 frw の保存 frw0 の要否を build が参照するため)
  sect_m = chlist%p_sect_m
  if (sect_m < 0.0) call par_stop("list_channel: p_sect_m must be >= 0")
  have_sect = sect_m > 0.0 .and. (g%bank_active .or. g%drw_active)
  if (sect_m > 0.0 .and. .not. have_sect) then
    call par_stop("list_channel: p_sect_m > 0 requires a transition depth source " &
                  //"(levee crest via fn_bank/bank0, or incision depth via depth_rw/fn_depth_rw)")
  end if
  if (have_sect) then
    sect_mp1 = sect_m + 1.0
    sect_rmp1 = 1.0 / sect_mp1
    sect_mfac = sect_m * sect_rmp1
  end if

  ! 境界条件の適用層を初期化する(辺型・面型・基準水位・流入区間の
  ! 開口幅の構築。開口幅が l8 を使うため init_weights より後に。
  ! 通過幅係数の構築が境界面の開閉(bc_open_face)を読むためその前に)
  call bc_init(p, g, b)

  if (have_frw) call build_channel_frw(g)
  if (have_width) call build_wfrac(g)

  ! σ の遷移深さ D の構築(zbank/drw は帯配布済み)
  if (have_sect) call build_sdep(g, b, s)
  ! 実効平面積率 af(§25/§26)。restore 後の統計・gwflow が最初のステップ
  ! 前に読むため init でも埋める(既定は m_state_init の gv のまま。
  ! 空隙率が時間変化する機能(s%gv_active。§63.1)も毎ステップ更新の対象)
  if (have_width .or. have_sect .or. s%gv_active) call update_af(g, s)

  ! 破堤サイトの解釈・検証・行バケット構築(zbank の帯と s%z を読むため
  ! この位置。have_breach を設定する)
  call breach_init(p, g, s, chlist)

  ! 初期条件を設定する
  call init_enc_status(p, g, s, sx_mod)

  ! 移流項計算サブモジュールを初期化する
  call adv_init(p, g)

  ! 拡散項計算サブモジュールを初期化する(l8/w8dr を使うため
  ! init_weights より後に)
  call diff_init(p, g)

  ! 非静水圧補正サブモジュールを初期化する(f_nonhydrostatic=0 なら
  ! 何も確保しない。l8/w8dr を使うため init_weights より後に)
  call nh_init(p, g, s)

  ! 高速摩擦計算ルーチンを初期化する
  call m_ffactor_init(f_friction_fastmath, p%dd, 30.0, 'UV')

  ! 水深の境界条件をセットする
  !   init 時点で実効なのはため池の初期吸収だけ: 降雨は s%pre=0
  !   (makepre は run_main が初期化後に呼ぶ)、ソースは q=0
  !   (makebdc 未実行)で、どちらも構造的に +0 となる。
  !   restore 時も安全: 保存状態は最終ステップの boundary_h 適用後
  !   なので、ため池転送は冪等(保存 h>0 はため池満杯時のみ)。
  !   この前提を崩す変更(makepre の前倒し、pre の初期条件化等)を
  !   する場合はここを要再検討(developer.md §15)
  call boundary_h(p, g, b, s, sx_mod)

  ! エッジの強制条件(境界面流量)を初期水深から初期化する(complete が
  ! mn1→mn にコミットするので、初回ステップの RK が読む「前ステップの
  ! 境界流量」が内部エッジ(init_enc_status で初期化)と同格になる)。
  ! リスタート時は呼ばない: 保存された uv/mn に境界面の値が含まれており、
  ! 復元後の h(保存時の連続式適用後)から再計算すると保存時の値
  ! (適用前の h 起源)と食い違い、厳密復元が破れる
  if (p%f_state_restore <= 0) then
    call boundary_uvmn(p, g, b, s, sx_mod)
  end if

  ! 界面エッジ行(js-1, je)の所有成分を南北で補完し合う(時間ループの
  ! momentum 直後と同じ)。init_enc_status は担当帯の基準セルのエッジだけを
  ! 書くため、初回ステップが読む界面行の他ランク所有成分(北ランクから見た
  ! 行 js-1 の k=4 等)はこれがないと 0 のまま: 初期流速が非零のケースで
  ! 非静水圧補正の u^n の複製(nh_prepare)がランク依存になる実バグ
  ! (test/nhbreak の np=2。2026-10-05)。逐次では no-op、静水圧の経路は
  ! 自エッジしか読まないので結果不変
  call par_edge_merge(sx_mod%uv,  esync_s, esync_n)
  call par_edge_merge(sx_mod%mn1, esync_s, esync_n)

  ! 変数を更新して次のタイムステップの準備をする(initial: σ 適用セルの
  ! h は正準のまま保ち、u,v の再正規化もしない。§26)
  call complete(p, g, s, sx_mod, initial=.true.)
  have_edge_flux = .true.

end subroutine


!----------------------------------------------------------------------
! ENCの計算
!----------------------------------------------------------------------
subroutine m_swflow_enc_calc(p, g, b, s, ierror)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(inout) :: b   ! ダム節が診断量を更新(§22)
  type(t_state), intent(inout) :: s
  integer, intent(inout) :: ierror

  ! ステップ頭: 前ステップ確定状態のハロ交換
  !   h/u/v/vv は幅2(移流項のハロ再計算=案Aの依存)、mn は幅1。
  !   交換対象と幅の根拠は developer.md §11 のステンシル解析を参照
  call par_halo_cell(s%h)
  call par_halo_cell(s%u)
  call par_halo_cell(s%v)
  call par_halo_cell(s%z)
  call par_halo_cell(s%vv)
  call par_halo_edge(sx_mod%mn)
  ! 運動量保存形移流(§68.6)は線 k 上の ±2 エッジ流速と、両セル・側方
  ! セルの流量 m, n を読む: uv をエッジ幅2、m, n をセル幅2で交換する
  ! (スキーム1では呼ばない=通信ゼロ追加。判定は namelist 由来で
  ! 全ランク同一 → collective 安全)
  if (f_advection_scheme >= 2) then
    call par_halo_edge(sx_mod%uv, 2)
    call par_halo_cell(s%m)
    call par_halo_cell(s%n)
  end if
  ! 浮遊砂柱状量(移流の風上濃度がハロ行の hs/h を読む。E-D による帯の
  ! 更新は前ステップの geomorph なので、ここで交換すれば最新)
  if (s%sed_active) call par_halo_cell(s%hs)
  ! 輸送物質柱状量(浮遊砂と同じ理由でステップ頭交換。§30)
  if (s%wq_active) call par_halo_cell(s%cq)
  if (s%dw_active) call par_halo_cell(s%hd)
  if (s%bd_active) call par_halo_cell(s%hbd)
  ! 地表塩水層厚(同上。§47)
  if (s%salt_active) call par_halo_cell(s%hss)

  ! 破堤サイトの現時刻の実効天端を更新する(サイト数ぶんの時系列補間。
  ! t の純関数なので全ランクが同値を冗長計算する=通信不要)
  if (have_breach) call breach_update(s%t)

  ! 塞がれた開口の動的振り替え表をステップ頭の h, z(ハロ交換済み)から
  ! 構築する(§68.14。無効時は呼ばない=ゼロ追加)
  if (have_fwd) call build_fwd(p, g, s)
  if (have_cwd) call build_cwd(g, s)

  ! 非静水圧補正: ステップ頭のエッジ流速 u^n を複製する(NH ON のみ)
  if (nh_active) call nh_prepare(sx_mod)

  ! 移流項を計算する
  call adv_prepare(p, g, s, sx_mod)

  ! 拡散項を計算する
  call diff_prepare(p, g, s)

  ! 曲率項の遠心加速度をセルごとに前計算する(f_dbcurv=1。§28.10)
  if (db_curv > 0) call curv_prepare(g, s)

  ! 運動方程式を解いて流速を計算する
  call momentum(p, g, s, sx_mod, ierror)

  ! 界面エッジ行(js-1, je)の所有成分を南北で補完し合う
  ! (同一エッジのフラックスを共有 → 質量保存がビット厳密になる)
  call par_edge_merge(sx_mod%uv,  esync_s, esync_n)
  call par_edge_merge(sx_mod%mn1, esync_s, esync_n)

  ! エッジの流速・流量への強制条件をセットする(辺境界の流出、
  ! 区間流入など。各条件の有効判定は boundary_uvmn 内の節ごとに行う)
  call boundary_uvmn(p, g, b, s, sx_mod)

  ! 非静水圧補正(NH ON のみ): 静水圧 predictor の全加速度に 1 層 NH の
  ! 射影を掛けてエッジ流速・流量を補正する(docs/nonhydrostatic_plan.md §5)
  if (nh_active) call nh_project(p, g, s, sx_mod)

  ! 連続式を解いて水深を更新する
  call continuous(p, g, s, sx_mod)

  ! 浮遊砂柱状量を移流する(連続式と同一のエッジ流量・係数による
  ! 風上輸送。時刻 n の s%h と s%hs が必要なため complete より前に置く)。
  ! 区間流入に濃度時系列があるときは境界流入濃度テーブルを渡す
  if (s%sed_active) then
    if (allocated(b%csin)) then
      call advect_scalar(p, g, s, sx_mod, s%hs, sx_mod%hs1, cbin=b%csin)
    else
      call advect_scalar(p, g, s, sx_mod, s%hs, sx_mod%hs1)
    end if
  end if

  ! 輸送物質柱状量を移流する(浮遊砂と同一の保存輸送カーネル。境界流入
  ! 濃度テーブル cqin は m_wq が毎ステップ更新する。§30)
  if (s%wq_active) then
    if (allocated(b%cqin)) then
      call advect_scalar(p, g, s, sx_mod, s%cq, sx_mod%cq1, cbin=b%cqin)
    else
      call advect_scalar(p, g, s, sx_mod, s%cq, sx_mod%cq1)
    end if
  end if

  ! 地表塩水層厚を移流する(同一カーネル。分担率 α で底層の流速分担を
  ! 表す。境界流入は清水 = cbin なし。§47)
  if (s%salt_active) then
    call advect_scalar(p, g, s, sx_mod, s%hss, sx_mod%hss1, share=s%salt_alpha)
  end if

  ! 流動流木柱状量を移流する(同一カーネル。鉛直平均流速と同速の単相
  ! 近似。境界流入は清水 = cbin なし。発生・停止は m_driftwood。§50)
  if (s%dw_active) then
    call advect_scalar(p, g, s, sx_mod, s%hd, sx_mod%hd1)
  end if
  ! 流動瓦礫柱状量を移流する(同上。破壊・停止は m_bldgdebris。§63)
  if (s%bd_active) then
    call advect_scalar(p, g, s, sx_mod, s%hbd, sx_mod%hbd1)
  end if

  ! ダムの適用(捕捉帯吸収→運転→放流。時間ループのみ。§22)
  call dam_apply(p, g, b, s, sx_mod)

  ! 水深の境界条件をセットする
  call boundary_h(p, g, b, s, sx_mod)

  ! 変数を更新して次のタイムステップの準備をする
  call complete(p, g, s, sx_mod)
end subroutine


!----------------------------------------------------------------------
! 土石流抵抗則の設定口(m_geomorph の init_debris が呼ぶ)
!   本モジュールの init より前に呼ばれる(m_main の初期化順序)。
!   検証は呼び出し側(init_debris)が済ませている
!----------------------------------------------------------------------
subroutine m_swflow_enc_set_debris(fres, tanphi, sgrav, vstop, cstar, cmin, d50, erest, &
                                   mu, xi, tauy, fcurv)
  integer, intent(in) :: fres
  real, intent(in) :: tanphi, sgrav, vstop
  real, intent(in) :: cstar             ! 河床の充填濃度 C* = 1−λ
  real, intent(in) :: cmin              ! 希薄側の濃度下限(f_dbres=2,3,4,5)
  real, intent(in) :: d50               ! 代表粒径 (m)(f_dbres=2)
  real, intent(in) :: erest             ! 粒子の反発係数 e(f_dbres=2)
  real, intent(in) :: mu                ! Voellmy 摩擦係数 μ(f_dbres=4)
  real, intent(in) :: xi                ! Voellmy 乱流係数 ξ (m/s²)(f_dbres=4)
  real, intent(in) :: tauy              ! 一定停止応力 τ_y (Pa)(f_dbres=5)
  integer, intent(in) :: fcurv          ! 曲率項の有無(f_dbcurv。§28.10)
  db_res = fres
  db_tanphi = tanphi
  db_sgrav = sgrav
  db_vstop = vstop
  db_cstar = cstar
  db_cmin = cmin
  db_d50v = d50
  ! 層流則第2項の係数 k_d・(σ/ρ)・(1−e²)(σ/ρ = s+1)
  db_kcol = db_kd * (sgrav + 1.0) * (1.0 - erest**2)
  db_mu = mu
  db_xi = xi
  db_tauy = tauy
  db_curv = fcurv
end subroutine


!----------------------------------------------------------------------
! ENCの終了
!----------------------------------------------------------------------
subroutine m_swflow_enc_dispose(p)
  type(t_sysparam), intent(in) :: p
  if (p%f_state_save > 0) call save_state(p, sx_mod)
  call bc_dispose
  call del_enc_status(sx_mod)
  if (allocated(frw)) deallocate(frw)
  if (allocated(fwd)) deallocate(fwd)
  have_fwd = .false.
  fwd_restored = .false.
  if (allocated(cwxd)) deallocate(cwxd)
  if (allocated(cwyd)) deallocate(cwyd)
  have_cwd = .false.
  cwd_restored = .false.
  if (allocated(wfrac)) deallocate(wfrac)
  if (allocated(cwx)) deallocate(cwx)
  if (allocated(sdep)) deallocate(sdep)
  if (allocated(screst)) deallocate(screst)
  if (allocated(frw0)) deallocate(frw0)
  if (allocated(cwy)) deallocate(cwy)
  if (allocated(acv)) deallocate(acv)
  db_curv = 0
  call breach_dispose
  if (allocated(nwall)) deallocate(nwall)
  have_bopen = .false.
  have_width = .false.
  have_sect = .false.
  have_edge_flux = .false.
  sect_m = 0.0
  have_frw = .false.
  db_res = 0
  db_tanphi = 0.0
  db_sgrav = 0.0
  db_vstop = 0.0
  db_cstar = 0.0
  db_cmin = 0.0
  db_d50v = 0.0
  db_kcol = 0.0
  db_mu = 0.0
  db_xi = 0.0
  db_tauy = 0.0
  call m_ffactor_dispose
  call adv_dispose
  call diff_dispose
  call nh_dispose
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 重み係数の初期化
!----------------------------------------------------------------------
subroutine init_weights(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g

  integer :: k
  real :: dr

  dr = sqrt(g%dx**2 + g%dy**2)

  forall(k=1:8) din2(k) = din(k)**2
  forall(k=1:8) djn2(k) = djn(k)**2
  forall(k=1:8) r8x(k) = real(din(k)) / g%dx
  forall(k=1:8) r8y(k) = real(djn(k)) / g%dy

  w8dr(1:8) = [ dr, g%dy, dr, g%dx, g%dx, dr, g%dy, dr ]
  forall(k=1:8) w8dr2(k) = w8dr(k)**2

  ! k軸の単位ベクトルのx, y方向成分
  n8x(1:8) = [ -g%dx/dr,  0.0,  g%dx/dr, -1.0, 1.0, -g%dx/dr, 0.0, g%dx/dr ]
  n8y(1:8) = [ -g%dy/dr, -1.0, -g%dy/dr,  0.0, 0.0,  g%dy/dr, 1.0, g%dy/dr ]

  ! フラックスの通過幅の割合
  !   lpy, ldyはy軸に投影したLの長さのΔyに対する割合(x方向フラックスが通過)
  !   lpx, ldxはx軸に投影したLの長さのΔxに対する割合(y方向フラックスが通過)
  !   lpy, lpxは斜め方向、ldy, ldxは軸方向
  !   ここで lpx + (ldx * 2) = 1, lpy + (ldy * 2) = 1 である
  if (g%dy > g%dx) then
    lpy = 1 - (g%dx / g%dy)**2 * p_diagratio
    ldy = p_diagratio / 2 * (g%dx / g%dy)**2
    lpx = 1 - p_diagratio
    ldx = p_diagratio / 2
  else
    lpy = 1 - p_diagratio
    ldy = p_diagratio / 2
    lpx = 1 - (g%dy / g%dx)**2 * p_diagratio
    ldx = p_diagratio / 2 * (g%dy / g%dx)**2
  end if

  ! k軸方向フラックスの通過幅の割合
  !   l8yはy軸に投影したLの長さのΔyに対する割合(x方向フラックスが通過)
  !   l8xはx軸に投影したLの長さのΔxに対する割合(y方向フラックスが通過)
  l8y(1:8) = [ ldy, 0.0, ldy, lpy, lpy, ldy, 0.0, ldy ]
  l8x(1:8) = [ ldx, lpx, ldx, 0.0, 0.0, ldx, lpx, ldx ]

  ! 勾配モデルの重み係数
  w8x(1:8) = [ ldy, 0.0, ldy, lpy, lpy, ldy, 0.0, ldy ]
  w8y(1:8) = [ ldx, lpx, ldx, 0.0, 0.0, ldx, lpx, ldx ]


  ! k軸方向フラックスの通過幅
  forall(k=1:8) l8(k) = sqrt((l8y(k) * g%dy)**2 + (l8x(k) * g%dx)**2)

  ! 通過幅ゼロのエッジは運動方程式の対象外(質量交換が常にゼロのまま
  ! 流速の積分だけが続くと、大きな段差のエッジで発散判定に掛かるため)
  forall(k=1:8) skip8(k) = (l8(k) <= 0)

  ! セル境界の流速・流量からセル中心の平均流速・平均流量の増分を計算するための係数
  !   セル中心から近傍に向かうフラックスuvをn8x, n8yで除して投影前のxとyの正の方向成分に戻す
  !   近傍の方向に応じた開口幅(辺長)をl8x, l8yで調整し、
  !   セルの左右(上下)の平均をとるために2で割る
  w8mx(1:8) = [ 1/n8x(1), 0.0, 1/n8x(3), 1/n8x(4), 1/n8x(5), 1/n8x(6), 0.0, 1/n8x(8) ]
  w8my(1:8) = [ 1/n8y(1), 1/n8y(2), 1/n8y(3), 0.0, 0.0, 1/n8y(6), 1/n8y(7), 1/n8y(8) ]
  forall(k=1:8) w8mx(k) = w8mx(k) * l8y(k) / 2
  forall(k=1:8) w8my(k) = w8my(k) * l8x(k) / 2

  ! セル境界での単位幅流量から中心セルの1時間ステップでの水位減少量を計算するための係数
  forall(k=1:8) mn2dh(k) = (l8(k) / (g%dx * g%dy)) * p%dt

end subroutine




!----------------------------------------------------------------------
! 状態変数の初期化と初期条件の設定
!----------------------------------------------------------------------
subroutine init_enc_status(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(out) :: sx

  real :: ue, ve
  integer :: i, j, k, in, jn, ie, je

  ! メモリを確保する
  ! エッジ配列の j 範囲: セル j を挟むエッジは j-1 と j なので下限は jsh-1
  allocate(sx%uv(1:4,0:g%nx,dcp%jsh-1:dcp%jeh), source = 0.0)
  allocate(sx%h1(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(sx%mn1(1:4,0:g%nx,dcp%jsh-1:dcp%jeh), source = 0.0)
  allocate(sx%mn(1:4,0:g%nx,dcp%jsh-1:dcp%jeh), source = 0.0)
  ! 浮遊砂の書き込みバッファ(sed_active は m_geomorph_init が設定済み。
  ! 初期化順序: geomorph init → swflow init)。正準状態 s%hs の複製で
  ! 初期化する(mn1 = mn と同じ流儀): init 末尾の complete は移流を
  ! 経ずにコミットするため、0 のままだと restore 済みの hs を消す
  ! (リスタート往復ビット一致で実検出したバグ)
  if (s%sed_active) then
    allocate(sx%hs1(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
    sx%hs1(:,:) = s%hs(:,:)
  end if
  ! 輸送物質の書き込みバッファ(hs1 と同じ理由で正準状態の複製で初期化。§30)
  if (s%wq_active) then
    allocate(sx%cq1(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
    sx%cq1(:,:) = s%cq(:,:)
  end if
  ! 地表塩水層の書き込みバッファ(同上の理由で複製初期化。§47)
  if (s%salt_active) then
    allocate(sx%hss1(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
    sx%hss1(:,:) = s%hss(:,:)
  end if
  ! 流動流木の書き込みバッファ(同上の理由で複製初期化。§50)
  if (s%dw_active) then
    allocate(sx%hd1(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
    sx%hd1(:,:) = s%hd(:,:)
  end if
  ! 流動瓦礫の書き込みバッファ(同上。§63)
  if (s%bd_active) then
    allocate(sx%hbd1(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
    sx%hbd1(:,:) = s%hbd(:,:)
  end if

  ! 流速の初期条件を設定する
  !$omp parallel do schedule(dynamic) private(i, j, k, in, jn, ie, je, ue, ve)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      do k = 1, 4
        ! k近傍セルのインデックスを計算する
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) cycle
        ! k近傍セルとの境界フラックスのインデックスを計算する
        ie = i + die(k)
        je = j + dje(k)
        ! セル境界での流速を計算する(座標軸方向が正)
        ue = (s%u(i,j) + s%u(in,jn)) / 2
        ve = (s%v(i,j) + s%v(in,jn)) / 2
        ! セル境界流速の境界法線方向成分を計算する(中心から近傍方向が正)
        sx%uv(k,ie,je) = ue * n8x(k) + ve * n8y(k)
      end do
    end do
  end do
  !$omp end parallel do

  ! 水深の初期条件を設定する(σ 有効時は continuous の seeding と同じく
  ! 矩形換算水深 vh。init 中の h1 の読み手は boundary_h のため池節
  ! (sdep=0 = 恒等単位)と complete(initial)のみ。§26)
  !$omp parallel do schedule(dynamic) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (have_sect) then
        sx%h1(i,j) = sect_v(s%h(i,j), sdep(i,j))
      else
        sx%h1(i,j) = s%h(i,j)
      end if
    end do
  end do
  !$omp end parallel do

  if (p%f_state_restore > 0) then
    call restore_state(p, sx)
    ! 動的振り替えの表は保存状態から復元する(最終ステップの連続式が使った
    ! ステップ頭 h^n の表。これで u,v,m,n の再導出が保存時とビット一致する。
    ! §68.14)。表なしで保存された状態からの復元は復元した h から作る
    ! (再導出が最終桁で異なりうる旧挙動)
    if (have_fwd .and. .not. fwd_restored) then
      call build_fwd(p, g, s)
      call par_info("swflow_enc: dynamic opening table rebuilt from the restored h " &
                    //"(state saved without the table; u,v,m,n may differ in the last digit)")
    end if
    if (have_cwd .and. .not. cwd_restored) then
      call build_cwd(g, s)
      call par_info("swflow_enc: dynamic conveyance ratio rebuilt from the restored h " &
                    //"(state saved without it; u,v may differ in the last digit)")
    end if
    call restore_uvmn(p, g, s, sx)
  end if

  sx%initialized = .true.

end subroutine


!----------------------------------------------------------------------
! 状態変数の削除
!----------------------------------------------------------------------
subroutine del_enc_status(sx)
  type(t_enc_status), intent(inout) :: sx
  if (allocated(sx%uv)) deallocate(sx%uv)
  if (allocated(sx%mn)) deallocate(sx%mn)
  if (allocated(sx%mn1)) deallocate(sx%mn1)
  if (allocated(sx%h1)) deallocate(sx%h1)
  if (allocated(sx%hs1)) deallocate(sx%hs1)
  if (allocated(sx%cq1)) deallocate(sx%cq1)
  if (allocated(sx%hd1)) deallocate(sx%hd1)
  if (allocated(sx%hbd1)) deallocate(sx%hbd1)
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
! (旧 prepare: mn0=mn の繰り越しコピーは mn1 方式への移行で不要になった。
!  時刻n+1の値のコミットは complete で行う)


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine momentum(p, g, s, sx, ierror)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(inout) :: sx
  integer, intent(inout) :: ierror

  integer :: i, j, k
  logical :: have_exflux
  logical :: have_runge
  logical :: have_error
  integer :: n_exfluxes
  integer :: n_runge
  integer :: n_error

  ! 全ての有効セルにおいて対象セルと近傍セルとの間の流量流速を計算する
  ! 同時に水を移動させて対象セルと近傍セルの水深を更新する
  ! (ただし連続式をここで解くとスレッドセーフでない)
  n_exfluxes = 0
  n_runge = 0
  n_error = 0
  !$omp parallel do schedule(dynamic) private(i, j, k, have_exflux, have_runge, have_error) &
  !$omp reduction(+:n_exfluxes), reduction(+:n_runge), reduction(+:n_error)
  ! This loop should be an independ "omp parallel do"
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      do k = 1, 4
        ! 対象セルi,jとそのk近傍との境界における流量流速と水深の計算を実行
        call calc_kth_momentum(p, g, s, sx, i, j, k, have_exflux, have_runge, have_error)
        if (have_exflux) n_exfluxes = n_exfluxes + 1
        if (have_runge) n_runge = n_runge + 1
        if (have_error) n_error = n_error + 1
      end do
    end do
    ! OpenMPのからexitで抜けることはできない?
  end do
  !$omp end parallel do
  s%n_exfluxes = n_exfluxes
  s%n_runge = n_runge

  if (n_error > 0) then
    call par_info("swflow: solution diverged, velocity exceeded 250 m/s")
    call par_info(" review dt, roughness and boundary/input data")
    call par_info(" the run stops after this step")
    ierror = ierror + n_error
  end if

end subroutine


!----------------------------------------------------------------------
! 曲率項の前計算(f_dbcurv=1。developer.md §28.10)
!   セルごとに a_c = (u²z_xx + 2uv z_xy + v²z_yy)/√(1+z_x²+z_y²) を求める。
!   これは地表面の流向法線曲率 κ_n と表面速度 V_s の積 V_s²κ_n を、水平
!   投影の流速 (u, v) と z の Hessian で書いたもの(z のグラフ曲面に対して
!   厳密。1次元では u²z''/√(1+z'²) = V_s²κ)。
!   ステンシルは 3×3(中心差分)。領域外・海域(x<=0, sw>0)を含む差分は
!   その項を 0 とする(壁沿いのセルは壁法線方向の曲率を持たない扱い)。
!   z, u, v はステップ頭で幅2交換済みなので js-1..je+1 の a_c が帯内で
!   閉じて求まる(辺の両セル平均が js-1, je+1 を読む)
!----------------------------------------------------------------------
subroutine curv_prepare(g, s)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: i, j, j1, j2
  real :: zc, zxx, zyy, zxy, zx, zy
  real :: rdx, rdy
  logical :: okw, oke, oks, okn

  rdx = 1.0 / g%dx
  rdy = 1.0 / g%dy
  j1 = max(dcp%js - 1, 1)
  j2 = min(dcp%je + 1, g%ny)
  !$omp parallel do schedule(dynamic) private(i, j, zc, zxx, zyy, zxy, zx, zy, okw, oke, oks, okn)
  do j = j1, j2
    do i = 1, g%nx
      acv(i,j) = 0.0
      if (.not. valid(i, j)) cycle
      if (s%vv(i,j) <= 0.0) cycle
      zc = s%z(i,j)
      okw = valid(i-1, j)
      oke = valid(i+1, j)
      oks = valid(i, j-1)
      okn = valid(i, j+1)
      zxx = 0.0; zyy = 0.0; zxy = 0.0; zx = 0.0; zy = 0.0
      if (okw .and. oke) then
        zxx = (s%z(i+1,j) - 2 * zc + s%z(i-1,j)) * rdx * rdx
        zx = (s%z(i+1,j) - s%z(i-1,j)) * rdx / 2
      end if
      if (oks .and. okn) then
        zyy = (s%z(i,j+1) - 2 * zc + s%z(i,j-1)) * rdy * rdy
        zy = (s%z(i,j+1) - s%z(i,j-1)) * rdy / 2
      end if
      if (okw .and. oke .and. oks .and. okn) then
        if (valid(i+1, j+1) .and. valid(i+1, j-1) .and. valid(i-1, j+1) .and. valid(i-1, j-1)) then
          zxy = (s%z(i+1,j+1) - s%z(i+1,j-1) - s%z(i-1,j+1) + s%z(i-1,j-1)) * rdx * rdy / 4
        end if
      end if
      acv(i,j) = (s%u(i,j)**2 * zxx + 2 * s%u(i,j) * s%v(i,j) * zxy + s%v(i,j)**2 * zyy) &
                 / sqrt(1.0 + zx**2 + zy**2)
    end do
  end do
  !$omp end parallel do

contains

  ! 計算対象セルか(領域内かつ海域でない)。x は番兵付き (0:nx+1, 0:ny+1)、
  ! sw は (1:nx, 1:ny) 確保なので x で先に弾く(Fortran の .and. は短絡
  ! 評価を保証しない)
  pure logical function valid(ii, jj)
    integer, intent(in) :: ii, jj
    valid = .false.
    if (g%x(ii,jj) <= 0) return
    valid = g%sw(ii,jj) <= 0
  end function

end subroutine


!----------------------------------------------------------------------
!
!----------------------------------------------------------------------
subroutine calc_kth_momentum(p, g, s, sx, i, j, k, have_exflux, have_runge, have_error)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(inout) :: sx
  integer, intent(in) :: i, j
  integer, intent(in) :: k
  logical, intent(out) :: have_exflux
  logical, intent(out) :: have_runge
  logical, intent(out) :: have_error

  integer :: in, jn
  integer :: ie, je
  real :: uve, mne
  real :: uve1, mne1
  real :: hee                     ! 面流束に使ったエッジ水深(calc_kth_flux が返す)
  real :: tae
  real :: dh
  real :: dhc, dhn
  real :: cor
  real :: maglim, maglim_inv
  logical :: wall                 ! 堤防壁エッジ(bank_wall が上書きする)

  ! この文はこの場所になければならない
  have_exflux = .false.
  have_runge = .false.
  have_error = .false.

  ! k近傍セルのインデックスを計算する
  !   領域外との遮断は x 番兵(x=0。確保 0:nx+1)が一手に担う。
  !   エッジ配列は (0:nx) 確保のため枠上セルのエッジ添字も範囲内で、
  !   枠の添字ガードは不要(境界面の定義は docs/boundary_plan.md §4.3)
  in = i + din(k)
  jn = j + djn(k)
  if (g%x(in,jn) <= 0) return

  ! k近傍セルとの境界フラックスのインデックスを計算する
  ie = i + die(k)
  je = j + dje(k)

  ! 通過幅ゼロのエッジ(p_diagratio=0 の対角等)は流量流速ゼロ
  if (skip8(k)) then
    sx%uv(k,ie,je) = 0
    sx%mn1(k,ie,je) = 0
    return
  end if

  ! 移動限界水深未満の場合は流量ゼロ(ddを大きくすると過大流出が増える)
  if (s%h(i,j) < p%dd .and. s%h(in,jn) < p%dd) then
    sx%uv(k,ie,je) = 0
    sx%mn1(k,ie,je) = 0
    return
  end if

  ! セル境界の流速をセットする(前ステップ値=無印から読む)
  uve = sx%uv(k,ie,je)
  mne = sx%mn(k,ie,je)

  ! セル境界の移流項をセットする
  !   f_channel_advection=0 のときは河道セルを含むエッジで移流を落とす
  !   (サブグリッド幅の強い不均質下での安定化オプション。§18)
  if (f_advection_term > 0) then
    tae = adv_edge(s, sx, i, j, k, in, jn, ie, je)
    if (adv_drop_rw) then
      if (g%rw(i,j) > 0 .or. g%rw(in,jn) > 0) tae = 0
    end if
  else
    tae = 0
  end if

  ! セル境界の拡散項を加算する(移流項と独立な重ね合わせ)
  if (f_diffusion_term > 0) tae = tae + diff_edge(i, j, k, in, jn)

  ! 中心セルi,jからk近傍セルin,jnへの流速uv1と単位幅流量mn1を計算する
  call calc_kth_flux(p, g, s, sx, uve, tae, i, j, k, in, jn, 0, uve1, mne1, hee)

  ! 適応的ルンゲクッタ
  !   流速または流量がmaglim倍以上、1/maglim以下、逆方向に変化した場合はルンゲクッタで再計算
  !   堤防壁エッジは bank_wall が結果を上書きするため判定しない(前ステップ値
  !   が堰流量なので毎ステップ閾値超になり、RK の再計算が無駄になるうえ
  !   Runge 列が壁エッジ数で埋まる。§68.29 原因 2)
  maglim = p_adprunge_thresh
  maglim_inv = 1.0 / maglim
  wall = .false.
  if (have_bank) wall = bank_edge(g, s, i, j, in, jn)
  if (f_adaptive_runge > 0 .and. .not. wall) then
    if ((mne >= 0 .and. (mne1 > mne * maglim .or. mne1 < mne * maglim_inv)) .or. &
        (mne < 0  .and. (mne1 < mne * maglim .or. mne1 > mne * maglim_inv))) then
      have_runge = .true.
      call calc_kth_flux(p, g, s, sx, uve, tae, i, j, k, in, jn, 1, uve1, mne1, hee)
    end if
  end if

  ! 発散チェック
  if (abs(uve1) > 250.) then
    have_error = .true.
  end if

  ! 河口から海への段落ち強制
  if (f_rivermouth_drop > 0) call rivermouth_drop

  ! 堤防(仮想壁面)エッジの流速・流量の上書き(submodule m_swflow_enc_channel)
  if (have_bank) call bank_wall(p, g, s, i, j, k, in, jn, uve1, mne1)

  ! 海岸堤防(仮想壁面)エッジの流速・流量の上書き(同 submodule。
  ! bank_wall は sw エッジに触れないため干渉しない)
  if (have_swall) call seawall_wall(p, g, s, i, j, in, jn, uve1, mne1)

  ! セル境界での単位幅流量から境界の両側のセルでの水深の減少量を計算する
  !   通過幅係数有効時はエッジ別係数 frw を乗じる(k<=4 は成分=k)。
  !   河道幅有効時はセルの平面積率 wfrac で水深換算を除算補正する
  dh = mne1 * mn2dh(k)    ! 家屋占有率がゼロの場合の中心セルの水深減少量
  if (have_frw) dh = dh * frw(k,ie,je)
  if (have_fwd) dh = dh * fwd(k,ie,je)
  dhc = dh / s%gv(i,j)
  dhn = -dh / s%gv(in,jn)
  if (have_width) then
    dhc = dhc / wfrac(i,j)
    dhn = dhn / wfrac(in,jn)
  end if

  ! 過大な流出の抑制
  !if ((dh > 0 .and. dhc + p%dd > s%h(i,j)) .or. (dh < 0 .and. dhn + p%dd > s%h(in,jn))) then
  if (have_sect) then
    ! σ 有効時は矩形換算水深(体積)で判定・抑制する(dhc/dhn は vh 増分。
    ! 非適用セルは sect_v が恒等のため従来と同値。§26)
    if ((dh > 0 .and. sect_v(s%h(i,j), sdep(i,j)) - dhc <= 0) .or. &
        (dh < 0 .and. sect_v(s%h(in,jn), sdep(in,jn)) - dhn <= 0)) then
      have_exflux = .true.
      if (f_exflux_reduction > 0) then
        if (dh > 0) then
          cor = max(sect_v(s%h(i,j), sdep(i,j)) - p%dd, 0.0) / dhc
        else
          cor = max(sect_v(s%h(in,jn), sdep(in,jn)) - p%dd, 0.0) / dhn
        end if
        uve1 = uve1 * cor
        mne1 = mne1 * cor
      end if
    end if
  else
  if ((dh > 0 .and. s%h(i,j) - dhc <= 0) .or. (dh < 0 .and. s%h(in,jn) - dhn <= 0)) then
    have_exflux = .true.
    if (f_exflux_reduction > 0) then
      if (dh > 0) then
        cor = max(s%h(i,j) - p%dd, 0.0) / dhc
      else
        cor = max(s%h(in,jn) - p%dd, 0.0) / dhn
      end if
      uve1 = uve1 * cor
      mne1 = mne1 * cor
    end if
  end if
  end if

  ! 非静水圧補正のためにエッジ水深を記録する(NH ON のみ。書き込み先は
  ! (k, ie, je) ごとに一意で競合なし)
  if (nh_active) nh_he(k,ie,je) = hee

  ! セル境界の流速を更新する
  !   uvは単一バッファ(自エッジread-then-writeのみ。developer.md §7の例外)
  sx%uv(k,ie,je) = uve1

  ! セル境界の流量を更新する(書き込みは時刻n+1バッファへ)
  sx%mn1(k,ie,je) = mne1

contains
  !--------------------------------------------------------------------
  ! 河口から海への段落ち強制
  subroutine rivermouth_drop
    real :: h
    if (g%rw(i,j) > 0 .and. g%sw(in,jn) > 0) then
      ! 中心から近傍に段落ち
      h = max(s%h(i,j), 0.0)      ! 中心セルの水深
      uve1 = ((2. / 3.)**(3. / 2)) * sqrt(p%gg * h)
      mne1 = uve1 * h
      if (have_sect) mne1 = uve1 * sect_v(h, sdep(i,j))   ! 断面積ベース(§68.28)
    else if (g%rw(in,jn) > 0 .and. g%sw(i,j) > 0) then
      ! 近傍から中心に段落ち
      h = max(s%h(in,jn), 0.0)    ! 近傍セルの水深
      uve1 = -((2. / 3.)**(3. / 2)) * sqrt(p%gg * h)
      mne1 = uve1 * h
      if (have_sect) mne1 = uve1 * sect_v(h, sdep(in,jn))
    end if
  end subroutine


end subroutine

!----------------------------------------------------------------------
! 中心セルi,jからk近傍セルへin,jnの流速uve1と単位幅流量mne1を計算する
!----------------------------------------------------------------------
subroutine calc_kth_flux(p, g, s, sx, uve0, tae0, i, j, k, in, jn, f_runge, uve1, mne1, hee)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  real, intent(in) :: uve0        ! セル境界での流速
  real, intent(in) :: tae0        ! セル境界での移流項
  integer, intent(in) :: i, j     ! 中心セルのインデックス
  integer, intent(in) :: k        ! 近傍セルの方位
  integer, intent(in) :: in, jn   ! 近傍セルのインデックス
  integer, intent(in) :: f_runge  ! ルンゲクッタのフラグ
  real, intent(out) :: uve1       ! 中心セルから近傍セルに向かう流速
  real, intent(out) :: mne1       ! 中心セルから近傍セルに向かう単位幅流量
  real, intent(out) :: hee        ! 最終段で面流束に使ったセル境界の水深 he
                                  !   (mne1 = uve1·he の he。非静水圧補正が流速を
                                  !   変えたあと同じ he で mn1 を再構成するため。
                                  !   σ 有効時は he そのもので、断面積換算は含まない)

  real :: he                      ! セル境界の水深
  real :: ge                      ! セル境界での重力加速度
  real :: tae                     ! セル境界での移流項(更新後)
  real :: tg0e, tge, tfe          ! セル境界での重力項、摩擦項
  real :: rne, hhe, vve           ! セル境界での粗度係数、摩擦項用水深、摩擦項用絶対流速
  real :: gve, bbe                ! セル境界での家屋の空隙率、家屋の平均サイズ
  real :: lme                     ! セル境界での付加質量力補正係数
  real :: vue2                    ! セル境界でのuveと直交する方向の流速の二乗
  real, parameter :: a(1:4) = [ 4., 3., 2., 1. ]
  real :: hc0, hn0
  real :: hc, hn
  real :: dtl
  integer :: l
  ! 土石流(debris_active。debris_plan.md §2.3-2.4)
  logical :: have_db              ! 運動量への hs 算入の有無
  real :: hsc, hsn, hse           ! 両セル・エッジの土砂柱状量(時刻 n。負値クランプ)
  real :: tgs                     ! 圧力項への hs 寄与(RK 内で不変)
  real :: aye                     ! 降伏減速度 (m/s²)(db_res>=1 のとき > 0)
  real :: cme                     ! エッジの混合体積濃度
  real :: fbe                     ! 江頭層流則の抵抗係数 f_b(db_res=2 かつ C>=cmin)
  real :: hte                     ! エッジの混合流動深(時刻 n。層流則用)
  real :: rme                     ! 1 + s・C(混合密度比 ρm/ρ)
  real :: vv0e                    ! 辺の速さ |V|(下限 p%vv 適用前。降伏停止判定用。§28.11)

  ! セル境界での物理量を求める
  vve = (s%vv(i,j) + s%vv(in,jn)) / 2       ! 速度の絶対値
  vv0e = vve
  rne = (g%rn(i,j) + g%rn(in,jn)) / 2       ! 粗度係数
  gve = (s%gv(i,j) + s%gv(in,jn)) / 2       ! 家屋の空隙率
  bbe = (g%bb(i,j) + g%bb(in,jn)) / 2       ! 家屋の平均サイズ
  lme = (s%lm(i,j) + s%lm(in,jn)) / 2       ! 有効慣性係数
  if (gve == 1) bbe = 1.e10                 ! 家屋なしの場合は家屋サイズは大きな値

  ! 摩擦項で使用する流速
  !   静止からの流動開始直後に流速が小さいために摩擦が過小となることを防ぐために
  !   (この現象は正攻法では時間刻みを極めて小さくしないと解消しない)
  vve = max(vve, p%vv)

  ! セル境界での有効重力加速度を計算
  ge = p%gg                                 ! 重力加速度
  if (f_gravity_correction > 0) ge = correct_ge()

  ! セル境界での底面勾配項(符合は中心セルから近傍セルに向かい正)
  tg0e = -ge * (s%z(in,jn) - s%z(i,j)) / w8dr(k) * gve

  ! セル境界でのuveと直交する流速成分の二乗を計算
  !   ルンゲクッタで流速の絶対値を更新する際に使用する
  vue2 = max(vve**2 - uve0**2, 0.0)

  ! 中心セルと近傍セルの水深をセット
  hc0 = s%h(i,j)
  hn0 = s%h(in,jn)
  hc = hc0
  hn = hn0

  ! 土石流: 運動量への hs 算入と抵抗則の前計算(RK 内で不変の量。
  ! hs は時刻 n の値 = ステップ頭交換済み。負値(強い乾燥化の名残)は
  ! クランプ。debris_active=偽 なら全て 0 で以降の加算は厳密に不変)
  have_db = s%debris_active
  hse = 0.0
  tgs = 0.0
  aye = 0.0
  fbe = 0.0
  hte = 0.0
  rme = 1.0
  if (have_db) then
    hsc = max(s%hs(i,j), 0.0)
    hsn = max(s%hs(in,jn), 0.0)
    hse = (hsc + hsn) / 2
    ! 圧力項への hs 寄与(水面 = z + h + hs。f_pressure_term に整合)
    if (f_pressure_term > 0) tgs = -ge * (hsn - hsc) / w8dr(k) * gve
    if (db_res > 0) then
      if (hsc + hsn > 0.0) then
        cme = (hsc + hsn) / (hc0 + hn0 + hsc + hsn)
        rme = 1.0 + db_sgrav * cme
        if (db_res == 4) then
          ! Voellmy 等価流体(RAMMS/Titan2D 系): 降伏 μ + 乱流項 ge・V²/(ξ・h_t)。
          ! μ は流動体全体の見かけ摩擦(濃度に依らず直接与える — §0)。
          ! 希薄側(C < db_cmin)はマニング+降伏なしに退化(数値的閉じ)
          if (cme >= db_cmin) then
            aye = ge * db_mu
            hte = max((hc0 + hn0) / 2 + hse, p%dv)
            ! 乱流項 減速度 ge・V²/(ξ・h_t) を −fbe・vve/(rme・hte) 形に載せる
            ! (fbe = ge・rme/ξ で rme が相殺)。マニング則は置換される
            fbe = ge * rme / db_xi
          end if
        else if (db_res == 5) then
          ! 一定停止応力(VolcFlow 型): a_y = τ_y/(ρm・h_t)+マニング合成。
          ! ρm = ρw(1+sC)。希薄側(C < db_cmin)は降伏なしに退化
          if (cme >= db_cmin) then
            aye = db_tauy / (db_rhow * rme * max((hc0 + hn0) / 2 + hse, p%dv))
          end if
        else
        ! 降伏減速度: a_y = ge・tanφ・sC/(1+sC)(水中固体重量の底面摩擦を
        ! 混合密度 ρ(1+sC) で除した加速度形。ge は correct_ge 済み =
        ! cos²θ を重力・圧力項と共有)。江頭構成則(db_res=2)はさらに
        ! (C/C*)^{1/5} を乗じる(Morpho2DH 式(17)。n=5 は原式固定)
        aye = ge * db_tanphi * db_sgrav * cme / rme
        if (db_res == 2) then
          aye = aye * (cme / db_cstar)**db_yexp
          ! 江頭層流則(江頭ら1989 式(25)/Morpho2DH 式(19)):
          !   f_b = (25/4){k_f(1−C)^{5/3}/C^{2/3} + k_d(σ/ρ)(1−e²)C^{1/3}}(h/d)^{−2}
          ! C < cmin の希薄側はマニングで閉じる(層流則は C→0 で発散)。
          ! 混合流動深 hte は時刻 n で固定(RK 内不変。hse と同じ近似)
          if (cme >= db_cmin) then
            hte = max((hc0 + hn0) / 2 + hse, p%dv)
            fbe = 6.25 * (db_kf * (1.0 - cme)**(5.0/3.0) / cme**(2.0/3.0) &
                          + db_kcol * cme**(1.0/3.0)) * (db_d50v / hte)**2
          end if
        else if (db_res == 3) then
          ! 高橋・中川(1991)石礫型(式(22)-(25)。単一粒径 ρm=ρ):
          !   降伏項の摩擦係数は流動時の tanα' = 0.45(原式固定。tanφ でなく)
          aye = ge * db_tana * db_sgrav * cme / rme
          hte = max((hc0 + hn0) / 2 + hse, p%dv)
          ! 流動型の自動切替(泥流域 C<cmin または h/d≥30 はマニング=式(4))
          if (cme >= db_cmin .and. hte < db_hdmud * db_d50v) then
            if (cme > db_cbl * db_cstar) then
              ! 石礫型(式(22)第2項): A'・{(1−C)/C}^{2/3}・(dL/h)²
              !   減速度 = A'ρm{...}(dL/h)²V²/(ρT h) → fbe/(rme・hte) 形
              fbe = db_apr * ((1.0 - cme) / cme)**(2.0/3.0) * (db_d50v / hte)**2
            else
              ! 掃流状集合流動(式(24)): (ρT/0.49)(dL/h)。ρT/ρT が相殺する
              ! ため rme を fbe に含めて同じ −fbe・vve/(rme・hte) 形に載せる
              fbe = rme * (db_d50v / hte) / db_c49
            end if
          else
            hte = 0.0     ! マニング経路(fbe=0)へ
          end if
        end if
        end if
      end if
    end if
  end if

  ! 曲率項(§28.10): 垂直応力 g_n → g_n + a_c による降伏項の倍率。
  !   a_c は辺の両セルの平均(c/n 対称)。g_n = √(g・ge)(ge = g cos²θ の
  !   Ni 補正下で g cosθ。補正なしなら g)。浮上条件は 0 に切る
  if (db_curv > 0 .and. aye > 0.0) then
    aye = aye * max(0.0, 1.0 + (acv(i,j) + acv(in,jn)) / 2 / sqrt(p%gg * ge))
  end if

  ! ルンゲクッタの段数を初期化
  if (f_runge > 0) then
    l = 1                ! ルンゲクッタの場合は1段目から
  else
    l = 4                ! 陽的オイラーの場合は4段目のみを実行
  end if

  ! ルンゲクッタでの更新後流速を初期流速で初期化
  uve1 = uve0

  ! ルンゲクッタのループ
  do while (l <= 4)
    ! セル境界での水深を求める
    he = (hc + hn) / 2

    ! セル境界での水深が上流側水深よりも深くならない様に調整
    if (f_hcap_upwind > 0) he = correct_he()

    ! 摩擦項で使用する水深
    !   水深が浅い場合に摩擦が過大となることを防ぐために水深の最小値を制限
    !   (土石流有効時は混合流動深 h + hs。hse=0 なら厳密に従来と同値)
    hhe = max(he + hse, p%dv)

    ! セル境界での移流項(時刻 n の値で固定。RK 段内の更新は比例形・
    ! アフィン形とも評価のうえ不採用。developer.md §68.19, §68.23)
    tae = tae0

    ! セル境界での重力項(符合は中心セルから近傍セルに向かい正)
    !   土石流有効時は水面勾配に hs を算入(z+h+hs。tgs は RK 内で不変)
    if (f_pressure_term > 0) then
      tge = tg0e - ge * (hn - hc) / w8dr(k) * gve + tgs
    else
      tge = tg0e
    end if

    ! セル境界での摩擦項
    !   摩擦項は半陰解法で計算するため、次元が他の項と異なる(値は常に正)。
    !   江頭層流則が有効なエッジ(fbe > 0)ではマニング則を置き換える:
    !   減速度 = f_b・V²/((1+sC)・h_t) → 半陰形 f_b・vve/((1+sC)・h_t)
    !   分母の max(hte, dv) は fbe > 0 のとき恒等(hte は dv 以上で設定済み)。
    !   fbe = 0 の経路では hte = 0 のままで、-Ofast の if 変換が両分岐を
    !   投機評価すると 0 除算の浮動小数点例外(-ffpe-trap=zero)を起こす
    !   ため、値を変えずに除算を安全にする(§63.6 の A1 記録。2026-10-01)
    if (fbe > 0.0) then
      tfe = -fbe * vve / (rme * max(hte, p%dv)) * gve
    else
      tfe = -ge * rne**2 * vve * m_ffactor_calc(hhe) * gve
    end if

    ! セル境界での抗力項
    !   摩擦項と一緒に半陰解法で計算するため、次元が他の項と異なる(値は常に正)
    tfe = tfe - p%kk * p%cd * hhe / bbe * (1 - gve) * vve / 2

    ! 土石流の降伏抵抗(db_res>=1)
    !   速度非依存の降伏減速度 a_y を半陰解法に合成(÷|V| で次元を合わせる)
    if (aye > 0.0) tfe = tfe - aye / max(vve, p%vv)

    ! l段目の時間刻み
    dtl = p%dt / a(l) / lme

    ! セル境界での流速(符合は中心セルから近傍セルに向かい正)を更新
    !   摩擦項を半陰解法で計算する
    !   どちらも中心セルから近傍セルに向かい正
    uve1 = (uve0 + (tae + tge) * dtl) / (1 - tfe * dtl)

    ! 乾燥セルへ向かうエッジ水深のエネルギー頭による頭打ち(§68.16)
    !   受け手(流向の下流側)が乾燥(h < dd)のとき、運べる水深は送り手の
    !   エネルギー頭 η + u_n²/2g が受け手の地盤 z を超える分まで
    !   (Bernoulli。堰越流の越流水深と同じ考え方)。地盤が水面より低い
    !   通常の前縁では頭打ちが効かず現状と厳密に同じ。超えられないエッジは
    !   流速も 0 にして、再構成・移流に幻の流速が残らないようにする。
    !   移流項が圧力項に勝って水面より高い乾いた地盤へ水が登る漏れ
    !   (§68.15 の掘込水路の発散)を物理条件で塞ぐ
    if (f_dry_head_cap > 0) then
      if (uve1 > 0.0 .and. hn < p%dd) then
        he = min(he, max(s%z(i,j) + hc + uve1**2 / (2 * p%gg) - s%z(in,jn), 0.0))
        if (he <= 0.0) uve1 = 0.0
      else if (uve1 < 0.0 .and. hc < p%dd) then
        he = min(he, max(s%z(in,jn) + hn + uve1**2 / (2 * p%gg) - s%z(i,j), 0.0))
        if (he <= 0.0) uve1 = 0.0
      end if
    end if
    ! 送り手(流向の上流側)が完全に乾いた(h <= 0)エッジは流速・流量を 0 に
    ! する(§68.31)。壁なし幅モードの河道—乾いた堤内地エッジでは、高い地盤
    ! から河道へ向く圧力勾配が毎ステップ流速を生み、過大流出の抑制が
    ! cor = 0 で零化していた(結果は同値だが ex_flux / Runge の計数が壁エッジ
    ! 数で埋まり、RK 再計算が無駄になる)。符号つきゼロは抑制の uve1·0 と
    ! 同じにして出力の表記も揃える。流量 0 で流速だけ残るエッジ(he = 0)も
    ! 同時に零化される(再構成・移流に幻の流速を残さない)
    if (uve1 > 0.0 .and. s%h(i,j) <= 0.0) uve1 = sign(0.0, uve1)
    if (uve1 < 0.0 .and. s%h(in,jn) <= 0.0) uve1 = sign(0.0, uve1)
    ! 面流束 = 流速 × 断面積(単位幅あたり)。σ(断面形 §26)有効時は矩形
    ! 換算水深 vh = ∫σ dh(断面積/W)を使う(両セルの D で評価した平均。
    ! σ 非適用セルは sect_v が恒等)。真の水深 h で流すと貯留 W·vh に対して
    ! 通水能が (m+1) 倍になり、段落ち・自由流出で終端セルが抜け切って
    ! 発散する(§68.27・§68.28。2026-10-04 に u·h から変更)
    if (have_sect) then
      mne1 = uve1 * 0.5 * (sect_v(he, sdep(i,j)) + sect_v(he, sdep(in,jn)))
    else
      mne1 = uve1 * he
    end if

    ! 土石流の降伏判定(動き出し・停止): 低速かつ駆動(移流+重力)が
    ! 降伏減速度以下なら静止を維持する(半陰解法の漸近だけでは完全静止に
    ! ならないための明示的な零化。debris_plan.md §2.3)。
    !   低速の判定は辺の**速さ** |V|(vv0e)で行う。辺の法線成分 uve0 で
    !   判定すると、速い一方向流の横断方向の辺(法線成分 ≈ 0、横断駆動 <
    !   a_y)が毎ステップ零化され、行間の質量交換が凍結して横断方向に
    !   一様にならない(§28.11 の実バグ)。Coulomb 降伏は速度ベクトルの
    !   大きさに対する条件で、動いている流れの一成分には掛からない
    if (aye > 0.0) then
      if (vv0e < db_vstop .and. abs(tae + tge) <= aye) then
        uve1 = 0.0
        mne1 = 0.0
      end if
    end if

    ! これ以降はルンゲクッタ最終段(陽的オイラー)では不要
    if (l >= 4) exit

    ! ルンゲクッタの次段のために流速の絶対値と水深を更新
    !   移流項はルンゲクッタのループに含まれないため精度は陽的オイラーのまま
    block
      integer :: kk
      real :: mnec, mnen
      real :: fwc, fwn
      real :: winvc, winvn
      integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
      real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]
      ! セル境界での流速の絶対値を更新
      vve = sqrt(uve1**2 + vue2)

      ! 河道幅有効時のセル平面積率の逆数(無効時は 1.0 の乗算で厳密に不変)
      winvc = 1.0
      winvn = 1.0
      if (have_width) then
        winvc = 1.0 / wfrac(i,j)
        winvn = 1.0 / wfrac(in,jn)
      end if

      ! 仮の水深を更新
      !   式の詳細は連続式を解くルーチン内のコメントを参照のこと
      if (have_sect .and. f_sect_rk) then
        ! σ 有効(かつ RK 再評価オン)時: vh 増分を積算してから逆変換する
        ! (§26。f_sect_rk=.false. なら下の従来経路=RK 中は矩形近似)
        block
          real :: dvc, dvn
          dvc = 0.0
          dvn = 0.0
          do kk = 1, 8
            mnec = sign_e(kk) * sx%mn(ke(kk),i+die(kk),j+dje(kk))
            mnen = sign_e(kk) * sx%mn(ke(kk),in+die(kk),jn+dje(kk))
            if (kk == k) mnec = mne1
            if (kk == 9 - k) mnen = -mne1
            fwc = 1.0
            fwn = 1.0
            if (have_frw) then
              fwc = frw(ke(kk),i+die(kk),j+dje(kk))
              fwn = frw(ke(kk),in+die(kk),jn+dje(kk))
            end if
            if (have_fwd) then
              fwc = fwc * fwd(ke(kk),i+die(kk),j+dje(kk))
              fwn = fwn * fwd(ke(kk),in+die(kk),jn+dje(kk))
            end if
            dvc = dvc + mnec * mn2dh(kk) * fwc * winvc / s%gv(i,j) / a(l)
            dvn = dvn + mnen * mn2dh(kk) * fwn * winvn / s%gv(in,jn) / a(l)
          end do
          hc = sect_hinv(sect_v(hc0, sdep(i,j)) - dvc, sdep(i,j))
          hn = sect_hinv(sect_v(hn0, sdep(in,jn)) - dvn, sdep(in,jn))
        end block
      else
      hc = hc0       ! 中心セルの水深
      hn = hn0       ! 近傍セルの水深
      do kk = 1, 8
        ! 中心セルと近傍セルの方位kkにおける流量
        !   前ステップ確定値(無印mn)を参照する。更新中のmn1を読むと
        !   スレッドタイミング依存のデータ競合になる(developer.md §8)
        mnec = sign_e(kk) * sx%mn(ke(kk),i+die(kk),j+dje(kk))   ! 中心セルからそのkk近傍への流量
        mnen = sign_e(kk) * sx%mn(ke(kk),in+die(kk),jn+dje(kk)) ! 近傍セルからそのkk近傍への流量
        ! 方位k(近傍セルでは方位9-k)は今回更新された流量
        if (kk == k) mnec = mne1
        if (kk == 9 - k) mnen = -mne1     ! 近傍セルの流出量は中心セルの流出量の逆符号
        ! 通過幅係数有効時はエッジ別係数を乗じる(無効時は 1.0 の
        ! 乗算で厳密に不変)
        fwc = 1.0
        fwn = 1.0
        if (have_frw) then
          fwc = frw(ke(kk),i+die(kk),j+dje(kk))
          fwn = frw(ke(kk),in+die(kk),jn+dje(kk))
        end if
        if (have_fwd) then
          fwc = fwc * fwd(ke(kk),i+die(kk),j+dje(kk))
          fwn = fwn * fwd(ke(kk),in+die(kk),jn+dje(kk))
        end if
        ! 仮の水深を更新
        hc = hc - mnec * mn2dh(kk) * fwc * winvc / s%gv(i,j) / a(l)
        hn = hn - mnen * mn2dh(kk) * fwn * winvn / s%gv(in,jn) / a(l)
      end do
      end if
    end block

    ! 段数を更新して次の段へ
    l = l + 1
  end do

  ! 最終段のエッジ水深を返す(mne1 = uve1·he の he)
  hee = he

contains
  !--------------------------------------------------------------------
  ! セル境界水深が上流側水深よりも深くならないよう調整
  function correct_he() result(he_corr)
    real :: he_corr
    ! f_hcap_upwind=1: 両側平均を上流側水深で頭打ち(既定)
    ! f_hcap_upwind=2: 上流側水深そのもの(Stelling & Duinmeijer の連続式。
    !   段波先端で両側平均が小さくなり、平坦区間の流量を通すために前線
    !   エッジの流速が過大になって手前の 1 セルに水が積み上がるスパイクを
    !   防ぐ。乾湿前縁では乾側 h≈0 に対して湿側水深で流出するため前縁の
    !   挙動が変わる。§68.7)
    if (uve0 > 0) then      ! 中心セルが上流側
      if (f_hcap_upwind == 2) then
        he_corr = hc
      else
        he_corr = min(he, hc)    !   中心セルの水深より深くならないように
      end if
    else if (uve0 < 0) then ! 近傍セルが上流側
      if (f_hcap_upwind == 2) then
        he_corr = hn
      else
        he_corr = min(he, hn)    !   近傍セルの水深より深くならないように
      end if
    else
      he_corr = he
    end if
  end function
  !--------------------------------------------------------------------
  ! 重力加速度を急勾配地形に合わせて調整
  !   Ni, Y., Cao, Z., & Liu, Q. (2019). 
  !     Mathematical modeling of shallow-water flows on steep slopes.
  !     Journal of Hydrology and Hydromechanics, 67(3), 252–259. DOI:10.2478/johh-2019-0012
  function correct_ge() result(ge_corr)
    real :: ge_corr
    if (vve > 0) then
      ge_corr = ge * w8dr2(k) / (w8dr2(k) + (s%z(in,jn) - s%z(i,j))**2)
    else
      ge_corr = ge
    end if
  end function

end subroutine


!----------------------------------------------------------------------
! 連続式による水深の更新と平均流速・流量の計算
!----------------------------------------------------------------------
subroutine continuous(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(inout) :: sx

  integer :: i, j, k
  integer :: in, jn, ie, je
  real :: uve, mne
  real :: dh
  real :: fw, winv
  real :: mnmax
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]

  !$omp parallel do schedule(dynamic) private(i, j, k, in, jn, ie, je, uve, mne, dh, fw, winv, mnmax)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%sw(i,j) > 0) cycle
      if (g%x(i,j) <= 0) cycle
      s%u(i,j) = 0
      s%v(i,j) = 0
      s%m(i,j) = 0
      s%n(i,j) = 0
      ! σ 有効時は h1 を矩形換算水深 vh で初期化(非適用セルは恒等。§26)
      if (have_sect) then
        sx%h1(i,j) = sect_v(s%h(i,j), sdep(i,j))
      else
        sx%h1(i,j) = s%h(i,j)
      end if
      ! 河道幅有効時のセル平面積率の逆数(無効時は 1.0 の乗算で厳密に不変)
      winv = 1.0
      if (have_width) winv = 1.0 / wfrac(i,j)
      mnmax = 0
      ! 対象セルi,jの8近傍全ての水の流出入を計算し平均流量・流速と水位を更新する
      s%ddir1(i,j) = 0
      s%ddir8(i,j) = 0
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) > 0) then
          ! ここでddと比較するのは前時間ステップでの値hでなければならない
          ! そのためこのループ内でhを直接更新してはいけない
          if (s%h(i,j) < p%dd .and. s%h(in,jn) < p%dd) cycle
        else
          ! 開いた辺の境界面は取り込む(流出が h1 と u,v,m,n に乗る)。
          ! 枠外近傍の s%h は確保範囲外のため dd 判定はしない
          ! (乾燥時は boundary_uvmn が 0 を書いており寄与も 0)
          if (.not. have_open_bc) cycle
          if (.not. bc_open_face(in, jn)) cycle
        end if
        ! 中心セルi,jから見たk近傍の境界フラックスのインデックス
        ie = i + die(k)
        je = j + dje(k)
        ! 境界での流速と流量を求める(中心から近傍に向かい正)
        !   近傍5~8は隣接するセルから見た(9-k)近傍に相当する(向きは逆)
        uve = sign_e(k) * sx%uv(ke(k),ie,je)
        mne = sign_e(k) * sx%mn1(ke(k),ie,je)
        ! 通過幅係数有効時はエッジ別係数を乗じる(無効時は 1.0 の
        ! 乗算で厳密に不変。質量換算と平均量の重みを同時に補正する)
        fw = 1.0
        if (have_frw) fw = frw(ke(k),ie,je)
        if (have_fwd) fw = fw * fwd(ke(k),ie,je)
        ! 水深の減少量(m)に換算
        !   家屋占有率が0.0で無い場合はここで補正係数を乗じる。
        !   河道幅有効時は平面積率 wfrac の逆数 winv も乗じる
        dh = mne * mn2dh(k) * fw * winv / s%gv(i,j)
        ! 水深を更新
        sx%h1(i,j) = sx%h1(i,j) - dh
        ! セル中心の平均流速・流量への寄与分を加算
        s%u(i,j) = s%u(i,j) + uve * (w8mx(k) * fw)
        s%v(i,j) = s%v(i,j) + uve * (w8my(k) * fw)
        s%m(i,j) = s%m(i,j) + mne * (w8mx(k) * fw)
        s%n(i,j) = s%n(i,j) + mne * (w8my(k) * fw)
        ! 流下方向を判定
        !if (mne > mnmax) s%ddir1(i,j) = 2**k             ! 最大流出方向
        if (mne > mnmax) then
          s%ddir1(i,j) = 2**k             ! 最大流出方向
          mnmax = mne
        end if
        if (dh > 0) s%ddir8(i,j) = s%ddir8(i,j) + 2**k   ! 全ての流出方向
      end do
      ! 河道幅有効セルは u,v をセル方向別通水率で正規化する(vv・摩擦・
      ! 抗力・移流が河道内流速を見る。m,n は流量積分の意味論を保つため
      ! 正規化しない=フラックス測線の実流量が保たれる条件。§18)
      ! σ 有効時はここでは正規化しない: この後の boundary_h・dam が h1 を
      ! さらに更新するため、確定水深 h(n+1) の σ で complete が正規化する
      ! (u,v と h の時刻整合、かつ restore_uvmn が保存 h から厳密に
      ! 再現できる条件。§26)
      if (have_width .and. .not. have_sect) then
        if (have_cwd) then
          s%u(i,j) = s%u(i,j) / cwxd(i,j)
          s%v(i,j) = s%v(i,j) / cwyd(i,j)
        else
          s%u(i,j) = s%u(i,j) / cwx(i,j)
          s%v(i,j) = s%v(i,j) / cwy(i,j)
        end if
      end if
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! 変数の更新
!----------------------------------------------------------------------
subroutine complete(p, g, s, sx, initial)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(inout) :: sx
  ! initial=.true. は init 末尾からの呼び出し(σ 有効時のみ意味を持つ):
  !   σ 適用セルでは h が正準(初期条件・復元状態)なので h1→h の逆変換
  !   コミットをせず、u,v の正規化もしない(初期条件・restore_uvmn が
  !   正規化済みの値を持つ)。恒等コミットに見えて hinv(h) を書いてしまい
  !   復元水深が最大 D·m/(m+1) 膨張する実バグの対策(hs1 の複製初期化と
  !   同族の問題。§26)
  logical, intent(in), optional :: initial
  integer :: i, j
  logical :: linit
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  linit = .false.
  if (present(initial)) linit = initial

  ! 流量のコミット: 時刻n+1の値を正準状態へ(セルの h1→h と対をなす)
  !   エッジの書き込み集合はセル窓より i,j とも1つ外側(die/dje=-1)に
  !   張り出すため、セルループに畳み込まず、行範囲 js-1..je で行う。
  !   ここでは行丸ごとメモリ転送するのでschedule(static)でよい
  !$omp parallel do schedule(static)
  do j = dcp%js - 1, dcp%je
    sx%mn(:,:,j) = sx%mn1(:,:,j)
  end do
  !$omp end parallel do

  !$omp parallel do schedule(dynamic) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      ! σ 有効時は矩形換算水深 vh から真の水深へ逆変換(非適用セルは恒等。§26)
      if (have_sect) then
        if (linit) then
          ! init 呼び出し: σ 適用セルは h が正準(h1 は seeding 済みで
          ! boundary_h の init 時実効対象はため池 = sdep=0 のみ)。
          ! sdep=0 セルは従来通り h1 をコミット(ため池初期吸収の反映)
          if (sdep(i,j) <= 0.0) s%h(i,j) = sx%h1(i,j)
        else
          s%h(i,j) = sect_hinv(sx%h1(i,j), sdep(i,j))
          ! u,v の正規化はここでは行わない: complete の後に h を変える
          ! モジュール(gwflow/evap)があるため、最終確定 h の σ で
          ! ステップ末尾パス m_swflow_enc_post が1回だけ行う(§26。
          ! ここで計算する vv は暫定値で、post が正規化後に上書きする)
        end if
      else
        s%h(i,j) = sx%h1(i,j)
      end if
      s%e(i,j) = s%h(i,j) + s%z(i,j)
      s%vv(i,j) = sqrt(s%u(i,j)**2 + s%v(i,j)**2)
      s%qq(i,j) = sqrt(s%m(i,j)**2 + s%n(i,j)**2)
    end do
  end do
  !$omp end parallel do

  ! 浮遊砂柱状量のコミット(セルの h1→h と同じ意味論。範囲・スキップは
  ! advect_scalar の書き込み集合と一致させる — 海セルは移流対象外)
  if (s%sed_active) then
    !$omp parallel do schedule(dynamic) private(i, j)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        s%hs(i,j) = sx%hs1(i,j)
      end do
    end do
    !$omp end parallel do
  end if

  ! 輸送物質柱状量のコミット(hs と同じ意味論。§30)
  if (s%wq_active) then
    !$omp parallel do schedule(dynamic) private(i, j)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        s%cq(i,j) = sx%cq1(i,j)
      end do
    end do
    !$omp end parallel do
  end if

  ! 地表塩水層厚のコミット(hs と同じ意味論。§47)
  if (s%salt_active) then
    !$omp parallel do schedule(dynamic) private(i, j)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        s%hss(i,j) = sx%hss1(i,j)
      end do
    end do
    !$omp end parallel do
  end if

  ! 流動流木柱状量のコミット(hs と同じ意味論。§50)
  if (s%dw_active) then
    !$omp parallel do schedule(dynamic) private(i, j)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        s%hd(i,j) = sx%hd1(i,j)
      end do
    end do
    !$omp end parallel do
  end if

  ! 流動瓦礫柱状量のコミット(同上。§63)
  if (s%bd_active) then
    !$omp parallel do schedule(dynamic) private(i, j)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        s%hbd(i,j) = sx%hbd1(i,j)
      end do
    end do
    !$omp end parallel do
  end if

  ! 実効平面積率 af の更新(§25/§26。幅・σ・可動 gv のいずれも無効なら
  ! af=gv のまま不変)
  if (have_width .or. have_sect .or. s%gv_active) call update_af(g, s)

end subroutine


!----------------------------------------------------------------------
! 柱状量スカラーの保存輸送(汎用カーネル。利用者第1号は浮遊砂 s%hs)
!   連続式(continuous)と同一のエッジ流量 mn1・通過幅係数 fw・
!   平面積率逆数 winv・空隙率 gv で風上輸送する。係数が完全に一致する
!   ため「一様濃度 c/h は一様のまま」が式の形で保証される。
!   契約(geomorph_plan.md §2.6):
!     - c は柱状量(セル平面積あたりの量。貯留の意味論は h と同一)。
!       単位は所有者が決める(線形輸送のため単位不問)。濃度 = c/h は導出量
!     - 読み: 時刻 n の s%h と c(ハロ行含む。ステップ頭交換が前提)、
!       sx%mn1(par_edge_merge・boundary_uvmn 適用後 = continuous と同一)
!     - 書き: c1 の自帯 js..je(海・域外セルは書かない。コミットは所有者)
!     - 源泉・消滅・乾燥時の処遇は所有モジュールの責務(ここは純移流)
!     - 風上セルが領域外(開境界からの流入)の濃度は 0(清水流入)
!     - 乾燥エッジ条件(h<dd 両セル)は continuous と同一。強い乾燥化では
!       h1 同様に c1 も僅かに負になり得る(f_exflux_reduction=1 で緩和)
!----------------------------------------------------------------------
subroutine advect_scalar(p, g, s, sx, c, c1, cbin, share)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  real, intent(in) :: c(1:, dcp%jsh:)
  real, intent(inout) :: c1(1:, dcp%jsh:)
  real, intent(in), optional :: cbin(1:, dcp%jsh:)   ! 境界流入濃度(セル別)
  real, intent(in), optional :: share                ! 移流分担率(省略時 1.0。
                                                     !   底層スカラーの流速分担。§47)
  integer :: i, j, k
  integer :: in, jn, ie, je
  real :: mne, fw, winv, cdon, sh
  logical :: has_cbin
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]

  has_cbin = present(cbin)
  sh = 1.0
  if (present(share)) sh = share

  !$omp parallel do schedule(dynamic) private(i, j, k, in, jn, ie, je, mne, fw, winv, cdon)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%sw(i,j) > 0) cycle
      if (g%x(i,j) <= 0) cycle
      c1(i,j) = c(i,j)
      ! 河道幅有効時のセル平面積率の逆数(無効時は 1.0 の乗算で厳密に不変)
      winv = 1.0
      if (have_width) winv = 1.0 / wfrac(i,j)
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) > 0) then
          ! 乾燥エッジ判定は時刻 n の h(continuous と同一の条件)
          if (s%h(i,j) < p%dd .and. s%h(in,jn) < p%dd) cycle
        else
          ! 開いた辺の境界面は取り込む(continuous と同一)
          if (.not. have_open_bc) cycle
          if (.not. bc_open_face(in, jn)) cycle
        end if
        ie = i + die(k)
        je = j + dje(k)
        mne = sign_e(k) * sx%mn1(ke(k),ie,je)
        if (mne == 0.0) cycle
        ! 風上(donor)セルの濃度。境界面からの流入は cbin(区間流入の
        ! 濃度時系列等)があればセル値、なければ清水 = 0
        ! 濃度は水の体積あたり = 柱状量 / 矩形換算水深 vh(σ 非適用セルは
        ! vh = h で従来と同値。面流束が u·vh なので、供給元濃度を c/vh に
        ! すると流束が u·c = 「スカラーは水と同じ速度で動く」になる。§26)
        cdon = 0.0
        if (mne > 0.0) then
          if (s%h(i,j) > 0.0) then
            if (have_sect) then
              cdon = c(i,j) / sect_v(s%h(i,j), sdep(i,j))
            else
              cdon = c(i,j) / s%h(i,j)
            end if
          end if
        else
          if (g%x(in,jn) > 0) then
            if (s%h(in,jn) > 0.0) then
              if (have_sect) then
                cdon = c(in,jn) / sect_v(s%h(in,jn), sdep(in,jn))
              else
                cdon = c(in,jn) / s%h(in,jn)
              end if
            end if
          else
            if (has_cbin) cdon = cbin(i,j)
          end if
        end if
        if (cdon == 0.0) cycle
        ! 通過幅係数(continuous と同一)
        fw = 1.0
        if (have_frw) fw = frw(ke(k),ie,je)
        if (have_fwd) fw = fw * fwd(ke(k),ie,je)
        c1(i,j) = c1(i,j) - mne * cdon * sh * mn2dh(k) * fw * winv / s%gv(i,j)
      end do
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! restoreしたsx%uv,sx%mnからs%u,s%v,s%m,s%n,s%vv,s%qq,s%eを復元する
!   (vv は摩擦項が complete より前に読む、qq は t=0 の出力・計測が読む)
!   セルループの範囲・スキップ・重み・総和順は continuous と完全に
!   一致させること(復元値が保存時の値とビット一致する条件)。
!   continuous にある乾燥エッジ条件(h<dd 両セル)の複製は不要:
!   momentum が同条件のエッジの uv/mn1 を 0 に零化しているため、
!   無条件に総和しても寄与が 0 でスキップと同値になる
!----------------------------------------------------------------------
!----------------------------------------------------------------------
! 塞がれた開口の動的振り替え表 fwd の構築(developer.md §68.14)
!   静的 build_channel_frw(堤防壁)と同じ振り替え規則を、塞がり率
!   s = clamp((z_n − z_c)/h_c, 0, 1) の実数版で毎ステップ適用する。
!   エッジの格納: 成分4 (i,j)-(i+1,j)、成分2 (i,j)-(i,j+1)、
!   成分1 (i,j)-(i+1,j+1)、成分3 (i,j+1)-(i+1,j)。
!   読み手(連続式・運動量の仮水深・再構成)は帯セル js..je とその
!   8近傍のエッジを読む → エッジ行 js-2..je+1(成分4は js-1..je+1)、
!   斜め先セル行 js-2..je+2 = セルハロ幅 2(jsh..jeh)に収まる(frw と
!   同じ確保範囲)。
!   各 (k,ie,je) の書き手は 1 つ(行 je のループ)= OpenMP 競合なし。
!   全ランクがハロ交換済みの h, z から同じ式で冗長構築する(決定的)。
!----------------------------------------------------------------------
subroutine build_fwd(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: i, j, jlo, jhi
  real :: nb, sh, s1d
  logical :: ok_c, ok_n

  if (p%initialized) continue  ! 引数未使用の警告を抑制
  ! 斜めの振り替え量: 斜め先 1 つあたり (自然幅 − l8_d)/2(静的規則と同形)
  s1d = (g%dx * g%dy / sqrt(g%dx**2 + g%dy**2) - l8(1)) / 2
  jlo = max(dcp%js - 2, 1)
  jhi = min(dcp%je + 1, g%ny)

  !$omp parallel do schedule(static) private(j)
  do j = dcp%jsh - 1, dcp%jeh
    fwd(:, :, j) = 1.0
  end do
  !$omp end parallel do

  !$omp parallel do schedule(dynamic) private(i, j, nb, sh, ok_c, ok_n)
  do j = jlo, jhi
    do i = 1, g%nx
      ok_c = fwd_cell(g, i, j)
      ! 成分4: (i,j)-(i+1,j)。斜め先は (i+1,j±1)(自セル側)と (i,j±1)(近傍側)
      !   読み手が参照する成分4の行は js-1..je+1(行 js-2 の成分4は近傍セル
      !   の 8 近傍にも含まれない)。行 js-2 で計算すると斜め先 js-3 が
      !   セル確保範囲 jsh の外になるため除く
      if (i < g%nx .and. j >= dcp%js - 1) then
        ok_n = fwd_cell(g, i+1, j)
        if (ok_c .and. ok_n .and. fwd_pair(g, i, j, i+1, j)) then
          nb = (sblk(g, s, i, j, i+1, j-1) + sblk(g, s, i, j, i+1, j+1) &
              + sblk(g, s, i+1, j, i, j-1) + sblk(g, s, i+1, j, i, j+1)) / 2
          if (nb > 0) fwd(4,i,j) = (lpy + nb * ldy) / lpy
        end if
      end if
      if (j < g%ny) then
        ! 成分2: (i,j)-(i,j+1)。斜め先は (i±1,j+1) と (i±1,j)
        ok_n = fwd_cell(g, i, j+1)
        if (ok_c .and. ok_n .and. fwd_pair(g, i, j, i, j+1)) then
          nb = (sblk(g, s, i, j, i-1, j+1) + sblk(g, s, i, j, i+1, j+1) &
              + sblk(g, s, i, j+1, i-1, j) + sblk(g, s, i, j+1, i+1, j)) / 2
          if (nb > 0) fwd(2,i,j) = (lpx + nb * ldx) / lpx
        end if
        if (i < g%nx) then
          ! 成分1: (i,j)-(i+1,j+1)。両端が共有する側方セル (i+1,j), (i,j+1)
          if (ok_c .and. fwd_cell(g, i+1, j+1) .and. fwd_pair(g, i, j, i+1, j+1)) then
            sh = (sblk(g, s, i, j, i+1, j) + sblk(g, s, i, j, i, j+1) &
                + sblk(g, s, i+1, j+1, i+1, j) + sblk(g, s, i+1, j+1, i, j+1)) / 2 * s1d
            if (sh > 0 .and. l8(1) > 0) fwd(1,i,j) = 1.0 + sh / l8(1)
          end if
          ! 成分3: (i,j+1)-(i+1,j)。共有する側方セル (i+1,j+1), (i,j)
          if (ok_n .and. fwd_cell(g, i+1, j) .and. fwd_pair(g, i, j+1, i+1, j)) then
            sh = (sblk(g, s, i, j+1, i+1, j+1) + sblk(g, s, i, j+1, i, j) &
                + sblk(g, s, i+1, j, i+1, j+1) + sblk(g, s, i+1, j, i, j)) / 2 * s1d
            if (sh > 0 .and. l8(3) > 0) fwd(3,i,j) = 1.0 + sh / l8(3)
          end if
        end if
      end if
    end do
  end do
  !$omp end parallel do
end subroutine


! 動的振り替えの対象になりうるセルか(有効な陸セル)
function fwd_cell(g, i, j) result(res)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i, j
  logical :: res
  res = g%x(i,j) > 0 .and. g%sw(i,j) == 0
end function


! エッジ (i1,j1)-(i2,j2) が適用範囲か(f_opening_dynamic=1 は両端が河道セル)
function fwd_pair(g, i1, j1, i2, j2) result(res)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i1, j1, i2, j2
  logical :: res
  res = .true.
  if (f_opening_dynamic == 1) res = g%rw(i1,j1) > 0 .and. g%rw(i2,j2) > 0
end function


!----------------------------------------------------------------------
! セル (ic,jc) から見た斜め先セル (id,jd) の塞がり率 s(0〜1)
!   領域外・無効セル = 壁(1)。海セル = 開水面(0)。堤防壁で静的に
!   振り替え済みの堤内地セル(have_bopen)は数えない(0)。それ以外は
!   s = clamp((z_d − z_c)/h_c, 0, 1): 水面が斜め先の地盤より低ければ 1、
!   地盤を越えた分は斜めが運ぶので地盤より下の水柱の割合だけ塞がる
!----------------------------------------------------------------------
function sblk(g, s, ic, jc, id, jd) result(res)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: ic, jc, id, jd
  real :: res
  real :: dz, hc
  res = 1.0
  if (id < 1 .or. id > g%nx .or. jd < 1 .or. jd > g%ny) return
  if (g%x(id,jd) <= 0) return
  res = 0.0
  if (g%sw(id,jd) > 0) return
  if (have_bopen) then
    if (g%rw(id,jd) <= 0 .and. is_wall(g%zbank(ic,jc), s%z(ic,jc), s%z(id,jd))) return
  end if
  dz = s%z(id,jd) - s%z(ic,jc)
  if (dz <= 0.0) return
  hc = s%h(ic,jc)
  if (hc <= dz) then
    res = 1.0
  else
    res = dz / hc
  end if
end function


!----------------------------------------------------------------------
! 河道セルの天端 zb が地盤 zc(河床)と zl(堤内地)の両方より高いとき
! だけ、そのエッジに堤防壁がある(§68.29 (B))。天端が地盤以下の部分は
! 地盤そのものが段差として通常計算(SWE)に入り、堤防としては非実体。
! bank_wall(動的 s%z)・静的開口表(g%z)・動的開口 sblk(s%z)・
! 通水率 build_cw/cw_cell(g%z)の壁判定はすべてこの述語を使う
!----------------------------------------------------------------------
pure function is_wall(zb, zc, zl) result(res)
  real, intent(in) :: zb, zc, zl
  logical :: res
  res = zb > zbank_min .and. zb > max(zc, zl)
end function


subroutine restore_uvmn(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(inout) :: sx
  integer :: i, j, k
  integer :: in, jn, ie, je
  real :: uve, mne
  real :: fw
  real :: cxv, cyv
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  !$omp parallel do schedule(dynamic) private(i, j, k, in, jn, ie, je, uve, mne, fw, cxv, cyv)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%sw(i,j) > 0) cycle   ! 海セルは continuous 同様に除外(u,v,m,n,vv,qq は 0 のまま)
      if (g%x(i,j) <= 0) cycle
      s%u(i,j) = 0.0
      s%v(i,j) = 0.0
      s%m(i,j) = 0.0
      s%n(i,j) = 0.0
      do k = 1, 8
        ! 中心セルi,jから見たk近傍セルのインデックス
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) then
          ! 開いた辺の境界面は continuous と同様に取り込む
          ! (取り込み条件は continuous と常に同時に更新すること)
          if (.not. have_open_bc) cycle
          if (.not. bc_open_face(in, jn)) cycle
        end if
        ! 中心セルi,jから見たk近傍の境界フラックスのインデックス
        ie = i + die(k)
        je = j + dje(k)
        ! 境界での流速と流量を求める(中心から近傍に向かい正)
        !   近傍5~8は隣接するセルから見た(9-k)近傍に相当する(向きは逆)
        uve = sign_e(k) * sx%uv(ke(k),ie,je)
        mne = sign_e(k) * sx%mn1(ke(k),ie,je)
        ! 通過幅係数は continuous と完全に一致させる(復元ビット一致の条件)
        fw = 1.0
        if (have_frw) fw = frw(ke(k),ie,je)
        if (have_fwd) fw = fw * fwd(ke(k),ie,je)
        ! セル中心の平均流速・流量への寄与分を加算
        s%u(i,j) = s%u(i,j) + uve * (w8mx(k) * fw)
        s%v(i,j) = s%v(i,j) + uve * (w8my(k) * fw)
        s%m(i,j) = s%m(i,j) + mne * (w8mx(k) * fw)
        s%n(i,j) = s%n(i,j) + mne * (w8my(k) * fw)
      end do
      ! u,v の正規化は正規化の実施箇所と完全に一致させる(復元ビット一致の
      ! 条件): σ 無効時は continuous(静的 cw)、σ 有効時は complete が
      ! 確定水深 h(n+1) の σ で行う。保存された s%h は最終ステップの
      ! h(n+1) なので、ここでの σ(s%h) 再評価は保存時の正規化と厳密に
      ! 同一の式・同一の引数になる(§26)
      if (have_width .and. have_cwd) then
        s%u(i,j) = s%u(i,j) / cwxd(i,j)
        s%v(i,j) = s%v(i,j) / cwyd(i,j)
      else if (have_width) then
        if (have_sect) then
          if (sdep(i,j) > 0.0) then
            ! 2026-10-04(§68.28): 面流束を断面積ベース u·vh にしたため、
            ! エッジ流速 = 河道内流速で、正規化の通水率は静的 cw と同じ
            ! (cw_cell は sig を無視して静的 cwx/cwy と同値を返す)
            call cw_cell(g, i, j, sect_sigma(s%h(i,j), sdep(i,j)), cxv, cyv)
          else
            cxv = cwx(i,j)
            cyv = cwy(i,j)
          end if
          s%u(i,j) = s%u(i,j) / cxv
          s%v(i,j) = s%v(i,j) / cyv
        else
          s%u(i,j) = s%u(i,j) / cwx(i,j)
          s%v(i,j) = s%v(i,j) / cwy(i,j)
        end if
      end if
      s%e(i,j) = s%h(i,j) + s%z(i,j)
      s%vv(i,j) = sqrt(s%u(i,j)**2 + s%v(i,j)**2)
      s%qq(i,j) = sqrt(s%m(i,j)**2 + s%n(i,j)**2)
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine save_state(p, sx)
  type(t_sysparam), intent(in) :: p
  type(t_enc_status), intent(in) :: sx
  integer :: un, ifwd, icw
  real, allocatable :: wuv(:,:,:), wmn(:,:,:), wfd(:,:,:), wcx(:,:), wcy(:,:)
  ! 全域バッファに集約してから rank0 のみが書く。
  ! バッファ形状・帯外ゼロとも旧形式(全域確保時)とバイト互換
  if (is_root) then
    allocate(wuv(1:4, 0:dcp%nx_g, 0:dcp%ny_g), source = 0.0)
    allocate(wmn(1:4, 0:dcp%nx_g, 0:dcp%ny_g), source = 0.0)
  else
    allocate(wuv(1, 1, 1), source = 0.0)   ! 参照されないダミー
    allocate(wmn(1, 1, 1), source = 0.0)
  end if
  call par_gather_edge_to(wuv, sx%uv)
  call par_gather_edge_to(wmn, sx%mn)
  ! 動的振り替えの表 fwd(最終ステップの連続式が使ったステップ頭 h^n の表)。
  ! 復元時の u,v,m,n 再導出をビット一致にするために保存する(§68.14。
  ! 有効判定は namelist 由来で全ランク同一 = collective 安全)
  ifwd = 0
  if (have_fwd) then
    ifwd = 1
    if (is_root) then
      allocate(wfd(1:4, 0:dcp%nx_g, 0:dcp%ny_g), source = 1.0)
    else
      allocate(wfd(1, 1, 1), source = 1.0)
    end if
    call par_gather_edge_to(wfd, fwd)
  end if
  icw = 0
  if (have_cwd) then
    icw = 1
    if (is_root) then
      allocate(wcx(1:dcp%nx_g, 1:dcp%ny_g), source = 1.0)
      allocate(wcy(1:dcp%nx_g, 1:dcp%ny_g), source = 1.0)
    else
      allocate(wcx(1, 1), source = 1.0)
      allocate(wcy(1, 1), source = 1.0)
    end if
    call par_gather_to(wcx, cwxd)
    call par_gather_to(wcy, cwyd)
  end if
  if (.not. is_root) return
  ! swflow の dispose は m_state より先に走るため、save ディレクトリは
  ! ここでも作る(sysdep_mkdir は冪等・rank0 限定)
  call sysdep_mkdir(p%dir_save)
  open(newunit=un, file=trim(p%dir_save)//'/swflow_enc.dat', form='unformatted', status='replace')
  ! ゼロ抑制 RLE で書く(乾燥エッジ・海域エッジのゼロを圧縮。§7)
  call fileio_write_rle(un, wuv)
  call fileio_write_rle(un, wmn)
  ! 動的振り替えの表の有無(0/1)と表(2026-10-04 の形式。§7)
  write(un) ifwd
  if (ifwd == 1) call fileio_write_rle(un, wfd)
  ! 動的通水率 cwxd/cwyd の有無(0/1)と表(§68.32。2026-10-04b の形式)
  write(un) icw
  if (icw == 1) then
    call fileio_write_rle(un, wcx)
    call fileio_write_rle(un, wcy)
  end if
  close(un)
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine restore_state(p, sx)
  type(t_sysparam), intent(in) :: p
  type(t_enc_status), intent(inout) :: sx
  integer :: un, ios
  integer :: nfl(1), ncw(1)
  real, allocatable :: wuv(:,:,:), wmn(:,:,:), wfd(:,:,:), wcx(:,:), wcy(:,:)
  character(:), allocatable :: fname
  logical :: found

  ! 版・格子・精度の検証は m_state(check_save_info)が済ませている。
  ! ここでは自ファイルの有無のみ確認する(developer.md §7)。
  ! 無い場合は黙ってスキップせず停止(保存時の格子系が ENC でない疑い)
  fname = trim(p%dir_save)//'/swflow_enc.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("swflow: state file not found " &
                  //"(was the state saved with the ENC grid system): "//fname)
  end if

  ! rank0 だけが全域一時配列に読み、par_scatter_edge で各ランクの
  ! エッジ確保範囲(jsh-1:jeh)へ直接配布する(旧 Bcast 方式の置き換え。
  ! 非 root は全域一時を確保しない。全域一時が rank0 に残るのは
  ! RLE ストリームが先頭からの逐次展開のため。developer.md §7)
  nfl(1) = 0
  if (is_root) then
    allocate(wuv(1:4, 0:dcp%nx_g, 0:dcp%ny_g), source = 0.0)
    allocate(wmn(1:4, 0:dcp%nx_g, 0:dcp%ny_g), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wuv)
    call fileio_read_rle(un, wmn)
    ! 動的振り替えの表の有無フラグ(2026-10-04 の形式。版検査済みのため
    ! 欠如はないはずだが、読めなければ「なし」として復元した h から作る)
    read(un, iostat=ios) nfl(1)
    if (ios /= 0) nfl(1) = 0
  else
    allocate(wuv(1, 1, 1), source = 0.0)   ! 参照されないダミー
    allocate(wmn(1, 1, 1), source = 0.0)
  end if
  call par_scatter_edge(wuv, sx%uv)
  call par_scatter_edge(wmn, sx%mn)
  sx%mn1(:,:,:) = sx%mn(:,:,:)   ! 書き込みバッファも正準状態で初期化する
  ! フラグを全ランクで共有する(rank0 以外は 0 を持ち寄るので和 = フラグ)。
  ! 表は復元側で動的振り替えが有効なときだけ読んで配布する(無効なら
  ! 読まずに捨てる = ファイル末尾の余りは無害)
  call par_allreduce_sumi(nfl)
  fwd_restored = .false.
  if (have_fwd .and. nfl(1) == 1) then
    if (is_root) then
      allocate(wfd(1:4, 0:dcp%nx_g, 0:dcp%ny_g), source = 1.0)
      call fileio_read_rle(un, wfd)
    else
      allocate(wfd(1, 1, 1), source = 1.0)
    end if
    call par_scatter_edge(wfd, fwd)
    fwd_restored = .true.
  end if
  ! 動的通水率(§68.32)。fwd と同じ手順(rank0 が読み、フラグを和で共有、
  ! 有効時だけ配布)。fwd の表がファイルにあって復元側で無効なら読み飛ばす
  ! ために、フラグの前に表を読まずに済むよう順序は fwd → cw
  ncw(1) = 0
  if (is_root) then
    if (nfl(1) == 1 .and. .not. have_fwd) then
      allocate(wfd(1:4, 0:dcp%nx_g, 0:dcp%ny_g), source = 1.0)
      call fileio_read_rle(un, wfd)       ! 読み飛ばし
    end if
    read(un, iostat=ios) ncw(1)
    if (ios /= 0) ncw(1) = 0
  end if
  call par_allreduce_sumi(ncw)
  cwd_restored = .false.
  if (have_cwd .and. ncw(1) == 1) then
    if (is_root) then
      allocate(wcx(1:dcp%nx_g, 1:dcp%ny_g), source = 1.0)
      allocate(wcy(1:dcp%nx_g, 1:dcp%ny_g), source = 1.0)
      call fileio_read_rle(un, wcx)
      call fileio_read_rle(un, wcy)
    else
      allocate(wcx(1, 1), source = 1.0)
      allocate(wcy(1, 1), source = 1.0)
    end if
    call par_scatter_cell(wcx, cwxd)
    call par_scatter_cell(wcy, cwyd)
    cwd_restored = .true.
  end if
  if (is_root) close(un)
end subroutine



!===== 8方位コロケート格子計算終了 ====================================
!======================================================================
!----------------------------------------------------------------------
! 断面形一般化(§26)の変換関数群
!   vh(矩形換算水深)= ∫0^h σ(h')dh'。真の体積 = vh×gv×wfrac×セル面積。
!   d<=0(σ 非適用セル)は恒等写像(ビット厳密)。h<=0/v<=0 も恒等
!   (強い乾燥化での僅かな負値の扱いを従来と同一に保つ)。
!   σ(h) = (h/D)^m (h<D), 1 (h>=D)。h=D で v・hinv とも連続
!----------------------------------------------------------------------
!----------------------------------------------------------------------
! ステップ末尾の u,v 正規化パス(§26。σ 有効時のみ実効)
!   σ 有効時の u,v 正規化は complete でなくここで行う: complete の後に
!   h を変えるモジュール(gwflow の鉛直交換、evap の蒸発)があるため、
!   「最終確定 h の σ で1回だけ割る」ことが (a) u,v と h の整合、
!   (b) restore_uvmn(保存 h で同じ式を再評価)による厳密復元、の
!   両方の条件になる(complete 内正規化では σ+gwflow/evap のリスタート
!   が ULP 単位で破れることをリスタート実検証で発見)。
!   run_main が gwflow・evap の後、geomorph・統計・出力の前に呼ぶ。
!   σ 無効(正規化は従来どおり continuous の静的 cw)・STG では no-op。
!   対象セル集合(窓・x・sw スキップ)は restore_uvmn と完全に一致させる
!----------------------------------------------------------------------
subroutine m_swflow_enc_post(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: cxv, cyv
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (.not. have_sect) return
  if (.not. have_width) return
  !$omp parallel do schedule(dynamic) private(i, j, cxv, cyv)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%sw(i,j) > 0) cycle
      if (g%x(i,j) <= 0) cycle
      if (have_cwd) then
        cxv = cwxd(i,j)
        cyv = cwyd(i,j)
      else if (sdep(i,j) > 0.0) then
        call cw_cell(g, i, j, sect_sigma(s%h(i,j), sdep(i,j)), cxv, cyv)
      else
        cxv = cwx(i,j)
        cyv = cwy(i,j)
      end if
      s%u(i,j) = s%u(i,j) / cxv
      s%v(i,j) = s%v(i,j) / cyv
      s%vv(i,j) = sqrt(s%u(i,j)**2 + s%v(i,j)**2)
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 矩形換算水深 vh の照会(§26/§30)。σ 非適用セル・σ 無効時は h を返す。
! 水質の体積平均濃度 conc = cq/vh の分母(m_wq が使う)
!----------------------------------------------------------------------
!----------------------------------------------------------------------
! 測線計測用のエッジ流量の観測口(§24.1 観測者規律。m_record 専用・
! 読み取り専用。2026-10-04)
!   セル (i,j) から 8 近傍セル (in,jn) へ向かうエッジの流量 [m³/s]
!   (中心セルから出る向きが正)。直前ステップで確定したエッジの単位幅
!   流量 sx_mod%mn に通過幅 l8 と通過幅係数 frw·fwd を乗じたもので、
!   連続式が水深変化に換算する体積 mne·l8·fw·dt を dt で割った量に等しい
!   (サブグリッド幅・動的開口・σ の面積ベース流束がそのまま乗る)。
!   (i,j) は自帯(js..je)のセルであること(エッジ添字 je は確定済み範囲
!   js-1..je に収まる。ハロは読まない)。(in,jn) が 8 近傍でなければ 0。
!   閉じた境界面・乾いた対・通過幅ゼロのエッジは momentum/boundary_uvmn が
!   mn を 0 にしているので、ここでは判定しない(continuous と同じ集合)。
!----------------------------------------------------------------------
function m_swflow_enc_edge_flux(i, j, in, jn) result(q)
  integer, intent(in) :: i, j, in, jn
  real :: q
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]
  integer :: k, ie, je
  real :: fw
  q = 0.0
  do k = 1, 8
    if (in - i == din(k) .and. jn - j == djn(k)) exit
  end do
  if (k > 8) return
  ie = i + die(k)
  je = j + dje(k)
  fw = 1.0
  if (have_frw) fw = frw(ke(k),ie,je)
  if (have_fwd) fw = fw * fwd(ke(k),ie,je)
  q = sign_e(k) * sx_mod%mn(ke(k),ie,je) * l8(k) * fw
end function


function swflow_vh(i, j, h) result(vh)
  integer, intent(in) :: i, j
  real, intent(in) :: h
  real :: vh
  if (have_sect) then
    vh = sect_v(h, sdep(i,j))
  else
    vh = h
  end if
end function


pure function sect_v(h, d) result(v)
  real, intent(in) :: h, d
  real :: v
  if (d <= 0.0) then
    v = h
  else if (h >= d) then
    v = h - d * sect_mfac
  else if (h <= 0.0) then
    v = h
  else
    v = d * (h / d)**sect_mp1 * sect_rmp1
  end if
end function


pure function sect_hinv(v, d) result(h)
  real, intent(in) :: v, d
  real :: h
  real :: vd
  if (d <= 0.0) then
    h = v
  else
    vd = d * sect_rmp1              ! 満杯遷移点(h=D)の vh
    if (v >= vd) then
      h = v + d * sect_mfac
    else if (v <= 0.0) then
      h = v
    else
      h = d * (v * sect_mp1 / d)**sect_rmp1
    end if
  end if
end function


pure function sect_sigma(h, d) result(sg)
  real, intent(in) :: h, d
  real :: sg
  if (d <= 0.0 .or. h >= d) then
    sg = 1.0
  else if (h <= 0.0) then
    sg = sect_sgmin
  else
    sg = max((h / d)**sect_m, sect_sgmin)
  end if
end function


!----------------------------------------------------------------------
! 断面遷移深さ D の構築(§26)
!   優先: 堤防有効かつ天端が有効なセルは D = zbank − 河床(σ の満杯
!   遷移点と堰天端が入力から整合する)。なければ掘り込み深さ分布 g%drw。
!   河道セル(rw>0)のみ。ため池(rscap>0)とダム捕捉帯は hrs 系の
!   機構と競合するため σ 非適用(D=0)。河床は init 時点の s%z で
!   固定(geomorph による河床変動後も D は不変=既知の妥協)
!----------------------------------------------------------------------
subroutine build_sdep(g, b, s)
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(in) :: s
  integer :: i, j, ist, k
  real :: d

  allocate(sdep(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(screst(1:g%nx, dcp%jsh:dcp%jeh), source = screst_none)
  do j = dcp%jsh, dcp%jeh
    do i = 1, g%nx
      if (g%x(i,j) <= 0) cycle
      if (g%rw(i,j) <= 0) cycle
      if (g%rscap(i,j) > 0.0) cycle
      ! 天端: 堤防の天端が河床より上ならそれ、なければ掘り込み指定の
      ! 元地盤 g%z + drw(g%z は入力地形 = 初期河床。河床が動いても天端は
      ! 動かない = 河床低下で D が増え、堆積で減る。天端まで埋まれば D = 0 で
      ! 矩形に退化)。初期(s%z = g%z)の D は従来の定義と同値
      d = 0.0
      if (g%bank_active) then
        if (g%zbank(i,j) > zbank_min) d = max(g%zbank(i,j) - s%z(i,j), 0.0)
      end if
      if (d > 0.0) then
        screst(i,j) = g%zbank(i,j)
      else if (g%drw_active) then
        if (g%drw(i,j) > 0.0) then
          screst(i,j) = g%z(i,j) + g%drw(i,j)
          d = max(screst(i,j) - s%z(i,j), 0.0)
        end if
      end if
      sdep(i,j) = d
    end do
  end do

  ! ダム捕捉帯セルは σ 非適用(hrs へ h1 をそのまま移すため。§22)
  do ist = 1, b%nstruct
    if (b%struct(ist)%kind /= e_struct_dam) cycle
    do k = 1, b%struct(ist)%ncin
      i = b%struct(ist)%cin(1,k)
      j = b%struct(ist)%cin(2,k)
      if (j < dcp%jsh .or. j > dcp%jeh) cycle
      sdep(i,j) = 0.0
      screst(i,j) = screst_none
    end do
  end do

end subroutine


!----------------------------------------------------------------------
! 河床変動後の σ 遷移深さ D の更新(§26。2026-10-04)
!   D(t) = 天端 screst − s%z(t)。D が変わったセルは保存量の矩形換算水深
!   vh = ∫σ dh を保ったまま真の水深 h を読み替える(体積は sect_v/hinv の
!   往復精度 1 ULP で保存)。e = z + h も回復する。
!   呼び出しは z を更新するプロセス(geomorph・溶岩・外部 z)の後、統計・
!   出力の前(run_step)。z のハロは各プロセスが交換済みなので sdep は
!   帯+ハロで更新できる。h の読み替えは自帯のみ(ハロ h は次ステップ頭の
!   交換で最新化)。σ 無効なら no-op。D が変わらなければ何も書かない
!----------------------------------------------------------------------
subroutine m_swflow_enc_sdep_update(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: dnew, vh
  logical :: changed
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (.not. have_sect) return
  changed = .false.
  !$omp parallel do schedule(dynamic) private(i, j, dnew, vh) reduction(.or.:changed)
  do j = dcp%jsh, dcp%jeh
    do i = 1, g%nx
      if (screst(i,j) <= screst_none) cycle
      dnew = max(screst(i,j) - s%z(i,j), 0.0)
      if (dnew == sdep(i,j)) cycle
      if (j >= dcp%js .and. j <= dcp%je) then
        vh = sect_v(s%h(i,j), sdep(i,j))
        s%h(i,j) = sect_hinv(vh, dnew)
        s%e(i,j) = s%z(i,j) + s%h(i,j)
        changed = .true.
      end if
      sdep(i,j) = dnew
    end do
  end do
  !$omp end parallel do
  ! af(実効平面積率)は σ(h, D) を含むため更新する(帯のみ)
  if (changed) call update_af(g, s)
end subroutine


!----------------------------------------------------------------------
! 実効平面積率 af の更新(§25/§26)
!   af = gv × wfrac × (v(h)/h)。h×af = 真の貯水体積/セル面積 となる
!   (v(h)/h は深さ平均の湿潤率)。幅・σ とも無効の場合は呼ばれず、
!   af は m_state_init の gv のまま(従来の S とビット一致)
!----------------------------------------------------------------------
subroutine update_af(g, s)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: base

  !$omp parallel do schedule(dynamic) private(i, j, base)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      base = s%gv(i,j)
      if (have_width) base = base * wfrac(i,j)
      if (have_sect) then
        if (sdep(i,j) > 0.0) then
          if (s%h(i,j) > 0.0) then
            base = base * (sect_v(s%h(i,j), sdep(i,j)) / s%h(i,j))
          else
            base = base * sect_sgmin
          end if
        end if
      end if
      s%af(i,j) = base
    end do
  end do
  !$omp end parallel do

end subroutine

end module
