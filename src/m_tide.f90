!======================================================================
! m_tide: 潮位境界(海域マスクのセルへの時変水位強制)
!
! 意味論(developer.md §23):
!   海域マスク(sw>0)の領域内セルは「解かない・水位を強制する」セル。
!   水位 η は標高側で表現する: s%z = η − hsea0, s%h = hsea0(一定)。
!   continuous は海セルを更新しないため h は init の値が恒久に保たれ、
!   海陸エッジのフラックスは momentum が水面勾配から通常計算する
!   (海が供給側の浸水も hsea0 の水柱が dd 判定・he・摩擦を賄う)。
!   fn_tide 未指定なら海セルは従来どおり z=0, h=0(既存 reference と
!   ビット一致)。
!
! 潮位タイプ(titype):
!   1: 一様固定値 ti0 (m)
!   2: 一様時系列 tival(時刻 min, 潮位 m。線形補間)
!   3: 分布1枚 fn_timap (m) × 倍率時系列 tival(線形補間)
!   4: 分布ファイルリスト fn_timaplist(フレーム i の時刻は
!      (i-1)*dt_timaplist。隣接2枚を線形補間。範囲外は端値を保持)
!
! 時刻・更新:
!   更新は dt_tiupdate 間隔(mod(s%it, idt_tiupdate) == 0)。位相は
!   絶対ステップ番号 it 基準なので、再開(§7: it 継続)後も中断なし
!   ランと同じステップで更新される。restore 時は初期適用をスキップする
!   (海セルの z, h は保存状態が正本。再適用すると更新位相の途中時刻の
!   値で上書きされ往復ビット一致が破れる)。
!
! MPI: 全て自帯(js..je)のローカル適用で通信なし(§5 の二分法)。
!   s%z のハロは swflow のステップ頭交換が既に毎ステップ運ぶ。
!   分布ファイルは全ランクが冗長に読む(§11。パス指定の
!   fileio_read_matrix のみ使用: un 系 API は増やさない)
!======================================================================
module m_tide
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use list_tide, only : t_list_tide, list_tide_read
  use m_fileio, only : fileio_read_matrix
  use m_util, only : str2sec, itoa, rtoa
  use m_parallel, only : par_info, par_stop, dcp
  implicit none
  private

  public :: t_tide
  public :: m_tide_init
  public :: m_tide_calc
  public :: m_tide_dispose

  integer, parameter :: maxpathlen = 256

  type t_tide
    ! 潮位タイプ (0:なし, 1:一様固定値, 2:一様時系列,
    !             3:分布×倍率時系列, 4:分布ファイルリスト)
    integer :: titype = 0
    real :: ti0 = 0.0                   ! 一様固定潮位 (m)
    real :: hsea0 = 1.0                 ! 海セルの見かけ水柱厚 (m)
    integer :: idt_tiupdate = 1         ! 潮位更新時間ステップ数
    integer :: nti = 0                  ! 時系列データの個数
    real, allocatable :: tival(:,:)     ! 潮位時系列 (時刻(s), 潮位(m)または倍率)
    real, allocatable :: timap(:,:)     ! 潮位分布 (m。titype=3。帯+ハロ)
    ! ---- titype=4: 分布ファイルリスト ----
    integer :: nmap = 0                 ! 分布ファイルの数
    real :: dt_timap = 0.0              ! 分布の時間間隔 (s)
    character(len=maxpathlen), allocatable :: fn_map(:)  ! 分布ファイル名
    real, allocatable :: timap0(:,:)    ! 補間用バッファ(前フレーム。帯+ハロ)
    real, allocatable :: timap1(:,:)    ! 補間用バッファ(後フレーム。帯+ハロ)
    integer :: imap0 = 0                ! timap0 のフレーム番号(0:未読)
    integer :: imap1 = 0                ! timap1 のフレーム番号(0:未読)
    logical :: initialized = .false.
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 潮位構造体を初期化し、海セルの初期状態(z, h)をセットする
!   m_state_init より後・m_swflow_init より前に呼ぶこと(swflow init が
!   初期 h から h1・境界流量を作るため)。検証の判定材料は namelist と
!   全域マスク(ゾーン1)のみで全ランク同一(par_stop は collective 安全)
!----------------------------------------------------------------------
subroutine m_tide_init(ti, p, g, s)
  type(t_tide), intent(out) :: ti
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_tide) :: list
  integer :: i, j, nsea

  if (len_trim(p%fn_tide) == 0) then
    ti%titype = 0                  ! 潮位なし: 海セルは従来どおり z=0, h=0
    ti%initialized = .true.
    return
  end if

  !---- 設定ファイルを読み込む ----
  call list_tide_read(p, list)

  !---- 検証 ----
  if (list%titype < 1 .or. list%titype > 4) then
    call par_stop("list_tide: titype must be 1(uniform fixed), 2(uniform series), " // &
                  "3(map with factor) or 4(map list): "//itoa(list%titype))
  end if
  if (p%f_gridsystem /= 0) then
    call par_stop("list_sysparam: tide (fn_tide) requires the ENC grid system (f_gridsystem=0)")
  end if
  if (list%hsea0 <= p%dd) then
    call par_stop("list_tide: hsea0("//rtoa(list%hsea0)//") must be larger than the " // &
                  "depth threshold dd("//rtoa(p%dd)//"), tens of times dd or more is " // &
                  "recommended (the hsea0 water column supplies sea-driven flooding)")
  end if

  ! 領域内の海セル(x>0 かつ sw>0)の存在検査(ゾーン1: マスクは全域)
  nsea = 0
  do j = 1, g%ny
    do i = 1, g%nx
      if (g%x(i,j) > 0 .and. g%sw(i,j) > 0) nsea = nsea + 1
    end do
  end do
  if (nsea <= 0) then
    call par_stop("list_tide: no sea cells (sea mask fn_sw) in the domain")
  end if
  call par_info("tide: applying to "//itoa(nsea)//" sea cells (hsea0 = " // &
                rtoa(list%hsea0)//" m)")

  ti%titype = list%titype
  ti%ti0 = list%ti0
  ti%hsea0 = list%hsea0
  ti%idt_tiupdate = max(nint(list%dt_tiupdate * 60 / p%dt), 1)

  !---- タイプ別の準備 ----
  select case (ti%titype)
    case (2, 3)
      call set_tival
      if (ti%titype == 3) call set_timap
    case (4)
      call set_maplist
  end select

  ! 海セルの初期状態を適用する。restore 時はスキップ: z, h は保存状態が
  ! 正本で、更新位相(絶対 it 基準)の途中時刻の値で上書きすると
  ! リスタート往復ビット一致が破れる(§7)
  if (p%f_state_restore <= 0) then
    call apply(ti, p, g, s, p%t0)
  end if

  ti%initialized = .true.

contains
  !--------------------------------------------------------------------
  ! 潮位時系列を保存する(時刻は分→秒に換算)
  subroutine set_tival
    integer :: k, nti
    nti = 0
    do k = 1, ubound(list%tival, 2)
      if (list%tival(1,k) < 0) exit    ! 時刻列の番兵(-9999)で終端
      nti = nti + 1
    end do
    if (nti <= 0) then
      call par_stop("list_tide: titype="//itoa(ti%titype)// &
                    " requires a tival time series")
    end if
    allocate(ti%tival(1:2,1:nti))
    ti%tival(1,1:nti) = list%tival(1,1:nti) * 60    ! 分を秒に換算
    ti%tival(2,1:nti) = list%tival(2,1:nti)
    ti%nti = nti
  end subroutine

  !--------------------------------------------------------------------
  ! 潮位分布(1枚)を読み込む(titype=3。全ランク冗長読み・帯へ切り出し)
  subroutine set_timap
    if (len_trim(list%fn_timap) == 0) then
      call par_stop("list_tide: titype=3 requires fn_timap")
    end if
    allocate(ti%timap(1:g%nx, dcp%jsh:dcp%jeh))
    call read_map_band(p, g, trim(list%fn_timap), ti%timap)
  end subroutine

  !--------------------------------------------------------------------
  ! 分布ファイルリストを読み込む(titype=4。名前だけ保持し、フレームは
  ! apply が必要時に読む=リスタート時も現在時刻の2枚だけ読めばよい)
  subroutine set_maplist
    character(:), allocatable :: fname
    character(len=maxpathlen) :: mapname
    integer :: un, k, n, ios
    if (len_trim(list%fn_timaplist) == 0) then
      call par_stop("list_tide: titype=4 requires fn_timaplist")
    end if
    ti%dt_timap = list%dt_timaplist * 60             ! 分を秒に換算
    if (len_trim(list%dt_timaplist_c) > 0) then
      ti%dt_timap = str2sec(list%dt_timaplist_c, "list_tide: bad time format in dt_timaplist_c")
    end if
    if (ti%dt_timap <= 0.0) then
      call par_stop("list_tide: dt_timaplist must be a positive interval")
    end if

    fname = trim(p%dir_data)//"/"//trim(list%fn_timaplist)
    call par_info(" reading tide map list "//fname)
    open(newunit=un, file=fname, status='old', iostat=ios)
    if (ios /= 0) call par_stop("list_tide: cannot open fn_timaplist: "//fname)
    n = 0
    do
      read(un, *, iostat=ios)
      if (ios < 0) exit
      n = n + 1
    end do
    if (n <= 0) call par_stop("list_tide: fn_timaplist is empty: "//fname)
    allocate(ti%fn_map(1:n))
    rewind(un)
    do k = 1, n
      read(un, '(a)') mapname
      ti%fn_map(k) = adjustl(mapname)
    end do
    close(un)
    ti%nmap = n
    allocate(ti%timap0(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(ti%timap1(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  end subroutine

end subroutine


!----------------------------------------------------------------------
! 潮位の時間更新(run_main が毎ステップ呼ぶ。無効時は no-op)
!   更新は dt_tiupdate 間隔。位相は絶対ステップ番号 it 基準なので
!   再開後も中断なしランと同じステップで更新される(§7)
!----------------------------------------------------------------------
subroutine m_tide_calc(ti, p, g, s)
  type(t_tide), intent(inout) :: ti
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s

  if (ti%titype <= 0) return
  if (mod(s%it, ti%idt_tiupdate) /= 0) return
  call apply(ti, p, g, s, s%t)

end subroutine


!----------------------------------------------------------------------
! 潮位構造体を破棄
!----------------------------------------------------------------------
subroutine m_tide_dispose(ti)
  type(t_tide), intent(inout) :: ti
  if (allocated(ti%tival)) deallocate(ti%tival)
  if (allocated(ti%timap)) deallocate(ti%timap)
  if (allocated(ti%fn_map)) deallocate(ti%fn_map)
  if (allocated(ti%timap0)) deallocate(ti%timap0)
  if (allocated(ti%timap1)) deallocate(ti%timap1)
  ti%initialized = .false.
end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 時刻 t の潮位を自帯の海セルに適用する
!   s%tide = η(診断・出力用)、s%z = η − hsea0、s%h = hsea0。
!   s%e は complete が毎ステップ z + h から導出する
!----------------------------------------------------------------------
subroutine apply(ti, p, g, s, t)
  type(t_tide), intent(inout) :: ti
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: t
  real :: eta0, fac, frac
  integer :: i, j
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  ! 一様成分・倍率・補間係数を先に決める(タイプ別)
  eta0 = 0.0
  fac = 0.0
  frac = 0.0
  select case (ti%titype)
    case (1)
      eta0 = ti%ti0
    case (2)
      eta0 = interp_series(ti%tival, ti%nti, t)
    case (3)
      fac = interp_series(ti%tival, ti%nti, t)
    case (4)
      call locate_maps(ti, p, g, t, frac)
  end select

  !$omp parallel do schedule(dynamic) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) <= 0) cycle
      select case (ti%titype)
        case (3)
          s%tide(i,j) = ti%timap(i,j) * fac
        case (4)
          s%tide(i,j) = (1.0 - frac) * ti%timap0(i,j) + frac * ti%timap1(i,j)
        case default
          s%tide(i,j) = eta0
      end select
      s%z(i,j) = s%tide(i,j) - ti%hsea0
      s%h(i,j) = ti%hsea0
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! titype=4: 時刻 t を挟む2フレームをバッファに確保し、補間係数を返す
!   フレーム i の時刻は (i-1)*dt_timap。範囲外は端のフレームを保持
!   (frac=0)。読み込みは前進のみ(t は単調増加)で、後フレームを
!   前バッファへ移す move_alloc により各ファイルは高々1回しか読まない
!----------------------------------------------------------------------
subroutine locate_maps(ti, p, g, t, frac)
  type(t_tide), intent(inout) :: ti
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: t
  real, intent(out) :: frac
  real :: x
  integer :: i0, i1
  real, allocatable :: tmp(:,:)

  x = max(t, 0.0) / ti%dt_timap
  i0 = min(int(x) + 1, ti%nmap)
  i1 = min(i0 + 1, ti%nmap)
  frac = min(max(x - real(i0 - 1), 0.0), 1.0)
  if (i1 == i0) frac = 0.0

  if (ti%imap0 /= i0) then
    if (ti%imap1 == i0) then
      ! 後バッファを前バッファへ移す(再読み込みなし)
      call move_alloc(ti%timap0, tmp)
      call move_alloc(ti%timap1, ti%timap0)
      call move_alloc(tmp, ti%timap1)
      ti%imap0 = i0
      ti%imap1 = 0
    else
      call read_map_band(p, g, trim(ti%fn_map(i0)), ti%timap0)
      ti%imap0 = i0
    end if
  end if
  if (ti%imap1 /= i1) then
    if (i1 == i0) then
      ! 最終フレーム以降: 補間は timap0 のみ(frac=0)なので読まない
      ti%imap1 = 0
    else
      call read_map_band(p, g, trim(ti%fn_map(i1)), ti%timap1)
      ti%imap1 = i1
    end if
  end if

end subroutine


!----------------------------------------------------------------------
! 潮位分布ファイルを読み、自帯(+ハロ)へ切り出す(全ランク冗長読み。§11)
!----------------------------------------------------------------------
subroutine read_map_band(p, g, fname, band)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fname
  real, intent(inout) :: band(1:, dcp%jsh:)
  real, allocatable :: wk(:,:)
  character(:), allocatable :: path
  path = trim(p%dir_data)//"/"//trim(fname)
  call par_info(" reading tide map "//path)
  allocate(wk(1:g%nx, 1:g%ny))
  call fileio_read_matrix(path, g%nx, g%ny, wk, p%f_input_mode)
  band(:,:) = wk(1:g%nx, dcp%jsh:dcp%jeh)
end subroutine


!----------------------------------------------------------------------
! 時系列の線形補間(範囲外は端値を保持。m_precip の get_prval と同型)
!----------------------------------------------------------------------
function interp_series(val, n, t) result(res)
  real, intent(in) :: val(1:,1:)
  integer, intent(in) :: n
  real, intent(in) :: t
  real :: res
  real :: t0, t1
  integer :: k
  if (t <= val(1,1)) then
    res = val(2,1)
  else if (t > val(1,n)) then
    res = val(2,n)
  else
    res = val(2,n)
    do k = 2, n
      t1 = val(1,k)
      if (t < t1) then
        t0 = val(1,k-1)
        res = val(2,k-1) + (t - t0) / (t1 - t0) * (val(2,k) - val(2,k-1))
        exit
      end if
    end do
  end if
end function

end module
