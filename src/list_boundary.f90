module list_boundary
  ! 境界条件設定ファイル(fn_boundary)の読み込み専任(層契約 §12)。
  ! 族別の namelist グループを生の値のまま t_list_boundary に運ぶ。
  ! 解釈・検証・導出は m_boundary_init が行う。
  !   &list_bound_edge   : 外縁4辺の境界条件型
  !   &list_bound_source : 内部の湧き出し・吸い込み(複数)
  ! グループ不在は正常(その族なし。present_* が偽のまま)。
  ! 構文エラー(iostat>0)は par_stop。
  ! 旧形式の単一グループ &list_boundary は検出して par_stop で
  ! 書式移行を案内する(黙って無視しない)
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public :: t_list_boundary
  public :: list_boundary_read
  public :: nbsrcmax, nsrccmax, nsrcvmax

  integer, parameter :: maxpathlen = 256
  integer, parameter :: nbsrcmax = 50    ! 湧き出し・吸い込みの最大数
  integer, parameter :: nsrccmax = 999   ! 1ソースあたりの最大セル数
  integer, parameter :: nsrcvmax = 999   ! 1ソースあたりの時系列最大データ数

  ! 大配列(セル座標・時系列)は allocatable 成分とし、対応する
  ! グループが存在した場合のみ read_* が確保・充填する
  ! (固定長成分にすると t_list_boundary のローカル変数が数 MB になり、
  !  スタックあふれで segfault する。実際に踏んだ)
  type t_list_boundary
    ! ---- &list_bound_edge ----
    logical :: present_edge = .false.              ! グループが存在したか
    integer :: f_bc_w = 0                          ! 西辺 (i=1)  0:不透過 1:自由流出 2:放射
    integer :: f_bc_e = 0                          ! 東辺 (i=nx)
    integer :: f_bc_n = 0                          ! 北辺 (j=1: ラスタ上端)
    integer :: f_bc_s = 0                          ! 南辺 (j=ny)
    real :: bc_eta_w = -9999.0                     ! 放射境界の基準水位 (m)。
    real :: bc_eta_e = -9999.0                     !   -9999(未指定)なら初期条件
    real :: bc_eta_n = -9999.0                     !   から自動導出(m_boundary_
    real :: bc_eta_s = -9999.0                     !   set_etaref)
    ! ---- &list_bound_source ----
    logical :: present_source = .false.            ! グループが存在したか
    integer, allocatable :: src_cell(:,:,:)        ! セル座標 (i, j)
    real, allocatable :: src_val(:,:,:)            ! 時系列 (min, m3/s)
    character(len=maxpathlen) :: fn_src_cell(1:nbsrcmax) = ""  ! セル一覧ファイル名
    character(len=maxpathlen) :: fn_src_val(1:nbsrcmax) = ""   ! 時系列ファイル名
    ! ---- &list_bound_stage ----
    logical :: present_stage = .false.             ! グループが存在したか
    integer, allocatable :: stage_cell(:,:,:)      ! セル座標 (i, j)
    real :: stage_eta(1:nbsrcmax) = -9999          ! 規定水位の固定値 (m)
    real, allocatable :: stage_val(:,:,:)          ! 時系列 (min, m)
    character(len=maxpathlen) :: fn_stage_cell(1:nbsrcmax) = ""  ! セル一覧ファイル名
    character(len=maxpathlen) :: fn_stage_val(1:nbsrcmax) = ""   ! 時系列ファイル名
    ! ---- &list_bound_inflow ----
    logical :: present_inflow = .false.            ! グループが存在したか
    integer, allocatable :: inflow_cell(:,:,:)     ! セル座標 (i, j)
    real, allocatable :: inflow_val(:,:,:)         ! 時系列 (min, m3/s)
    integer :: inflow_dist(1:nbsrcmax) = 0         ! 配分モード(0:均等 1:水深 2:通水能)
    character(len=maxpathlen) :: fn_inflow_cell(1:nbsrcmax) = ""  ! セル一覧ファイル名
    character(len=maxpathlen) :: fn_inflow_val(1:nbsrcmax) = ""   ! 時系列ファイル名
  end type

  ! namelist 読み込み用の静的作業配列(スタックに置かないための措置。
  ! 読み込み時のみ使用し、値は read_* が毎回既定値で初期化する)
  integer :: src_cell(1:2,1:nsrccmax,1:nbsrcmax)
  real :: src_val(1:2,1:nsrcvmax,1:nbsrcmax)
  integer :: stage_cell(1:2,1:nsrccmax,1:nbsrcmax)
  real :: stage_val(1:2,1:nsrcvmax,1:nbsrcmax)
  integer :: inflow_cell(1:2,1:nsrccmax,1:nbsrcmax)
  real :: inflow_val(1:2,1:nsrcvmax,1:nbsrcmax)

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 境界条件設定ファイルの全グループを読み込む
!----------------------------------------------------------------------
subroutine list_boundary_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_boundary), intent(inout) :: list
  integer :: un
  integer :: ios

  call par_info("reading boundary lists in "//trim(p%fn_boundary))
  call check_old_format(p)

  open(newunit=un, file=trim(p%fn_boundary), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: "//trim(p%fn_boundary))
  call read_edge(un, list)
  call read_source(un, list)
  call read_stage(un, list)
  call read_inflow(un, list)
  close(un)

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! &list_bound_edge を読む(不在なら present_edge を偽のまま返す)
!----------------------------------------------------------------------
subroutine read_edge(un, list)
  integer, intent(in) :: un
  type(t_list_boundary), intent(inout) :: list
  integer :: f_bc_w, f_bc_e, f_bc_n, f_bc_s
  real :: bc_eta_w, bc_eta_e, bc_eta_n, bc_eta_s
  integer :: ios
  character(len=1024) :: iom
  namelist /list_bound_edge/ f_bc_w, f_bc_e, f_bc_n, f_bc_s, &
                             bc_eta_w, bc_eta_e, bc_eta_n, bc_eta_s

  f_bc_w = list%f_bc_w
  f_bc_e = list%f_bc_e
  f_bc_n = list%f_bc_n
  f_bc_s = list%f_bc_s
  bc_eta_w = list%bc_eta_w
  bc_eta_e = list%bc_eta_e
  bc_eta_n = list%bc_eta_n
  bc_eta_s = list%bc_eta_s

  rewind(un)
  read(un, nml=list_bound_edge, iostat=ios, iomsg=iom)
  if (ios > 0) call par_stop("list_bound_edge 読込失敗: "//trim(iom))
  if (ios < 0) return              ! グループ不在(この族なし)
  list%present_edge = .true.

  list%f_bc_w = f_bc_w
  list%f_bc_e = f_bc_e
  list%f_bc_n = f_bc_n
  list%f_bc_s = f_bc_s
  list%bc_eta_w = bc_eta_w
  list%bc_eta_e = bc_eta_e
  list%bc_eta_n = bc_eta_n
  list%bc_eta_s = bc_eta_s

end subroutine


!----------------------------------------------------------------------
! &list_bound_source を読む(不在なら present_source を偽のまま返す)
!----------------------------------------------------------------------
subroutine read_source(un, list)
  integer, intent(in) :: un
  type(t_list_boundary), intent(inout) :: list
  character(len=maxpathlen) :: fn_src_cell(1:nbsrcmax)
  character(len=maxpathlen) :: fn_src_val(1:nbsrcmax)
  integer :: ios
  character(len=1024) :: iom
  namelist /list_bound_source/ src_cell, src_val, fn_src_cell, fn_src_val

  src_cell = -9999
  src_val = -9999
  fn_src_cell = list%fn_src_cell
  fn_src_val = list%fn_src_val

  rewind(un)
  read(un, nml=list_bound_source, iostat=ios, iomsg=iom)
  if (ios > 0) call par_stop("list_bound_source 読込失敗: "//trim(iom))
  if (ios < 0) return              ! グループ不在(この族なし)
  list%present_source = .true.

  list%src_cell = src_cell
  list%src_val = src_val
  list%fn_src_cell = fn_src_cell
  list%fn_src_val = fn_src_val

end subroutine


!----------------------------------------------------------------------
! &list_bound_stage を読む(不在なら present_stage を偽のまま返す)
!----------------------------------------------------------------------
subroutine read_stage(un, list)
  integer, intent(in) :: un
  type(t_list_boundary), intent(inout) :: list
  real :: stage_eta(1:nbsrcmax)
  character(len=maxpathlen) :: fn_stage_cell(1:nbsrcmax)
  character(len=maxpathlen) :: fn_stage_val(1:nbsrcmax)
  integer :: ios
  character(len=1024) :: iom
  namelist /list_bound_stage/ stage_cell, stage_eta, stage_val, &
                              fn_stage_cell, fn_stage_val

  stage_cell = -9999
  stage_eta = list%stage_eta
  stage_val = -9999
  fn_stage_cell = list%fn_stage_cell
  fn_stage_val = list%fn_stage_val

  rewind(un)
  read(un, nml=list_bound_stage, iostat=ios, iomsg=iom)
  if (ios > 0) call par_stop("list_bound_stage 読込失敗: "//trim(iom))
  if (ios < 0) return              ! グループ不在(この族なし)
  list%present_stage = .true.

  list%stage_cell = stage_cell
  list%stage_eta = stage_eta
  list%stage_val = stage_val
  list%fn_stage_cell = fn_stage_cell
  list%fn_stage_val = fn_stage_val

end subroutine


!----------------------------------------------------------------------
! &list_bound_inflow を読む(不在なら present_inflow を偽のまま返す)
!----------------------------------------------------------------------
subroutine read_inflow(un, list)
  integer, intent(in) :: un
  type(t_list_boundary), intent(inout) :: list
  integer :: inflow_dist(1:nbsrcmax)
  character(len=maxpathlen) :: fn_inflow_cell(1:nbsrcmax)
  character(len=maxpathlen) :: fn_inflow_val(1:nbsrcmax)
  integer :: ios
  character(len=1024) :: iom
  namelist /list_bound_inflow/ inflow_cell, inflow_val, inflow_dist, &
                               fn_inflow_cell, fn_inflow_val

  inflow_cell = -9999
  inflow_val = -9999
  inflow_dist = list%inflow_dist
  fn_inflow_cell = list%fn_inflow_cell
  fn_inflow_val = list%fn_inflow_val

  rewind(un)
  read(un, nml=list_bound_inflow, iostat=ios, iomsg=iom)
  if (ios > 0) call par_stop("list_bound_inflow 読込失敗: "//trim(iom))
  if (ios < 0) return              ! グループ不在(この族なし)
  list%present_inflow = .true.

  list%inflow_cell = inflow_cell
  list%inflow_val = inflow_val
  list%inflow_dist = inflow_dist
  list%fn_inflow_cell = fn_inflow_cell
  list%fn_inflow_val = fn_inflow_val

end subroutine


!----------------------------------------------------------------------
! 旧形式(単一グループ &list_boundary)の検出。
! namelist の探索は「不在」と区別できないため、行頭トークンの
! 文字列比較で行う(大文字小文字は同一視)
!----------------------------------------------------------------------
subroutine check_old_format(p)
  type(t_sysparam), intent(in) :: p
  integer :: un, ios
  character(len=1024) :: line
  character(len=14) :: tok
  character(len=1) :: c

  open(newunit=un, file=trim(p%fn_boundary), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: "//trim(p%fn_boundary))
  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    line = adjustl(line)
    if (len_trim(line) < 14) cycle
    tok = to_lower(line(1:14))
    if (tok /= "&list_boundary") cycle
    c = line(15:15)                ! 次の文字が名前文字なら別グループ
    if (is_name_char(c)) cycle
    close(un)
    call par_stop("list_boundary: 旧形式の &list_boundary グループを検出しました。" &
                  //"&list_bound_edge / &list_bound_source の新形式へ移行してください" &
                  //"(examples/List_samples/list_boundary.txt 参照): "//trim(p%fn_boundary))
  end do
  close(un)

end subroutine


!----------------------------------------------------------------------
! 英大文字を小文字化した文字列を返す
!----------------------------------------------------------------------
function to_lower(str) result(low)
  character(len=*), intent(in) :: str
  character(len=len(str)) :: low
  integer :: i, ic
  low = str
  do i = 1, len(str)
    ic = iachar(str(i:i))
    if (ic >= iachar('A') .and. ic <= iachar('Z')) low(i:i) = achar(ic + 32)
  end do
end function


!----------------------------------------------------------------------
! namelist グループ名に使える文字(英数字・アンダースコア)か
!----------------------------------------------------------------------
function is_name_char(c) result(yes)
  character(len=1), intent(in) :: c
  logical :: yes
  yes = (c >= 'a' .and. c <= 'z') .or. (c >= 'A' .and. c <= 'Z') &
        .or. (c >= '0' .and. c <= '9') .or. c == '_'
end function

end module
