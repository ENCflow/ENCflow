!======================================================================
! bmi_encflow: ENCflow の CSDMS Basic Model Interface (BMI 2.0) アダプタ
!
!   ENCflow 全体をひとつの BMI component として公開する薄い翻訳層。
!   モデル状態は m_main 内部のインスタンス(ネスト系では格子ごとに 1 つ)
!   であり、本モジュールは m_main の公開手続き(ライフサイクル+アクセサ+
!   インスタンス選択)だけを使う(t_encflow・t_state 等の内部構造は参照
!   しない)。
!
!   設計の正本: docs/bmi_plan.md(§5 構成、§6 段2)、developer.md §53〜§60、
!   多格子(ネスト系)の公開は docs/nesting_plan.md §3.9 と developer.md §73。
!   仕様: bmif_2_0(vendor/bmi.f90。CSDMS bmi-fortran、MIT)。
!
!   規約:
!   - 配列の受け渡しは BMI 仕様どおり flatten した 1 次元。
!     **行順は BMI 標準形に正規化する**(bmi_plan.md §7-5 案A):
!     要素 0 = 南西隅、行は南→北(origin = 左下・spacing 正と整合し、
!     consumer が origin + index*spacing で座標復元できる)。内部の
!     j=1 = 北とは行が逆順のため、get / set のコピー時に反転する。
!     x は内部と同じ西→東(index = i + (ny-j)*nx)。
!   - **格子(grid id)**: ネスト系(fn_nest)は全体が 1 component で、
!     格子を BMI の grid id で区別する。grid 0 = ルート、grid k = 一覧の
!     k+1 行目(= m_main のインスタンス k+1)。ネストなしでは grid 0 のみ。
!     update() はルートの 1 歩(子はその中でサブステップ)、時間情報は
!     ルートのもの。
!   - **変数名**: 基本変数(出力 8・入力 3)の名前はルートの変数。非ルート
!     格子の変数は object 部の末尾に修飾 ~grid<id> を付けて区別する
!     (例: surface_water__depth → surface_water~grid2__depth)。CSDMS
!     Standard Names の文法(object~adjective__quantity)に収まるので
!     bmi-tester・pymt の名前検査を通る。入出力変数表は initialize 時に
!     格子数に応じて生成する(ensure_items)。encflow_var_on_grid() が
!     名前を組み立てる公開ヘルパ。
!   - 基本変数は出力8(h, z, pre, e, 速さ, 比流量, 流速成分 x/y)・
!     入力3(h, z, pre)。set_value の受理条件と意味論は変数ごとに
!     異なり、格子によらず同じ(Setters 節と developer.md §56・§57)。
!     流速成分は vv・qdir からの導出量で、y 成分は標準形(+y=北)へ符号
!     変換して返す(§60)。
!   - 該当機能がない問い合わせは BMI_FAILURE を返す(仕様が許容)。
!   - 本ファイルは計算本体(src/)の外の optional アダプタであり、
!     src/ のビルドはこのファイルに依存しない(方針10 追記 2026-08-28)
!======================================================================
module bmi_encflow
  use bmif_2_0
  use m_main, only : m_main_initialize, m_main_update, m_main_finished, &
                     m_main_finalize, m_main_get_timeinfo, &
                     m_main_get_gridinfo, m_main_get_ierror, &
                     m_main_get_value, m_main_set_value, &
                     m_main_select, m_main_get_ngrids
  use m_util, only : itoa
  implicit none
  private

  public :: encflow_bmi
  public :: encflow_var_on_grid

  ! 基本変数表(CSDMS Standard Name ↔ m_main 内部名)。
  ! 追加するときは n_base_* と base_* と var_internal() と
  ! get_var_units() を同時に更新すること。3変数は入出力の両方だが
  ! set の受理条件は変数ごとに異なる(m_main_set_value が判定。
  ! developer.md §56: 降水は prtype=0 のときのみ。§57: z は z 更新
  ! プロセス無効時のみ、h は常時 = データ同化型の状態置換)
  integer, parameter :: n_base_in = 3
  integer, parameter :: n_base_out = 8

  character(len=BMI_MAX_COMPONENT_NAME), target :: &
    component_name = "ENCflow"

  character(len=BMI_MAX_VAR_NAME), parameter :: &
    base_out(n_base_out) = [ character(len=BMI_MAX_VAR_NAME) :: &
      "surface_water__depth", &
      "land_surface__elevation", &
      "atmosphere_water__precipitation_leq-volume_flux", &
      "surface_water__elevation", &
      "surface_water_flow__speed", &
      "surface_water_flow__unit_width_volume_flow_rate", &
      "surface_water__x_component_of_velocity", &
      "surface_water__y_component_of_velocity" ]

  character(len=BMI_MAX_VAR_NAME), parameter :: &
    base_in(n_base_in) = [ character(len=BMI_MAX_VAR_NAME) :: &
      "surface_water__depth", &
      "land_surface__elevation", &
      "atmosphere_water__precipitation_leq-volume_flux" ]

  ! 公開変数表(格子数 × 基本変数。ensure_items が生成する。names を
  ! ポインタで返す仕様のため target のモジュール変数に置く)
  character(len=BMI_MAX_VAR_NAME), allocatable, target, save :: output_items(:)
  character(len=BMI_MAX_VAR_NAME), allocatable, target, save :: input_items(:)
  integer, save :: items_ngrids = 0    ! 表を生成したときの格子数(0 = 未生成)

  type, extends(bmi) :: encflow_bmi
  contains
    procedure :: initialize => encflow_initialize
    procedure :: update => encflow_update
    procedure :: update_until => encflow_update_until
    procedure :: finalize => encflow_finalize
    procedure :: get_component_name => encflow_component_name
    procedure :: get_input_item_count => encflow_input_item_count
    procedure :: get_output_item_count => encflow_output_item_count
    procedure :: get_input_var_names => encflow_input_var_names
    procedure :: get_output_var_names => encflow_output_var_names
    procedure :: get_var_grid => encflow_var_grid
    procedure :: get_var_type => encflow_var_type
    procedure :: get_var_units => encflow_var_units
    procedure :: get_var_itemsize => encflow_var_itemsize
    procedure :: get_var_nbytes => encflow_var_nbytes
    procedure :: get_var_location => encflow_var_location
    procedure :: get_current_time => encflow_current_time
    procedure :: get_start_time => encflow_start_time
    procedure :: get_end_time => encflow_end_time
    procedure :: get_time_units => encflow_time_units
    procedure :: get_time_step => encflow_time_step
    procedure :: get_value_int => encflow_get_int
    procedure :: get_value_float => encflow_get_float
    procedure :: get_value_double => encflow_get_double
    procedure :: get_value_ptr_int => encflow_get_ptr_int
    procedure :: get_value_ptr_float => encflow_get_ptr_float
    procedure :: get_value_ptr_double => encflow_get_ptr_double
    procedure :: get_value_at_indices_int => encflow_get_at_indices_int
    procedure :: get_value_at_indices_float => encflow_get_at_indices_float
    procedure :: get_value_at_indices_double => encflow_get_at_indices_double
    procedure :: set_value_int => encflow_set_int
    procedure :: set_value_float => encflow_set_float
    procedure :: set_value_double => encflow_set_double
    procedure :: set_value_at_indices_int => encflow_set_at_indices_int
    procedure :: set_value_at_indices_float => encflow_set_at_indices_float
    procedure :: set_value_at_indices_double => encflow_set_at_indices_double
    procedure :: get_grid_rank => encflow_grid_rank
    procedure :: get_grid_size => encflow_grid_size
    procedure :: get_grid_type => encflow_grid_type
    procedure :: get_grid_shape => encflow_grid_shape
    procedure :: get_grid_spacing => encflow_grid_spacing
    procedure :: get_grid_origin => encflow_grid_origin
    procedure :: get_grid_x => encflow_grid_x
    procedure :: get_grid_y => encflow_grid_y
    procedure :: get_grid_z => encflow_grid_z
    procedure :: get_grid_node_count => encflow_grid_node_count
    procedure :: get_grid_edge_count => encflow_grid_edge_count
    procedure :: get_grid_face_count => encflow_grid_face_count
    procedure :: get_grid_edge_nodes => encflow_grid_edge_nodes
    procedure :: get_grid_face_edges => encflow_grid_face_edges
    procedure :: get_grid_face_nodes => encflow_grid_face_nodes
    procedure :: get_grid_nodes_per_face => encflow_grid_nodes_per_face
  end type encflow_bmi

