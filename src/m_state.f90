module m_state
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use list_initial, only : t_list_initial, list_initial_read
  use m_parallel, only : is_root, par_info, par_stop, dcp, &
                       par_sum_rows, par_allreduce_max, par_allreduce_sumi, &
                       par_gather_to, par_bcast_cell
  use m_util, only : itoa, rtoa
  use m_sysdep_util, only : sysdep_mkdir
  use m_fileio, only : fileio_write_rle, fileio_read_rle, fileio_read_matrix
  use iso_fortran_env, only : output_unit, real64
  implicit none
  private

  public :: t_state
  public :: t_initial
  public :: m_state_init
  public :: m_state_dispose
  public :: m_state_updatetime
  public :: m_state_calcstat
  public :: m_state_printstate


  ! 画面出力用変数
  ! 解釈済みの初期条件(list_initial から m_state_init が構築)。
  ! t_state の成分(s%ini)として保持され、set_z/set_h/set_uv・
  ! user フック・他モジュール(放射境界の基準水位導出等)が参照する。
  ! init に早期 return 経路がある型は全成分デフォルト初期化必須(§13)
  type t_initial
    integer :: f_htype = 0        ! 初期水深タイプ (0:水深固定, 1:水深ファイル,
                                  !                 2:水位固定, 3:水位ファイル)
    integer :: f_uvtype = 0       ! 初期流速タイプ
    integer :: f_fill_depres = 0  ! 窪地の充填 (0:なし, 1:全域で満水, 2:河道のみ,
                                  !   3:河道のみ満水後に地盤高へ転換)
    real :: h0 = 0.0              ! 初期水深固定値 (m)
    real :: e0 = 0.0              ! 初期水位固定値 (m。z と同じ基準)
    real :: u0 = 0.0              ! 初期x方向流速 (m/s)
    real :: v0 = 0.0              ! 初期y方向流速 (m/s)
    real :: h0_rw = 0.0           ! 河道マスク部の初期水深増分 (m)
    character(len=256) :: fn_hinit = ""  ! 初期水深/水位の分布ファイル名
  end type

  type t_state4prt
    real :: h = 0.0
    real :: vv = 0.0
    real :: qq = 0.0
    real :: cn = 0.0
    real :: runger = 0.0
    integer :: n_exf = 0
    integer :: count_disp = 0
  end type


  type t_state
    real :: t                           ! 現在時刻 (s)
    integer :: it                       ! 時刻カウンタ
    character(len=12) :: ctime          ! 現在時刻文字列 'hhh:mm:ss.ss'
    real, allocatable :: h(:,:)         ! 全水深(m)
    real, allocatable :: u(:,:)         ! x方向流速(m/s)
    real, allocatable :: v(:,:)         ! y方向流速(m/s)
    real, allocatable :: m(:,:)         ! x方向線流量(m^2/s)
    real, allocatable :: n(:,:)         ! y方向線流量(m^2/s)
    real, allocatable :: qq(:,:)        ! 線流量の絶対値(m^2/s)
    real, allocatable :: vv(:,:)        ! 流速の絶対値(m/s)
    real, allocatable :: e(:,:)         ! 水位(m)
    real, allocatable :: z(:,:)         ! 標高(m)
    real, allocatable :: pre(:,:)       ! precipitation (m/s)
    real, allocatable :: prh(:,:)       ! precipitation (mm/h)
    real, allocatable :: hrs(:,:)       ! water depth of reservoir (m)
    real, allocatable :: af(:,:)        ! 実効平面積率(gv×wfrac×平均湿潤率。§26)。
                                        !   h×af = 真の貯水体積/セル面積 となるよう
                                        !   swflow(complete)が毎ステップ更新する導出量
                                        !   (save 対象外。既定・非河道セルは gv と同値)
    real, allocatable :: hg(:,:)        ! 地下貯留水深(柱状換算)(m)。どの地下水
                                        ! モデルも毎ステップここに反映する契約
    real, allocatable :: hs(:,:)        ! 浮遊砂柱状量(m。単位床面積あたりの固体
                                        ! 体積)。濃度 C = hs/h は導出量。移流は
                                        ! swflow_enc がステップ内で行い(sed_active
                                        ! フラグ)、浸食・沈降(E-D)は m_geomorph が
                                        ! 行う(geomorph_plan.md §2.2)
    real, allocatable :: sd(:,:)        ! 土層厚(=可動層厚)(m)。動的共有状態。
                                        ! 初期値は g%sd(入力係数)から sd を要する
                                        ! モジュールの init が転記する(restore 時は
                                        ! 復元値が勝つ)。gwflow の容量 sd*sy0・
                                        ! 全水頭と、geomorph の浸食限界(sd>=0)を
                                        ! 兼ねる。浸食・堆積は z と同じ Δz で共動
                                        ! 更新される(geomorph_plan.md §2.5)
    real, allocatable :: tide(:,:)      ! tidal level (m)
    real, allocatable :: hmax(:,:)      ! maximum depth (m)
    real, allocatable :: hmaxt(:,:)     ! maximum depth time (min)
    real, allocatable :: vvmax(:,:)     ! maximum velocity (m/s)
    ! --- 土砂災害の危険度統計(f_out_* 指定時のみ確保。§28.9)---
    real, allocatable :: dmax(:,:)      ! 最大流動深 h+hs (m)(f_out_dmax/dmaxt)
    real, allocatable :: dmaxt(:,:)     ! 最大流動深の時刻 (min)
    real, allocatable :: fmax(:,:)      ! 最大流体力 (ρm/ρw)・(h+hs)・vv² (m3/s2。
                                        ! 清水密度で規格化 = 水のみでは u²h と同一。
                                        ! ×ρw で N/m)(f_out_fmax)
    real, allocatable :: fs(:,:)        ! 斜面安全率 Fs(f_out_fs。slide_pass1 が
                                        ! dt_geomorph 周期で更新。-1 = 評価対象外)
    real, allocatable :: fsmin(:,:)     ! Fs の期間最小(-1 = 未評価。危険度マップ)
    real, allocatable :: qqmax(:,:)     ! maximum discharge (m^2/s)
    real, allocatable :: qqdir(:,:)     ! maximum discharge direction (angle from x-axis, -pi~pi)
    real, allocatable :: qdir(:,:)      ! discharge direction (angle from x-axis, -pi~pi)
    real, allocatable :: qqt(:,:)       ! maximum discharge time (min)
    real, allocatable :: qcum(:,:)      ! cumulative flow rate (me
    real, allocatable :: fr(:,:)        ! Froude number
    real, allocatable :: cn(:,:)        ! Courant number
    integer, allocatable :: ddir1(:,:)  ! dominant down stream direction flag (2**(1~8))
    integer, allocatable :: ddir8(:,:)  ! all down stream direction flag (sum(2**(1~8)))
    real :: hgmean = 0.0     ! 領域平均の地下貯留高(m)。gw_active 時のみ更新
    real :: swemean = 0.0    ! 領域平均の積雪水量(m)。fn_snow 有効時のみ更新
    real :: himean = 0.0     ! 領域平均の氷河貯留(m 水当量)。fn_glacier 有効時のみ更新
    logical :: gw_active = .false.  ! 地下水モデルの有効化(m_gwflow_init が設定)
    real, allocatable :: cq(:,:)        ! 輸送物質柱状量 (g/m2。§30。濃度 = cq/vh は
                                        ! 導出量 cqc。移流は swflow_enc がステップ内で
                                        ! 行い(wq_active)、発生源・浸透同伴・減衰は
                                        ! m_wq が担う。確保は m_wq_init(有効時のみ))
    real, allocatable :: cqc(:,:)       ! 体積平均濃度 (mg/L。導出量。m_wq が毎ステップ
                                        ! 更新。σ・河道幅の換算込み。出力・プローブ用)
    real, allocatable :: cg(:,:)        ! 地下質量プール (g/m2。§30。地下横輸送は
                                        ! m_gwflow_lateral がステップ内で行い、
                                        ! 浸透同伴・湧出還元・減衰・保存は m_wq が
                                        ! 担う。確保は m_wq_init(f_wq_infil=1 のみ))
    real, allocatable :: bp(:,:)        ! 表面蓄積プール (g/m2。幾何面積基底 =
                                        ! セル内質量 bp×A。m_wq が確保・更新・保存し、
                                        ! m_output が B 場(kg/ha)を書く。§30)
    real, allocatable :: hg2(:,:)       ! 風化基岩層の貯留水深 (m。柱状換算。
                                        ! m_gwflow_layer2 が確保・更新・保存する。
                                        ! f_gwlayer2=0 なら未確保。§16)
    real, allocatable :: hgc(:,:)       ! 管路連続体層の貯留水量 (m。柱状換算。
                                        ! m_gwflow_conduit が確保・更新・保存する。
                                        ! f_gwconduit=0 なら未確保。§46)
    real, allocatable :: hss(:,:)       ! 地表水の塩水層厚 (m。柱状換算。h の内数 =
                                        ! 最下層の塩水。m_saltwater が確保・更新・
                                        ! 保存する。fn_salt 未指定なら未確保。§47)
    real, allocatable :: hgs(:,:)       ! 地下水(層1)の塩水貯留 (m。柱状換算。
                                        ! hg の内数。m_saltwater が確保・更新・
                                        ! 保存する。fn_salt 未指定なら未確保。§47)
    logical :: salt_active = .false.    ! 地表塩水層の有効化(m_saltwater_init が設定。
                                        ! swflow_enc がステップ内で s%hss を移流する)
    real :: salt_alpha = 1.0            ! 塩水層のバロトロピック移流分担率 α
                                        ! (m_saltwater_init が設定。§47)
    real, allocatable :: swe(:,:)       ! 積雪水量 SWE (m 水柱。幾何面積基底。
                                        ! m_snow が確保・更新・保存する。
                                        ! fn_snow 未指定なら未確保。§31)
    real, allocatable :: swi(:,:)       ! 土壌雨量指数 SWI (mm)。m_swi が確保・
                                        ! 更新(タンクは私有、SWI は診断和)。
                                        ! fn_swi 未指定なら未確保。§49
    real, allocatable :: swimax(:,:)    ! SWI の期間最大 (mm)(save 対象外。§7)
    real, allocatable :: swimaxt(:,:)   ! SWI 最大の発生時刻 (min)
    real, allocatable :: hi(:,:)        ! 氷河の氷厚 (m 氷柱。幾何面積基底。水当量は
                                        ! hi×(ρi/ρw)。m_glacier が確保・更新・保存する。
                                        ! fn_glacier 未指定なら未確保。§45)
    real, allocatable :: hl(:,:)        ! 溶岩厚 (m 溶岩柱。幾何面積基底。水柱でない
                                        ! ため S 台帳には算入しない。m_lavaflow が
                                        ! 確保・更新・保存する。fn_lavaflow 未指定
                                        ! なら未確保。lava_plan.md)
    real, allocatable :: hd(:,:)        ! 流動流木柱状量 (m3/m2 = m。貯留の意味論は
                                        ! h・hs と同一)。移流は swflow_enc がステップ
                                        ! 内で行い(dw_active)、発生・停止・再流動は
                                        ! m_driftwood が担う。確保・保存は
                                        ! m_driftwood_init(有効時のみ)。§50
    real, allocatable :: wd(:,:)        ! 堆積流木 (m3/m2。柱状量。m_driftwood が
                                        ! 確保・更新・保存し、m_output が Wd 場を
                                        ! 書く。fn_driftwood 未指定なら未確保。§50)
    real, allocatable :: wdmax(:,:)     ! 流木の期間最大到達量 max(hd+wd)
                                        ! (f_out_wd 指定時のみ確保。save 対象外。§7)
    logical :: dw_active = .false.      ! 流木輸送の有効化(m_driftwood_init が設定。
                                        ! swflow_enc がステップ内で s%hd を移流する)
    real :: geo_morfac = 0.0 ! geomorph の地形時間加速係数(m_geomorph_init が設定。
                             ! 0 = geomorph 無効。m_glacier_init が「morfac は
                             ! 全プロセス共通の1個」の検査に使う。§45)
    real :: gl_ir = 0.0      ! 氷の密度比 ρi/ρw(m_glacier_init が設定。himean の
                             ! 水当量換算に使う。fn_glacier 無効時は未使用)
    real, allocatable :: fxg(:,:)       ! 浸透フラックスの記録 (m。gwflow の鉛直交換が
                                        ! 書き、m_wq が読んでゼロ戻し。§30 の契約。
                                        ! 確保は m_wq_init(f_wq_infil=1 のときのみ))
    real, allocatable :: fxci(:,:)      ! 地表→管路(枡流入)交換量の記録 (m。fxg と
                                        ! 同じ契約: m_gwflow_conduit が書き、m_wq が
                                        ! 読んでゼロ戻し。確保は m_wq_init(管路連携
                                        ! wq_gwc_conc 指定かつ f_wq_gwc_in=1 のみ)。§30)
    real, allocatable :: fxco(:,:)      ! 管路→地表(噴出・陸側吐口)交換量の記録 (m。
                                        ! 同上。確保は m_wq_init(管路連携指定時)。§30)
    real, allocatable :: frofac(:,:)    ! 凍土の浸透低減係数 [fro_fmin,1](m_gwflow_frost
                                        ! が書き、鉛直浸透モデルが浸透能に乗じる。
                                        ! 確保は gwflow_frost_init(f_gwfrost=1 のみ)。§16.4)
    logical :: wq_active = .false.  ! 水質輸送の有効化(m_wq_init が設定。
                                    ! swflow_enc がステップ内で s%cq を移流する)
    logical :: sed_active = .false. ! 浮遊砂輸送の有効化(m_geomorph_init が設定。
                                    ! swflow_enc がステップ内で s%hs を移流する)
    real :: sed_sgrav = 0.0         ! 土粒子の水中比重 s(m_geomorph_init が
                                    ! sed_active とともに設定。fmax の混合密度
                                    ! 係数 ρm/ρw = 1+sC に使用。無効時 0 = 水)
    logical :: debris_active = .false. ! 土石流モデルの有効化(m_geomorph_init が
                                    ! 設定。swflow_enc が運動量へ hs を算入し、
                                    ! 抵抗則を切り替える。debris_plan.md §2.3-2.4)
    real :: hmean
    real :: cnmax
    integer :: it0 = 0       ! 時間ループの開始ステップ(フレッシュランは 0。
                             ! restore 時は save 記録の it から継続する = 時間軸は
                             ! 絶対時刻1本で、s%t = t0 + dt*it の式が中断なしランと
                             ! 全ステップでビット同一になる。§7)
    integer :: ifn = 0       ! 出力ファイル通し番号(run_main が更新。save に記録し
                             ! restore 時は続き番号から再開する)
    integer :: n_valcells               ! number of valid cells
    integer :: n_exfluxes               ! number of excessive fluxes
    integer :: n_runge                  ! number of Runge-Kutta flux calculations
    integer :: un_log                   ! ログファイルの装置番号
    type(t_initial) :: ini              ! 解釈済み初期条件
    type(t_state4prt) :: sp             ! 画面出力用
    logical :: initialized = .false.
  end type



  ! user_initial submodule の入口(個々のルーチンへの分岐と識別名簿は
  ! submodule 側に閉じる。ルーチンの追加は user_initial.f90 だけで完結する)
  interface
    module function user_initial_defined(name) result(res)
      character(len=*), intent(in) :: name
      logical :: res
    end function
    module function user_initial_names() result(names)
      character(len=:), allocatable :: names
    end function
    module subroutine user_initial_run(p, g, s, name)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
      character(len=*), intent(in) :: name
    end subroutine
  end interface


  ! ---- save/restore 形式の版 ----
  !   仕様変更日の日付文字列。save の並び・成分・メタデータ・圧縮形式を
  !   変更したら必ずこの日付を更新する(restore 時の照合に使う。§7)。
  !   同日に複数回変更した場合は英字サフィックスで区別する
  character(len=*), parameter :: save_version_cur = "2026-08-09"
  integer, parameter :: n_state_save = 6     ! state.dat の成分数(h,z,hrs,hg,sd,hs)


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 状態構造体を初期化
!----------------------------------------------------------------------
subroutine m_state_init(s, p, g)
  type(t_state), intent(out) :: s
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  type(t_list_initial) :: list
  type(t_state) :: ts    ! 初期化用の全域一時状態(h, u, v, z のみ確保。
                         ! 全ランクが全域で冗長に初期化し、最後に帯を切り出す。
                         ! user フックと fill_depression の「全域添字」契約を
                         ! 帯確保の下でも保つための方式。developer.md §11)

  ! メモリ確保
  allocate(s%h(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%u(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%v(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%m(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%n(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%qq(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%vv(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%e(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%z(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%pre(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%prh(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%hrs(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%af(1:g%nx,dcp%jsh:dcp%jeh), source = 1.0)
  s%af(:,dcp%jsh:dcp%jeh) = g%gv(:,dcp%jsh:dcp%jeh)   ! 実効平面積率の初期値 = gv
  allocate(s%hg(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  ! 土層厚 sd は利用モジュール(fn_geomorph / fn_gwflow)があるときのみ
  ! 確保する(§0 方針8: 有効化しないモデルはメモリを確保しない)。
  ! state は list を読まない層のためファイル指定の有無で判定する
  ! (bucket 等 sd 不要モデルでも確保される粗い判定 = 既知の妥協)
  if (len_trim(p%fn_geomorph) > 0 .or. len_trim(p%fn_gwflow) > 0) then
    allocate(s%sd(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  end if
  allocate(s%hs(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%tide(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%hmax(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%hmaxt(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%vvmax(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%qqmax(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%qqdir(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%qdir(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%qqt(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%qcum(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%fr(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%cn(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%ddir1(1:g%nx,dcp%jsh:dcp%jeh), source = 0)
  allocate(s%ddir8(1:g%nx,dcp%jsh:dcp%jeh), source = 0)

  ! 土砂災害の危険度統計(指定時のみ確保 = 無効時ゼロコスト。§28.9。
  ! 前提条件(土砂モジュール・f_slide)の検証は m_geomorph_init が行う)
  if (p%f_out_dmax > 0 .or. p%f_out_dmaxt > 0) then
    allocate(s%dmax(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
    allocate(s%dmaxt(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  end if
  if (p%f_out_fmax > 0) allocate(s%fmax(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  if (p%f_out_fs > 0) then
    allocate(s%fs(1:g%nx,dcp%jsh:dcp%jeh), source = -1.0)
    allocate(s%fsmin(1:g%nx,dcp%jsh:dcp%jeh), source = -1.0)
  end if

  ! 初期条件設定ファイル読み込み(fn_initial 未指定なら読まず、
  ! t_list_initial の既定値=乾いた状態 h=0 から開始する。
  ! 空文字のまま open して実行時エラーになる実バグの修正 2026-08-14)
  if (len_trim(p%fn_initial) > 0) call list_initial_read(p, list)

  ! 解釈済み初期条件を構築する(層契約: list は生値のまま、解釈はここ)
  ts%ini%f_htype = list%f_htype
  ts%ini%f_uvtype = list%f_uvtype
  ts%ini%f_fill_depres = list%f_fill_depres
  ts%ini%h0 = list%h0
  ts%ini%e0 = list%e0
  ts%ini%u0 = list%u0
  ts%ini%v0 = list%v0
  ts%ini%h0_rw = list%h0_rw
  ts%ini%fn_hinit = list%fn_hinit

  ! --- 初期条件は全域一時状態 ts 上で全ランク冗長に構築する ---
  allocate(ts%h(1:g%nx,1:g%ny), source = 0.0)
  allocate(ts%u(1:g%nx,1:g%ny), source = 0.0)
  allocate(ts%v(1:g%nx,1:g%ny), source = 0.0)
  allocate(ts%z(1:g%nx,1:g%ny), source = 0.0)
  allocate(ts%hrs(1:g%nx,1:g%ny), source = 0.0)
  allocate(ts%hg(1:g%nx,1:g%ny), source = 0.0)
  allocate(ts%sd(1:g%nx,1:g%ny), source = 0.0)
  allocate(ts%hs(1:g%nx,1:g%ny), source = 0.0)

  call m_state_updatetime(s, p, 0)
  call set_z(p, g, ts)
  call set_h(p, g, ts)     ! set_z()よりも後に実行
  call set_uv(p, g, ts)

  s%n_valcells = 0           ! number of valid cells
  s%n_exfluxes = 0           ! number of excessive fluxes
  s%n_runge = 0              ! number of Runge-Kutta flux calculations

  if (p%f_state_restore > 0) call restore_state(p, ts)

  ! ユーザールーチンによる初期条件をセット(全域添字契約: ts に書く)。
  ! 指定は f_user_routine(識別名。trim 後完全一致)。
  ! 個々のルーチンへの分岐は user_initial submodule 内。実行は全ランク冗長。
  ! restore 時は名前の検証だけ行い実行しない: 保存状態が正本であり、
  ! 加算型のフック(wave_hump 等)を復元値に重ねると初期擾乱が二重に
  ! 乗る(リスタート往復ビット一致で実検出)。フックによる地形改変
  ! (壁等)は保存された z に含まれているので、スキップしても失われない
  if (len_trim(list%f_user_routine) > 0) then
    if (.not. user_initial_defined(list%f_user_routine)) then
      call par_stop("list_initial: undefined f_user_routine: "//trim(list%f_user_routine)// &
                    " (defined: "//user_initial_names()//")")
    end if
    if (p%f_state_restore <= 0) call user_initial_run(p, g, ts, list%f_user_routine)
  end if

  ! --- 担当帯(+ハロ)を切り出す。ts はスコープ終了で自動解放 ---
  s%h(:,:) = ts%h(1:g%nx, dcp%jsh:dcp%jeh)
  s%u(:,:) = ts%u(1:g%nx, dcp%jsh:dcp%jeh)
  s%v(:,:) = ts%v(1:g%nx, dcp%jsh:dcp%jeh)
  s%z(:,:) = ts%z(1:g%nx, dcp%jsh:dcp%jeh)
  s%hrs(:,:) = ts%hrs(1:g%nx, dcp%jsh:dcp%jeh)
  s%hg(:,:) = ts%hg(1:g%nx, dcp%jsh:dcp%jeh)
  if (allocated(s%sd)) s%sd(:,:) = ts%sd(1:g%nx, dcp%jsh:dcp%jeh)
  s%hs(:,:) = ts%hs(1:g%nx, dcp%jsh:dcp%jeh)
  s%ini = ts%ini
  s%it0 = ts%it0        ! restore 時は save 記録の it(フレッシュランは 0)
  s%ifn = ts%ifn        ! restore 時は save 記録の出力番号(続き番号で再開)

  ! 初期水位をセット
  s%e(:,:) = s%z(:,:) + s%h(:,:)

  ! 計算対象セルの数をセット(海域は除く)
  ! カウント自体は m_geoinfo_init 内(sw が全域のゾーン1)で実施済み。
  ! ここ(ゾーン2)で sw を全域添字で読んではならない(帯縮小済みのため。
  ! 実際に np=2 で1セル誤除外し S がずれた実バグ)
  s%n_valcells = g%n_valcells

  ! 状態ログファイルをオープン
  !   ログファイルを出力するのはランクゼロのみ
  if (is_root) s%un_log = open_logfile()

  s%initialized = .true.

contains
  function open_logfile() result(un)
    integer :: un
    character(len=256) :: fname
    fname = trim(p%dir_result) // "/" // trim(p%fn_log)
    open(newunit=un, file=fname, status='replace')
  end function 

end subroutine

!----------------------------------------------------------------------
! 統計量を計算
!----------------------------------------------------------------------
subroutine m_state_calcstat(s, p, g)
  type(t_state), intent(inout) :: s
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real :: hmax
  real :: vvmax
  real :: ht
  real :: qqmax
  real :: cnmax
  ! 診断集約の総和は PREC によらず real64 で行う(単精度ビルドでの
  ! 桁落ち防止。倍精度ビルドでは real64=既定 real で従来と同一。§1)
  real(real64) :: hsum
  real(real64) :: hsum_j(dcp%js:dcp%je)
  real(real64) :: hgsum
  real(real64) :: hgsum_j(dcp%js:dcp%je)
  real(real64) :: swesum_j(dcp%js:dcp%je), swesum
  real(real64) :: hisum_j(dcp%js:dcp%je), hisum
  real :: qcumf
  real :: dtpdx     ! dt / min(dx, dy)
  real :: cosdir
  real :: cc
  real :: rmax(4)      ! 全ランク集約用 [hmax, vvmax, qqmax, cnmax]
  integer :: nglob(2)  ! 全ランク集約用 [n_exfluxes, n_runge]
  integer :: i, j

  hsum = 0
  hsum_j(:) = 0.0
  hgsum = 0
  hgsum_j(:) = 0.0
  swesum_j(:) = 0.0
  hisum_j(:) = 0.0
  hmax = 0
  vvmax = 0
  qqmax = 0
  cnmax = 0
  qcumf = p%dt / g%dx / g%dy / s%n_valcells * 1000
  dtpdx = p%dt / min(g%dx, g%dy)

  !$omp parallel do schedule(dynamic) private(i, j, cosdir, cc, ht), & 
  !$omp reduction(max: hmax, vvmax, qqmax, cnmax)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) == 0) cycle
      ! ため池・ダムの貯留(hrs)は h と独立に貯水量へ計上する
      ! (h=0 のセルでも貯留は存在する。ゼロ加算はスキップ=従来ケースと
      !  総和のビット一致を保つ)
      if (s%hrs(i,j) > 0.0) then
        hsum_j(j) = hsum_j(j) + real(s%hrs(i,j), real64) * g%gv(i,j)
      end if
      ! 積雪は乾燥セルにも存在するため h 判定より前に計上する(§31)
      if (allocated(s%swe)) then
        if (s%swe(i,j) > 0.0) swesum_j(j) = swesum_j(j) + s%swe(i,j)
      end if
      ! 氷河の氷も同様(氷厚のまま総和し、平均化の際に水当量へ換算。§45)
      if (allocated(s%hi)) then
        if (s%hi(i,j) > 0.0) hisum_j(j) = hisum_j(j) + s%hi(i,j)
      end if
      ! 地下水も乾燥セルに存在するため h 判定より前に計上する
      ! (浸透で乾いたセルの hg が S_grnd から漏れ、S_total が見かけ上
      !  減る実バグの修正 2026-08-14。ゼロ加算はスキップ=湿潤のみの
      !  既存ケースと総和のビット一致を保つ)
      if (s%gw_active) then
        if (s%hg(i,j) > 0.0) hgsum_j(j) = hgsum_j(j) + s%hg(i,j)
        if (allocated(s%hg2)) then
          if (s%hg2(i,j) > 0.0) hgsum_j(j) = hgsum_j(j) + s%hg2(i,j)
        end if
        if (allocated(s%hgc)) then
          if (s%hgc(i,j) > 0.0) hgsum_j(j) = hgsum_j(j) + s%hgc(i,j)
        end if
      end if
      if (s%h(i,j) <= 0) cycle
      if (s%h(i,j) > s%hmax(i,j)) then
        s%hmax(i,j) = s%h(i,j)                                 ! 最大水深
        s%hmaxt(i,j) = s%t / 60.                               ! 最大水深発生時刻(min)
      end if
      if (s%vv(i,j) > s%vvmax(i,j)) s%vvmax(i,j) = s%vv(i,j)   ! 最大流速
      ! 土砂災害の危険度統計(確保時のみ。§28.9。混合流動深 h+hs)
      if (allocated(s%dmax)) then
        ht = s%h(i,j) + max(s%hs(i,j), 0.0)
        if (ht > s%dmax(i,j)) then
          s%dmax(i,j) = ht                                     ! 最大流動深
          s%dmaxt(i,j) = s%t / 60.                             ! 発生時刻(min)
        end if
      end if
      if (allocated(s%fmax)) then
        ! 流体力 = (ρm/ρw)(h+hs)V² = (h + (1+s)hs)V²(混合密度
        ! ρm = ρw(1+sC)、C = hs/(h+hs) より。清水規格化 = 水のみでは
        ! u²h と厳密に同一。§28.9)
        ht = (s%h(i,j) + (1.0 + s%sed_sgrav) * max(s%hs(i,j), 0.0)) * s%vv(i,j)**2
        if (ht > s%fmax(i,j)) s%fmax(i,j) = ht                 ! 最大流体力
      end if
      if (s%qq(i,j) > 0.0) then
        cosdir = min(1.,max(-1.,s%m(i,j) / s%qq(i,j)))         ! 流向のcos
        s%qdir(i,j) = acos(cosdir) * sign(1., s%n(i,j))        ! 流向
        if (s%qq(i,j) > s%qqmax(i,j)) then
          s%qqmax(i,j) = s%qq(i,j)                             ! 最大流量
          s%qqdir(i,j) = s%qdir(i,j)                           ! 最大流量時の流向
          s%qqt(i,j) = s%t / 60.                               ! 最大流量発生時刻(min)
        end if
      end if
      cc = sqrt(p%gg * s%h(i,j))                               ! 長波の波速
      s%fr(i,j) = s%vv(i,j) / cc                               ! フルード数
      if (p%f_check_cfl >= 2) then
        s%cn(i,j) = s%vv(i,j) * dtpdx                          ! クーラン数(波速を無視)
      else
        s%cn(i,j) = (s%vv(i,j) + cc) * dtpdx                   ! クーラン数(波速を考慮)
      end if
      ! 真の貯水量: 空隙率 gv で体積換算した水深(2026-08-08 定義変更。
      ! gv=1 のケースは従来とビット一致)。河道幅 wfrac は m_state から
      ! 不可視のため未反映(幅有効時の S は河道セルで過大。§18 の妥協)
      hsum_j(j) = hsum_j(j) + real(s%h(i,j), real64) * s%af(i,j)
      hmax = max(hmax, s%h(i,j))
      vvmax = max(vvmax, s%vv(i,j))
      qqmax = max(qqmax, s%qq(i,j))
      cnmax = max(cnmax, s%cn(i,j))
      s%qcum(i,j) = s%qcum(i,j) + (abs(s%m(i,j)) * g%dy + abs(s%n(i,j)) * g%dx) * qcumf
    end do
  end do
  !$omp end parallel do

  ! --- 全ランク集約 ---
  ! 総和は「全域窓の行部分和を j 昇順に並べて一括総和」で決定化
  ! (ランク数に依存しない)。max は順序不変な厳密演算なので allreduce。
  ! 事象カウント(ランク局所)は全ランク合計に集約してから使う。
  call par_sum_rows(hsum_j, hsum)
  ! 地下貯留の総和(collective なので判定 gw_active は全ランク同一)
  if (s%gw_active) then
    call par_sum_rows(hgsum_j, hgsum)
    s%hgmean = hgsum / s%n_valcells
  end if
  ! 積雪水量の総和(判定 allocated(s%swe) は namelist 由来 = 全ランク同一)
  if (allocated(s%swe)) then
    call par_sum_rows(swesum_j, swesum)
    s%swemean = swesum / s%n_valcells
  end if
  ! 氷河貯留の総和(判定 allocated(s%hi) は namelist 由来 = 全ランク同一)。
  ! 水当量への密度比換算 gl_ir は m_glacier_init が s に設定する
  if (allocated(s%hi)) then
    call par_sum_rows(hisum_j, hisum)
    s%himean = hisum / s%n_valcells * s%gl_ir
  end if
  rmax = [hmax, vvmax, qqmax, cnmax]
  call par_allreduce_max(rmax)
  hmax  = rmax(1)
  vvmax = rmax(2)
  qqmax = rmax(3)
  cnmax = rmax(4)
  nglob = [s%n_exfluxes, s%n_runge]
  call par_allreduce_sumi(nglob)

  s%hmean = hsum / s%n_valcells                                ! 領域平均貯留高(m。
                                                               !   gv 換算+ため池・ダム貯留込み)
  s%cnmax = cnmax                                              ! 領域最大クーラン数(全域値)

  ! 画面出力ステップ内での最大値(画面出力時にリセットされる)
  s%sp%h = max(s%sp%h, hmax)
  s%sp%vv = max(s%sp%vv, vvmax)
  s%sp%qq = max(s%sp%qq, qqmax)
  s%sp%cn = max(s%sp%cn, cnmax)
  s%sp%n_exf = max(s%sp%n_exf, nglob(1))
  s%sp%runger = max(s%sp%runger, nglob(2) / (real(s%n_valcells) * 4) * 100)

end subroutine


!----------------------------------------------------------------------
! 時間情報を更新
!----------------------------------------------------------------------
subroutine m_state_updatetime(s, p, it)
  type(t_state), intent(inout) :: s
  type(t_sysparam), intent(in) :: p
  integer, intent(in) :: it
  s%it = it
  s%t = p%t0 + p%dt * it
  call t2ctime(s%t, s%ctime)
end subroutine


!----------------------------------------------------------------------
! 計算状態を画面に出力
!----------------------------------------------------------------------
subroutine m_state_printstate(p, s)
  ! 列は「ヘッダ名と値を同じ場所で積む」方式で組み立てる(addcol)。
  ! 列を追加・削除するときはヘッダと値がずれないよう addcol を使うこと
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  real :: progress      ! 進行割合(%)
  character(len=256) :: fmt, fmt0, hdr
  character(len=1024) :: msg
  integer :: digi1, digi2, digi3
  real :: hmean
  real :: sblk(3)       ! 保存量列 S(1列)または S_surf/S_grnd/S_total(3列)
  real :: tail(4)       ! 場の最大値の列(f10.4 固定書式)
  integer :: ns, ntl

  if (.not. is_root) return

  hmean = s%hmean

  ! --- 保存量列: 地下水か積雪の有効時は S_surf / S_grnd / S_total に拡張。
  !     S_total には積雪水量も算入(閉じた系の保存監視列) ---
  ns = 1
  sblk(1) = hmean
  if (s%gw_active .or. allocated(s%swe) .or. allocated(s%hi)) then
    ! 全水量列は積雪水量・氷河貯留(水当量)も算入
    ! (fn_snow / fn_glacier 無効時は 0 で従来と同値)
    sblk(2) = s%hgmean
    sblk(3) = hmean + s%hgmean + s%swemean + s%himean
    ns = 3
  end if

  ! --- 保存量列の書式 ---
  !     f_disp_debug=1: 全有効桁を表示(バグ発見用。回帰テストはこちら)。
  !     桁数は最大の量(1列なら S、3列なら S_total)に合わせる。
  !     既定(0)は他列と同じ f10.4
  if (p%f_disp_debug > 0) then
    digi1 = p%real_precision + 5                          ! 全体の表示桁数
    digi2 =  max(1, int(log10(max(sblk(ns), 1e-6))) + 1)  ! 整数部の桁数(1未満の場合も1桁)
    digi3 = max(p%real_precision - digi2, 1)              ! 小数点以下の表示桁数
    write(fmt0, '("f",i2,".",i0)') digi1, digi3
  else
    fmt0 = "f10.4"
  end if

  ! --- 行全体の書式(RN は round='nearest' に相当) ---
  if (ns == 3) then
    fmt = '(RN,a," ",f5.1,"%",3(' //trim(fmt0)// ',1x)," ",f5.1,"%",i7,*(f10.4))'
  else
    fmt = '(RN,a," ",f5.1,"%",' //trim(fmt0)// '," ",f5.1,"%",i7,*(f10.4))'
  end if

  ! --- ヘッダの組み立てと、場の最大値の列の選択(f_disp_*) ---
  !     並びは 固定(time, progress)→ 保存量(S 系列)→ 健康監視
  !     (Runge, ex_flux, Cn_max)→ 場の最大値。時刻・保存量・Runge・
  !     ex_flux は常設
  if (ns == 3) then
    hdr = "time, progress, S_surf(m), S_grnd(m), S_total(m), Runge, ex_flux"
  else
    hdr = "time, progress, S(m), Runge, ex_flux"
  end if
  ntl = 0
  call addcol(p%f_disp_cn, s%sp%cn, "Cn_max")
  call addcol(p%f_disp_h, s%sp%h, "h_max(m)")
  call addcol(p%f_disp_vv, s%sp%vv, "V_max(m/s)")
  call addcol(p%f_disp_qq, s%sp%qq, "Q_max(m2/s)")

  ! 凡例を表示
  if (mod(s%sp%count_disp, 36) == 0) then
    call par_info(trim(hdr))
    write(s%un_log, '(a)') trim(hdr)
    flush(s%un_log)
  end if

  progress = (s%it) / real(p%nt) * 100
  write(msg, fmt) s%ctime, progress, sblk(1:ns), s%sp%runger, s%sp%n_exf, tail(1:ntl)
  call par_info(trim(msg))
  write(s%un_log, fmt) s%ctime, progress, sblk(1:ns), s%sp%runger, s%sp%n_exf, tail(1:ntl)
  flush(s%un_log)

  ! 画面出力用の最大値のリセット
  s%sp%h = 0
  s%sp%vv = 0
  s%sp%qq = 0
  s%sp%cn = 0
  s%sp%n_exf = 0
  s%sp%runger = 0

  ! 凡例表示のカウンタを更新
  s%sp%count_disp = s%sp%count_disp + 1

contains
  !--------------------------------------------------------------------
  ! 列の登録: ヘッダ名の追記と値の格納を同時に行う(flag<=0 なら非表示)
  !--------------------------------------------------------------------
  subroutine addcol(flag, val, name)
    integer, intent(in) :: flag
    real, intent(in) :: val
    character(len=*), intent(in) :: name
    if (flag <= 0) return
    ntl = ntl + 1
    tail(ntl) = val
    hdr = trim(hdr)//", "//name
  end subroutine
end subroutine


!----------------------------------------------------------------------
! 状態構造体を破棄
!----------------------------------------------------------------------
subroutine m_state_dispose(s, p)
  type(t_state), intent(inout) :: s
  type(t_sysparam), intent(in) :: p

  if (p%f_state_save > 0) call save_state(p, s)

  s%t = 0
  s%it = 0
  s%ctime = ""
  if (allocated(s%h)) deallocate(s%h)
  if (allocated(s%u)) deallocate(s%u)
  if (allocated(s%v)) deallocate(s%v)
  if (allocated(s%m)) deallocate(s%m)
  if (allocated(s%n)) deallocate(s%n)
  if (allocated(s%z)) deallocate(s%z)
  if (allocated(s%vv)) deallocate(s%vv)
  if (allocated(s%qq)) deallocate(s%qq)
  if (allocated(s%pre)) deallocate(s%pre)
  if (allocated(s%prh)) deallocate(s%prh)
  if (allocated(s%hrs)) deallocate(s%hrs)
  if (allocated(s%af)) deallocate(s%af)
  if (allocated(s%hg)) deallocate(s%hg)
  if (allocated(s%sd)) deallocate(s%sd)
  if (allocated(s%hs)) deallocate(s%hs)
  if (allocated(s%cq)) deallocate(s%cq)
  if (allocated(s%cqc)) deallocate(s%cqc)
  if (allocated(s%cg)) deallocate(s%cg)
  if (allocated(s%bp)) deallocate(s%bp)
  if (allocated(s%hg2)) deallocate(s%hg2)
  if (allocated(s%hgc)) deallocate(s%hgc)
  if (allocated(s%hss)) deallocate(s%hss)
  if (allocated(s%hgs)) deallocate(s%hgs)
  if (allocated(s%swe)) deallocate(s%swe)
  if (allocated(s%swi)) deallocate(s%swi)
  if (allocated(s%swimax)) deallocate(s%swimax)
  if (allocated(s%swimaxt)) deallocate(s%swimaxt)
  if (allocated(s%hi)) deallocate(s%hi)
  if (allocated(s%hl)) deallocate(s%hl)
  if (allocated(s%hd)) deallocate(s%hd)
  if (allocated(s%wd)) deallocate(s%wd)
  if (allocated(s%wdmax)) deallocate(s%wdmax)
  if (allocated(s%fxg)) deallocate(s%fxg)
  if (allocated(s%fxci)) deallocate(s%fxci)
  if (allocated(s%fxco)) deallocate(s%fxco)
  if (allocated(s%frofac)) deallocate(s%frofac)
  if (allocated(s%tide)) deallocate(s%tide)
  if (allocated(s%hmax)) deallocate(s%hmax)
  if (allocated(s%hmaxt)) deallocate(s%hmaxt)
  if (allocated(s%vvmax)) deallocate(s%vvmax)
  if (allocated(s%dmax)) deallocate(s%dmax)
  if (allocated(s%dmaxt)) deallocate(s%dmaxt)
  if (allocated(s%fmax)) deallocate(s%fmax)
  if (allocated(s%fs)) deallocate(s%fs)
  if (allocated(s%fsmin)) deallocate(s%fsmin)
  if (allocated(s%qqmax)) deallocate(s%qqmax)
  if (allocated(s%qqdir)) deallocate(s%qqdir)
  if (allocated(s%qdir)) deallocate(s%qdir)
  if (allocated(s%qqt)) deallocate(s%qqt)
  if (allocated(s%qcum)) deallocate(s%qcum)
  if (allocated(s%cn)) deallocate(s%cn)
  if (allocated(s%ddir1)) deallocate(s%ddir1)
  if (allocated(s%ddir8)) deallocate(s%ddir8)
  s%initialized = .false.
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 初期水深をセット
!----------------------------------------------------------------------
subroutine set_h(p, g, s)
  ! f_htype 0: 水深固定 h0 / 1: 水深ファイル / 2: 水位固定 e0 /
  ! 3: 水位ファイル。水位指定は h = max(η − z, 0)(z は set_z 済みの s%z)。
  ! 分布ファイルは全ランク冗長の全域読み(ゾーン2。prtype3 と同じ流儀)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  type(t_state), intent(inout) :: s
  real, allocatable :: wk(:,:)
  integer :: i, j

  select case (s%ini%f_htype)
    case (0)      ! 水深固定値
      forall(i=1:g%nx, j=1:g%ny, g%x(i,j) > 0) s%h(i,j) = s%ini%h0
    case (1)      ! 水深ファイル
      call read_hinit(p, g, s%ini, wk)
      forall(i=1:g%nx, j=1:g%ny, g%x(i,j) > 0) s%h(i,j) = max(wk(i,j), 0.0)
    case (2)      ! 水位固定値
      forall(i=1:g%nx, j=1:g%ny, g%x(i,j) > 0) s%h(i,j) = max(s%ini%e0 - s%z(i,j), 0.0)
    case (3)      ! 水位ファイル
      call read_hinit(p, g, s%ini, wk)
      forall(i=1:g%nx, j=1:g%ny, g%x(i,j) > 0) s%h(i,j) = max(wk(i,j) - s%z(i,j), 0.0)
    case default
      call par_stop("list_initial: f_htype must be 0(fixed depth), 1(depth file), " &
                    //"2(fixed water level) or 3(water level file): "//itoa(s%ini%f_htype))
  end select
  if (s%ini%f_fill_depres > 0)  call fill_depression(p, g, s)
  if (s%ini%h0_rw > 0.0) call adjust_h0rw(p, g, s)

end subroutine


!----------------------------------------------------------------------
! 初期水深/水位の分布ファイルを読む(全ランク冗長。ゾーン2)
!----------------------------------------------------------------------
subroutine read_hinit(p, g, ini, wk)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_initial), intent(in) :: ini
  real, allocatable, intent(out) :: wk(:,:)
  if (len_trim(ini%fn_hinit) <= 0) then
    call par_stop("list_initial: f_htype="//itoa(ini%f_htype) &
                  //" requires fn_hinit")
  end if
  allocate(wk(1:g%nx,1:g%ny), source = 0.0)
  call fileio_read_matrix(trim(p%dir_data)//"/"//trim(ini%fn_hinit), &
                          g%nx, g%ny, wk, p%f_input_mode)
end subroutine

!----------------------------------------------------------------------
! 窪地を水で埋める
!----------------------------------------------------------------------
subroutine fill_depression(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, k
  integer :: in, jn
  integer :: l
  integer :: iadj, nadj
  real :: ec, en, ec1, en1
  ! 水位比較の許容差 (m)。これ未満の水位差は平衡とみなす。
  ! 許容差なしの大小比較は収束条件が水位 z+h のビット一致要求になり、
  ! 単精度では丸め(ulp ~ 0.1mm 級)により収束しない。
  ! 入力地形の不確実性から 1mm 未満の水位差は物理的に無意味(§9)。
  real, parameter :: tol = 1.0e-3
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]

  if (p%initialized) continue  ! 引数未使用の警告を抑制

  ! 注意: 本ルーチンは全域窓(g%wy)で全ランク冗長実行する。
  !       近傍セルへの書き込みを含む緩和反復のため行分割できない。
  !       受け取る s は全域一時状態 ts(m_state_init 参照)なので、
  !       帯確保の下でも全域添字で安全に動く。

  if (is_root) then
    write(output_unit, '(a)', advance='no') " filling depressions "
    flush(output_unit)
  end if

  ! 対象セルに初期水深を与える
  do j = g%wy(1), g%wy(2)
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) < 1) cycle        ! 領域外は除外
      if (g%sw(i,j) > 0) cycle       ! 海は除外
      if (s%ini%f_fill_depres >= 2 .and. g%rw(i,j) < 1) cycle   ! 河道以外は除外
      s%h(i,j) = 1000
    end do
  end do
  

  do l = 1, 3000
    if (mod(l, 100) == 0) then
      if (is_root) then
        write(output_unit, '(a)', advance='no') ">"
        flush(output_unit)
      end if
    end if
    nadj = 0
    do j = g%wy(1), g%wy(2)
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) < 1) cycle                                 ! 領域外は除外
        if (s%ini%f_fill_depres >= 2 .and. g%rw(i,j) < 1) cycle  ! 河道以外は除外
        if (s%h(i,j) <= 0) cycle                                ! 既に水が無いセルは除外
        ec = g%z(i,j) + s%h(i,j)                                ! 自セルの水位
        iadj = 0
        do k = 1, 8
          in = i + din(k)
          jn = j + djn(k)
          if (g%sw(in,jn) > 0) then                             ! 海に隣接する場合は
            s%h(i,j) = 0                                        ! 自セルの水深をゼロに
            ! 水位も更新(古い水位のまま後続の近傍比較で復水させない)
            ec = g%z(i,j)
          else
            if (s%ini%f_fill_depres >= 2 .and. g%rw(in,jn) < 1) cycle   ! 近傍セルが河道以外は除外
            en = g%z(in,jn) + s%h(in,jn)      ! 近傍セルの水位
            if (ec > en + tol) then           ! 自セルの方が水位が高い場合は自セルの水位を下げる
              ec1 = max(en, g%z(i,j))         ! 自セルの水位は自セルの標高以下にはならない
              s%h(i,j) = ec1 - g%z(i,j)       ! 水深は水位から標高を減じる
              ec = g%z(i,j) + s%h(i,j)        ! 下げた水位を以降の近傍比較に使う
              iadj = 1
            else if (en > ec + tol .and. s%h(in,jn) > 0) then   ! 近傍セルに水が有りかつ水位が高い
              ! 近傍セルを自セルの水位まで下げる(近傍セルの標高以下にはならない)
              en1 = max(ec, g%z(in,jn))
              s%h(in,jn) = en1 - g%z(in,jn)     ! 水深は水位から標高を減じる
              iadj = 1
            end if
          end if
        end do
        nadj = nadj + iadj

      end do
    end do
    if (nadj == 0) exit
  end do

  if (s%ini%f_fill_depres >= 3) then
    if (is_root) then
      write(output_unit, '(a)', advance='no') " lifting riverbed"
      flush(output_unit)
    end if
    do j = g%wy(1), g%wy(2)
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) < 1) cycle        ! 領域外は除外
        if (g%sw(i,j) > 0) cycle       ! 海は除外
        if (g%rw(i,j) < 1) cycle       ! 河道以外は除外
        if (s%h(i,j) > 0) then
          s%z(i,j) = s%z(i,j) + s%h(i,j)
          s%h(i,j) = 0
        end if
      end do
    end do
  end if
  if (is_root) then
    write(output_unit, *)
    flush(output_unit)
  end if
  
end subroutine

!----------------------------------------------------------------------
! 河道部の初期水深を増やす
!----------------------------------------------------------------------
subroutine adjust_h0rw(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  do j = g%wy(1), g%wy(2)
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) > 0 .and. g%rw(i,j) > 0) then
        s%h(i,j) = s%h(i,j) + s%ini%h0_rw
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 初期流速をセット
!----------------------------------------------------------------------
subroutine set_uv(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  forall(i=1:g%nx, j=1:g%ny, g%x(i,j) > 0) s%u(i,j) = s%ini%u0
  forall(i=1:g%nx, j=1:g%ny, g%x(i,j) > 0) s%v(i,j) = s%ini%v0
end subroutine


!----------------------------------------------------------------------
! 初期標高をセット
!----------------------------------------------------------------------
subroutine set_z(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  if (p%initialized) continue      ! 引数未使用の警告を抑制
  s%z(:,:) = g%z(:,:)
end subroutine


!----------------------------------------------------------------------
! 時刻を文字列に変換
!----------------------------------------------------------------------
subroutine t2ctime(t, ctime)
  real, intent(in) :: t
  character(len=12), intent(out) :: ctime
  integer :: h, m, s, ss
  h = int(t / 60. / 60.)
  m = int(t / 60.) - h * 60
  s = int(t) - h * 60 * 60 - m * 60
  ss = nint((t - int(t)) * 100)
  write(ctime, '(i3,a1,i2.2,a1,i2.2,a1,i2.2)') h, ":", m, ":", s, ".", ss
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine save_state(p, s)
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  integer :: un
  real, allocatable :: wk(:,:,:)
  ! 全域バッファに集約してから rank0 のみが書く。
  ! write(un) wk のレコードは h, z, hrs, hg, sd, hs の連結。
  ! 運動量表現(uv/mn 等)はスキーム私有の保存(swflow_enc.dat)、
  ! u,v,m,n,vv,qq,e は復元時に再導出される導出量(§7 の線引き)
  call sysdep_mkdir(p%dir_save)
  if (is_root) then
    allocate(wk(1:dcp%nx_g, 1:dcp%ny_g, n_state_save), source = 0.0)
  else
    allocate(wk(1, 1, n_state_save))          ! 参照されないダミー
  end if
  call par_gather_to(wk(:,:,1), s%h)
  call par_gather_to(wk(:,:,2), s%z)
  call par_gather_to(wk(:,:,3), s%hrs)
  call par_gather_to(wk(:,:,4), s%hg)
  if (allocated(s%sd)) call par_gather_to(wk(:,:,5), s%sd)   ! 未確保時は 0(形式不変)
  call par_gather_to(wk(:,:,6), s%hs)
  if (.not. is_root) return
  open(newunit=un, file=trim(p%dir_save)//'/state.dat', form='unformatted', status='replace')
  ! 成分ごとにゼロ抑制 RLE で書く(海域・乾燥域のゼロを圧縮。§7)
  call fileio_write_rle(un, wk(:,:,1))   ! h
  call fileio_write_rle(un, wk(:,:,2))   ! z
  call fileio_write_rle(un, wk(:,:,3))   ! hrs
  call fileio_write_rle(un, wk(:,:,4))   ! hg
  call fileio_write_rle(un, wk(:,:,5))   ! sd
  call fileio_write_rle(un, wk(:,:,6))   ! hs
  close(un)

  ! メタデータは最後に書く(save 一式の完成マーカーを兼ねる。
  ! m_state_dispose は dispose 列の最後の saver — この順序を崩さない)
  call write_save_info(p, s)
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine restore_state(p, s)
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  integer :: un
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (s%initialized) continue  ! 引数未使用の警告を抑制
  ! 門番: メタデータを検証してから読む(不一致は par_stop)。
  ! 時間軸の継続情報(it0, ifn)もここで s(呼び出し側の全域一時状態 ts)
  ! に取り込む(m_state_init が帯切り出し時に正準 s へ写す)
  call check_save_info(p, s)

  ! rank0 が読み、全ランクへ配布する。受け取る s は全域一時状態 ts
  ! (全ランク同形)なので Bcast が成立する。帯への切り出しは呼び出し側
  if (is_root) then
    open(newunit=un, file=trim(p%dir_save)//'/state.dat', form='unformatted', status='old')
    ! 読み並びは save_state の書き込み順(h, z, hrs, hg, sd, hs)と一致させること。
    ! 成分を足すときは save と restore を必ず同時に更新する
    call fileio_read_rle(un, s%h)
    call fileio_read_rle(un, s%z)
    call fileio_read_rle(un, s%hrs)
    call fileio_read_rle(un, s%hg)
    call fileio_read_rle(un, s%sd)
    call fileio_read_rle(un, s%hs)
    close(un)
  end if
  call par_bcast_cell(s%h)
  call par_bcast_cell(s%z)
  call par_bcast_cell(s%hrs)
  call par_bcast_cell(s%hg)
  call par_bcast_cell(s%sd)
  call par_bcast_cell(s%hs)
end subroutine


!----------------------------------------------------------------------
! save メタデータ(save_info.txt)を namelist 形式で書く(rank0 のみ)
!   全ファイルの書き込み完了後に呼ぶ(save 一式の完成マーカーを兼ねる)
!----------------------------------------------------------------------
subroutine write_save_info(p, s)
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  integer :: un
  character(len=8) :: d
  character(len=10) :: tod
  character(len=16) :: save_version
  integer :: nx, ny, precision_bits, n_state, it, ifn
  real :: t, t0, dt
  namelist /save_info/ save_version, nx, ny, precision_bits, n_state, t, it, t0, dt, ifn

  if (.not. is_root) return
  save_version = save_version_cur
  nx = dcp%nx_g
  ny = dcp%ny_g
  precision_bits = storage_size(1.0)
  n_state = n_state_save
  t = s%t
  it = s%it
  ! 再開の継続に必要な時間軸情報(§7)。t0, dt は restore 時の一致検査用、
  ! it は時間ループの開始ステップ、ifn は出力ファイルの続き番号
  t0 = p%t0
  dt = p%dt
  ifn = s%ifn
  call date_and_time(date=d, time=tod)
  open(newunit=un, file=trim(p%dir_save)//'/save_info.txt', status='replace')
  write(un, '(11a)') "! ENCflow restart save (", d(1:4), "-", d(5:6), "-", d(7:8), &
                     " ", tod(1:2), ":", tod(3:4), ")"
  write(un, nml=save_info)
  close(un)
end subroutine


!----------------------------------------------------------------------
! save メタデータを検証する(restore の門番。全ランクが冗長に読む)
!   版・格子サイズ・実数精度・成分数の不一致は par_stop。
!   検証は全ランク同一 → par_stop の collective 条件を満たす。
!   後段のモジュール(swflow_enc、内部状態を持つ gwflow モデル等)は
!   ここで検証済みとして自ファイルの有無だけを確認すればよい(§7)。
!   再開の時間軸(§7): 時間軸は絶対時刻1本で、f_state_restore=1 の
!   restore は save 記録の it から時間ループを継続する(s%it0)。
!   namelist の t0 と dt は軸の同一性の条件なので save 記録との一致を
!   検査し、矛盾なら par_stop(無言でどちらかを優先しない)。tt は
!   絶対終了時刻のままで、保存時刻以前なら回すステップが無いので
!   エラーにする。f_state_restore=2 は場だけを引き継ぐ「初期条件と
!   して利用」モードで、時間軸は新規(検査対象は形式の門番のみ)
!----------------------------------------------------------------------
subroutine check_save_info(p, s)
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s    ! it0(開始ステップ)と ifn(出力番号)を設定
  integer :: un, ios
  character(:), allocatable :: fname
  character(len=16) :: save_version
  integer :: nx, ny, precision_bits, n_state, it, ifn
  real :: t, t0, dt
  real, parameter :: rtol = 1.0e-6   ! t0, dt の一致判定の相対許容差
  namelist /save_info/ save_version, nx, ny, precision_bits, n_state, t, it, t0, dt, ifn

  fname = trim(p%dir_save)//'/save_info.txt'
  save_version = ""
  nx = -1; ny = -1; precision_bits = -1; n_state = -1
  t = 0.0; it = 0; ifn = 0
  t0 = 0.0; dt = 0.0

  open(newunit=un, file=fname, status='old', action='read', iostat=ios)
  if (ios /= 0) then
    call par_stop("save: save_info.txt not found (state file is missing or incomplete): "//fname)
  end if
  read(un, nml=save_info, iostat=ios)
  close(un)
  if (ios /= 0) call par_stop("save: cannot read save_info.txt: "//fname)

  if (trim(save_version) /= save_version_cur) then
    call par_stop("save: state file format version "//trim(save_version)//" does not match " &
                  //"the version this executable reads ("//save_version_cur//"): "//fname)
  end if
  if (nx /= dcp%nx_g .or. ny /= dcp%ny_g) then
    call par_stop("save: grid in state file ("//itoa(nx)//" x "//itoa(ny)//") does not match " &
                  //"the current grid ("//itoa(dcp%nx_g)//" x "//itoa(dcp%ny_g)//")")
  end if
  if (precision_bits /= storage_size(1.0)) then
    call par_stop("save: real precision in state file ("//itoa(precision_bits)//" bit) does " &
                  //"not match this run ("//itoa(storage_size(1.0))//" bit)")
  end if
  if (n_state /= n_state_save) then
    call par_stop("save: number of state components in state file ("//itoa(n_state)//") does " &
                  //"not match the expected ("//itoa(n_state_save)//")")
  end if

  ! 時間軸(§7): f_state_restore=1(再開)は同じ軸の続き — t0, dt の
  ! 一致を検査し、it・出力番号 ifn を継続する。=2(初期条件として利用)
  ! は場だけを引き継ぎ、新しい軸(新しい t0・暦。dt の変更も可)を
  ! it=0, ifn=0 から開始する。時系列強制(潮位・降雨等)は新しい軸で
  ! 頭から読まれるため、シナリオ先頭の強制値を保存状態と整合させるのは
  ! 利用者の責務(不整合だと初期に擾乱が走る)
  if (p%f_state_restore == 2) then
    s%it0 = 0
    s%ifn = 0
    call par_info("save: reading state at t="//rtoa(t)//" s as the initial condition and " &
                  //"starting a new time axis from t0="//rtoa(p%t0)//" s")
    return
  end if

  if (abs(p%t0 - t0) > rtol * max(1.0, abs(t0))) then
    call par_stop("list_sysparam: t0("//rtoa(p%t0)//") does not match t0 in state file (" &
                  //rtoa(t0)//"); use the same parameter file as when saved" &
                  //" (f_state_restore=2 starts a new time axis)")
  end if
  if (abs(p%dt - dt) > rtol * dt) then
    call par_stop("list_sysparam: dt("//rtoa(p%dt)//") does not match dt in state file (" &
                  //rtoa(dt)//"); restart cannot change dt" &
                  //" (f_state_restore=2 starts a new time axis with a new dt)")
  end if
  if (p%nt <= it) then
    call par_stop("list_sysparam: end time tt("//rtoa(p%tt)//" s) is not after the saved " &
                  //"time t1("//rtoa(t)//" s); increase tt to extend the run")
  end if

  s%it0 = it
  s%ifn = ifn

  call par_info("save: resuming from saved state at t="//rtoa(t)//" s (it="//itoa(it)//")")
end subroutine

end module
