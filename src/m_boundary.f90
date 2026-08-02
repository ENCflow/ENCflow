module m_boundary
  ! 境界条件のデータ供給層(スキーム非依存。docs/boundary_plan.md)。
  !   - 辺境界(edge): 計算領域外縁4辺の境界条件型(不透過/自由流出/長波放射)。
  !     適用(離散化)は m_swflow_XX 側(ENC は boundary_uvmn)。
  !     方角と添字の正本: 西= i=1、東= i=nx、北= j=1(ラスタ上端)、
  !     南= j=ny(m_georef の北西隅原点・行順に一致)
  !   - 内部ソース(source): 湧き出し・吸い込み(複数。セル集合+
  !     流量時系列 Q(t)、負値=吸い込み)。makebdc が現時刻の
  !     セルあたり水深増分 q を毎ステップ用意し、適用は
  !     m_swflow_enc の boundary_h。
  ! 将来の族(辺上区間の流入・流出境界)も本モジュールへ足し、
  ! 肥大したら族別モジュールに分割する(boundary_plan.md §4.1)
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_parallel, only : par_stop, dcp
  use m_util, only : itoa
  use list_boundary, only : t_list_boundary, list_boundary_read, &
                            nbsrcmax, nsrccmax, nsrcvmax
  implicit none
  private

  public :: t_boundary
  public :: m_boundary_init
  public :: m_boundary_set_etaref
  public :: m_boundary_dispose
  public :: m_boundary_makebdc
  public :: e_bc_wall, e_bc_outflow, e_bc_radiation
  public :: e_side_w, e_side_e, e_side_n, e_side_s

  ! 辺境界の型コード
  integer, parameter :: e_bc_wall = 0      ! 不透過(既定)
  integer, parameter :: e_bc_outflow = 1   ! 自由流出(洪水向け: 通過流+段落ち)
  integer, parameter :: e_bc_radiation = 2 ! 長波放射(津波向け: 水位偏差を透過)

  ! 辺番号(btype の添字)
  integer, parameter :: e_side_w = 1       ! 西 (i=1)
  integer, parameter :: e_side_e = 2       ! 東 (i=nx)
  integer, parameter :: e_side_n = 3       ! 北 (j=1: ラスタ上端)
  integer, parameter :: e_side_s = 4       ! 南 (j=ny)

  ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
  type t_bound_edge
    integer :: btype(1:4) = e_bc_wall      ! 4辺の境界条件型 (W, E, N, S)
    real :: eta_man(1:4) = -9999.0         ! 基準水位の明示指定値 (-9999=未指定)
    real, allocatable :: eta_cell(:,:)     ! 確定した基準水位(セル別。
                                           !   (j,W/E)・(i,N/S)。set_etaref が構築)
  end type

  type t_bound_src                         ! 湧き出し・吸い込み1個
    integer :: ncell = 0                   ! セル数
    integer, allocatable :: cell(:,:)      ! セル座標 (1:2, 1:ncell)
    integer :: nval = 0                    ! 時系列データ数
    real, allocatable :: val(:,:)          ! 時系列 (1:2, 1:nval) (s, m3/s)
    real :: q = 0.0                        ! 現時刻のセルあたり水深増分 (m)
  end type

  type t_boundary
    type(t_bound_edge) :: edge             ! 辺境界
    integer :: nsrc = 0                    ! ソース数
    type(t_bound_src), allocatable :: src(:)  ! 湧き出し・吸い込み
    logical :: initialized = .false.
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 境界条件の読み込み・検証・位置解決(初期化ゾーン2: 全域マスク前提)
!----------------------------------------------------------------------
subroutine m_boundary_init(b, p, g)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_boundary) :: list

  b%initialized = .true.

  !--- 境界条件パラメータ自体が設定されていない場合(全て既定のまま) ---
  if (len_trim(p%fn_boundary) <= 0) return

  !--- 境界条件パラメータファイルを読み込む ---
  call list_boundary_read(p, list)

  !--- 辺境界 ---
  call init_edge(b, list)

  !--- 内部ソース(湧き出し・吸い込み) ---
  call init_source(b, p, g, list)

end subroutine


!----------------------------------------------------------------------
! 現時刻の境界条件値を用意する(毎ステップ、swflow より前に呼ぶ)
!----------------------------------------------------------------------
subroutine m_boundary_makebdc(b, p, g, s)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: isrc
  real :: q

  !--- ソースが無い場合は何もしない ---
  if (b%nsrc <= 0) return

  !--- 各ソースの現時刻の流量をセル1個・1ステップあたりの水深増分に換算 ---
  do isrc = 1, b%nsrc
    q = interp_series(b%src(isrc)%val, b%src(isrc)%nval, s%t)
    b%src(isrc)%q = q / (b%src(isrc)%ncell * g%dx * g%dy) * p%dt
  end do

end subroutine