contains

  !====================== Grids and variable names =====================

  !--------------------------------------------------------------------
  ! 基本変数名 + grid id → その格子の変数名(grid 0 はそのまま)。
  !   "surface_water__depth", 2 → "surface_water~grid2__depth"
  !--------------------------------------------------------------------
  function encflow_var_on_grid(base, grid) result(name)
    character(len=*), intent(in) :: base
    integer, intent(in) :: grid
    character(len=BMI_MAX_VAR_NAME) :: name
    integer :: p
    p = index(base, "__")
    if (grid <= 0 .or. p < 2) then
      name = base
    else
      name = base(1:p-1) // "~grid" // itoa(grid) // trim(base(p:))
    end if
  end function encflow_var_on_grid

  !--------------------------------------------------------------------
  ! 変数名 → 基本変数名と grid id(修飾がなければ 0)。ierr: 0 = 形式
  ! として解釈できた(格子の存在は var_internal が検査)、1 = 修飾の
  ! 数字が読めない
  !--------------------------------------------------------------------
  subroutine split_name(name, base, grid, ierr)
    character(len=*), intent(in) :: name
    character(len=BMI_MAX_VAR_NAME), intent(out) :: base
    integer, intent(out) :: grid, ierr
    integer :: p, q, ios
    ierr = 0
    grid = 0
    base = name
    p = index(name, "__")
    if (p < 2) return
    q = index(name(1:p-1), "~grid", back=.true.)
    if (q < 1) return
    if (p - (q + 5) < 1) then
      ierr = 1
      return
    end if
    read(name(q+5:p-1), *, iostat=ios) grid
    if (ios /= 0 .or. grid < 1) then
      ierr = 1
      return
    end if
    base = name(1:q-1) // trim(name(p:))
  end subroutine split_name

  !--------------------------------------------------------------------
  ! Standard Name → m_main 内部名と grid id。ierr: 0 = 対応、1 = 未対応
  ! (未知の変数、または存在しない格子)
  !--------------------------------------------------------------------
  subroutine var_internal(name, iname, grid, ierr)
    character(len=*), intent(in) :: name
    character(len=8), intent(out) :: iname
    integer, intent(out) :: grid, ierr
    character(len=BMI_MAX_VAR_NAME) :: base
    call split_name(name, base, grid, ierr)
    if (ierr /= 0 .or. grid >= m_main_get_ngrids()) then
      iname = ""
      grid = -1
      ierr = 1
      return
    end if
    ierr = 0
    select case (trim(base))
    case ("surface_water__depth")
      iname = "h"
    case ("land_surface__elevation")
      iname = "z"
    case ("atmosphere_water__precipitation_leq-volume_flux")
      iname = "pre"
    case ("surface_water__elevation")
      iname = "e"
    case ("surface_water_flow__speed")
      iname = "vv"
    case ("surface_water_flow__unit_width_volume_flow_rate")
      iname = "qq"
    case ("surface_water__x_component_of_velocity")
      iname = "ux"
    case ("surface_water__y_component_of_velocity")
      iname = "uy"
    case default
      iname = ""
      grid = -1
      ierr = 1
    end select
  end subroutine var_internal

  !--------------------------------------------------------------------
  ! 公開変数表を現在の格子数に合わせて(再)生成する。並びは格子ごとに
  ! 基本変数の順(grid 0 の 8 個、grid 1 の 8 個、…)
  !--------------------------------------------------------------------
  subroutine ensure_items()
    integer :: ng, g, i
    ng = m_main_get_ngrids()
    if (items_ngrids == ng) return
    if (allocated(output_items)) deallocate(output_items)
    if (allocated(input_items)) deallocate(input_items)
    allocate(output_items(n_base_out * ng))
    allocate(input_items(n_base_in * ng))
    do g = 0, ng - 1
      do i = 1, n_base_out
        output_items(g * n_base_out + i) = encflow_var_on_grid(trim(base_out(i)), g)
      end do
      do i = 1, n_base_in
        input_items(g * n_base_in + i) = encflow_var_on_grid(trim(base_in(i)), g)
      end do
    end do
    items_ngrids = ng
  end subroutine ensure_items

  !--------------------------------------------------------------------
  ! grid id の存在検査
  !--------------------------------------------------------------------
  logical function grid_ok(grid)
    integer, intent(in) :: grid
    grid_ok = (grid >= 0 .and. grid < m_main_get_ngrids())
  end function grid_ok

  !--------------------------------------------------------------------
  ! 格子 grid を「現在のインスタンス」にする / ルートに戻す。
  !   ルート(grid 0)は update の後は常に選択済みなので何もしない =
  !   ネストなしの経路は m_main_select に触れない(従来と同一)。
  !   MPI では全ランクが同じ順序で呼ぶ(本モジュールの呼び出し規約)
  !--------------------------------------------------------------------
  subroutine enter_grid(grid)
    integer, intent(in) :: grid
    if (grid > 0) call m_main_select(grid + 1)
  end subroutine enter_grid

  subroutine leave_grid(grid)
    integer, intent(in) :: grid
    if (grid > 0) call m_main_select(1)
  end subroutine leave_grid

  !--------------------------------------------------------------------
  ! 格子 grid の格子情報(m_main_get_gridinfo を格子を選んで呼ぶ)
  !--------------------------------------------------------------------
  subroutine grid_info(grid, nx, ny, dx, dy, x0, y0)
    integer, intent(in) :: grid
    integer, intent(out) :: nx, ny
    double precision, intent(out) :: dx, dy, x0, y0
    call enter_grid(grid)
    call m_main_get_gridinfo(nx, ny, dx, dy, x0, y0)
    call leave_grid(grid)
  end subroutine grid_info

  !===================== Initialize, run, finalize =====================

  function encflow_initialize(this, config_file) result(bmi_status)
    class(encflow_bmi), intent(out) :: this
    character(len=*), intent(in) :: config_file
    integer :: bmi_status
    call m_main_initialize(config_file)
    call ensure_items()               ! 格子数が確定したので変数表を生成
    bmi_status = BMI_SUCCESS
  end function

  function encflow_update(this) result(bmi_status)
    class(encflow_bmi), intent(inout) :: this
    integer :: bmi_status
    if (m_main_finished()) then
      ! 終了時刻到達後・エラー後は進められない
      bmi_status = BMI_FAILURE
      return
    end if
    call m_main_update()              ! ネスト系ではルートの 1 歩(子はその中)
    if (m_main_get_ierror() > 0) then
      bmi_status = BMI_FAILURE
    else
      bmi_status = BMI_SUCCESS
    end if
  end function

  function encflow_update_until(this, time) result(bmi_status)
    class(encflow_bmi), intent(inout) :: this
    double precision, intent(in) :: time
    integer :: bmi_status
    double precision :: t, t0, tend, dt
    integer :: k, nstep
    call m_main_get_timeinfo(t, t0, tend, dt)
    ! dt の整数倍・現在以降・終了時刻以内のみ受け付ける(bmi_plan.md §8)
    if (time < t .or. time > tend + 0.5d0*dt) then
      bmi_status = BMI_FAILURE
      return
    end if
    nstep = nint((time - t) / dt)
    if (abs(t + nstep*dt - time) > 1d-6*dt) then
      bmi_status = BMI_FAILURE
      return
    end if
    bmi_status = BMI_SUCCESS
    do k = 1, nstep
      bmi_status = this%update()
      if (bmi_status /= BMI_SUCCESS) return
    end do
  end function

  function encflow_finalize(this) result(bmi_status)
    class(encflow_bmi), intent(inout) :: this
    integer :: bmi_status
    call m_main_finalize()
    bmi_status = BMI_SUCCESS
  end function

  !========================= Exchange items ============================

  function encflow_component_name(this, name) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), pointer, intent(out) :: name
    integer :: bmi_status
    name => component_name
    bmi_status = BMI_SUCCESS
  end function

  function encflow_input_item_count(this, count) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(out) :: count
    integer :: bmi_status
    call ensure_items()
    count = size(input_items)
    bmi_status = BMI_SUCCESS
  end function

  function encflow_output_item_count(this, count) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(out) :: count
    integer :: bmi_status
    call ensure_items()
    count = size(output_items)
    bmi_status = BMI_SUCCESS
  end function

  function encflow_input_var_names(this, names) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), pointer, intent(out) :: names(:)
    integer :: bmi_status
    call ensure_items()
    names => input_items
    bmi_status = BMI_SUCCESS
  end function

  function encflow_output_var_names(this, names) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), pointer, intent(out) :: names(:)
    integer :: bmi_status
    call ensure_items()
    names => output_items
    bmi_status = BMI_SUCCESS
  end function

  !======================= Variable information ========================

  function encflow_var_grid(this, name, grid) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    integer, intent(out) :: grid
    integer :: bmi_status
    character(len=8) :: iname
    integer :: ierr
    call var_internal(name, iname, grid, ierr)
    if (ierr /= 0) then
      grid = -1
      bmi_status = BMI_FAILURE
    else
      bmi_status = BMI_SUCCESS       ! セル中心量は格子ごとに 1 種(grid = 格子番号)
    end if
  end function

  function encflow_var_type(this, name, type) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    character(len=*), intent(out) :: type
    integer :: bmi_status
    character(len=8) :: iname
    integer :: ierr, grid
    call var_internal(name, iname, grid, ierr)
    if (ierr /= 0) then
      type = ""
      bmi_status = BMI_FAILURE
      return
    end if
    ! 実数精度は PREC(make.inc)に追随して報告する
    if (storage_size(1.0) == 64) then
      type = "double_precision"
    else
      type = "real"
    end if
    bmi_status = BMI_SUCCESS
  end function

  function encflow_var_units(this, name, units) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    character(len=*), intent(out) :: units
    integer :: bmi_status
    character(len=8) :: iname
    integer :: ierr, grid
    call var_internal(name, iname, grid, ierr)
    if (ierr /= 0) then
      units = ""
      bmi_status = BMI_FAILURE
      return
    end if
    select case (trim(iname))
    case ("pre", "vv", "ux", "uy")
      units = "m s-1"
    case ("qq")
      units = "m2 s-1"
    case default
      units = "m"
    end select
    bmi_status = BMI_SUCCESS
  end function

  function encflow_var_itemsize(this, name, size) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    integer, intent(out) :: size
    integer :: bmi_status
    character(len=8) :: iname
    integer :: ierr, grid
    call var_internal(name, iname, grid, ierr)
    if (ierr /= 0) then
      size = 0
      bmi_status = BMI_FAILURE
    else
      size = storage_size(1.0) / 8
      bmi_status = BMI_SUCCESS
    end if
  end function

  function encflow_var_nbytes(this, name, nbytes) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    integer, intent(out) :: nbytes
    integer :: bmi_status
    integer :: itemsize, gsize, grid
    bmi_status = this%get_var_itemsize(name, itemsize)
    if (bmi_status /= BMI_SUCCESS) then
      nbytes = 0
      return
    end if
    bmi_status = this%get_var_grid(name, grid)
    if (bmi_status /= BMI_SUCCESS) then
      nbytes = 0
      return
    end if
    bmi_status = this%get_grid_size(grid, gsize)
    nbytes = itemsize * gsize
  end function

  function encflow_var_location(this, name, location) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    character(len=*), intent(out) :: location
    integer :: bmi_status
    character(len=8) :: iname
    integer :: ierr, grid
    call var_internal(name, iname, grid, ierr)
    if (ierr /= 0) then
      location = ""
      bmi_status = BMI_FAILURE
    else
      location = "node"               ! uniform grid のノード = ENCflow のセル中心
      bmi_status = BMI_SUCCESS
    end if
  end function

  !========================= Time information ==========================
  ! いずれもルート(ネスト系の時間軸)。update の後はルートが選択済み

  function encflow_current_time(this, time) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    double precision, intent(out) :: time
    integer :: bmi_status
    double precision :: t0, tend, dt
    call m_main_get_timeinfo(time, t0, tend, dt)
    bmi_status = BMI_SUCCESS
  end function

  function encflow_start_time(this, time) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    double precision, intent(out) :: time
    integer :: bmi_status
    double precision :: t, tend, dt
    call m_main_get_timeinfo(t, time, tend, dt)
    bmi_status = BMI_SUCCESS
  end function

  function encflow_end_time(this, time) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    double precision, intent(out) :: time
    integer :: bmi_status
    double precision :: t, t0, dt
    call m_main_get_timeinfo(t, t0, time, dt)
    bmi_status = BMI_SUCCESS
  end function

  function encflow_time_units(this, units) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(out) :: units
    integer :: bmi_status
    units = "s"
    bmi_status = BMI_SUCCESS
  end function

  function encflow_time_step(this, time_step) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    double precision, intent(out) :: time_step
    integer :: bmi_status
    double precision :: t, t0, tend
    call m_main_get_timeinfo(t, t0, tend, time_step)
    bmi_status = BMI_SUCCESS
  end function

  !========================= Getters, by type ==========================

  !--------------------------------------------------------------------
  ! get 共通処理: 変数名 → 格子を選んで全域場を取り出し、標準形
  ! (要素0=南西・+y 北)に正規化した 2 次元 buf(nx, ny) を返す。
  ! n = 呼び出し側の配列長(格子サイズと一致しなければ FAILURE)
  !--------------------------------------------------------------------
  function get_field(name, n, buf, nx, ny) result(bmi_status)
    character(len=*), intent(in) :: name
    integer, intent(in) :: n
    real, allocatable, intent(out) :: buf(:,:)
    integer, intent(out) :: nx, ny
    integer :: bmi_status
    character(len=8) :: iname
    integer :: ierr, grid
    double precision :: dx, dy, x0, y0
    real, allocatable :: wk(:,:)
    call var_internal(name, iname, grid, ierr)
    if (ierr /= 0) then
      bmi_status = BMI_FAILURE
      return
    end if
    call grid_info(grid, nx, ny, dx, dy, x0, y0)
    if (n /= nx*ny) then
      bmi_status = BMI_FAILURE
      return
    end if
    allocate(wk(nx, ny))
    call enter_grid(grid)
    call m_main_get_value(iname, wk, ierr)
    call leave_grid(grid)
    if (ierr /= 0) then
      bmi_status = BMI_FAILURE
      return
    end if
    ! y 成分は符号変換(内部 +y = j 増加方向 = 南 → 標準形 +y = 北)
    if (trim(iname) == "uy") wk = -wk
    ! 行反転(内部 j=1=北 → BMI 標準形 要素0=南西。ヘッダ参照)
    allocate(buf(nx, ny))
    buf = wk(:, ny:1:-1)
    bmi_status = BMI_SUCCESS
  end function

  function encflow_get_int(this, name, dest) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    integer, intent(inout) :: dest(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE          ! 整数の公開変数なし
  end function

  function encflow_get_float(this, name, dest) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    real, intent(inout) :: dest(:)
    integer :: bmi_status
    integer :: nx, ny
    real, allocatable :: buf(:,:)
    bmi_status = get_field(name, size(dest), buf, nx, ny)
    if (bmi_status /= BMI_SUCCESS) return
    dest = reshape(buf, [nx*ny])
  end function

  function encflow_get_double(this, name, dest) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    double precision, intent(inout) :: dest(:)
    integer :: bmi_status
    integer :: nx, ny
    real, allocatable :: buf(:,:)
    bmi_status = get_field(name, size(dest), buf, nx, ny)
    if (bmi_status /= BMI_SUCCESS) return
    dest = reshape(dble(buf), [nx*ny])
  end function

  function encflow_get_ptr_int(this, name, dest_ptr) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    integer, pointer, intent(inout) :: dest_ptr(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE          ! 参照は返さない(bmi_plan.md §2, §7)
  end function

  function encflow_get_ptr_float(this, name, dest_ptr) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    real, pointer, intent(inout) :: dest_ptr(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_get_ptr_double(this, name, dest_ptr) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    double precision, pointer, intent(inout) :: dest_ptr(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_get_at_indices_int(this, name, dest, inds) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    integer, intent(inout) :: dest(:)
    integer, intent(in) :: inds(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_get_at_indices_float(this, name, dest, inds) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    real, intent(inout) :: dest(:)
    integer, intent(in) :: inds(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_get_at_indices_double(this, name, dest, inds) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    double precision, intent(inout) :: dest(:)
    integer, intent(in) :: inds(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  !========================= Setters, by type ==========================
  ! 対応は input_items(基本 3 変数 × 格子)。値はステージングされ、その
  ! 格子の次の 1 歩の冒頭で適用される(pre は持続強制、z・h は置換の
  ! 一回適用)。受理条件は m_main_set_value が格子ごとに判定(pre:
  ! prtype=0 のみ、z: z 更新プロセス無効時のみ、h: 常時。§56・§57)

  !--------------------------------------------------------------------
  ! set 共通処理: 標準形 1 次元(要素0=南西)→ 内部行順に反転して
  ! 変数の格子を選び m_main へ渡す
  !--------------------------------------------------------------------
  function set_field(name, src) result(bmi_status)
    character(len=*), intent(in) :: name
    real, intent(in) :: src(:)
    integer :: bmi_status
    character(len=8) :: iname
    integer :: ierr, nx, ny, grid
    double precision :: dx, dy, x0, y0
    real, allocatable :: buf(:,:)
    call var_internal(name, iname, grid, ierr)
    if (ierr /= 0) then
      bmi_status = BMI_FAILURE
      return
    end if
    call grid_info(grid, nx, ny, dx, dy, x0, y0)
    if (size(src) /= nx*ny) then
      bmi_status = BMI_FAILURE
      return
    end if
    allocate(buf(nx, ny))
    ! 行反転(BMI 標準形 要素0=南西 → 内部 j=1=北。get と逆写像)
    buf(:, ny:1:-1) = reshape(src, [nx, ny])
    call enter_grid(grid)
    call m_main_set_value(trim(iname), buf, ierr)
    call leave_grid(grid)
    if (ierr /= 0) then
      bmi_status = BMI_FAILURE
    else
      bmi_status = BMI_SUCCESS
    end if
  end function

  function encflow_set_int(this, name, src) result(bmi_status)
    class(encflow_bmi), intent(inout) :: this
    character(len=*), intent(in) :: name
    integer, intent(in) :: src(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE          ! 整数の入力変数なし
  end function

  function encflow_set_float(this, name, src) result(bmi_status)
    class(encflow_bmi), intent(inout) :: this
    character(len=*), intent(in) :: name
    real, intent(in) :: src(:)
    integer :: bmi_status
    bmi_status = set_field(name, src)
  end function

  function encflow_set_double(this, name, src) result(bmi_status)
    class(encflow_bmi), intent(inout) :: this
    character(len=*), intent(in) :: name
    double precision, intent(in) :: src(:)
    integer :: bmi_status
    bmi_status = set_field(name, real(src))
  end function

  function encflow_set_at_indices_int(this, name, inds, src) result(bmi_status)
    class(encflow_bmi), intent(inout) :: this
    character(len=*), intent(in) :: name
    integer, intent(in) :: inds(:)
    integer, intent(in) :: src(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_set_at_indices_float(this, name, inds, src) result(bmi_status)
    class(encflow_bmi), intent(inout) :: this
    character(len=*), intent(in) :: name
    integer, intent(in) :: inds(:)
    real, intent(in) :: src(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_set_at_indices_double(this, name, inds, src) result(bmi_status)
    class(encflow_bmi), intent(inout) :: this
    character(len=*), intent(in) :: name
    integer, intent(in) :: inds(:)
    double precision, intent(in) :: src(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  !========================= Grid information ==========================
  ! grid 0 = ルート、grid k = 一覧の k+1 行目。いずれも uniform_rectilinear

  function encflow_grid_rank(this, grid, rank) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    integer, intent(out) :: rank
    integer :: bmi_status
    if (.not. grid_ok(grid)) then
      rank = 0
      bmi_status = BMI_FAILURE
    else
      rank = 2
      bmi_status = BMI_SUCCESS
    end if
  end function

  function encflow_grid_size(this, grid, size) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    integer, intent(out) :: size
    integer :: bmi_status
    integer :: nx, ny
    double precision :: dx, dy, x0, y0
    if (.not. grid_ok(grid)) then
      size = 0
      bmi_status = BMI_FAILURE
      return
    end if
    call grid_info(grid, nx, ny, dx, dy, x0, y0)
    size = nx * ny
    bmi_status = BMI_SUCCESS
  end function

  function encflow_grid_type(this, grid, type) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    character(len=*), intent(out) :: type
    integer :: bmi_status
    if (.not. grid_ok(grid)) then
      type = ""
      bmi_status = BMI_FAILURE
    else
      type = "uniform_rectilinear"
      bmi_status = BMI_SUCCESS
    end if
  end function

  function encflow_grid_shape(this, grid, shape) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    integer, dimension(:), intent(out) :: shape
    integer :: bmi_status
    integer :: nx, ny
    double precision :: dx, dy, x0, y0
    if (.not. grid_ok(grid) .or. size(shape) < 2) then
      bmi_status = BMI_FAILURE
      return
    end if
    call grid_info(grid, nx, ny, dx, dy, x0, y0)
    shape(1:2) = [ny, nx]             ! BMI 規約: 行(y)を先に返す
    bmi_status = BMI_SUCCESS
  end function

  function encflow_grid_spacing(this, grid, spacing) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    double precision, dimension(:), intent(out) :: spacing
    integer :: bmi_status
    integer :: nx, ny
    double precision :: dx, dy, x0, y0
    if (.not. grid_ok(grid) .or. size(spacing) < 2) then
      bmi_status = BMI_FAILURE
      return
    end if
    call grid_info(grid, nx, ny, dx, dy, x0, y0)
    spacing(1:2) = [dy, dx]           ! shape と同順([y, x])
    bmi_status = BMI_SUCCESS
  end function

  function encflow_grid_origin(this, grid, origin) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    double precision, dimension(:), intent(out) :: origin
    integer :: bmi_status
    integer :: nx, ny
    double precision :: dx, dy, x0, y0
    if (.not. grid_ok(grid) .or. size(origin) < 2) then
      bmi_status = BMI_FAILURE
      return
    end if
    call grid_info(grid, nx, ny, dx, dy, x0, y0)
    ! shape と同順([y, x])。georef 未管理のルートは 0。子格子は親の原点と
    ! 整列位置から導かれ、全格子がルートの座標系で自己記述される(m_main)
    origin(1:2) = [y0, x0]
    bmi_status = BMI_SUCCESS
  end function

  function encflow_grid_x(this, grid, x) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    double precision, dimension(:), intent(out) :: x
    integer :: bmi_status
    bmi_status = BMI_FAILURE          ! uniform_rectilinear は shape/spacing/origin で表現
  end function

  function encflow_grid_y(this, grid, y) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    double precision, dimension(:), intent(out) :: y
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_grid_z(this, grid, z) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    double precision, dimension(:), intent(out) :: z
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_grid_node_count(this, grid, count) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    integer, intent(out) :: count
    integer :: bmi_status
    bmi_status = this%get_grid_size(grid, count)
  end function

  function encflow_grid_edge_count(this, grid, count) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    integer, intent(out) :: count
    integer :: bmi_status
    bmi_status = BMI_FAILURE          ! 非構造格子の口は対象外
  end function

  function encflow_grid_face_count(this, grid, count) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    integer, intent(out) :: count
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_grid_edge_nodes(this, grid, edge_nodes) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    integer, dimension(:), intent(out) :: edge_nodes
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_grid_face_edges(this, grid, face_edges) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    integer, dimension(:), intent(out) :: face_edges
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_grid_face_nodes(this, grid, face_nodes) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    integer, dimension(:), intent(out) :: face_nodes
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_grid_nodes_per_face(this, grid, nodes_per_face) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    integer, dimension(:), intent(out) :: nodes_per_face
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

end module bmi_encflow
