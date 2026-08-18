module m_saltwater
  ! ============== 淡塩2層(鋭利界面)モジュール m_saltwater ==============
  ! 地表水(s%h)と浅層地下水(層1 s%hg)に塩水層を導入し、SWI2(MODFLOW)
  ! 型の準静的・鋭利界面近似で塩水くさび・海水浸入・淡水レンズを扱う。
  ! 設計の正本は docs/swi_plan.md、決定は developer.md §47。
  ! fn_salt で有効化(未指定なら状態もエッジ配列も確保しない = ゼロ追加)。
  !
  ! 【簿記(§47 決定)】
  !   s%h / s%hg は淡塩「合計」のまま(既存機構は不変)。塩水層厚
  !   s%hss(地表)/ s%hgs(地下)は合計の内数で、常に層の最下部にある
  !   (鋭利界面。塩水が加わった瞬間に最下部へ置かれる = 即時入替規則)。
  !   密度は 2 値。ε = (ρs − ρf)/ρf。Boussinesq 近似(質量≒体積)。
  !
  ! 【完全加算方式(§47 決定。既存ムーバー無変更の分解)】
  !   2 zone 系の合計流束 = T_total·∇η + ε·T_s·∇ζ と分解でき、第1項は
  !   既存の側方流(lateral_core)/浅水流がそのまま計算している。本
  !   モジュールは
  !     (a) 塩水 zone 流束 q_s = K·b_s·∇(η + εζ) で hgs を更新
  !     (b) その ε バロクリニック成分 ε·K·b_s·∇ζ を合計 hg にも加算
  !   だけを「追加」する(暗黙の淡水流束 = 合計 − 塩水 = K·b_f·∇η と
  !   なり 2 zone の式に厳密一致)。地表は SWE が合計を動かし、塩水層は
  !     (c) swflow_enc のスカラー移流フック(分担率 α)による輸送
  !     (d) 底層重力流(Manning 型・駆動水頭 Φs = η + εζ の拡散型
  !         1 方程式。摩擦支配の近似。方針 §0 の「SWE+1方程式拡散」の内側)
  !   で動く((d) は交換流なので h には触れない)。
  !
  ! 【毎ステップの処理(run_main で gwflow の後・wq の前)】
  !  (1) 整合クランプ(乾燥・蒸発等による hss > h の解消)
  !  (2) 地表の底層重力流(f_salt_surf=1): 適応サブサイクリング
  !      (m_glacier の SIA と同じ「D_max の allreduce → 分割数」方式。
  !       全ランク同一 = collective 安全・決定的)
  !  (3) 地下の塩水 zone 側方流(f_salt_gw=1): 上記 (a)(b)。
  !      容量超過(hg > sd·sy)は層1の規則どおり地表へ湧出
  !  (4) 地下の海側境界: 海域セル(sw>0)を「全塩水・水位 = 潮位」の
  !      規定水頭とし、塩水は双方向(hg と hgs を同時更新)、淡水は
  !      流出のみ(海に淡水はない)。等化量で制限し振動を防ぐ
  !  (5) 海域セルの hss 維持(hss = h。移流フックの風上濃度が
  !      「海water = 全塩水」を読むため。潮位更新に対し 1 ステップ遅れ)
  !
  ! 【前提・制約】
  !  - f_salt_gw=1 は層1側方流(f_gwlateral=1)の有効化が前提
  !    (K_sh・sy を共有し、バロトロピック応答を lateral が担うため)
  !  - 蒸発散・浸透の淡塩配分は未実装(現状は暗黙に淡水扱い。
  !    swi_plan.md の段 4)。整合は (1) のクランプが保証する
  !  - 混合・連行なし(界面は鋭利のまま)。内部波の慣性なし
  !
  ! 【初期値】salt_hss0(既存 h のうち塩水と見なす厚。min(h, 値))/
  !  salt_hgs0(塩水の追加投入 = hgs と hg の両方に加算)。分布はマップ
  !  (fn_salt_hss0 / fn_salt_hgs0)。restore 時は復元値が勝つ
  !
  ! 【リスタート】hss・hgs はモデル私有ファイル saltwater.dat(RLE 2 面)。
  !  restore 時に自ファイルが無ければ par_stop(契約5)
  ! =====================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_gwflow_lateral, only : gwflow_lateral_geom_init, gwflow_lateral_geom_get, &
                               gwflow_lateral_layer1_get
  use m_fileio, only : fileio_read_matrix, fileio_write_rle, fileio_read_rle
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : par_info, par_stop, dcp, is_root, par_halo_cell, &
                         par_gather_to, par_scatter_cell, par_allreduce_max
  implicit none
  private
  public :: t_saltwater
  public :: m_saltwater_init
  public :: m_saltwater_calc
  public :: m_saltwater_dispose

  type t_saltwater
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.
    logical :: initialized = .false.
  end type

  ! 8近傍の規約(m_swflow_enc / m_gwflow_lateral と同一)
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]
  integer, parameter :: die(1:8) = [ -1,  0,  0, -1,  0, -1,  0,  0]
  integer, parameter :: dje(1:8) = [ -1, -1, -1,  0,  0,  0,  0,  0]
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]

  ! モジュール私有の設定・作業領域(単一インスタンス前提。developer.md §12)
  type t_salt
    real :: epsr = 0.0               ! ε = (ρs − ρf)/ρf
    logical :: surf = .false.        ! 地表塩水層の有効化
    logical :: gw = .false.          ! 地下塩水 zone の有効化
    real :: rni = 0.0                ! 界面 Manning n の逆数 1/n_i(地表)
    real :: eps = 1.0e-3             ! 乾燥判定の正則化量 (m 柱状)
    real :: eps_h = 1.0e-2           ! sqrt 則の線形化幅 (m 水頭差)
    integer :: nsubmax = 200         ! 地表サブサイクルの上限
    real :: ksh = 0.0                ! 層1の側方飽和透水係数 (m/s。getter)
    real :: sy = 0.0                 ! 層1の比湧水量
    real :: syinv = 0.0              ! 1 / sy
    real :: rdr(1:8) = 0.0           ! 幾何(gwflow_lateral_geom_get)
    real :: wl(1:8) = 0.0
    real :: ainv = 0.0
    real, allocatable :: qs(:,:,:)   ! エッジ流量4成分。一時作業領域(共用)
    real, allocatable :: qb(:,:,:)   ! 同(バロクリニック成分。gw のみ)
    logical :: initialized = .false.
  end type
  type(t_salt) :: sw

