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
    integer :: f_fill_depres = 0  ! 窪地を満水にする (0:無効, 1:有効, ...)
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
    real, allocatable :: rsh(:,:)       ! water depth of reservoir (m)
    real, allocatable :: hg(:,:)        ! 地下貯留水深(柱状換算)(m)。どの地下水
                                        ! モデルも毎ステップここに反映する契約
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
    real :: hgmean = 0.0     ! 領域平均の地下貯留高(m)。gw_active 時のみ更新
    logical :: gw_active = .false.  ! 地下水モデルの有効化(m_gwflow_init が設定)
    real :: hmean
    real :: cnmax
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
    module function user_initial_id2name(id) result(name)
      integer, intent(in) :: id
      character(len=:), allocatable :: name
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
  character(len=*), parameter :: save_version_cur = "2026-07-31b"
  integer, parameter :: n_state_save = 4     ! state.dat の成分数(h,z,rsh,hg)


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
  character(len=:), allocatable :: uname   ! user フックの識別名

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
  allocate(s%rsh(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%hg(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
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

  ! 初期条件設定ファイル読み込み
  call list_initial_read(p, list)

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
  allocate(ts%rsh(1:g%nx,1:g%ny), source = 0.0)
  allocate(ts%hg(1:g%nx,1:g%ny), source = 0.0)

  call m_state_updatetime(s, p, 0)
  call set_z(p, g, ts)
  call set_h(p, g, ts)     ! set_z()よりも後に実行
  call set_uv(p, g, ts)

  s%n_valcells = 0           ! number of valid cells
  s%n_exfluxes = 0           ! number of excessive fluxes
  s%n_runge = 0              ! number of Runge-Kutta flux calculations

  if (p%f_state_restore > 0) call restore_state(p, ts)

  ! ユーザールーチンによる初期条件をセット(全域添字契約: ts に書く)。
  ! 個々のルーチンへの分岐は user_initial submodule 内(互換入力の id は
  ! 識別名に変換して単一の名簿で解決する)。実行は全ランク冗長
  if (list%f_user_routine_id /= 0) then
    uname = user_initial_id2name(list%f_user_routine_id)
    if (len_trim(uname) == 0) then
      call par_stop("undefined f_user_routine_id in list_initial"//itoa(list%f_user_routine_id))
    end if
    call user_initial_run(p, g, ts, uname)
  end if

  ! --- 担当帯(+ハロ)を切り出す。ts はスコープ終了で自動解放 ---
  s%h(:,:) = ts%h(1:g%nx, dcp%jsh:dcp%jeh)
  s%u(:,:) = ts%u(1:g%nx, dcp%jsh:dcp%jeh)
  s%v(:,:) = ts%v(1:g%nx, dcp%jsh:dcp%jeh)
  s%z(:,:) = ts%z(1:g%nx, dcp%jsh:dcp%jeh)
  s%rsh(:,:) = ts%rsh(1:g%nx, dcp%jsh:dcp%jeh)
  s%hg(:,:) = ts%hg(1:g%nx, dcp%jsh:dcp%jeh)
  s%ini = ts%ini

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
  real :: qqmax
  real :: cnmax
  ! 診断集約の総和は PREC によらず real64 で行う(単精度ビルドでの
  ! 桁落ち防止。倍精度ビルドでは real64=既定 real で従来と同一。§1)
  real(real64) :: hsum
  real(real64) :: hsum_j(dcp%js:dcp%je)
  real(real64) :: hgsum
  real(real64) :: hgsum_j(dcp%js:dcp%je)
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
  hmax = 0
  vvmax = 0
  qqmax = 0
  cnmax = 0
  qcumf = p%dt / g%dx / g%dy / s%n_valcells * 1000
  dtpdx = p%dt / min(g%dx, g%dy)

  !$omp parallel do schedule(dynamic) private(i, j, cosdir, cc), & 
  !$omp reduction(max: hmax, vvmax, qqmax, cnmax)
  do j = dcp%js, dcp%je
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
        s%cn(i,j) = s%vv(i,j) * dtpdx                          ! クーラン数(波速を無視)
      else
        s%cn(i,j) = (s%vv(i,j) + cc) * dtpdx                   ! クーラン数(波速を考慮)
      end if
      hsum_j(j) = hsum_j(j) + s%h(i,j)
      if (s%gw_active) hgsum_j(j) = hgsum_j(j) + s%hg(i,j)
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
  rmax = [hmax, vvmax, qqmax, cnmax]
  call par_allreduce_max(rmax)
  hmax  = rmax(1)
  vvmax = rmax(2)
  qqmax = rmax(3)
  cnmax = rmax(4)
  nglob = [s%n_exfluxes, s%n_runge]
  call par_allreduce_sumi(nglob)

  s%hmean = hsum / s%n_valcells                                ! 領域平均貯留高(m)
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
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  real :: progress      ! 進行割合(%)
  character(len=256) :: fmt, fmt0
  character(len=1024) :: msg
  integer :: digi1, digi2, digi3
  real :: hmean

  if (.not. is_root) return

  ! 凡例を表示
  if (mod(s%sp%count_disp, 36) == 0) then
    if (s%gw_active) then
      call par_info("time, progress, S_surf(m), S_grnd(m), S_total(m), Runge, ex_flux, h_max(m), V_max(m/s), Q_max(m2/s), Cn_max")
      write(s%un_log, '(a)') "time, progress, S_surf(m), S_grnd(m), S_total(m), Runge, " &
                             //"ex_flux, h_max(m), V_max(m/s), Q_max(m2/s), Cn_max"
    else
      call par_info("time, progress, S(m), Runge, ex_flux, h_max(m), V_max(m/s), Q_max(m2/s), Cn_max")
      write(s%un_log, '(a)') "time, progress, S(m), Runge, ex_flux, h_max(m), V_max(m/s), Q_max(m2/s), Cn_max"
    end if
    flush(s%un_log)
  end if

  progress = (s%it) / real(p%nt) * 100
  hmean = s%hmean
  if (s%gw_active) then
    ! 地下水有効時: S を S_surf / S_grnd / S_total の3列に拡張。
    ! 桁数は最大の量(S_total)に合わせる。閉じた系では S_total が保存監視列
    digi1 = p%real_precision + 5
    digi2 =  max(1, int(log10(max(hmean + s%hgmean, 1e-6))) + 1)
    digi3 = p%real_precision - digi2 - 0
    digi3 = max(digi3, 1)
    write(fmt0, '("f",i2,".",i0)') digi1, digi3
    fmt = '(RN,a," ",f5.1,"%",3(' //trim(fmt0)// ',1x)," ",f5.1,"%",i7,*(f10.4))'
    write(msg, fmt) s%ctime, progress, hmean, s%hgmean, hmean + s%hgmean, &
                    s%sp%runger, s%sp%n_exf, s%sp%h, s%sp%vv, s%sp%qq, s%sp%cn
    call par_info(trim(msg))
    write(s%un_log, fmt) s%ctime, progress, hmean, s%hgmean, hmean + s%hgmean, &
                    s%sp%runger, s%sp%n_exf, s%sp%h, s%sp%vv, s%sp%qq, s%sp%cn
  else
    digi1 = p%real_precision + 5                          ! 全体の表示桁数
    digi2 =  max(1, int(log10(max(hmean, 1e-6))) + 1)     ! 整数部の桁数(1未満の場合も1桁)
    digi3 = p%real_precision - digi2 - 0                  ! 小数点以下の表示桁数
    digi3 = max(digi3, 1)
    write(fmt0, '("f",i2,".",i0)') digi1, digi3
    fmt = '(RN,a," ",f5.1,"%",' //trim(fmt0)// '," ",f5.1,"%",i7,*(f10.4))'     ! RNはround='nearest'に相当
    write(msg, fmt) s%ctime, progress, hmean, s%sp%runger, s%sp%n_exf, s%sp%h, s%sp%vv, s%sp%qq, s%sp%cn
    call par_info(trim(msg))
    write(s%un_log, fmt) s%ctime, progress, hmean, s%sp%runger, s%sp%n_exf, s%sp%h, s%sp%vv, s%sp%qq, s%sp%cn
  end if
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
  if (allocated(s%rsh)) deallocate(s%rsh)
  if (allocated(s%hg)) deallocate(s%hg)
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
      call par_stop("list_initial: f_htype は 0(水深固定)・1(水深ファイル)・" &
                    //"2(水位固定)・3(水位ファイル)です: "//itoa(s%ini%f_htype))
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
                  //" には fn_hinit の指定が必要です")
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
  ! write(un) wk のレコードは h, z, rsh, hg の連結。
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
  call par_gather_to(wk(:,:,3), s%rsh)
  call par_gather_to(wk(:,:,4), s%hg)
  if (.not. is_root) return
  open(newunit=un, file=trim(p%dir_save)//'/state.dat', form='unformatted', status='replace')
  ! 成分ごとにゼロ抑制 RLE で書く(海域・乾燥域のゼロを圧縮。§7)
  call fileio_write_rle(un, wk(:,:,1))   ! h
  call fileio_write_rle(un, wk(:,:,2))   ! z
  call fileio_write_rle(un, wk(:,:,3))   ! rsh
  call fileio_write_rle(un, wk(:,:,4))   ! hg
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
  ! 門番: メタデータを検証してから読む(不一致は par_stop)
  call check_save_info(p)

  ! rank0 が読み、全ランクへ配布する。受け取る s は全域一時状態 ts
  ! (全ランク同形)なので Bcast が成立する。帯への切り出しは呼び出し側
  if (is_root) then
    open(newunit=un, file=trim(p%dir_save)//'/state.dat', form='unformatted', status='old')
    ! 読み並びは save_state の書き込み順(h, z, rsh, hg)と一致させること。
    ! 成分を足すときは save と restore を必ず同時に更新する
    call fileio_read_rle(un, s%h)
    call fileio_read_rle(un, s%z)
    call fileio_read_rle(un, s%rsh)
    call fileio_read_rle(un, s%hg)
    close(un)
  end if
  call par_bcast_cell(s%h)
  call par_bcast_cell(s%z)
  call par_bcast_cell(s%rsh)
  call par_bcast_cell(s%hg)
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
  integer :: nx, ny, precision_bits, n_state, it
  real :: t
  namelist /save_info/ save_version, nx, ny, precision_bits, n_state, t, it

  if (.not. is_root) return
  save_version = save_version_cur
  nx = dcp%nx_g
  ny = dcp%ny_g
  precision_bits = storage_size(1.0)
  n_state = n_state_save
  t = s%t
  it = s%it
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
!   ここで検証済みとして自ファイルの有無だけを確認すればよい(§7)
!----------------------------------------------------------------------
subroutine check_save_info(p)
  type(t_sysparam), intent(in) :: p
  integer :: un, ios
  character(:), allocatable :: fname
  character(len=16) :: save_version
  integer :: nx, ny, precision_bits, n_state, it
  real :: t
  namelist /save_info/ save_version, nx, ny, precision_bits, n_state, t, it

  fname = trim(p%dir_save)//'/save_info.txt'
  save_version = ""
  nx = -1; ny = -1; precision_bits = -1; n_state = -1
  t = 0.0; it = 0

  open(newunit=un, file=fname, status='old', action='read', iostat=ios)
  if (ios /= 0) then
    call par_stop("save_info.txt がありません(save が存在しないか不完全です): "//fname)
  end if
  read(un, nml=save_info, iostat=ios)
  close(un)
  if (ios /= 0) call par_stop("save_info.txt を読めません: "//fname)

  if (trim(save_version) /= save_version_cur) then
    call par_stop("save は "//trim(save_version)//" 版の形式で保存されていますが、" &
                  //"この実行形式が読めるのは "//save_version_cur//" 版です: "//fname)
  end if
  if (nx /= dcp%nx_g .or. ny /= dcp%ny_g) then
    call par_stop("save の格子("//itoa(nx)//" x "//itoa(ny)//")が" &
                  //"現在の格子("//itoa(dcp%nx_g)//" x "//itoa(dcp%ny_g)//")と一致しません")
  end if
  if (precision_bits /= storage_size(1.0)) then
    call par_stop("save の実数精度("//itoa(precision_bits)//" bit)が" &
                  //"実行時の精度("//itoa(storage_size(1.0))//" bit)と一致しません")
  end if
  if (n_state /= n_state_save) then
    call par_stop("save の状態成分数("//itoa(n_state)//")が想定(" &
                  //itoa(n_state_save)//")と一致しません")
  end if

  call par_info("restore: t="//rtoa(t)//" s (it="//itoa(it)//") の保存状態を初期条件に読み込みます")
end subroutine

end module
