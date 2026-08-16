module m_precip
  use,intrinsic :: ieee_arithmetic
  use m_sysparam, only : t_sysparam
  use m_state, only : t_state
  use m_geoinfo, only : t_geoinfo
  use m_meteo, only : t_meteo, meteo_prec_factor
  use m_util, only : str2sec, itoa
  use m_fileio, only : fileio_un_open, fileio_un_read_matrix, fileio_read_matrix
  use list_precip, only : t_list_precip, list_precip_read
  use m_parallel, only : par_info, par_stop, dcp
  implicit none
  private

  public :: t_precip
  public :: m_precip_init
  public :: m_precip_dispose
  public :: m_precip_makepre

  type t_precip
    ! 降雨タイプ(0:降雨なし, 1:一様時系列, 2:分布×割合時系列, 3:分布時系列ファイル)
    integer :: prtype = 0
    real :: dt_prupdate = 0.0           ! 降雨分布更新時間間隔 (min)
    integer :: idt_prupdate = 0         ! 降雨分布更新時間ステップ数
    integer :: npr = 0                  ! 時系列データの個数
    real, allocatable :: prval(:,:)     ! 降雨時系列 (時刻(s), 降水強度(mm/h)または倍率)
    real, allocatable :: prmap(:,:)     ! 降雨分布 (mm/day)
    real :: dt_maplist = 0.0            ! 降雨分布ファイル時間間隔 (min)
    real :: dt_mapunit = 0.0            ! 降雨分布ファイルの積算時間単位 (min)
    integer :: idt_maplist = 0          ! 降雨分布ファイル更新時間ステップ数
    integer, allocatable :: un_maplist(:)  ! 降雨分布ファイル装置番号
    real :: runoff_rate = 0.0           ! 流出率
    logical :: initialized = .false.
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 降水構造体を初期化
!----------------------------------------------------------------------
subroutine m_precip_init(pr, p, g)
  type(t_precip), intent(out) :: pr
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
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
    pr%idt_prupdate = p%nt + 1     ! 降雨分布の更新間隔を全時間ステップ以上に
    return
  end if

  if (prtype == 1 .or. prtype == 2) then
    call set_precip                  ! 降水時系列データを保存
    if (prtype == 2 ) call set_prmap ! 降水分布データを保存
  else if (prtype == 3) then
    call set_maplist
  else
    call par_stop("list_precip: prtype must be 1(uniform series), 2(map with factor series) or " &
                  //"3(map list): "//itoa(prtype))
  end if

  pr%prtype = prtype
  pr%dt_prupdate = list%dt_prupdate
  pr%idt_prupdate = max(nint(pr%dt_prupdate * 60 / p%dt), 1)
  pr%dt_maplist = list%dt_maplist
  pr%idt_maplist = max(nint(pr%dt_maplist * 60 / p%dt), 1)
  pr%runoff_rate = max(list%runoff_rate, 0.0)

  if (len(trim(list%dt_maplist_c)) > 0) pr%dt_maplist = &
                str2sec(list%dt_maplist_c, "list_precip: dt_maplist_c is not a valid duration")
  if (len(trim(list%dt_mapunit_c)) > 0) pr%dt_mapunit = &
                str2sec(list%dt_mapunit_c, "list_precip: dt_mapunit_c is not a valid duration")

  if (list%dt_mapunit > 0.0) then
    pr%dt_mapunit = list%dt_mapunit
  else
    if (prtype == 2) then
      pr%dt_mapunit = 24 * 3600          ! 分布×倍率の場合はデフォルトは(mm/day)
    else
      pr%dt_mapunit = pr%dt_maplist * 60 ! 解析雨量の場合はデフォルトはファイルの間隔 (min->sec)
    end if
  end if

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

  if (npr <= 0) call par_stop("list_precip: prval has no valid entries (required for prtype=1 and 2)")

end subroutine

!----------------------------------------------------------------------
subroutine set_prmap
  character(:), allocatable :: fname
  integer :: i, j, have_nan
  if (len_trim(list%fn_prmap) == 0) then
    call par_stop("list_precip: prtype=2 requires fn_prmap")
  end if

  ! 降水分布の読み込み
  ! 入力データ配列は全域確保のまま(全ランク冗長読み込み。developer.md §11)
  allocate(pr%prmap(1:g%nx,1:g%ny))
  fname = trim(p%dir_data)//"/"//trim(list%fn_prmap)
  call fileio_read_matrix(fname, g%nx, g%ny, pr%prmap, p%f_input_mode)

  ! データにNaNが含まれている場合はゼロに修正
  have_nan = 0
  do j = 1, g%ny
    do i = 1, g%nx
      if (ieee_is_nan(pr%prmap(i,j))) then
        pr%prmap(i,j) = 0
        have_nan = have_nan + 1
      end if
    end do
  end do
  if (have_nan > 0) then
    call par_info("precip: "//itoa(have_nan)//" cells with NaN in the precipitation map, treated as 0")
  end if
end subroutine

!----------------------------------------------------------------------
subroutine set_maplist
  character(:), allocatable :: fname, fname_map
  character(len=256) :: mapname
  integer :: un
  integer :: i, n
  integer :: ios
  if (len_trim(list%fn_maplist) == 0) then
    call par_stop("list_precip: prtype=3 requires fn_maplist")
  end if

  ! 分布リストの行数をカウント
  fname = trim(p%dir_data)//"/"//trim(list%fn_maplist)
  call par_info(" reading precipitation map list "//trim(fname))
  open(newunit=un, file=trim(fname), status='old')
  n = 0
  do 
    read(un, *, iostat=ios)
    if (ios < 0) exit
    n = n + 1
  end do
  allocate(pr%un_maplist(n))
  rewind(un)

  ! 分布ファイルを全てオープン
  do i = 1, n
    read(un, '(a256)') mapname
    fname_map = trim(p%dir_data)//"/"//trim(mapname)
    call par_info(" checking precipitation map "//trim(fname_map))
    pr%un_maplist(i) = fileio_un_open(fname_map, p%f_input_mode)
  end do
  close(un)
end subroutine

end subroutine m_precip_init

!----------------------------------------------------------------------
! 時刻tでの降水分布を作成
!   updated: このコールで s%pre / s%prh を実際に更新したか。
!   m_intercept_calc(遮断)の呼び出しガードに使う(prtype=3 は呼ばれても
!   更新しないステップがあり、そこで遮断を再適用すると二重減衰になる)。
!   判定は全ランクで同一(s%it は全ランク共通)。
!   mt: 降水の標高勾配(f_prec_lapse。§45)。更新時に倍率を乗じる
!   (更新のたび元データから作り直すため二重適用はない)。無効時は
!   乗算経路に入らず従来とビット同一
!----------------------------------------------------------------------
subroutine m_precip_makepre(pr, p, g, s, mt, updated)
  type(t_precip), intent(in) :: pr
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_meteo), intent(in) :: mt
  logical, intent(out) :: updated
  real :: prval     ! 降水強度(mm/h)
  real :: f
  integer :: i, j
  integer :: un

  updated = .false.

  !---- 降水無しの場合は何もしない ----
  if (pr%prtype == 0) return


  !---- 降雨強度時系列から一様分布データを作成 ----
  if (pr%prtype == 1) then
    updated = .true.
    call get_prval(teval_cyc(), prval)   ! 現在時間ステップでの降水強度を計算
    f = 1. / 1000. / 3600.         ! 単位を(mm/h)から(m/s)に換算
    !$omp parallel do
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
        s%pre(i,j) = prval * f                  ! (m/s)
        s%prh(i,j) = s%pre(i,j) * 3600 * 1000    ! (mm/h)
        s%prh(i,j) = s%prh(i,j) * pr%runoff_rate
      end do
    end do
    !$omp end parallel do
  !---- 時系列倍率から分布データを作成 ----
  else if (pr%prtype == 2) then
    updated = .true.
    call get_prval(teval_cyc(), prval)   ! 現在時間ステップでの倍率を計算
    !f = 1. / 1000. / 3600. / 24.   ! 単位を(mm/day)から(m/s)に換算
    f = 1. / 1000. / pr%dt_mapunit   ! 単位を(m/s)に換算
    !$omp parallel do
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
        s%pre(i,j) = pr%prmap(i,j) * prval * f  ! (m/s)
        s%prh(i,j) = s%pre(i,j) * 3600 * 1000    ! (mm/h)
        s%prh(i,j) = s%prh(i,j) * pr%runoff_rate
      end do
    end do
    !$omp end parallel do
  !---- 降雨分布ファイルから作成 ----
  else if (pr%prtype == 3) then
    ! 分布境界ステップで次のフレームへ。restore 直後の初回呼び出し
    ! (s%it = s%it0 > 0)は境界ステップでなくても現在時刻を含む
    ! フレームを読み直す(中断なしランと同じ分布で継続する条件。§7)
    if (mod(s%it, pr%idt_maplist) == 0 .or. (s%it0 > 0 .and. s%it == s%it0)) then
      updated = .true.
      i = s%it / pr%idt_maplist + 1
      if (i <= size(pr%un_maplist)) then
        un = pr%un_maplist(i)
        ! 全域一時配列に読み、担当帯(+ハロ)を切り出す
        ! (降雨分布ファイルは全ランクが冗長に読む。developer.md §11)
        block
          real, allocatable :: wk(:,:)
          allocate(wk(1:g%nx, 1:g%ny))
          call fileio_un_read_matrix(un, g%nx, g%ny, wk, p%f_input_mode)
          s%prh(:,:) = wk(1:g%nx, dcp%jsh:dcp%jeh)
        end block
      else
        s%prh(:,:) = 0.0                         ! (mm/h)
      end if
      !s%pre(:,:) = s%prh(:,:) / 3600. / 1000.    ! (m/s)
      s%pre(:,:) = s%prh(:,:) / pr%dt_mapunit / 1000. * pr%runoff_rate   ! (m/s)
    end if
  end if

  ! ---- 降水の標高勾配(f_prec_lapse。§45)----
  !   標高は氷河有効時は氷面 z+hi(涵養は氷面の標高で決まる)。
  !   書き手は自帯 js..je のみ(pre のハロは全経路で従来から未使用)
  if (updated .and. mt%plapse) then
    !$omp parallel do private(i, j, f)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
        if (allocated(s%hi)) then
          f = meteo_prec_factor(mt, s%z(i,j) + s%hi(i,j))
        else
          f = meteo_prec_factor(mt, s%z(i,j))
        end if
        s%pre(i,j) = s%pre(i,j) * f
        s%prh(i,j) = s%prh(i,j) * f
      end do
    end do
    !$omp end parallel do
  end if

contains
 !----------------------------------------------------
 ! 系列参照の評価時刻(周期強制 t_cycle 指定時は mod で折り返す。§32.4。
 ! 未指定なら s%t のまま = 従来とビット同一)
 function teval_cyc() result(tv)
  real :: tv
  tv = s%t
  if (p%t_cycle > 0.0) tv = mod(max(s%t, 0.0), p%t_cycle)
 end function
 !----------------------------------------------------
 ! 時刻tでの降水強度または倍率を計算
 subroutine get_prval(t, val)
  real, intent(in) :: t
  real, intent(out) :: val
  real :: t0, t1, pre0, pre1
  integer :: k
  val = 0
  if (t <= pr%prval(1,1)) then
    val = pr%prval(2,1)
  else if (t > pr%prval(1,pr%npr)) then
    val = pr%prval(2,pr%npr)
  else
    do k = 2, pr%npr
      t1 = pr%prval(1,k)
      if (t < t1) then
        t0 = pr%prval(1,k-1)
        pre0 = pr%prval(2,k-1)
        pre1 = pr%prval(2,k)
        val = pre0 + (t - t0) / (t1 - t0) * (pre1 - pre0)
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