!----------------------------------------------------------------------
! 放射境界の基準水位を確定する(m_state_init の直後に呼ぶ)
!   優先順位:
!     (1) bc_eta_* の明示指定(一様値)
!     (2) 初期条件が水位固定(f_htype=2)なら一様 e0(乾いた境界セルも
!         海面基準で排水される)
!     (3) それ以外は境界セルの初期水位 s%e(セルごと)
!   (3) は初期条件と厳密に整合し、t=0 の放射フラックスが全境界セルで
!   厳密にゼロになる。restore 時は復元状態から再導出する(「保存状態を
!   初期条件に使う」restore の意味論と整合。復元時に波が境界を通過中だと
!   基準がずれる点は既知の制約)。
!   MPI: 各ランクは自分が参照しうる行(帯+ハロ)だけを埋める。共有行は
!   隣接ランクが同じ s%e(帯切り出しで同値)から冗長に導出する(通信不要)
!----------------------------------------------------------------------
subroutine m_boundary_set_etaref(b, p, g, s)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: sd, i, j
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  if (.not. any(b%edge%btype == e_bc_radiation)) return
  allocate(b%edge%eta_cell(1:max(g%nx, g%ny), 1:4), source = 0.0)

  do sd = 1, 4
    if (b%edge%btype(sd) /= e_bc_radiation) cycle
    if (b%edge%eta_man(sd) > -9998.0) then
      b%edge%eta_cell(:,sd) = b%edge%eta_man(sd)       ! 明示指定(一様)
    else if (s%ini%f_htype == 2) then
      b%edge%eta_cell(:,sd) = s%ini%e0                 ! 水位固定の初期条件と同値
    else
      ! 境界セルの初期水位から導出
      select case (sd)
        case (e_side_w)
          do j = dcp%jsh, dcp%jeh
            b%edge%eta_cell(j,sd) = s%e(1,j)
          end do
        case (e_side_e)
          do j = dcp%jsh, dcp%jeh
            b%edge%eta_cell(j,sd) = s%e(g%nx,j)
          end do
        case (e_side_n)
          if (dcp%jsh <= 1 .and. 1 <= dcp%jeh) then
            do i = 1, g%nx
              b%edge%eta_cell(i,sd) = s%e(i,1)
            end do
          end if
        case (e_side_s)
          if (dcp%jsh <= g%ny .and. g%ny <= dcp%jeh) then
            do i = 1, g%nx
              b%edge%eta_cell(i,sd) = s%e(i,g%ny)
            end do
          end if
      end select
    end if
  end do

