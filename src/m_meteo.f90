module m_meteo
  ! ==================== 気象強制場モジュール(§29) ====================
  ! 気温(将来: 湿度・風速・放射等)の入力と評価を一元化し、消費者
  ! (蒸発散 m_evap、水質 m_wq の温度補正等)へ提供する。
  !   有効化: fn_meteo の指定(&list_meteo)
  !   気温入力: 一様定数 temp0 / 一様時系列 tempval(経過日, ℃)/
  !            分布時系列 fn_tempmap(リスト形式・dt_tempmap_c 間隔・
  !            終端は端値保持。rank0 読み+帯 scatter)
  !   標高減率: 一様入力のみ。T(z) = Tb − γ(z − zref)。zref 省略時は
  !            使用セルの領域最低標高(min の allreduce = 決定的)
  !   評価: 消費者が meteo_temp_set(teval) で評価時刻をセットし(分布
  !         ファイルの読み進みを含むため collective = 全ランク同一時刻で
  !         呼ぶこと)、meteo_temp_cell / meteo_temp_mean / _global で
  !         値を取り出す2段構え。時系列は線形補間・端値保持
  !   MPI: 一様系は (t, z) の純関数で全ランク同値。分布は帯 scatter。
  !        代表セル値の共有(_global)は単一寄与の allreduce(厳密)
  ! ====================================================================
  use iso_fortran_env, only : real64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_boundary, only : interp_series
  use list_meteo, only : t_list_meteo, list_meteo_read, nmtmax
  use m_fileio, only : fileio_read_matrix
  use m_parallel, only : dcp, is_root, par_info, par_stop, &
                         par_allreduce_min, par_allreduce_sumr, par_sum_rows, &
                         par_scatter_cell
  use m_util, only : str2sec
  implicit none
  private
  public :: t_meteo
  public :: m_meteo_init
  public :: m_meteo_dispose
  public :: meteo_temp_set
  public :: meteo_temp_cell
  public :: meteo_temp_global
  public :: meteo_temp_mean

  real, parameter :: secday = 86400.0

  ! 気温入力の種別
  integer, parameter :: e_tsrc_const = 1, e_tsrc_series = 2, e_tsrc_map = 3

  type t_meteo
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.
    logical :: initialized = .false.
    integer :: tsrc = 0            ! 気温入力の種別 (e_tsrc_*)
    real :: t0c = 0.0              ! 一様定数気温 (℃)
    integer :: ntser = 0
    real, allocatable :: tser(:,:) ! 一様時系列 (1:2,1:ntser) = (s, ℃)
    integer :: nmap = 0
    character(len=1024), allocatable :: mapfiles(:)  ! 分布ファイル名(dir_data 込み)
    real :: dtmap = 86400.0        ! 分布の時間間隔 (s)
    integer :: imap = -1           ! 読み込み済みファイル番号(1-based。-1=未読)
    real, allocatable :: tmap(:,:) ! 現在の気温分布 (℃)(帯)
    logical :: lapse = .false.
    real :: gam = 0.0              ! 気温減率 (℃/m)
    real :: zref = 0.0             ! 減率の基準標高 (m)
    real :: tb = 0.0               ! 現在の評価時刻の一様基準気温(℃。set が更新)
  end type

contains


