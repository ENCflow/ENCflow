module list_structure
  ! 内部水理構造物設定ファイル(fn_structure)の読み込み専任(層契約 §12)。
  ! 型別の namelist グループを生の値のまま t_list_structure に運ぶ。
  ! 解釈・検証・導出は m_boundary の init_structure
  ! (submodule m_boundary_structure)が行う。
  !   &list_struct_pump    : 排水ポンプ(旧 &list_bound_pump を fn_boundary
  !                          から移設。2026-08-07)
  !   &list_struct_culvert : カルバート(矩形断面・双方向。樋管・樋門は
  !                          ゲート拡張で表す。2026-08-07)
  !   &list_struct_diversion : 分水(取水堰の rating による受動的な
  !                          一方向取水。流域外分水が主用途。2026-08-08)
  !   &list_struct_dam     : ダム(捕捉帯吸収+hrs バケツ貯留+運転
  !                          ルール放流。2026-08-08)
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
    ! ---- &list_struct_culvert ----
    logical :: present_culvert = .false.           ! グループが存在したか
    integer, allocatable :: culv_in_cell(:,:,:)    ! 上流側セル座標 (i, j)
    integer, allocatable :: culv_out_cell(:,:,:)   ! 下流側セル座標 (i, j。必須)
    real :: culv_width(1:nstmax) = -9999.0         ! 断面幅 B (m)
    real :: culv_height(1:nstmax) = -9999.0        ! 断面高 D (m)
    real :: culv_zin(1:nstmax) = -9999.0           ! 上流側敷高 (m)
    real :: culv_zout(1:nstmax) = -9999.0          ! 下流側敷高 (m)
    real :: culv_length(1:nstmax) = 0.0            ! 管路長 L (m。0=摩擦損失なし)
    real :: culv_manning(1:nstmax) = 0.02          ! 管内粗度 n
    real :: culv_ce(1:nstmax) = 0.5                ! 流入損失係数
    integer :: culv_flap(1:nstmax) = 0             ! フラップゲート (0:なし, 1:逆流遮断)
    real, allocatable :: culv_gate_rule(:,:,:)     ! ゲート開度折れ線 (基準水位η m, 開度0-1)。
                                                   !   未指定=常時全開(樋門の operated gate)
    integer :: culv_gate_ref(1:nstmax) = 1         ! 開度ルールの基準セル
                                                   !   (0:in側代表, 1:out側代表=河川側)
    character(len=maxpathlen) :: fn_culv_in_cell(1:nstmax) = ""   ! 上流側セル一覧ファイル名
    character(len=maxpathlen) :: fn_culv_out_cell(1:nstmax) = ""  ! 下流側セル一覧ファイル名
    ! ---- &list_struct_diversion ----
    logical :: present_diversion = .false.         ! グループが存在したか
    integer, allocatable :: div_in_cell(:,:,:)     ! 取水セル座標 (i, j)
    integer, allocatable :: div_out_cell(:,:,:)    ! 送水先セル座標 (i, j)。未指定=域外分水
    real :: div_q0(1:nstmax) = -9999.0             ! 一定流量 (m3/s。div_rule と排他)
    real, allocatable :: div_rule(:,:,:)           ! 取水 rating 折れ線 (取水代表セルの
                                                   !   水位η m, 流量 m3/s)
    character(len=maxpathlen) :: fn_div_in_cell(1:nstmax) = ""    ! 取水セル一覧ファイル名
    character(len=maxpathlen) :: fn_div_out_cell(1:nstmax) = ""   ! 送水先セル一覧ファイル名
    ! ---- &list_struct_dam ----
    logical :: present_dam = .false.               ! グループが存在したか
    integer, allocatable :: dam_in_cell(:,:,:)     ! 貯水池セル群=捕捉帯 (i, j)
    integer, allocatable :: dam_out_cell(:,:,:)    ! 放流セル群 (i, j。必須)
    real, allocatable :: dam_hv(:,:,:)             ! HV 曲線 (水位 m, 貯水量 m3)。
                                                   !   最低2点(最低水位・サーチャージ)
    integer :: f_dam_mode(1:nstmax) = 0            ! 運転モード (1:一定量, 2:一定率カット,
                                                   !   3:自然調節)
    real :: dam_q0(1:nstmax) = -9999.0             ! モード1: 一定放流量 (m3/s)
    real :: dam_rate(1:nstmax) = -9999.0           ! モード2: 放流率 r (0-1)
    real, allocatable :: dam_hq_rule(:,:,:)        ! モード3(a): H-Q 折れ線 (水位 m, m3/s)
    real :: dam_ori_width(1:nstmax) = -9999.0      ! モード3(b): オリフィス幅 B (m)
    real :: dam_ori_height(1:nstmax) = -9999.0     ! モード3(b): オリフィス高 D (m)
    real :: dam_ori_zbase(1:nstmax) = -9999.0      ! モード3(b): オリフィス敷高 (m)
    real :: dam_ori_ce(1:nstmax) = -9999.0         ! モード3(b): 流入損失係数 (省略時 0.5)
    real :: dam_qmax(1:nstmax) = -9999.0           ! モード3(c): 計画最大放流量 (m3/s。
                                                   !   サーチャージ時。√則で自動構成)
    real :: dam_zbase(1:nstmax) = -9999.0          ! モード3(c): √則の敷高 (m。省略時=最低水位)
    real :: dam_tadashigaki(1:nstmax) = -9999.0    ! 但し書き開始水位 (m。モード1,2。
                                                   !   省略時=最低+0.9×(サーチャージ−最低))
    real :: dam_h_init(1:nstmax) = -9999.0         ! 初期水位 (m。省略時=最低水位=空虚)
    real :: dam_area(1:nstmax) = -9999.0           ! 湛水面積 (m2。蒸発散用オプション。
                                                   !   指定時は貯水面からの蒸発をこの面積で
                                                   !   評価し、捕捉帯セルの個別蒸発は止める。§27)
    character(len=maxpathlen) :: fn_dam_in_cell(1:nstmax) = ""    ! 捕捉帯セル一覧ファイル名
    character(len=maxpathlen) :: fn_dam_out_cell(1:nstmax) = ""   ! 放流セル一覧ファイル名
  end type

  ! namelist 読み込み用の静的作業配列(スタックに置かないための措置。
  ! 読み込み時のみ使用し、値は read_* が毎回既定値で初期化する)
  integer :: pump_in_cell(1:2,1:nstccmax,1:nstmax)
  integer :: pump_out_cell(1:2,1:nstccmax,1:nstmax)
  real :: pump_rule(1:2,1:nstvmax,1:nstmax)
  integer :: culv_in_cell(1:2,1:nstccmax,1:nstmax)
  integer :: culv_out_cell(1:2,1:nstccmax,1:nstmax)
  real :: culv_gate_rule(1:2,1:nstvmax,1:nstmax)
  integer :: div_in_cell(1:2,1:nstccmax,1:nstmax)
  integer :: div_out_cell(1:2,1:nstccmax,1:nstmax)
  real :: div_rule(1:2,1:nstvmax,1:nstmax)
  integer :: dam_in_cell(1:2,1:nstccmax,1:nstmax)
  integer :: dam_out_cell(1:2,1:nstccmax,1:nstmax)
  real :: dam_hv(1:2,1:nstvmax,1:nstmax)
  real :: dam_hq_rule(1:2,1:nstvmax,1:nstmax)

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
  if (ios /= 0) call par_stop("list_structure: cannot open file "//trim(p%fn_structure))
  call read_pump(un, list)
  call read_culvert(un, list)
  call read_diversion(un, list)
  call read_dam(un, list)
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
  if (ios > 0) call par_stop("list_struct_pump: namelist read failed: "//trim(iom))
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


!----------------------------------------------------------------------
! &list_struct_culvert を読む(不在なら present_culvert を偽のまま返す)
!   解釈・検証(セル・形状の妥当性)は init_structure が行う
!----------------------------------------------------------------------
subroutine read_culvert(un, list)
  integer, intent(in) :: un
  type(t_list_structure), intent(inout) :: list
  real :: culv_width(1:nstmax), culv_height(1:nstmax)
  real :: culv_zin(1:nstmax), culv_zout(1:nstmax)
  real :: culv_length(1:nstmax), culv_manning(1:nstmax), culv_ce(1:nstmax)
  integer :: culv_flap(1:nstmax), culv_gate_ref(1:nstmax)
  character(len=maxpathlen) :: fn_culv_in_cell(1:nstmax)
  character(len=maxpathlen) :: fn_culv_out_cell(1:nstmax)
  integer :: ios
  character(len=1024) :: iom
  namelist /list_struct_culvert/ culv_in_cell, culv_out_cell, &
                                 culv_width, culv_height, culv_zin, culv_zout, &
                                 culv_length, culv_manning, culv_ce, &
                                 culv_flap, culv_gate_rule, culv_gate_ref, &
                                 fn_culv_in_cell, fn_culv_out_cell

  culv_in_cell = -9999
  culv_out_cell = -9999
  culv_gate_rule = -9999
  culv_width = list%culv_width
  culv_height = list%culv_height
  culv_zin = list%culv_zin
  culv_zout = list%culv_zout
  culv_length = list%culv_length
  culv_manning = list%culv_manning
  culv_ce = list%culv_ce
  culv_flap = list%culv_flap
  culv_gate_ref = list%culv_gate_ref
  fn_culv_in_cell = list%fn_culv_in_cell
  fn_culv_out_cell = list%fn_culv_out_cell

  rewind(un)
  read(un, nml=list_struct_culvert, iostat=ios, iomsg=iom)
  if (ios > 0) call par_stop("list_struct_culvert: namelist read failed: "//trim(iom))
  if (ios < 0) return              ! グループ不在(この型なし)
  list%present_culvert = .true.

  list%culv_in_cell = culv_in_cell
  list%culv_out_cell = culv_out_cell
  list%culv_gate_rule = culv_gate_rule
  list%culv_width = culv_width
  list%culv_height = culv_height
  list%culv_zin = culv_zin
  list%culv_zout = culv_zout
  list%culv_length = culv_length
  list%culv_manning = culv_manning
  list%culv_ce = culv_ce
  list%culv_flap = culv_flap
  list%culv_gate_ref = culv_gate_ref
  list%fn_culv_in_cell = fn_culv_in_cell
  list%fn_culv_out_cell = fn_culv_out_cell

end subroutine


!----------------------------------------------------------------------
! &list_struct_diversion を読む(不在なら present_diversion を偽のまま返す)
!   解釈・検証(セル・ルールの妥当性)は init_structure が行う
!----------------------------------------------------------------------
subroutine read_diversion(un, list)
  integer, intent(in) :: un
  type(t_list_structure), intent(inout) :: list
  real :: div_q0(1:nstmax)
  character(len=maxpathlen) :: fn_div_in_cell(1:nstmax)
  character(len=maxpathlen) :: fn_div_out_cell(1:nstmax)
  integer :: ios
  character(len=1024) :: iom
  namelist /list_struct_diversion/ div_in_cell, div_out_cell, div_q0, &
                                   div_rule, fn_div_in_cell, fn_div_out_cell

  div_in_cell = -9999
  div_out_cell = -9999
  div_rule = -9999
  div_q0 = list%div_q0
  fn_div_in_cell = list%fn_div_in_cell
  fn_div_out_cell = list%fn_div_out_cell

  rewind(un)
  read(un, nml=list_struct_diversion, iostat=ios, iomsg=iom)
  if (ios > 0) call par_stop("list_struct_diversion: namelist read failed: "//trim(iom))
  if (ios < 0) return              ! グループ不在(この型なし)
  list%present_diversion = .true.

  list%div_in_cell = div_in_cell
  list%div_out_cell = div_out_cell
  list%div_rule = div_rule
  list%div_q0 = div_q0
  list%fn_div_in_cell = fn_div_in_cell
  list%fn_div_out_cell = fn_div_out_cell

end subroutine


!----------------------------------------------------------------------
! &list_struct_dam を読む(不在なら present_dam を偽のまま返す)
!   解釈・検証(セル・HV・モードの妥当性)は init_structure が行う
!----------------------------------------------------------------------
subroutine read_dam(un, list)
  integer, intent(in) :: un
  type(t_list_structure), intent(inout) :: list
  integer :: f_dam_mode(1:nstmax)
  real :: dam_q0(1:nstmax), dam_rate(1:nstmax)
  real :: dam_ori_width(1:nstmax), dam_ori_height(1:nstmax)
  real :: dam_ori_zbase(1:nstmax), dam_ori_ce(1:nstmax)
  real :: dam_qmax(1:nstmax), dam_zbase(1:nstmax)
  real :: dam_tadashigaki(1:nstmax), dam_h_init(1:nstmax)
  real :: dam_area(1:nstmax)
  character(len=maxpathlen) :: fn_dam_in_cell(1:nstmax)
  character(len=maxpathlen) :: fn_dam_out_cell(1:nstmax)
  integer :: ios
  character(len=1024) :: iom
  namelist /list_struct_dam/ dam_in_cell, dam_out_cell, dam_hv, f_dam_mode, &
                             dam_q0, dam_rate, dam_hq_rule, &
                             dam_ori_width, dam_ori_height, dam_ori_zbase, dam_ori_ce, &
                             dam_qmax, dam_zbase, dam_tadashigaki, dam_h_init, &
                             dam_area, fn_dam_in_cell, fn_dam_out_cell

  dam_in_cell = -9999
  dam_out_cell = -9999
  dam_hv = -9999
  dam_hq_rule = -9999
  f_dam_mode = list%f_dam_mode
  dam_q0 = list%dam_q0
  dam_rate = list%dam_rate
  dam_ori_width = list%dam_ori_width
  dam_ori_height = list%dam_ori_height
  dam_ori_zbase = list%dam_ori_zbase
  dam_ori_ce = list%dam_ori_ce
  dam_qmax = list%dam_qmax
  dam_zbase = list%dam_zbase
  dam_tadashigaki = list%dam_tadashigaki
  dam_h_init = list%dam_h_init
  dam_area = list%dam_area
  fn_dam_in_cell = list%fn_dam_in_cell
  fn_dam_out_cell = list%fn_dam_out_cell

  rewind(un)
  read(un, nml=list_struct_dam, iostat=ios, iomsg=iom)
  if (ios > 0) call par_stop("list_struct_dam: namelist read failed: "//trim(iom))
  if (ios < 0) return              ! グループ不在(この型なし)
  list%present_dam = .true.

  list%dam_in_cell = dam_in_cell
  list%dam_out_cell = dam_out_cell
  list%dam_hv = dam_hv
  list%dam_hq_rule = dam_hq_rule
  list%f_dam_mode = f_dam_mode
  list%dam_q0 = dam_q0
  list%dam_rate = dam_rate
  list%dam_ori_width = dam_ori_width
  list%dam_ori_height = dam_ori_height
  list%dam_ori_zbase = dam_ori_zbase
  list%dam_ori_ce = dam_ori_ce
  list%dam_qmax = dam_qmax
  list%dam_zbase = dam_zbase
  list%dam_tadashigaki = dam_tadashigaki
  list%dam_h_init = dam_h_init
  list%dam_area = dam_area
  list%fn_dam_in_cell = fn_dam_in_cell
  list%fn_dam_out_cell = fn_dam_out_cell

end subroutine

end module
