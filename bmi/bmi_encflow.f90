!======================================================================
! bmi_encflow: ENCflow の CSDMS Basic Model Interface (BMI 2.0) アダプタ
!
!   ENCflow 全体をひとつの BMI component として公開する薄い翻訳層。
!   モデル状態は m_main 内部の単一インスタンスであり、本モジュールは
!   m_main の公開手続き(ライフサイクル+アクセサ)だけを使う
!   (t_encflow・t_state 等の内部構造は参照しない)。
!
!   設計の正本: docs/bmi_plan.md(§5 構成、§6 段2)、developer.md §53。
!   仕様: bmif_2_0(vendor/bmi.f90。CSDMS bmi-fortran、MIT)。
!
!   規約:
!   - 配列の受け渡しは BMI 仕様どおり flatten した 1 次元。
!     **行順は BMI 標準形に正規化する**(bmi_plan.md §7-5 案A):
!     要素 0 = 南西隅、行は南→北(origin = 左下・spacing 正と整合し、
!     consumer が origin + index*spacing で座標復元できる)。内部の
!     j=1 = 北とは行が逆順のため、get(将来は set も)のコピー時に
!     反転する。x は内部と同じ西→東(index = i + (ny-j)*nx)。
!   - 現段階(段2)は逐次専用・出力変数のみ(set_value は BMI_FAILURE)。
!   - 該当機能がない問い合わせは BMI_FAILURE を返す(仕様が許容)。
!   - 本ファイルは計算本体(src/)の外の optional アダプタであり、
!     src/ のビルドはこのファイルに依存しない(方針10 追記 2026-08-28)
!======================================================================
module bmi_encflow
  use bmif_2_0
  use m_main, only : m_main_initialize, m_main_update, m_main_finished, &
                     m_main_finalize, m_main_get_timeinfo, &
                     m_main_get_gridinfo, m_main_get_ierror, m_main_get_value
  implicit none
  private

  public :: encflow_bmi

  ! 公開変数表(CSDMS Standard Name ↔ m_main 内部名)。
  ! 追加するときは n_outputs と var_internal() と get_var_units() を
  ! 同時に更新すること
  integer, parameter :: n_inputs = 0
  integer, parameter :: n_outputs = 3

  character(len=BMI_MAX_COMPONENT_NAME), target :: &
    component_name = "ENCflow"

  character(len=BMI_MAX_VAR_NAME), target :: &
    output_items(n_outputs) = [ character(len=BMI_MAX_VAR_NAME) :: &
      "surface_water__depth", &
      "land_surface__elevation", &
      "atmosphere_water__precipitation_leq-volume_flux" ]

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

  !--------------------------------------------------------------------
  ! Standard Name → m_main 内部名。ierr: 0 = 対応、1 = 未対応
  !--------------------------------------------------------------------
  subroutine var_internal(name, iname, ierr)
    character(len=*), intent(in) :: name
    character(len=8), intent(out) :: iname
    integer, intent(out) :: ierr
    ierr = 0
    select case (trim(name))
    case ("surface_water__depth")
      iname = "h"
    case ("land_surface__elevation")
      iname = "z"
    case ("atmosphere_water__precipitation_leq-volume_flux")
      iname = "pre"
    case default
      iname = ""
      ierr = 1
    end select
  end subroutine var_internal

  !===================== Initialize, run, finalize =====================

  function encflow_initialize(this, config_file) result(bmi_status)
    class(encflow_bmi), intent(out) :: this
    character(len=*), intent(in) :: config_file
    integer :: bmi_status
    call m_main_initialize(config_file)
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
    call m_main_update()
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
    count = n_inputs
    bmi_status = BMI_SUCCESS
  end function

  function encflow_output_item_count(this, count) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(out) :: count
    integer :: bmi_status
    count = n_outputs
    bmi_status = BMI_SUCCESS
  end function

  function encflow_input_var_names(this, names) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), pointer, intent(out) :: names(:)
    integer :: bmi_status
    ! 入力変数なし(段2)。空リストの返却はできないため FAILURE とし、
    ! 利用側は get_input_item_count == 0 を正とする
    names => null()
    bmi_status = BMI_FAILURE
  end function

  function encflow_output_var_names(this, names) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), pointer, intent(out) :: names(:)
    integer :: bmi_status
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
    call var_internal(name, iname, ierr)
    if (ierr /= 0) then
      grid = -1
      bmi_status = BMI_FAILURE
    else
      grid = 0                        ! セル中心量は grid 0 の1種のみ(段2)
      bmi_status = BMI_SUCCESS
    end if
  end function

  function encflow_var_type(this, name, type) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    character(len=*), intent(out) :: type
    integer :: bmi_status
    character(len=8) :: iname
    integer :: ierr
    call var_internal(name, iname, ierr)
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
    integer :: ierr
    call var_internal(name, iname, ierr)
    if (ierr /= 0) then
      units = ""
      bmi_status = BMI_FAILURE
      return
    end if
    select case (trim(iname))
    case ("pre")
      units = "m s-1"
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
    integer :: ierr
    call var_internal(name, iname, ierr)
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
    integer :: itemsize, gsize
    bmi_status = this%get_var_itemsize(name, itemsize)
    if (bmi_status /= BMI_SUCCESS) then
      nbytes = 0
      return
    end if
    bmi_status = this%get_grid_size(0, gsize)
    nbytes = itemsize * gsize
  end function

  function encflow_var_location(this, name, location) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    character(len=*), intent(out) :: location
    integer :: bmi_status
    character(len=8) :: iname
    integer :: ierr
    call var_internal(name, iname, ierr)
    if (ierr /= 0) then
      location = ""
      bmi_status = BMI_FAILURE
    else
      location = "node"               ! uniform grid のノード = ENCflow のセル中心
      bmi_status = BMI_SUCCESS
    end if
  end function

  !========================= Time information ==========================

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
    character(len=8) :: iname
    integer :: ierr, nx, ny
    double precision :: dx, dy, x0, y0
    real, allocatable :: buf(:,:)
    call var_internal(name, iname, ierr)
    if (ierr /= 0) then
      bmi_status = BMI_FAILURE
      return
    end if
    call m_main_get_gridinfo(nx, ny, dx, dy, x0, y0)
    if (size(dest) /= nx*ny) then
      bmi_status = BMI_FAILURE
      return
    end if
    allocate(buf(nx, ny))
    call m_main_get_value(iname, buf, ierr)
    if (ierr /= 0) then
      bmi_status = BMI_FAILURE
      return
    end if
    ! flatten + 行反転(内部 j=1=北 → BMI 標準形 要素0=南西。ヘッダ参照)
    dest = reshape(buf(:, ny:1:-1), [nx*ny])
    bmi_status = BMI_SUCCESS
  end function

  function encflow_get_double(this, name, dest) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    character(len=*), intent(in) :: name
    double precision, intent(inout) :: dest(:)
    integer :: bmi_status
    character(len=8) :: iname
    integer :: ierr, nx, ny
    double precision :: dx, dy, x0, y0
    real, allocatable :: buf(:,:)
    call var_internal(name, iname, ierr)
    if (ierr /= 0) then
      bmi_status = BMI_FAILURE
      return
    end if
    call m_main_get_gridinfo(nx, ny, dx, dy, x0, y0)
    if (size(dest) /= nx*ny) then
      bmi_status = BMI_FAILURE
      return
    end if
    allocate(buf(nx, ny))
    call m_main_get_value(iname, buf, ierr)
    if (ierr /= 0) then
      bmi_status = BMI_FAILURE
      return
    end if
    ! flatten + 行反転(内部 j=1=北 → BMI 標準形 要素0=南西。ヘッダ参照)
    dest = reshape(dble(buf(:, ny:1:-1)), [nx*ny])
    bmi_status = BMI_SUCCESS
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
  ! 強制場の所有権設計(bmi_plan.md §4.2)が済むまで set は非対応

  function encflow_set_int(this, name, src) result(bmi_status)
    class(encflow_bmi), intent(inout) :: this
    character(len=*), intent(in) :: name
    integer, intent(in) :: src(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_set_float(this, name, src) result(bmi_status)
    class(encflow_bmi), intent(inout) :: this
    character(len=*), intent(in) :: name
    real, intent(in) :: src(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE
  end function

  function encflow_set_double(this, name, src) result(bmi_status)
    class(encflow_bmi), intent(inout) :: this
    character(len=*), intent(in) :: name
    double precision, intent(in) :: src(:)
    integer :: bmi_status
    bmi_status = BMI_FAILURE
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

  function encflow_grid_rank(this, grid, rank) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    integer, intent(out) :: rank
    integer :: bmi_status
    if (grid /= 0) then
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
    if (grid /= 0) then
      size = 0
      bmi_status = BMI_FAILURE
      return
    end if
    call m_main_get_gridinfo(nx, ny, dx, dy, x0, y0)
    size = nx * ny
    bmi_status = BMI_SUCCESS
  end function

  function encflow_grid_type(this, grid, type) result(bmi_status)
    class(encflow_bmi), intent(in) :: this
    integer, intent(in) :: grid
    character(len=*), intent(out) :: type
    integer :: bmi_status
    if (grid /= 0) then
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
    if (grid /= 0 .or. size(shape) < 2) then
      bmi_status = BMI_FAILURE
      return
    end if
    call m_main_get_gridinfo(nx, ny, dx, dy, x0, y0)
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
    if (grid /= 0 .or. size(spacing) < 2) then
      bmi_status = BMI_FAILURE
      return
    end if
    call m_main_get_gridinfo(nx, ny, dx, dy, x0, y0)
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
    if (grid /= 0 .or. size(origin) < 2) then
      bmi_status = BMI_FAILURE
      return
    end if
    call m_main_get_gridinfo(nx, ny, dx, dy, x0, y0)
    origin(1:2) = [y0, x0]            ! shape と同順([y, x]。georef 未管理なら 0)
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
