module list_wq
  ! ============ 水質(負荷流出)設定ファイルの読み込み(&list_wq) ============
  ! list_* は namelist を読むだけ。解釈・検証・導出(セル検証、単位換算、
  ! 系列の変換など)は m_wq の init が行う(developer.md §12, §30)
  ! ==========================================================================
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_wq
  public :: list_wq_read
  public :: nwqgmax, nwqcmax, nwqvmax, nwqfmax

  integer, parameter :: maxpathlen = 256
  integer, parameter :: nwqgmax = 20     ! 発生源グループの最大数(点源・面源各)
  integer, parameter :: nwqcmax = 400    ! 1グループのセル最大数(inline 指定時)
  integer, parameter :: nwqvmax = 400    ! 負荷・濃度時系列の最大点数
  integer, parameter :: nwqfmax = 40     ! 境界流入区間の最大数

  type t_list_wq
    integer :: f_wq = 1                            ! 0 でファイルを残したまま一時無効化
    real :: wq_c0 = 0.0                            ! 初期濃度 (mg/L。一様)
    integer :: f_wq_infil = 1                      ! 浸透時の輸送物質 (0:地表に残留=粒子態向け,
                                                   !   1:濃度同伴で地下質量プール cg へ=溶存態向け)
    real :: wq_thalf = -9999.0                     ! 半減期 (day。放射性核種等。wq_k20 と排他)
    real :: wq_k20 = -9999.0                       ! 一次減衰係数 (1/day。20℃基準。温度補正は将来)
    real :: wq_vs = -9999.0                        ! 沈降速度 (m/day。地表水のみ。河床への消失)
    ! ---- 点源(セル群+負荷 g/s。一定 wq_pt_load か時系列 wq_pt_series の排他)----
    integer, allocatable :: wq_pt_cell(:,:,:)      ! セル (1:2, 1:nwqcmax, 1:nwqgmax)
    character(len=maxpathlen) :: fn_wq_pt_cell(1:nwqgmax) = ""  ! セル一覧ファイル(inline との排他)
    real :: wq_pt_load(1:nwqgmax) = -9999.0        ! 一定負荷 (g/s。グループ合計)
    real, allocatable :: wq_pt_series(:,:,:)       ! 負荷時系列 (1:2, 1:nwqvmax, 1:nwqgmax)
                                                   !   = (t=0 からの経過日, g/s)
    ! ---- 面源(セル群+原単位 kg/ha/day。同上)----
    integer, allocatable :: wq_ar_cell(:,:,:)
    character(len=maxpathlen) :: fn_wq_ar_cell(1:nwqgmax) = ""
    real :: wq_ar_load(1:nwqgmax) = -9999.0        ! 原単位 (kg/ha/day)
    real, allocatable :: wq_ar_series(:,:,:)       ! (経過日, kg/ha/day)
    ! ---- 分布面源(全有効セル。原単位 kg/ha/day のセル別分布。一定)----
    !   点源・面源・境界流入と排他でなく重ね合わせ(背景負荷+特定源)
    character(len=maxpathlen) :: fn_wq_map = ""    ! 原単位分布ファイル名 (kg/ha/day)
    real :: wq_map_factor = 1.0                    ! 分布への倍率(校正用)
    integer :: f_wq_map = 0                        ! 分布の解釈 (0:地表水へ直接投入,
                                                   !   1:表面蓄積プールへの蓄積レート)
    ! ---- 表面蓄積プール+洗い出し(buildup-washoff。L-Q 非線形の機構)----
    real :: wq_bd_rate = -9999.0                   ! 一様蓄積レート (kg/ha/day。
                                                   !   f_wq_map=1 と排他)
    real :: wq_bd_max = -9999.0                    ! 蓄積上限 (kg/ha。省略で線形無限)
    real :: wq_bd0 = -9999.0                       ! 一様初期プール (kg/ha)
    character(len=maxpathlen) :: fn_wq_bd0 = ""    ! 初期プール分布 (kg/ha。wq_bd0 と排他)
    real :: wq_wash_kr = -9999.0                   ! 雨滴洗い出し係数 (1/m。雨 1 m あたりの
                                                   !   洗い出し割合 = SWMM c1[1/mm]×1000)
    real :: wq_wash_kf = -9999.0                   ! せん断洗い出し係数 (1/s)
    real :: wq_wash_tauc = -9999.0                 ! 限界せん断応力 (N/m2。kf に必須)
    integer :: f_wq_settle = 0                     ! 沈降の行き先 (0:河床へ消失,
                                                   !   1:蓄積プールへ=再懸濁サイクル)
    ! ---- 降雨中濃度(湿性沈着。地表到達雨量 × 濃度で全域投入)----
    real :: wq_rain_conc = -9999.0                 ! 一定濃度 (mg/L。wq_rain_series と排他)
    real, allocatable :: wq_rain_series(:,:)       ! (1:2, 1:nwqvmax) = (経過日, mg/L)
    ! ---- 境界流入濃度(list_boundary の区間流入番号ごと。一定か時系列)----
    real :: wq_in_conc(1:nwqfmax) = -9999.0        ! 一定濃度 (mg/L)
    real, allocatable :: wq_in_series(:,:,:)       ! (1:2, 1:nwqvmax, 1:nwqfmax) = (経過日, mg/L)
  end type

contains

