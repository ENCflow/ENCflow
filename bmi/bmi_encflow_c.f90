!======================================================================
! bmi_encflow_c: BMI アダプタの C 相互運用層(bind(c))
!
!   bmi_encflow(bmif_2_0 実装)を C 互換シンボルとして公開し、
!   Python(ctypes)等から共有ライブラリ経由で呼べるようにする。
!   言語標準(iso_c_binding)のみで書かれ、外部依存はない
!   (bmi_plan.md §4.3 軽量ルート。babelizer が生成する相互運用層と
!   同種の定型コードを ENCflow 側で提供する、という位置づけ)。
!
!   規約:
!   - 全関数が BMI status(0 = 成功、1 = 失敗)を返す。
!   - 文字列入力は NULL 終端の C 文字列。
!   - 配列は flatten 1 次元・c_double(PREC=single ビルドでも受け渡しは
!     c_double に統一し、内部で変換する)。
!   - モデルは単一インスタンス(m_main の singleton に対応)。
!   - 公開するのは Python 利用に必要な実用サブセット。完全な BMI-C
!     互換(babelizer 互換)が必要になったら拡張する。
!======================================================================
module bmi_encflow_c
  use, intrinsic :: iso_c_binding, only : c_char, c_int, c_double, c_null_char
  use bmif_2_0, only : BMI_SUCCESS, BMI_FAILURE, BMI_MAX_COMPONENT_NAME, &
                       BMI_MAX_VAR_NAME
  use bmi_encflow, only : encflow_bmi
  implicit none
  private

  ! 単一インスタンス(m_main 側も singleton のため 1 プロセス 1 モデル)
  type(encflow_bmi), save :: model