!----------------------------------------------------------------------
! 気象強制場モジュールを初期化する
!   fn_meteo 未指定なら何もしない(enabled = .false.)。
!   検証はすべてここで行う(list_meteo は読むだけ。§12)
!----------------------------------------------------------------------
subroutine m_meteo_init(mt, p, g, s)
  type(t_meteo), intent(out) :: mt
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_list_meteo) :: list
  integer :: k, nsrc
  real :: zmin

  if (len_trim(p%fn_meteo) == 0) return

  call list_meteo_read(p, list)

  ! --- 気温入力(ちょうど1つを指定) ---
  nsrc = 0
  if (list%temp0 > -9998.0) then
    nsrc = nsrc + 1
    mt%tsrc = e_tsrc_const
    mt%t0c = list%temp0
  end if
  if (list%tempval(1,1) > -9998.0) then
    nsrc = nsrc + 1
    mt%tsrc = e_tsrc_series
    call setup_tseries(mt, list)
  end if
  if (len_trim(list%fn_tempmap) > 0) then
    nsrc = nsrc + 1
    mt%tsrc = e_tsrc_map
    call setup_tmaplist(mt, p, g, list)
  end if
  if (nsrc /= 1) then
    call par_stop("list_meteo: 気温入力は temp0 / tempval / fn_tempmap の" &
                  //"いずれか1つを指定してください")
  end if

  ! --- 標高減率(一様入力のみ) ---
  if (list%f_temp_lapse > 0) then
    if (mt%tsrc == e_tsrc_map) then
      call par_stop("list_meteo: f_temp_lapse は一様気温(temp0 / tempval)専用です" &
                    //"(分布気温には適用できません)")
    end if
    mt%lapse = .true.
    mt%gam = list%temp_lapse / 100.0            ! ℃/100m -> ℃/m
    if (list%temp_zref > -9998.0) then
      mt%zref = list%temp_zref
    else
      ! 既定 = 領域(使用セル)の最低標高。min は演算順によらず厳密 = 決定的
      zmin = huge(zmin)
      do k = dcp%js, dcp%je
        zmin = min(zmin, minval(s%z(g%wx(1,k):g%wx(2,k), k), &
                                mask = g%x(g%wx(1,k):g%wx(2,k), k) > 0))
      end do
      call par_allreduce_min(zmin)
      mt%zref = zmin
    end if
  end if

  mt%enabled = .true.
  mt%initialized = .true.
  call par_info("meteo forcing enabled (temperature)")
end subroutine


!----------------------------------------------------------------------
! 一様気温時系列の変換(経過日 -> 秒。interp_series の規約に合わせる)
!----------------------------------------------------------------------
subroutine setup_tseries(mt, list)
  type(t_meteo), intent(inout) :: mt
  type(t_list_meteo), intent(in) :: list
  integer :: k, n
  n = 0
  do k = 1, nmtmax
    if (list%tempval(1,k) <= -9998.0) exit     ! 番兵で終端
    n = n + 1
  end do
  if (n < 1) call par_stop("list_meteo: tempval が空です")
  do k = 2, n
    if (list%tempval(1,k) <= list%tempval(1,k-1)) then
      call par_stop("list_meteo: tempval の時刻(経過日)は単調増加で指定してください")
    end if
  end do
  allocate(mt%tser(1:2, 1:n))
  mt%tser(1,1:n) = list%tempval(1,1:n) * secday    ! 日 -> 秒
  mt%tser(2,1:n) = list%tempval(2,1:n)
  mt%ntser = n
end subroutine


!----------------------------------------------------------------------
! 気温分布ファイルリストの読み込み(1行1ファイル名。等間隔で順次適用、
! リストを過ぎたら最終ファイルを保持=端値保持)
!----------------------------------------------------------------------
subroutine setup_tmaplist(mt, p, g, list)
  type(t_meteo), intent(inout) :: mt
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_meteo), intent(in) :: list
  character(:), allocatable :: fname
  character(len=1024) :: line
  integer :: un, ios, n
  logical :: found

  mt%dtmap = str2sec(trim(list%dt_tempmap_c), "bad dt_tempmap_c in &list_meteo")
  if (mt%dtmap <= 0.0) call par_stop("list_meteo: dt_tempmap_c は正の時間です")

  fname = trim(p%dir_data)//"/"//trim(list%fn_tempmap)
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("list_meteo: fn_tempmap が見つかりません: "//fname)

  ! 1回目: 行数を数える / 2回目: 取り込む(全ランク冗長・同一)
  open(newunit=un, file=fname, status='old', action='read')
  n = 0
  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    if (len_trim(line) == 0) cycle
    n = n + 1
  end do
  if (n < 1) call par_stop("list_meteo: fn_tempmap にファイル名がありません: "//fname)
  allocate(mt%mapfiles(1:n))
  rewind(un)
  n = 0
  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    if (len_trim(line) == 0) cycle
    n = n + 1
    mt%mapfiles(n) = trim(p%dir_data)//"/"//trim(adjustl(line))
  end do
  close(un)
  mt%nmap = n

  allocate(mt%tmap(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
end subroutine


!----------------------------------------------------------------------
! 評価時刻のセット(collective: 分布ファイルの読み進みを含むため、
! 全ランクが同一の teval で呼ぶこと)。一様系は基準気温 tb を更新する
!----------------------------------------------------------------------
subroutine meteo_temp_set(mt, p, g, teval)
  type(t_meteo), intent(inout) :: mt
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: teval          ! シミュレーション時刻 (s)
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  integer :: need
  logical :: found

  if (.not. mt%enabled) call par_stop("meteo_temp_set: fn_meteo が未指定です")
  select case (mt%tsrc)
    case (e_tsrc_const)
      mt%tb = mt%t0c
    case (e_tsrc_series)
      ! 周期強制 t_cycle 指定時は mod で折り返す(§32.4。分布 map は対象外)
      if (p%t_cycle > 0.0) then
        mt%tb = interp_series(mt%tser, mt%ntser, mod(max(teval, 0.0), p%t_cycle))
      else
        mt%tb = interp_series(mt%tser, mt%ntser, teval)
      end if
    case (e_tsrc_map)
      need = min(max(int(floor(max(teval, 0.0) / mt%dtmap)) + 1, 1), mt%nmap)
      if (need == mt%imap) return
      inquire(file=trim(mt%mapfiles(need)), exist=found)
      if (.not. found) then
        call par_stop("list_meteo: 気温分布ファイルが見つかりません: "//trim(mt%mapfiles(need)))
      end if
      if (is_root) then
        allocate(wk(1:g%nx, 1:g%ny))
        call par_info(" reading "//trim(mt%mapfiles(need)))
        call fileio_read_matrix(trim(mt%mapfiles(need)), g%nx, g%ny, wk, p%f_input_mode)
        call par_scatter_cell(wk, mt%tmap)
      else
        call par_scatter_cell(dum, mt%tmap)
      end if
      mt%imap = need
  end select
end subroutine


!----------------------------------------------------------------------
! 自帯セルの気温(℃)。zc = セル標高(一様系の減率評価用。分布では無視)。
! 最後に set した評価時刻の値
!----------------------------------------------------------------------
function meteo_temp_cell(mt, i, j, zc) result(tc)
  type(t_meteo), intent(in) :: mt
  integer, intent(in) :: i, j
  real, intent(in) :: zc
  real :: tc
  if (mt%tsrc == e_tsrc_map) then
    tc = mt%tmap(i,j)
  else if (mt%lapse) then
    tc = mt%tb - mt%gam * (zc - mt%zref)
  else
    tc = mt%tb
  end if
end function


!----------------------------------------------------------------------
! 任意セルの気温(collective)。帯外セルでも全ランクが同値を得る:
! 一様系は (zc) の純関数、分布は所有ランクだけが寄与する allreduce
! (単一寄与の総和 = 順序によらず厳密)
!----------------------------------------------------------------------
function meteo_temp_global(mt, i, j, zc) result(tc)
  type(t_meteo), intent(in) :: mt
  integer, intent(in) :: i, j
  real, intent(in) :: zc
  real :: tc
  real :: w1(1)
  if (mt%tsrc == e_tsrc_map) then
    w1(1) = 0.0
    if (j >= dcp%js .and. j <= dcp%je) w1(1) = mt%tmap(i,j)
    call par_allreduce_sumr(w1)
    tc = w1(1)
  else
    tc = meteo_temp_cell(mt, i, j, zc)
  end if
end function


!----------------------------------------------------------------------
! 使用セル平均気温(collective。診断用)。一様・減率なしは tb を返す。
! 減率時は基準標高の値(=tb)を代表値とする
!----------------------------------------------------------------------
function meteo_temp_mean(mt, g) result(tc)
  type(t_meteo), intent(in) :: mt
  type(t_geoinfo), intent(in) :: g
  real :: tc
  integer :: i, j
  real :: tsum, tnum
  real :: w1(1)
  real(real64) :: rows(dcp%js:dcp%je), rsum
  if (mt%tsrc /= e_tsrc_map) then
    tc = mt%tb
    return
  end if
  rows(:) = 0.0_real64
  tnum = 0.0
  do j = dcp%js, dcp%je
    tsum = 0.0
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      tsum = tsum + mt%tmap(i,j)
      tnum = tnum + 1.0
    end do
    rows(j) = real(tsum, real64)
  end do
  call par_sum_rows(rows, rsum)
  w1(1) = tnum
  call par_allreduce_sumr(w1)     ! セル数(整数値の和 = 丸め順不問で厳密)
  tnum = w1(1)
  if (tnum > 0.0) then
    tc = real(rsum) / tnum
  else
    tc = 0.0
  end if
end function


!----------------------------------------------------------------------
! 気象強制場モジュールを破棄する
!----------------------------------------------------------------------
subroutine m_meteo_dispose(mt)
  type(t_meteo), intent(inout) :: mt
  if (allocated(mt%tser)) deallocate(mt%tser)
  if (allocated(mt%mapfiles)) deallocate(mt%mapfiles)
  if (allocated(mt%tmap)) deallocate(mt%tmap)
  mt%enabled = .false.
  mt%initialized = .false.
end subroutine

end module
