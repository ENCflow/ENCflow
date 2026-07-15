module m_state
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use list_initial, only : t_list_initial, list_initial_read
  use m_parallel, only : is_root, par_info, par_stop
  use iso_fortran_env, only : output_unit
  implicit none
  private

  public :: t_state
  public :: m_state_init
  public :: m_state_dispose
  public :: m_state_updatetime
  public :: m_state_calcstat
  public :: m_state_printstate


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
    real, allocatable :: pre(:,:)       ! precipitation (m/s)
    real, allocatable :: prh(:,:)       ! precipitation (mm/h)
    real, allocatable :: tide(:,:)      ! tidal level (m)
    real, allocatable :: hmax(:,:)      ! maximum depth (m)
    real, allocatable :: hmaxt(:,:)     ! maximum depth time (min)
    real, allocatable :: vvmax(:,:)     ! maximum velocity (m/s)
    real, allocatable :: qqmax(:,:)     ! maximum discharge (m^2/s)
    real, allocatable :: qqdir(:,:)     ! maximum discharge direction (angle from x-axis, -pi~pi)
    real, allocatable :: qdir(:,:)      ! discharge direction (angle from x-axis, -pi~pi)
    real, allocatable :: qqt(:,:)       ! maximum discharge time (min)
    real, allocatable :: qcum(:,:)      ! cumulative flow rate (me
    real, allocatable :: fr(:,:)        ! Froude number
    real, allocatable :: cn(:,:)        ! Courant number
    integer, allocatable :: ddir1(:,:)  ! dominant down stream direction flag (2**(1~8))
    integer, allocatable :: ddir8(:,:)  ! all down stream direction flag (sum(2**(1~8)))
    real :: hmean
    real :: cnmax
    integer :: n_valcells               ! number of valid cells
    integer :: n_exfluxes               ! number of excessive fluxes
    integer :: n_runge                  ! number of Runge-Kutta flux calculations
    integer :: un_log                   ! ログファイルの装置番号
    logical :: initialized = .false.
  end type


  type t_state4prt
    real :: h
    real :: vv
    real :: qq
    real :: cn
    real :: runger
    integer :: n_exf
    integer :: count_disp
  end type
  type(t_state4prt) :: sp


  interface
    module subroutine init_state_user_1(p, g, s)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
    end subroutine
    module subroutine init_state_user_2(p, g, s)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
    end subroutine
    module subroutine init_state_user_3(p, g, s)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
    end subroutine
    module subroutine init_state_user_4(p, g, s)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
    end subroutine
  end interface


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
  integer :: i, j
  character(len=1024) :: msg

  ! メモリ確保
  allocate(s%h(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%u(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%v(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%m(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%n(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%qq(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%vv(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%e(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%pre(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%prh(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%tide(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%hmax(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%hmaxt(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%vvmax(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%qqmax(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%qqdir(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%qdir(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%qqt(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%qcum(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%fr(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%cn(1:p%nx,1:p%ny), source = 0.0)
  allocate(s%ddir1(1:p%nx,1:p%ny), source = 0)
  allocate(s%ddir8(1:p%nx,1:p%ny), source = 0)

  ! 初期条件設定ファイル読み込み
  call list_initial_read(p, list)

  ! 初期条件をセット
  call m_state_updatetime(s, p, 0)
  call set_h(p, g, s, list)
  call set_uv(p, g, s, list)

  s%n_valcells = 0           ! number of valid cells
  s%n_exfluxes = 0           ! number of excessive fluxes
  s%n_runge = 0              ! number of Runge-Kutta flux calculations

  if (p%f_state_restore > 0) call restore_state(p, s)

  ! ユーザールーチンによる初期条件をセット
  select case (list%f_user_routine_id)
    case (0)
      continue
    case (1)
      call init_state_user_1(p, g, s)
    case (2)
      call init_state_user_2(p, g, s)
    case (3)
      call init_state_user_3(p, g, s)
    case (4)
      call init_state_user_4(p, g, s)
    case default
      write(msg,'(a,i0)') "error: undefined f_user_routine_id in list_initial", list%f_user_routine_id
      call par_stop(trim(msg))
  end select

  ! 初期水位をセット
  s%e(:,:) = g%z(:,:) + s%h(:,:)

  ! 計算対称セルの数をセット(海域は除く)
  s%n_valcells = 0
  do j = 1, p%ny
    do i = 1, p%nx
      if (g%x(i,j) > 0 .and. g%sw(i,j) == 0) s%n_valcells = s%n_valcells + 1
    end do
  end do
  if (s%n_valcells <= 0) then
    call par_stop("No valid cell in the entire domain")
  end if

  ! 画面表示用の変数を初期化
  sp%h = 0
  sp%vv = 0
  sp%qq = 0
  sp%cn = 0
  sp%runger = 0
  sp%n_exf = 0
  sp%count_disp = 0

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
  real :: qqmax
  real :: cnmax
  real :: hsum
  real :: hsum_j(1:p%ny)
  real :: qcumf
  real :: cosdir
  real :: cc
  integer :: i, j

  hsum = 0
  hsum_j(:) = 0.0
  hmax = 0
  vvmax = 0
  qqmax = 0
  cnmax = 0
  qcumf = p%dt / p%dx / p%dy / s%n_valcells * 1000

  !$omp parallel do private(i, j, cosdir, cc), & 
  !$omp reduction(+: hsum), reduction(max: hmax, vvmax, qqmax, cnmax)
  do j = 1, p%ny
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) == 0) cycle
      if (s%h(i,j) <= 0) cycle
      if (s%h(i,j) > s%hmax(i,j)) then
        s%hmax(i,j) = s%h(i,j)                                 ! 最大水深
        s%hmaxt(i,j) = s%t / 60.                               ! 最大水深発生時刻(min)
      end if
      if (s%vv(i,j) > s%vvmax(i,j)) s%vvmax(i,j) = s%vv(i,j)   ! 最大流速
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
        s%cn(i,j) = s%vv(i,j) * p%dtpdx                        ! クーラン数(波速を無視)
      else
        s%cn(i,j) = (s%vv(i,j) + cc) * p%dtpdx                 ! クーラン数(波速を考慮)
      end if
      hsum_j(j) = hsum_j(j) + s%h(i,j)
      hmax = max(hmax, s%h(i,j))
      vvmax = max(vvmax, s%vv(i,j))
      qqmax = max(qqmax, s%qq(i,j))
      cnmax = max(cnmax, s%cn(i,j))
      s%qcum(i,j) = s%qcum(i,j) + (abs(s%m(i,j)) * p%dy + abs(s%n(i,j)) * p%dx) * qcumf
    end do
  end do
  !$omp end parallel do

  hsum = sum(hsum_j(:))                                        ! 並列化時の実行順依存誤差対策
  s%hmean = hsum / s%n_valcells                                ! 領域平均貯留高(m)
  s%cnmax = cnmax                                              ! 領域最大クーラン数

  ! 画面出力ステップ内での最大値(画面出力時にリセットされる)
  sp%h = max(sp%h, hmax)
  sp%vv = max(sp%vv, vvmax)
  sp%qq = max(sp%qq, qqmax)
  sp%cn = max(sp%cn, cnmax)
  sp%n_exf = max(sp%n_exf, s%n_exfluxes)
  sp%runger = max(sp%runger, s%n_runge / (real(s%n_valcells) * 4) * 100)

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
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  real :: progress      ! 進行割合(%)
  character(len=256) :: fmt, fmt0
  character(len=1024) :: msg
  integer :: digi1, digi2, digi3
  real :: hmean

  if (.not. is_root) return

  ! 凡例を表示
  if (mod(sp%count_disp, 36) == 0) then
    call par_info("time, progress, S(m), Runge, ex_flux, h_max(m), V_max(m/s), Q_max(m2/s), Cn_max")
    write(s%un_log, '(a)') "time, progress, S(m), Runge, ex_flux, h_max(m), V_max(m/s), Q_max(m2/s), Cn_max"
    flush(s%un_log)
  end if

  progress = (s%it) / real(p%nt) * 100
  hmean = s%hmean
  digi1 = p%real_precision + 5                          ! 全体の表示桁数
  digi2 =  max(1, int(log10(max(hmean, 1e-6))) + 1)     ! 整数部の桁数(1未満の場合も1桁)
  digi3 = p%real_precision - digi2 - 0                  ! 小数点以下の表示桁数
  digi3 = max(digi3, 1)
  write(fmt0, '("f",i2,".",i0)') digi1, digi3
  fmt = '(RN,a," ",f5.1,"%",' //trim(fmt0)// '," ",f5.1,"%",i7,*(f10.4))'     ! RNはround='nearest'に相当
  write(msg, fmt) s%ctime, progress, hmean, sp%runger, sp%n_exf, sp%h, sp%vv, sp%qq, sp%cn
  call par_info(trim(msg))
  write(s%un_log, fmt) s%ctime, progress, hmean, sp%runger, sp%n_exf, sp%h, sp%vv, sp%qq, sp%cn
  flush(s%un_log)

  ! 画面出力用の最大値のリセット
  sp%h = 0
  sp%vv = 0
  sp%qq = 0
  sp%cn = 0
  sp%n_exf = 0
  sp%runger = 0

  ! 凡例表示のカウンタを更新
  sp%count_disp = sp%count_disp + 1
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
  if (allocated(s%vv)) deallocate(s%vv)
  if (allocated(s%qq)) deallocate(s%qq)
  if (allocated(s%pre)) deallocate(s%pre)
  if (allocated(s%prh)) deallocate(s%prh)
  if (allocated(s%tide)) deallocate(s%tide)
  if (allocated(s%hmax)) deallocate(s%hmax)
  if (allocated(s%hmaxt)) deallocate(s%hmaxt)
  if (allocated(s%vvmax)) deallocate(s%vvmax)
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
subroutine set_h(p, g, s, list)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  type(t_state), intent(inout) :: s
  type(t_list_initial), intent(in) :: list
  integer :: i, j
  forall(i=1:p%nx, j=1:p%ny, g%x(i,j) > 0) s%h(i,j) = list%h0
  if (list%f_fill_depres > 0)  call fill_depression(p, g, s, list)
  if (list%h0_rw > 0.0) call adjust_h0rw(p, g, s, list)

end subroutine

!----------------------------------------------------------------------
! 窪地を水で埋める
!----------------------------------------------------------------------
subroutine fill_depression(p, g, s, list)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  type(t_state), intent(inout) :: s
  type(t_list_initial), intent(in) :: list
  integer :: i, j, k
  integer :: in, jn
  integer :: l
  integer :: iadj, nadj
  real :: ec, en, ec1, en1
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]

  if (p%initialized) continue

  if (is_root) then
    write(output_unit, '(a)', advance='no') " filling depressions "
    flush(output_unit)
  end if

  ! 対象セルに初期水深を与える
  do j = g%wy(1), g%wy(2)
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) < 1) cycle        ! 領域外は除外
      if (g%sw(i,j) > 0) cycle       ! 海は除外
      if (list%f_fill_depres >= 2 .and. g%rw(i,j) < 1) cycle   ! 河道以外は除外
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
        if (list%f_fill_depres >= 2 .and. g%rw(i,j) < 1) cycle  ! 河道以外は除外
        if (s%h(i,j) <= 0) cycle                                ! 既に水が無いセルは除外
        ec = g%z(i,j) + s%h(i,j)                                ! 自セルの水位
        iadj = 0
        do k = 1, 8
          in = i + din(k)
          jn = j + djn(k)
          if (g%sw(in,jn) > 0) then                             ! 海に隣接する場合は
            s%h(i,j) = 0                                        ! 自セルの水深をゼロに
          else
            if (list%f_fill_depres >= 2 .and. g%rw(in,jn) < 1) cycle   ! 近傍セルが河道以外は除外
            en = g%z(in,jn) + s%h(in,jn)      ! 近傍セルの水位
            if (ec > en) then                 ! 自セルの方が水位が高い場合は自セルの水位を下げる
              ec1 = max(en, g%z(i,j))         ! 自セルの水位は自セルの標高以下にはならない
              s%h(i,j) = ec1 - g%z(i,j)       ! 水深は水位から標高を減じる
              iadj = 1
            else if (en > ec .and. s%h(in,jn) > 0) then   ! 近傍セルに水が有りかつ水位が高い
              en1 = max(en, g%z(in,jn))         ! 近傍セルの水位は近傍セルの標高以下にはならない
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

  if (list%f_fill_depres >= 3) then
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
          g%z(i,j) = g%z(i,j) + s%h(i,j)
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
subroutine adjust_h0rw(p, g, s, list)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_initial), intent(in) :: list
  integer :: i, j
  if (p%initialized) continue
  do j = g%wy(1), g%wy(2)
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) > 0 .and. g%rw(i,j) > 0) then
        s%h(i,j) = s%h(i,j) + list%h0_rw
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 初期流速をセット
!----------------------------------------------------------------------
subroutine set_uv(p, g, s, list)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_initial), intent(in) :: list
  integer :: i, j
  forall(i=1:p%nx, j=1:p%ny, g%x(i,j) > 0) s%u(i,j) = list%u0
  forall(i=1:p%nx, j=1:p%ny, g%x(i,j) > 0) s%v(i,j) = list%v0
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
  if (p%initialized) continue
  if (s%initialized) continue
  open(newunit=un, file=trim(p%dir_result)//'/save_state.dat', form='unformatted', status='replace')
  write(un) s%h, s%u, s%v
  close(un)
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine restore_state(p, s)
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  integer :: un
  if (p%initialized) continue
  if (s%initialized) continue
  open(newunit=un, file=trim(p%dir_result)//'/save_state.dat', form='unformatted', status='old')
  read(un) s%h, s%u, s%v
  close(un)
end subroutine

end module
