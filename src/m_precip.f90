module m_precip
  use,intrinsic :: ieee_arithmetic
  use m_sysparam, only : t_sysparam
  use m_state, only : t_state
  use m_geoinfo, only : t_geoinfo
  use m_fileio
  use list_precip, only : t_list_precip, list_precip_read
  implicit none
  private

  public :: t_precip
  public :: m_precip_init
  public :: m_precip_dispose
  public :: m_precip_makepre

  type t_precip
    integer :: prtype                   ! 0:降雨なし, 1:一様時系列, 2:分布×割合時系列, 3:分布時系列ファイル
    real :: dt_prupdate                 ! 降雨分布更新時間間隔 (min)
    integer :: idt_prupdate             ! 降雨分布更新時間ステップ数
    integer :: npr                      ! 時系列データの個数
    real, allocatable :: prval(:,:)     ! 降雨時系列 (時刻(s), 降水強度(mm/h)または倍率)
    real, allocatable :: prmap(:,:)     ! 降雨分布 (mm/day)
    real :: dt_maplist                  ! 降雨分布ファイル時間間隔 (min)
    integer :: idt_maplist              ! 降雨分布ファイル更新時間ステップ数
    integer, allocatable :: un_maplist(:)  ! 降雨分布ファイル装置番号
    logical :: initialized = .false.
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 降水構造体を初期化
!----------------------------------------------------------------------
subroutine m_precip_init(pr, p)
  type(t_precip), intent(out) :: pr
  type(t_sysparam), intent(in) :: p
  type(t_list_precip) :: list
  integer :: prtype
  real, allocatable :: prval(:,:)

  !--- システムパラメータファイル内で設定ファイルが指定されている場合 ---
  if (len_trim(p%fn_precip) > 0) then
    !---- 設定ファイルを読み込む ----
    call list_precip_read(p, list)
    prtype = list%prtype
    prval = list%prval
  else
    prtype = 0
  end if

  if (prtype == 1 .or. prtype == 2) then
    call set_precip                  ! 降水時系列データを保存
    if (prtype == 2 ) call set_prmap ! 降水分布データを保存
  else if (prtype == 3) then
    call set_maplist
  else
    print *, "Error, Unknown prtype in list_precip", prtype
    stop
  end if

  pr%prtype = prtype
  pr%dt_prupdate = list%dt_prupdate
  pr%idt_prupdate = max(nint(pr%dt_prupdate * 60 / p%dt), 1)
  pr%dt_maplist = list%dt_maplist
  pr%idt_maplist = max(nint(pr%dt_maplist * 60 / p%dt), 1)

  pr%initialized = .true.

contains
!----------------------------------------------------------------------
subroutine set_precip
  integer :: npr
  integer :: i

  !---- 降水時系列データ数をカウント----
  npr = 0
  do i = 1, ubound(prval, 2)
    if (prval(1,i) < 0) exit  ! 有効なデータが無い場合は終了
    npr = npr + 1
  end do

  !---- 降水時系列データを保存 ----
  allocate(pr%prval(1:2,npr))
  pr%prval(1,1:npr) = prval(1,1:npr) * 60    ! 分を秒に換算
  pr%prval(2,1:npr) = prval(2,1:npr)
  pr%npr = npr

end subroutine

!----------------------------------------------------------------------
subroutine set_prmap
  character(:), allocatable :: fname
  integer :: i, j, have_nan
  if (len_trim(list%fn_prmap) == 0) then
    print *, "Error, prtype=2 but fn_prmap is not set" 
    stop
  end if

  ! 降水分布の読み込み
  allocate(pr%prmap(1:p%nx,1:p%ny))
  fname = trim(p%dir_data)//"/"//trim(list%fn_prmap)
  call fileio_read_matrix_real(fname, p%nx, p%ny, pr%prmap, p%f_input_mode)

  ! データにNaNが含まれている場合はゼロに修正
  have_nan = 0
  do j = 1, p%ny
    do i = 1, p%nx
      if (ieee_is_nan(pr%prmap(i,j))) then
        pr%prmap(i,j) = 0
        have_nan = have_nan + 1
      end if
    end do
  end do
  if (have_nan > 0) then
    print *, "warning: precipitation map has NaN in", have_nan, " cells"
  end if
end subroutine