!----------------------------------------------------------------------
! 水質設定ファイルを読み込む(大配列は allocatable 成分とし、グループが
! 存在した場合のみ充填する — list_boundary / list_structure の流儀)
!----------------------------------------------------------------------
subroutine list_wq_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_wq), intent(inout) :: list

  integer :: f_wq
  real :: wq_c0
  integer :: f_wq_infil
  real :: wq_thalf, wq_k20, wq_vs
  integer :: wq_pt_cell(1:2,1:nwqcmax,1:nwqgmax)
  character(len=maxpathlen) :: fn_wq_pt_cell(1:nwqgmax)
  real :: wq_pt_load(1:nwqgmax)
  real :: wq_pt_series(1:2,1:nwqvmax,1:nwqgmax)
  integer :: wq_ar_cell(1:2,1:nwqcmax,1:nwqgmax)
  character(len=maxpathlen) :: fn_wq_ar_cell(1:nwqgmax)
  real :: wq_ar_load(1:nwqgmax)
  real :: wq_ar_series(1:2,1:nwqvmax,1:nwqgmax)
  character(len=maxpathlen) :: fn_wq_map
  real :: wq_map_factor
  integer :: f_wq_map
  real :: wq_bd_rate, wq_bd_max, wq_bd0
  character(len=maxpathlen) :: fn_wq_bd0
  real :: wq_wash_kr, wq_wash_kf, wq_wash_tauc
  integer :: f_wq_settle
  real :: wq_rain_conc
  real :: wq_rain_series(1:2,1:nwqvmax)
  real :: wq_in_conc(1:nwqfmax)
  real :: wq_in_series(1:2,1:nwqvmax,1:nwqfmax)
  integer :: un
  integer :: ios
  character(len=1024) :: iom

  namelist /list_wq/ f_wq, wq_c0, f_wq_infil, wq_thalf, wq_k20, wq_vs, &
                     wq_pt_cell, fn_wq_pt_cell, wq_pt_load, wq_pt_series, &
                     wq_ar_cell, fn_wq_ar_cell, wq_ar_load, wq_ar_series, &
                     fn_wq_map, wq_map_factor, f_wq_map, &
                     wq_bd_rate, wq_bd_max, wq_bd0, fn_wq_bd0, &
                     wq_wash_kr, wq_wash_kf, wq_wash_tauc, f_wq_settle, &
                     wq_rain_conc, wq_rain_series, &
                     wq_in_conc, wq_in_series

  f_wq = list%f_wq
  wq_c0 = list%wq_c0
  f_wq_infil = list%f_wq_infil
  wq_thalf = list%wq_thalf
  wq_k20 = list%wq_k20
  wq_vs = list%wq_vs
  wq_pt_cell = -9999
  fn_wq_pt_cell = list%fn_wq_pt_cell
  wq_pt_load = list%wq_pt_load
  wq_pt_series = -9999.0
  wq_ar_cell = -9999
  fn_wq_ar_cell = list%fn_wq_ar_cell
  wq_ar_load = list%wq_ar_load
  wq_ar_series = -9999.0
  fn_wq_map = list%fn_wq_map
  wq_map_factor = list%wq_map_factor
  f_wq_map = list%f_wq_map
  wq_bd_rate = list%wq_bd_rate
  wq_bd_max = list%wq_bd_max
  wq_bd0 = list%wq_bd0
  fn_wq_bd0 = list%fn_wq_bd0
  wq_wash_kr = list%wq_wash_kr
  wq_wash_kf = list%wq_wash_kf
  wq_wash_tauc = list%wq_wash_tauc
  f_wq_settle = list%f_wq_settle
  wq_rain_conc = list%wq_rain_conc
  wq_rain_series = -9999.0
  wq_in_conc = list%wq_in_conc
  wq_in_series = -9999.0

  call par_info("reading list_wq in "//trim(p%fn_wq))
  open(newunit=un, file=trim(p%fn_wq), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("cannot open file: "//trim(p%fn_wq)//" : "//trim(iom))
  read(un, nml=list_wq, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("error in reading list_wq: "//trim(iom))
  close(un)

  list%f_wq = f_wq
  list%wq_c0 = wq_c0
  list%f_wq_infil = f_wq_infil
  list%wq_thalf = wq_thalf
  list%wq_k20 = wq_k20
  list%wq_vs = wq_vs
  allocate(list%wq_pt_cell(1:2,1:nwqcmax,1:nwqgmax), source = wq_pt_cell)
  list%fn_wq_pt_cell = fn_wq_pt_cell
  list%wq_pt_load = wq_pt_load
  allocate(list%wq_pt_series(1:2,1:nwqvmax,1:nwqgmax), source = wq_pt_series)
  allocate(list%wq_ar_cell(1:2,1:nwqcmax,1:nwqgmax), source = wq_ar_cell)
  list%fn_wq_ar_cell = fn_wq_ar_cell
  list%wq_ar_load = wq_ar_load
  allocate(list%wq_ar_series(1:2,1:nwqvmax,1:nwqgmax), source = wq_ar_series)
  list%fn_wq_map = fn_wq_map
  list%wq_map_factor = wq_map_factor
  list%f_wq_map = f_wq_map
  list%wq_bd_rate = wq_bd_rate
  list%wq_bd_max = wq_bd_max
  list%wq_bd0 = wq_bd0
  list%fn_wq_bd0 = fn_wq_bd0
  list%wq_wash_kr = wq_wash_kr
  list%wq_wash_kf = wq_wash_kf
  list%wq_wash_tauc = wq_wash_tauc
  list%f_wq_settle = f_wq_settle
  list%wq_rain_conc = wq_rain_conc
  allocate(list%wq_rain_series(1:2,1:nwqvmax), source = wq_rain_series)
  list%wq_in_conc = wq_in_conc
  allocate(list%wq_in_series(1:2,1:nwqvmax,1:nwqfmax), source = wq_in_series)

end subroutine

end module