contains


!----------------------------------------------------------------------
! 淡塩2層モジュールを初期化する(fn_salt 未指定なら何もしない)
!----------------------------------------------------------------------
subroutine m_saltwater_init(sl, p, g, s)
  type(t_saltwater), intent(out) :: sl
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: un, ios, i, j
  logical :: lat_active
  real :: sdmax(1), sum_ldr, dt_lim
  character(len=256) :: msg
  integer :: f_salt_surf, f_salt_gw, salt_nsubmax
  real :: salt_rhof, salt_rhos, salt_alpha, salt_ni
  real :: salt_hss0, salt_hgs0, salt_eps, salt_eps_h, salt_diagratio
  character(len=1024) :: fn_salt_hss0, fn_salt_hgs0
  namelist /list_salt/ f_salt_surf, f_salt_gw, salt_rhof, salt_rhos, &
    salt_alpha, salt_ni, salt_hss0, fn_salt_hss0, salt_hgs0, fn_salt_hgs0, &
    salt_eps, salt_eps_h, salt_diagratio, salt_nsubmax

  if (len_trim(p%fn_salt) == 0) return

  f_salt_surf = 1
  f_salt_gw = 1
  salt_rhof = 1000.0
  salt_rhos = 1025.0
  salt_alpha = 1.0
  salt_ni = 0.025
  salt_hss0 = 0.0
  fn_salt_hss0 = ""
  salt_hgs0 = 0.0
  fn_salt_hgs0 = ""
  salt_eps = 1.0e-3
  salt_eps_h = 1.0e-2
  salt_diagratio = 2.0 / (2.0 + sqrt(2.0))   ! m_swflow_enc の p_diagratio と同値
  salt_nsubmax = 200

  call par_info("reading list_salt in " // trim(p%fn_salt))
  open(newunit=un, file=trim(p%fn_salt), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_salt: cannot open " // trim(p%fn_salt))
  read(un, nml=list_salt, iostat=ios)
  if (ios /= 0) call par_stop("list_salt: cannot read namelist")
  close(un)

  ! --- 検証(範囲・整合) ---
  if (f_salt_surf /= 0 .and. f_salt_surf /= 1) then
    call par_stop("list_salt: f_salt_surf must be 0 or 1")
  end if
  if (f_salt_gw /= 0 .and. f_salt_gw /= 1) then
    call par_stop("list_salt: f_salt_gw must be 0 or 1")
  end if
  if (f_salt_surf == 0 .and. f_salt_gw == 0) then
    call par_stop("list_salt: enable at least one of f_salt_surf / f_salt_gw")
  end if
  if (salt_rhof <= 0.0 .or. salt_rhos <= salt_rhof) then
    call par_stop("list_salt: densities must satisfy 0 < salt_rhof < salt_rhos")
  end if
  if (salt_alpha < 0.0 .or. salt_alpha > 1.0) then
    call par_stop("list_salt: salt_alpha must be in [0,1]")
  end if
  if (f_salt_surf == 1 .and. salt_ni <= 0.0) then
    call par_stop("list_salt: salt_ni must be > 0")
  end if
  if (salt_hss0 < 0.0 .or. salt_hgs0 < 0.0) then
    call par_stop("list_salt: salt_hss0 / salt_hgs0 must be >= 0")
  end if
  if (salt_eps <= 0.0) call par_stop("list_salt: salt_eps must be > 0")
  if (salt_eps_h <= 0.0) call par_stop("list_salt: salt_eps_h must be > 0")
  if (salt_diagratio < 0.0 .or. salt_diagratio > 1.0) then
    call par_stop("list_salt: salt_diagratio must be in [0,1]")
  end if
  if (salt_nsubmax < 1) call par_stop("list_salt: salt_nsubmax must be >= 1")

  sw%surf = (f_salt_surf == 1)
  sw%gw = (f_salt_gw == 1)
  sw%epsr = (salt_rhos - salt_rhof) / salt_rhof
  sw%rni = 0.0
  if (sw%surf) sw%rni = 1.0 / salt_ni
  sw%eps = salt_eps
  sw%eps_h = salt_eps_h
  sw%nsubmax = salt_nsubmax

  ! --- 層1側方流の前提(f_salt_gw=1)と係数の取得 ---
  if (sw%gw) then
    call gwflow_lateral_layer1_get(lat_active, sw%ksh, sw%sy)
    if (.not. lat_active) then
      call par_stop("saltwater: f_salt_gw=1 requires f_gwlateral=1 " &
                    // "(the barotropic response and K_sh/sy0 come from layer-1 lateral flow)")
    end if
    sw%syinv = 1.0 / sw%sy
  end if

  ! --- 幾何(gwflow の側方系と共有・冪等)とエッジ作業領域 ---
  call gwflow_lateral_geom_init(g, salt_diagratio, 1.0e-3)
  call gwflow_lateral_geom_get(sw%rdr, sw%wl, sw%ainv)
  allocate(sw%qs(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)
  if (sw%gw) allocate(sw%qb(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)

  ! --- 状態の確保と初期値(海セル・無効セルには置かない) ---
  ! hss0 は既存 h のうち塩水と見なす厚(min クランプ)、hgs0 は塩水の
  ! 追加投入(hgs と hg の両方に加算 = 塩水も水)。ゾーン2 = x/sw は
  ! 全域が使える(帯行 jsh:jeh は全域の有効行)
  allocate(s%hss(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%hgs(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (len_trim(fn_salt_hss0) > 0) then
    call read_map_scatter(p, g, fn_salt_hss0, s%hss, "salt_hss0")
  else if (salt_hss0 > 0.0) then
    s%hss(:,:) = salt_hss0
  end if
  if (len_trim(fn_salt_hgs0) > 0) then
    call read_map_scatter(p, g, fn_salt_hgs0, s%hgs, "salt_hgs0")
  else if (salt_hgs0 > 0.0) then
    s%hgs(:,:) = salt_hgs0
  end if
  do j = dcp%jsh, dcp%jeh
    do i = 1, g%nx
      if (g%x(i,j) <= 0) then
        s%hss(i,j) = 0.0
        s%hgs(i,j) = 0.0
        cycle
      end if
      if (g%sw(i,j) > 0) then
        s%hss(i,j) = s%h(i,j)          ! 海域セルは常に全塩水
        s%hgs(i,j) = 0.0
        cycle
      end if
      s%hss(i,j) = min(s%hss(i,j), s%h(i,j))
      if (s%hgs(i,j) > 0.0) s%hg(i,j) = s%hg(i,j) + s%hgs(i,j)
    end do
  end do

  ! --- 地下塩水 zone の安定条件(静的検査。§47) ---
  ! 塩水 zone 流束の水頭感度は (1+ε)/sy(∇η と ε∇ζ の和)、厚さ上界は
  ! max(sd)。層1側方の検査と同型で dt(毎ステップ実行)を検査する
  if (sw%gw) then
    sdmax(1) = 0.0
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        sdmax(1) = max(sdmax(1), s%sd(i,j))
      end do
    end do
    call par_allreduce_max(sdmax)
    sum_ldr = 0.0
    do i = 1, 8
      sum_ldr = sum_ldr + sw%wl(i) * sw%rdr(i)
    end do
    if (sw%ksh * sdmax(1) * sum_ldr > 0.0) then
      dt_lim = 0.5 * sw%sy * g%dx * g%dy &
               / (sw%ksh * (1.0 + sw%epsr) * sdmax(1) * sum_ldr)
      write(msg,'(a,es10.3,a,es10.3,a)') "saltwater_gw: dt limit = ", dt_lim, &
                                         " s (dt = ", p%dt, " s)"
      call par_info(trim(msg))
      if (p%dt > dt_lim) then
        call par_stop("saltwater_gw: dt exceeds the explicit stability limit " &
                      // "(reduce dt or K_sh)")
      end if
    end if
  end if

  ! --- リスタート ---
  if (p%f_state_restore > 0) call restore_state(p, g, s)

  ! --- 地表移流フックの有効化(swflow init より前に立てる契約) ---
  s%salt_active = sw%surf
  s%salt_alpha = salt_alpha

  sw%initialized = .true.
  sl%enabled = .true.
  sl%initialized = .true.
  call par_info("saltwater two-fluid (fresh/salt) layers enabled")
end subroutine


!----------------------------------------------------------------------
! rank0 が全域マップを読み par_scatter_cell で帯+ハロへ配布する(方式2)
!----------------------------------------------------------------------
subroutine read_map_scatter(p, g, fn, a, label)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn
  real, intent(inout) :: a(1:, dcp%jsh:)
  character(len=*), intent(in) :: label
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  integer :: i, j
  character(len=1024) :: msg

  fname = trim(p%dir_data) // "/" // trim(fn)
  call par_info(" reading " // fname)
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    call fileio_read_matrix(fname, g%nx, g%ny, wk, p%f_input_mode)
    call par_scatter_cell(wk, a)
  else
    call par_scatter_cell(dum, a)
  end if
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      if (g%x(i,j) <= 0) cycle
      if (a(i,j) < 0.0) then
        write(msg,'(a,2i7,es12.4)') "saltwater: negative " // label // " at", &
                                    i, j, a(i,j)
        call par_stop(trim(msg))
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 淡塩2層の計算(毎ステップ。ヘッダの (1)〜(5) の順で固定)
!----------------------------------------------------------------------
subroutine m_saltwater_calc(sl, p, g, s, it)
  type(t_saltwater), intent(in) :: sl
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  integer :: i, j

  if (.not. sl%enabled) return
  if (it < 0) continue  ! 引数未使用の警告を抑制

  ! (1) 整合クランプ(乾燥・蒸発等が h を hss より下げた場合の解消)
  !$omp parallel do schedule(static) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%hss(i,j) > s%h(i,j)) s%hss(i,j) = max(s%h(i,j), 0.0)
      if (s%hgs(i,j) > s%hg(i,j)) s%hgs(i,j) = max(s%hg(i,j), 0.0)
    end do
  end do
  !$omp end parallel do

  ! ステップ頭のハロ交換(h は swflow のステップ頭交換の後に gwflow 等が
  ! 帯のみ更新しているため、ここで再交換する。z は swflow 交換済み)
  call par_halo_cell(s%h)
  if (sw%gw) then
    call par_halo_cell(s%hg)
    call par_halo_cell(s%hgs)
  end if

  ! (2) 地表の底層重力流(適応サブサイクリング。hss のハロは
  !     サブサイクルごとに内部で交換する)
  if (sw%surf) call surf_gravity_current(g, s, p%dt)

  ! (3) 地下の塩水 zone 側方流+(4) 海側境界
  if (sw%gw) then
    call gw_salt_zone(g, s, p%dt)
    call gw_sea_exchange(g, s, p%dt)
  end if

  ! (5) 海域セルの hss 維持(次ステップの移流フックの風上濃度用。
  !     潮位更新に対して 1 ステップ遅れ = ヘッダ参照)
  if (sw%surf) then
    !$omp parallel do schedule(static) private(i, j)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) s%hss(i,j) = s%h(i,j)
      end do
    end do
    !$omp end parallel do
  end if
end subroutine


!----------------------------------------------------------------------
! 地表の底層重力流(拡散型 1 方程式。交換流なので h には触れない)
!   Φs = (z + h) + ε(z + hss)。流束は Manning 型
!     q = (1/n_i)·hse^{5/3}·sqrt(|ΔΦ|·rdr)·sign·wl(|ΔΦ| < eps_h は線形化)
!   安定条件は ∂Φ/∂hss = ε の線形化枝で評価し、適応サブサイクリング
!   (分割数は hss 最大値の allreduce から全ランク同一に決める)
!----------------------------------------------------------------------
subroutine surf_gravity_current(g, s, dts)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt, isub, nsub
  real :: hmax(1), sum_fac, dcoef, dt_lim, dtsub
  real :: pc, pn, zc, zn, hup, hse, dp, gq, dh_up, dh_rcv, cap_rcv, dhg
  character(len=256) :: msg

  ! --- 分割数(全ランク同一。hss=0 なら何もしない) ---
  hmax(1) = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      hmax(1) = max(hmax(1), s%hss(i,j))
    end do
  end do
  call par_allreduce_max(hmax)
  if (hmax(1) <= sw%eps) return
  sum_fac = 0.0
  do k = 1, 8
    sum_fac = sum_fac + sw%wl(k) * sqrt(sw%rdr(k) / sw%eps_h)
  end do
  dcoef = sw%epsr * sw%rni * hmax(1)**(5.0/3.0) * sum_fac * sw%ainv
  nsub = 1
  if (dcoef > 0.0) then
    dt_lim = 0.5 / dcoef
    nsub = max(1, ceiling(dts / dt_lim))
  end if
  if (nsub > sw%nsubmax) then
    write(msg,'(a,i8,a,i8,a)') "saltwater_surf: required subcycles ", nsub, &
                               " exceed salt_nsubmax ", sw%nsubmax, &
                               " (reduce dt or increase salt_ni/salt_eps_h)"
    call par_stop(trim(msg))
  end if
  dtsub = dts / nsub

  do isub = 1, nsub
    call par_halo_cell(s%hss)

    ! --- ループ1: エッジ流量(書き手はハロ行 je+1 まで冗長計算) ---
    jt = min(dcp%je + 1, dcp%jeh)
    !$omp parallel do schedule(static) &
    !$omp   private(i, j, k, in, jn, pc, pn, zc, zn, hup, hse, dp, gq, dh_up, dh_rcv, cap_rcv)
    do j = dcp%js, jt
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        zc = s%z(i,j) + s%hss(i,j)
        pc = (s%z(i,j) + s%h(i,j)) + sw%epsr * zc
        do k = 1, 4
          in = i + din(k)
          jn = j + djn(k)
          gq = 0.0
          if (g%sw(i,j) <= 0 .and. g%x(in,jn) > 0) then
            if (g%sw(in,jn) <= 0) then
              if (s%hss(i,j) > sw%eps .or. s%hss(in,jn) > sw%eps) then
                zn = s%z(in,jn) + s%hss(in,jn)
                pn = (s%z(in,jn) + s%h(in,jn)) + sw%epsr * zn
                if (pc /= pn) then
                  if (pc > pn) then
                    hup = s%hss(i,j)
                  else
                    hup = s%hss(in,jn)
                  end if
                  if (hup > sw%eps) then
                    hse = min(0.5 * (s%hss(i,j) + s%hss(in,jn)), hup)
                    dp = pc - pn
                    if (abs(dp) >= sw%eps_h) then
                      gq = sw%rni * hse**(5.0/3.0) &
                           * sign(sqrt(abs(dp) * sw%rdr(k)), dp) * sw%wl(k)
                    else
                      gq = sw%rni * hse**(5.0/3.0) &
                           * dp * sqrt(sw%rdr(k) / sw%eps_h) * sw%wl(k)
                    end if
                    ! 過大流出の抑制(上流側)と受け側容量(hss <= h)の制限
                    dh_up = abs(gq) * dtsub * sw%ainv
                    if (hup - dh_up <= sw%eps) then
                      gq = gq * (max(hup - sw%eps, 0.0) / dh_up)
                      dh_up = abs(gq) * dtsub * sw%ainv
                    end if
                    if (gq > 0.0) then
                      cap_rcv = max(s%h(in,jn) - s%hss(in,jn), 0.0)
                    else
                      cap_rcv = max(s%h(i,j) - s%hss(i,j), 0.0)
                    end if
                    dh_rcv = abs(gq) * dtsub * sw%ainv
                    if (dh_rcv > cap_rcv) then
                      gq = gq * (cap_rcv / dh_rcv)
                    end if
                  end if
                end if
              end if
            end if
          end if
          sw%qs(k, i+die(k), j+dje(k)) = gq
        end do
      end do
    end do
    !$omp end parallel do

    ! --- ループ2: 連続式(発散)。h は不変(交換流) ---
    !$omp parallel do schedule(static) private(i, j, k, dhg)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        dhg = 0.0
        do k = 1, 8
          dhg = dhg + sign_e(k) * sw%qs(ke(k), i+die(k), j+dje(k))
        end do
        s%hss(i,j) = s%hss(i,j) - dhg * dtsub * sw%ainv
      end do
    end do
    !$omp end parallel do
  end do
end subroutine


!----------------------------------------------------------------------
! 地下の塩水 zone 側方流(完全加算方式。ヘッダ (a)(b))
!   η は lateral_core の層1定義と同一(z − sd + hg/sy。飽和セルは + h)。
!   ζ = z − sd + hgs/sy。qs = K·b_s·ΔΦs·rdr·wl(Φs = η + εζ)、
!   qb = K·b_s·ε·Δζ·rdr·wl(合計 hg への追加分)。制限は両者に同率適用
!----------------------------------------------------------------------
subroutine gw_salt_zone(g, s, dts)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt
  real :: bc, bn, etac, etan, zetac, zetan, psc, psn, bup, bse
  real :: gqs, gqb, dh_up, r, dhs, dhb, capc, fx

  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) &
  !$omp   private(i, j, k, in, jn, bc, bn, etac, etan, zetac, zetan, psc, psn, &
  !$omp           bup, bse, gqs, gqb, dh_up, r)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      bc = s%hgs(i,j) * sw%syinv
      zetac = s%z(i,j) - s%sd(i,j) + bc
      etac = s%z(i,j) - s%sd(i,j) + s%hg(i,j) * sw%syinv
      if (s%hg(i,j) >= s%sd(i,j) * sw%sy) etac = etac + s%h(i,j)
      psc = etac + sw%epsr * zetac
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        gqs = 0.0
        gqb = 0.0
        if (g%sw(i,j) <= 0 .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            ! 乾燥判定は lateral_core と同じ飽和帯厚単位(柱状量単位だと
            ! sy 倍だけ保守的になり、前線で塩水輸送だけが削られて
            ! 見かけの淡水が残る系統誤差になる — 実検出 2026-08-18)
            bn = s%hgs(in,jn) * sw%syinv
            if (bc > sw%eps .or. bn > sw%eps) then
              zetan = s%z(in,jn) - s%sd(in,jn) + bn
              etan = s%z(in,jn) - s%sd(in,jn) + s%hg(in,jn) * sw%syinv
              if (s%hg(in,jn) >= s%sd(in,jn) * sw%sy) etan = etan + s%h(in,jn)
              psn = etan + sw%epsr * zetan
              if (psc /= psn) then
                ! 上流側(Φs の高い側)の塩水飽和帯厚
                if (psc > psn) then
                  bup = bc
                else
                  bup = bn
                end if
                if (bup > sw%eps) then
                  bse = min(0.5 * (bc + bn), bup)
                  gqs = sw%ksh * bse * (psc - psn) * sw%rdr(k) * sw%wl(k)
                  gqb = sw%ksh * bse * sw%epsr * (zetac - zetan) * sw%rdr(k) * sw%wl(k)
                  ! 過大流出の抑制(上流側。厚さ単位 = lateral_core と同一)。
                  ! 同率を qb にも適用(zone 流束の成分なので一体で縮小)
                  dh_up = abs(gqs) * dts * sw%ainv * sw%syinv
                  if (bup - dh_up <= sw%eps) then
                    r = max(bup - sw%eps, 0.0) / dh_up
                    gqs = gqs * r
                    gqb = gqb * r
                  end if
                end if
              end if
            end if
          end if
        end if
        sw%qs(k, i+die(k), j+dje(k)) = gqs
        sw%qb(k, i+die(k), j+dje(k)) = gqb
      end do
    end do
  end do
  !$omp end parallel do

  ! --- ループ2: 発散+容量超過の湧出(層1の規則)+整合クランプ ---
  !$omp parallel do schedule(static) private(i, j, k, dhs, dhb, capc, fx)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      dhs = 0.0
      dhb = 0.0
      do k = 1, 8
        dhs = dhs + sign_e(k) * sw%qs(ke(k), i+die(k), j+dje(k))
        dhb = dhb + sign_e(k) * sw%qb(ke(k), i+die(k), j+dje(k))
      end do
      s%hgs(i,j) = s%hgs(i,j) - dhs * dts * sw%ainv
      s%hg(i,j) = s%hg(i,j) - dhb * dts * sw%ainv
      ! 容量超過は地表へ湧出(層1の既存規則と同じ。湧出は下層 = 塩水を
      ! 先に持ち上げる…は追わず、湧出分だけ塩水を同伴させる近似:
      ! 溢れるのは水面直下の水 = 淡水優先が実態に近いので合計のみ動かす)
      capc = s%sd(i,j) * sw%sy
      if (s%hg(i,j) > capc) then
        fx = s%hg(i,j) - capc
        s%hg(i,j) = capc
        s%h(i,j) = s%h(i,j) + fx
        s%e(i,j) = s%z(i,j) + s%h(i,j)
      end if
      if (s%hgs(i,j) < 0.0) s%hgs(i,j) = 0.0
      if (s%hgs(i,j) > s%hg(i,j)) s%hgs(i,j) = s%hg(i,j)
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 地下の海側境界(規定水頭の交換。owner-compute のセル局所処理)
!   海域セル = 全塩水・水位 = 潮位(s%e)。塩水は双方向(hg と hgs を
!   同時更新)、淡水は流出のみ。行き過ぎ防止に等化量で制限する
!----------------------------------------------------------------------
subroutine gw_sea_exchange(g, s, dts)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn
  real :: base, bc, bsea, bse, zetac, etac, etasea, psc, pssea, capc
  real :: fx, bf

  !$omp parallel do schedule(static) &
  !$omp   private(i, j, k, in, jn, base, bc, bsea, bse, zetac, etac, etasea, &
  !$omp           psc, pssea, capc, fx, bf)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) cycle
        if (g%sw(in,jn) <= 0) cycle
        ! --- 海域セルとの交換(セル局所。複数の海隣接は k 順に直列) ---
        etasea = s%z(in,jn) + s%h(in,jn)              ! 潮位(m_tide が強制)
        base = s%z(i,j) - s%sd(i,j)                   ! 陸側の帯水層底
        if (etasea <= base) cycle                     ! 海が底より低い = 無接続
        capc = s%sd(i,j) * sw%sy
        bc = s%hgs(i,j) * sw%syinv
        zetac = base + bc
        etac = base + s%hg(i,j) * sw%syinv
        if (s%hg(i,j) >= capc) etac = etac + s%h(i,j)
        psc = etac + sw%epsr * zetac
        pssea = (1.0 + sw%epsr) * etasea              ! 海側 Φs(ζ_sea = η_sea)
        bsea = etasea - base                          ! 海側の塩水飽和厚
        ! 塩水交換(流入正)。界面厚は算術平均を上流側でキャップ
        if (pssea /= psc) then
          if (pssea > psc) then
            bse = min(0.5 * (bc + bsea), bsea)
          else
            bse = min(0.5 * (bc + bsea), bc)
          end if
          if (bse > 0.0) then
            fx = sw%ksh * bse * (pssea - psc) * sw%rdr(k) * sw%wl(k) * dts * sw%ainv
            ! 等化量・在庫・容量の制限
            fx = sign(min(abs(fx), abs(pssea - psc) * sw%sy / (1.0 + sw%epsr)), fx)
            if (fx > 0.0) then
              fx = min(fx, max(capc - s%hg(i,j), 0.0))
            else
              fx = -min(-fx, s%hgs(i,j))
            end if
            s%hgs(i,j) = s%hgs(i,j) + fx
            s%hg(i,j) = s%hg(i,j) + fx
          end if
        end if
        ! 淡水流出(η_land > 潮位のとき。海に淡水は存在しないため流入なし)
        bf = (s%hg(i,j) - s%hgs(i,j)) * sw%syinv
        if (etac > etasea .and. bf > sw%eps) then
          fx = sw%ksh * bf * (etac - etasea) * sw%rdr(k) * sw%wl(k) * dts * sw%ainv
          fx = min(fx, (etac - etasea) * sw%sy, s%hg(i,j) - s%hgs(i,j))
          if (fx > 0.0) s%hg(i,j) = s%hg(i,j) - fx
        end if
      end do
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル saltwater.dat。契約5。§7)
!   書き並び: hss, hgs(2 面 RLE。read も同順で更新すること)
!----------------------------------------------------------------------
subroutine save_state(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, allocatable :: wk(:,:)
  integer :: un
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
  else
    allocate(wk(1, 1), source = 0.0)
  end if
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/saltwater.dat', form='unformatted', &
         status='replace')
  end if
  call par_gather_to(wk, s%hss)
  if (is_root) call fileio_write_rle(un, wk)
  call par_gather_to(wk, s%hgs)
  if (is_root) then
    call fileio_write_rle(un, wk)
    close(un)
  end if
end subroutine


subroutine restore_state(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  logical :: found
  integer :: un

  ! 版・格子・精度の検証は m_state(check_save_info)が済ませている
  fname = trim(p%dir_save)//'/saltwater.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("saltwater: state file not found " &
                  // "(was fn_salt enabled when saving): "//fname)
  end if

  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, s%hss)
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, s%hgs)
    close(un)
  else
    call par_scatter_cell(dum, s%hss)
    call par_scatter_cell(dum, s%hgs)
  end if
end subroutine


!----------------------------------------------------------------------
! 淡塩2層モジュールを破棄する(save は dispose で行う。契約5)
!----------------------------------------------------------------------
subroutine m_saltwater_dispose(sl, p, g, s)
  type(t_saltwater), intent(inout) :: sl
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (.not. sl%enabled) return
  if (p%f_state_save > 0) call save_state(p, g, s)
  if (allocated(sw%qs)) deallocate(sw%qs)
  if (allocated(sw%qb)) deallocate(sw%qb)
  sw%initialized = .false.
  sl%enabled = .false.
  sl%initialized = .false.
end subroutine

end module