contains

  !--------------------------------------------------------------------
  ! NULL 終端 C 文字列 → Fortran 文字列
  !--------------------------------------------------------------------
  subroutine c_to_f_string(cstr, fstr)
    character(kind=c_char), intent(in) :: cstr(*)
    character(len=:), allocatable, intent(out) :: fstr
    integer, parameter :: maxlen = 4096
    integer :: n, i
    n = 0
    do while (n < maxlen)
      if (cstr(n+1) == c_null_char) exit
      n = n + 1
    end do
    allocate(character(len=n) :: fstr)
    do i = 1, n
      fstr(i:i) = cstr(i)
    end do
  end subroutine c_to_f_string

  !--------------------------------------------------------------------
  ! Fortran 文字列 → NULL 終端 C 文字列(dest(n) に収まる分だけ)
  !--------------------------------------------------------------------
  subroutine f_to_c_string(fstr, dest, n)
    character(len=*), intent(in) :: fstr
    character(kind=c_char), intent(out) :: dest(*)
    integer(c_int), intent(in) :: n
    integer :: m, i
    m = min(len_trim(fstr), int(n) - 1)
    do i = 1, m
      dest(i) = fstr(i:i)
    end do
    dest(m+1) = c_null_char
  end subroutine f_to_c_string

  !===================== Initialize, run, finalize =====================

  function ebmi_initialize(config) bind(c, name="encflow_bmi_initialize") &
      result(status)
    character(kind=c_char), intent(in) :: config(*)
    integer(c_int) :: status
    character(len=:), allocatable :: fn
    call c_to_f_string(config, fn)
    status = int(model%initialize(fn), c_int)
  end function

  function ebmi_update() bind(c, name="encflow_bmi_update") result(status)
    integer(c_int) :: status
    status = int(model%update(), c_int)
  end function

  function ebmi_update_until(t) bind(c, name="encflow_bmi_update_until") &
      result(status)
    real(c_double), value :: t
    integer(c_int) :: status
    status = int(model%update_until(dble(t)), c_int)
  end function

  function ebmi_finalize() bind(c, name="encflow_bmi_finalize") result(status)
    integer(c_int) :: status
    status = int(model%finalize(), c_int)
  end function

  !========================== Model information ========================

  function ebmi_get_component_name(dest, n) &
      bind(c, name="encflow_bmi_get_component_name") result(status)
    character(kind=c_char), intent(out) :: dest(*)
    integer(c_int), value :: n
    integer(c_int) :: status
    character(len=BMI_MAX_COMPONENT_NAME), pointer :: cname
    status = int(model%get_component_name(cname), c_int)
    if (status == BMI_SUCCESS) call f_to_c_string(cname, dest, n)
  end function

  function ebmi_get_output_item_count(count) &
      bind(c, name="encflow_bmi_get_output_item_count") result(status)
    integer(c_int), intent(out) :: count
    integer(c_int) :: status
    integer :: c
    status = int(model%get_output_item_count(c), c_int)
    count = int(c, c_int)
  end function

  function ebmi_get_output_var_name(i, dest, n) &
      bind(c, name="encflow_bmi_get_output_var_name") result(status)
    ! i 番目(1 始まり)の出力変数名を返す
    integer(c_int), value :: i
    character(kind=c_char), intent(out) :: dest(*)
    integer(c_int), value :: n
    integer(c_int) :: status
    character(len=BMI_MAX_VAR_NAME), pointer :: names(:)
    integer :: c
    status = int(model%get_output_item_count(c), c_int)
    if (status /= BMI_SUCCESS) return
    if (i < 1 .or. i > c) then
      status = int(BMI_FAILURE, c_int)
      return
    end if
    status = int(model%get_output_var_names(names), c_int)
    if (status == BMI_SUCCESS) call f_to_c_string(names(i), dest, n)
  end function

  !========================= Time information ==========================

  function ebmi_get_current_time(t) &
      bind(c, name="encflow_bmi_get_current_time") result(status)
    real(c_double), intent(out) :: t
    integer(c_int) :: status
    double precision :: tt
    status = int(model%get_current_time(tt), c_int)
    t = real(tt, c_double)
  end function

  function ebmi_get_start_time(t) &
      bind(c, name="encflow_bmi_get_start_time") result(status)
    real(c_double), intent(out) :: t
    integer(c_int) :: status
    double precision :: tt
    status = int(model%get_start_time(tt), c_int)
    t = real(tt, c_double)
  end function

  function ebmi_get_end_time(t) &
      bind(c, name="encflow_bmi_get_end_time") result(status)
    real(c_double), intent(out) :: t
    integer(c_int) :: status
    double precision :: tt
    status = int(model%get_end_time(tt), c_int)
    t = real(tt, c_double)
  end function

  function ebmi_get_time_step(dt) &
      bind(c, name="encflow_bmi_get_time_step") result(status)
    real(c_double), intent(out) :: dt
    integer(c_int) :: status
    double precision :: d
    status = int(model%get_time_step(d), c_int)
    dt = real(d, c_double)
  end function

  !========================= Grid information ==========================

  function ebmi_get_grid_shape(ny, nx) &
      bind(c, name="encflow_bmi_get_grid_shape") result(status)
    integer(c_int), intent(out) :: ny, nx
    integer(c_int) :: status
    integer :: shp(2)
    status = int(model%get_grid_shape(0, shp), c_int)
    ny = int(shp(1), c_int)
    nx = int(shp(2), c_int)
  end function

  function ebmi_get_grid_spacing(dy, dx) &
      bind(c, name="encflow_bmi_get_grid_spacing") result(status)
    real(c_double), intent(out) :: dy, dx
    integer(c_int) :: status
    double precision :: sp(2)
    status = int(model%get_grid_spacing(0, sp), c_int)
    dy = real(sp(1), c_double)
    dx = real(sp(2), c_double)
  end function

  function ebmi_get_grid_origin(y0, x0) &
      bind(c, name="encflow_bmi_get_grid_origin") result(status)
    real(c_double), intent(out) :: y0, x0
    integer(c_int) :: status
    double precision :: og(2)
    status = int(model%get_grid_origin(0, og), c_int)
    y0 = real(og(1), c_double)
    x0 = real(og(2), c_double)
  end function

  function ebmi_get_grid_size(n) &
      bind(c, name="encflow_bmi_get_grid_size") result(status)
    integer(c_int), intent(out) :: n
    integer(c_int) :: status
    integer :: sz
    status = int(model%get_grid_size(0, sz), c_int)
    n = int(sz, c_int)
  end function

  !=========================== Get values ==============================

  function ebmi_get_value_double(name, dest, n) &
      bind(c, name="encflow_bmi_get_value_double") result(status)
    ! flatten した全域場のコピー(c_double 固定。PREC=single でも
    ! この口は倍精度で受け渡し、内部で変換する)
    character(kind=c_char), intent(in) :: name(*)
    integer(c_int), value :: n
    real(c_double), intent(inout) :: dest(n)
    integer(c_int) :: status
    character(len=:), allocatable :: fname
    double precision, allocatable :: buf(:)
    call c_to_f_string(name, fname)
    allocate(buf(n))
    status = int(model%get_value_double(fname, buf), c_int)
    if (status == int(BMI_SUCCESS, c_int)) dest = real(buf, c_double)
  end function

end module bmi_encflow_c
