module list_structure
  ! 内部水理構造物設定ファイル(fn_structure)の読み込み専任(層契約 §12)。
  ! 型別の namelist グループを生の値のまま t_list_structure に運ぶ。
  ! 解釈・検証・導出は m_boundary の init_structure
  ! (submodule m_boundary_structure)が行う。
  !   &list_struct_pump    : 排水ポンプ(旧 &list_bound_pump を fn_boundary
  !                          から移設。2026-08-07)
  ! グループ不在は正常(その型なし。present_* が偽のまま)。
  ! 構文エラー(iostat>0)は par_stop。
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public :: t_list_structure
  public :: list_structure_read
  public :: nstmax, nstccmax, nstvmax

  integer, parameter :: maxpathlen = 256
  integer, parameter :: nstmax = 50      ! 構造物の型別最大数
  integer, parameter :: nstccmax = 999   ! 1構造物あたりの最大セル数
  integer, parameter :: nstvmax = 999    ! 1構造物あたりのルール折れ線最大点数

  ! 大配列(セル座標・折れ線)は allocatable 成分とし、対応する
  ! グループが存在した場合のみ read_* が確保・充填する
  ! (固定長成分にするとローカル変数がスタックあふれする。list_boundary と同じ)
  type t_list_structure
    ! ---- &list_struct_pump ----
    logical :: present_pump = .false.              ! グループが存在したか
    integer, allocatable :: pump_in_cell(:,:,:)    ! 取水セル座標 (i, j)
    integer, allocatable :: pump_out_cell(:,:,:)   ! 吐口セル座標 (i, j)。未指定=域外排水
    real :: pump_q0(1:nstmax) = -9999.0            ! 一定流量 (m3/s。pump_rule と排他)
    integer :: f_pump_ref(1:nstmax) = 0            ! 運転基準 (0:水位η=z+h, 1:水深h)
    real, allocatable :: pump_rule(:,:,:)          ! 運転ルール折れ線 (基準値 m, 流量 m3/s)
    character(len=maxpathlen) :: fn_pump_in_cell(1:nstmax) = ""   ! 取水セル一覧ファイル名
    character(len=maxpathlen) :: fn_pump_out_cell(1:nstmax) = ""  ! 吐口セル一覧ファイル名
  end type

  ! namelist 読み込み用の静的作業配列(スタックに置かないための措置。
  ! 読み込み時のみ使用し、値は read_* が毎回既定値で初期化する)
  integer :: pump_in_cell(1:2,1:nstccmax,1:nstmax)
  integer :: pump_out_cell(1:2,1:nstccmax,1:nstmax)
  real :: pump_rule(1:2,1:nstvmax,1:nstmax)

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 内部水理構造物設定ファイルの全グループを読み込む
!----------------------------------------------------------------------
subroutine list_structure_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_structure), intent(inout) :: list
  integer :: un
  integer :: ios

  call par_info("reading structure lists in "//trim(p%fn_structure))

  open(newunit=un, file=trim(p%fn_structure), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: "//trim(p%fn_structure))
  call read_pump(un, list)
  close(un)

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! &list_struct_pump を読む(不在なら present_pump を偽のまま返す)
!   解釈・検証(セル・ルールの妥当性)は init_structure が行う
!----------------------------------------------------------------------
subroutine read_pump(un, list)
  integer, intent(in) :: un
  type(t_list_structure), intent(inout) :: list
  real :: pump_q0(1:nstmax)
  integer :: f_pump_ref(1:nstmax)
  character(len=maxpathlen) :: fn_pump_in_cell(1:nstmax)
  character(len=maxpathlen) :: fn_pump_out_cell(1:nstmax)
  integer :: ios
  character(len=1024) :: iom
  namelist /list_struct_pump/ pump_in_cell, pump_out_cell, pump_q0, f_pump_ref, &
                              pump_rule, fn_pump_in_cell, fn_pump_out_cell

  pump_in_cell = -9999
  pump_out_cell = -9999
  pump_rule = -9999
  pump_q0 = list%pump_q0
  f_pump_ref = list%f_pump_ref
  fn_pump_in_cell = list%fn_pump_in_cell
  fn_pump_out_cell = list%fn_pump_out_cell

  rewind(un)
  read(un, nml=list_struct_pump, iostat=ios, iomsg=iom)
  if (ios > 0) call par_stop("list_struct_pump 読込失敗: "//trim(iom))
  if (ios < 0) return              ! グループ不在(この型なし)
  list%present_pump = .true.

  list%pump_in_cell = pump_in_cell
  list%pump_out_cell = pump_out_cell
  list%pump_rule = pump_rule
  list%pump_q0 = pump_q0
  list%f_pump_ref = f_pump_ref
  list%fn_pump_in_cell = fn_pump_in_cell
  list%fn_pump_out_cell = fn_pump_out_cell

end subroutine

end module