!----------------------------------------------------------------------
subroutine set_maplist
  character(:), allocatable :: fname, fname_map
  character(len=256) :: mapname
  integer :: un
  integer :: i, n
  if (len_trim(list%fn_maplist) == 0) then
    print *, "Error, prtype=3 but fn_maplist is not set" 
    stop
  end if

  ! 分布リストの行数をカウント
  fname = trim(p%dir_data)//"/"//trim(list%fn_maplist)
  open(newunit=un, file=fname, status='old')
  n = 0
  do 
    read(un, *, end=99)
    n = n + 1
  end do
  99 continue
  allocate(pr%un_maplist(n))
  rewind(un)

  ! 分布ファイルを全てオープン
  do i = 1, n
    read(un, *) mapname
    fname_map = trim(p%dir_data)//"/"//trim(mapname)
    pr%un_maplist(i) = fileio_open_un(fname_map, p%f_input_mode)
  end do
  close(un)
end subroutine

end subroutine m_precip_init

!----------------------------------------------------------------------
! 時刻tでの降水分布を作成
!----------------------------------------------------------------------
subroutine m_precip_makepre(pr, p, g, s)
  type(t_precip), intent(in) :: pr
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real :: precip     ! 降水強度(mm/h)
  real :: f
  integer :: i, j
  integer :: un
  if (p%initialized) continue

  !---- 降水無しの場合は何もしない ----
  if (pr%prtype == 0) return


  !---- 降雨強度時系列から一様分布データを作成 ----
  if (pr%prtype == 1) then
    call get_precip(s%t, precip)   ! 現在時間ステップでの降水強度を計算
    f = 1. / 1000. / 3600.         ! 単位を(mm/h)から(m/s)に換算
    !$omp parallel do
    do j = g%wy(1), g%wy(2)
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
        s%pre(i,j) = precip * f                  ! (m/s)
        s%prh(i,j) = s%pre(i,j) * 3600 * 1000    ! (mm/h)
      end do
    end do
    !$omp end parallel do
  !---- 時系列倍率から分布データを作成 ----
  else if (pr%prtype == 2) then
    call get_precip(s%t, precip)   ! 現在時間ステップでの倍率を計算
    f = 1. / 1000. / 3600. / 24.   ! 単位を(mm/day)から(m/s)に換算
    !$omp parallel do
    do j = g%wy(1), g%wy(2)
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
        s%pre(i,j) = pr%prmap(i,j) * precip * f  ! (m/s)
        s%prh(i,j) = s%pre(i,j) * 3600 * 1000    ! (mm/h)
      end do
    end do
    !$omp end parallel do
  !---- 降雨分布ファイルから作成 ----
  else if (pr%prtype == 3) then
    if (mod(s%it, pr%idt_maplist) == 0) then
      i = s%it / pr%idt_maplist
      if (i <= size(pr%un_maplist)) then
        un = pr%un_maplist(i)
        call fileio_read_matrix_real_un(un, p%nx, p%ny, s%prh, p%f_input_mode)
      else
        s%prh(:,:) = 0.0                         ! (mm/h)
      end if
      s%pre(:,:) = s%prh(:,:) / 3600. / 1000.    ! (m/s)
    end if
  end if

contains
 !----------------------------------------------------
 ! 時刻tでの降水強度または倍率を計算
 subroutine get_precip(t, precip)
  real, intent(in) :: t
  real, intent(out) :: precip
  real :: t0, t1, pre0, pre1
  integer :: i
  precip = 0
  if (t <= pr%prval(1,1)) then
    precip = pr%prval(2,1)
  else if (t > pr%prval(1,pr%npr)) then
    precip = pr%prval(2,pr%npr)
  else
    do i = 2, pr%npr
      t1 = pr%prval(1,i)
      if (t < t1) then
        t0 = pr%prval(1,i-1)
        pre0 = pr%prval(2,i-1)
        pre1 = pr%prval(2,i)
        precip = pre0 + (t - t0) / (t1 - t0) * (pre1 - pre0)
        exit
      end if
    end do
  end if
 end subroutine
 !----------------------------------------------------
end subroutine

!----------------------------------------------------------------------
! 降水構造体を破棄
!----------------------------------------------------------------------
subroutine m_precip_dispose(pr)
  type(t_precip), intent(inout) :: pr
  if (allocated(pr%prval)) deallocate(pr%prval)
  if (allocated(pr%prmap)) deallocate(pr%prmap)
  if (allocated(pr%un_maplist)) deallocate(pr%un_maplist)
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