end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_boundary_dispose(b)
  type(t_boundary), intent(inout) :: b
  if (allocated(b%src)) deallocate(b%src)
  if (allocated(b%edge%eta_cell)) deallocate(b%edge%eta_cell)
  b%nsrc = 0
  b%initialized = .false.
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 辺境界の解釈と検証
!----------------------------------------------------------------------
subroutine init_edge(b, list)
  type(t_boundary), intent(inout) :: b
  type(t_list_boundary), intent(in) :: list
  character(len=1), parameter :: side_name(1:4) = ['w', 'e', 'n', 's']
  integer :: bt(1:4)
  integer :: sd

  if (.not. list%present_edge) return

  bt(e_side_w) = list%f_bc_w
  bt(e_side_e) = list%f_bc_e
  bt(e_side_n) = list%f_bc_n
  bt(e_side_s) = list%f_bc_s
  do sd = 1, 4
    if (bt(sd) < e_bc_wall .or. bt(sd) > e_bc_radiation) then
      call par_stop("list_bound_edge: f_bc_"//side_name(sd) &
                    //" は 0(不透過)・1(自由流出)・2(放射) を指定してください: "//itoa(bt(sd)))
    end if
  end do
  b%edge%btype = bt
  b%edge%eta_man(e_side_w) = list%bc_eta_w
  b%edge%eta_man(e_side_e) = list%bc_eta_e
  b%edge%eta_man(e_side_n) = list%bc_eta_n
  b%edge%eta_man(e_side_s) = list%bc_eta_s

end subroutine


!----------------------------------------------------------------------
! 内部ソースの解釈・検証・格納
!   セル集合と時系列は namelist 配列(番兵 -9999 で終端)または
!   ファイル指定。位置の検証は全域マスク(ゾーン2)で全ランク冗長に行う
!----------------------------------------------------------------------
subroutine init_source(b, p, g, list)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_boundary), intent(in) :: list
  logical :: active(1:nbsrcmax)
  integer :: isrc, n, k, i, j

  if (.not. list%present_source) return

  !--- 有効なソース(セルか時系列かファイル指定がある)を数える ---
  do isrc = 1, nbsrcmax
    active(isrc) = (list%src_cell(1,1,isrc) > -9999) &
                   .or. (list%src_val(1,1,isrc) > -9999) &
                   .or. (len_trim(list%fn_src_cell(isrc)) > 0) &
                   .or. (len_trim(list%fn_src_val(isrc)) > 0)
  end do
  b%nsrc = count(active)
  if (b%nsrc <= 0) return
  if (.not. all(active(1:b%nsrc))) then
    call par_stop("list_bound_source: ソース番号は 1 から連続で指定してください")
  end if

  allocate(b%src(1:b%nsrc))

  do isrc = 1, b%nsrc

    !--- セル集合(ファイル指定が優先) ---
    if (len_trim(list%fn_src_cell(isrc)) > 0) then
      call read_cell_file(trim(p%dir_data)//"/"//trim(list%fn_src_cell(isrc)), b%src(isrc))
    else
      n = 0
      do k = 1, nsrccmax
        if (list%src_cell(1,k,isrc) <= -9999) exit   ! 番兵で終端
        n = n + 1
      end do
      allocate(b%src(isrc)%cell(1:2,1:max(n,1)))
      b%src(isrc)%cell(1:2,1:n) = list%src_cell(1:2,1:n,isrc)
      b%src(isrc)%ncell = n
    end if

    !--- 流量時系列(ファイル指定が優先。namelist の時刻は分→秒に換算) ---
    if (len_trim(list%fn_src_val(isrc)) > 0) then
      call read_val_file(trim(p%dir_data)//"/"//trim(list%fn_src_val(isrc)), b%src(isrc))
    else
      n = 0
      do k = 1, nsrcvmax
        if (list%src_val(1,k,isrc) <= -9999) exit    ! 番兵で終端
        n = n + 1
      end do
      allocate(b%src(isrc)%val(1:2,1:max(n,1)))
      b%src(isrc)%val(1,1:n) = list%src_val(1,1:n,isrc) * 60   ! 分を秒に換算
      b%src(isrc)%val(2,1:n) = list%src_val(2,1:n,isrc)
      b%src(isrc)%nval = n
    end if

    !--- 検証 ---
    if (b%src(isrc)%ncell <= 0) then
      call par_stop("list_bound_source: ソース "//itoa(isrc)//" にセルがありません")
    end if
    if (b%src(isrc)%nval <= 0) then
      call par_stop("list_bound_source: ソース "//itoa(isrc)//" に時系列がありません")
    end if
    do k = 1, b%src(isrc)%ncell
      i = b%src(isrc)%cell(1,k)
      j = b%src(isrc)%cell(2,k)
      if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
        call par_stop("list_bound_source: ソース "//itoa(isrc)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が領域外です")
      end if
      if (g%x(i,j) <= 0) then
        call par_stop("list_bound_source: ソース "//itoa(isrc)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が無効セル(x=0)です")
      end if
    end do

  end do

end subroutine


!----------------------------------------------------------------------
! セル一覧ファイルを読む(各行 "i j")
!----------------------------------------------------------------------
subroutine read_cell_file(fname, src)
  character(len=*), intent(in) :: fname
  type(t_bound_src), intent(inout) :: src
  integer :: un, n, k, ios

  open(newunit=un, file=fname, status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: "//fname)
  n = 0
  do
    read(un, *, iostat=ios)
    if (ios < 0) exit
    n = n + 1
  end do
  rewind(un)
  allocate(src%cell(1:2,1:max(n,1)))
  do k = 1, n
    read(un, *) src%cell(1,k), src%cell(2,k)
  end do
  close(un)
  src%ncell = n

end subroutine


!----------------------------------------------------------------------
! 流量時系列ファイルを読む(各行 "時刻(min) 流量(m3/s)"。時刻は秒に換算)
!----------------------------------------------------------------------
subroutine read_val_file(fname, src)
  character(len=*), intent(in) :: fname
  type(t_bound_src), intent(inout) :: src
  integer :: un, n, k, ios
  real :: t, val

  open(newunit=un, file=fname, status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: "//fname)
  n = 0
  do
    read(un, *, iostat=ios)
    if (ios < 0) exit
    n = n + 1
  end do
  rewind(un)
  allocate(src%val(1:2,1:max(n,1)))
  do k = 1, n
    read(un, *) t, val
    src%val(1,k) = t * 60
    src%val(2,k) = val
  end do
  close(un)
  src%nval = n

end subroutine


!----------------------------------------------------------------------
! 時系列 val(1,:)=時刻(s), val(2,:)=値 を時刻 t で線形補間する
! (範囲外は端の値を保持)
!----------------------------------------------------------------------
function interp_series(val, n, t) result(q)
  real, intent(in) :: val(:,:)
  integer, intent(in) :: n
  real, intent(in) :: t
  real :: q
  real :: t0, t1, q0, q1
  integer :: k

  if (t <= val(1,1)) then             ! 最初の時刻よりも前の場合
    q = val(2,1)
  else if (t > val(1,n)) then         ! 最後の時刻より後の場合
    q = val(2,n)
  else
    q = val(2,n)
    do k = 2, n
      t1 = val(1,k)
      if (t < t1) then
        t0 = val(1,k-1)
        q0 = val(2,k-1)
        q1 = val(2,k)
        q = q0 + (t - t0) / (t1 - t0) * (q1 - q0)
        exit
      end if
    end do
  end if

end function

end module
