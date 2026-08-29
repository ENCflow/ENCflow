!======================================================================
! test_bmi: BMI アダプタの検証ドライバ(逐次)
!
!   ENCflow のケースを BMI 経由で最後まで実行する。呼び出し列は
!   initialize → update×nt → finalize となり、既存 CLI(m_main_all)と
!   同一のため、result/Log.txt は既存 reference とビット一致するはず
!   (= BMI 経由の等価性検証。test/<case> ディレクトリで実行し、
!   Compare_ref.sh で比較する)。
!
!   併せて以下を検査する(不合格なら非零終了):
!   - 格子情報の整合(size = nx*ny、shape は [ny, nx] 順)
!   - get_value の flatten 順序(2つの取得法の一致)と時間情報
!   - 誤用が BMI_FAILURE になること(未知変数・サイズ不一致・過去への
!     update_until・終了後の update)
!
!   使い方:  ./test_encflow_bmi param.txt [set]
!     第2引数 set: 中間時点で get した h・z をそのまま set して継続する
!     (同値 set の不変性 = Log は set なしと一致するはず。z の set は
!     z 更新プロセスが無効なケースでのみ使えることに注意)。
!     MPI 版(test_encflow_bmi_mpi)は mpirun で全ランク起動する。
!======================================================================
program test_bmi
  use bmif_2_0
  use bmi_encflow, only : encflow_bmi
  implicit none

  type(encflow_bmi) :: model
  character(len=256) :: fn
  character(len=BMI_MAX_COMPONENT_NAME), pointer :: cname
  character(len=BMI_MAX_VAR_NAME), pointer :: onames(:)
  character(len=BMI_MAX_UNITS_NAME) :: units
  integer :: i, nx, ny, gsize, nstep, nhalf, icount, ocount
  logical :: do_set        ! 同値 set の不変性検査を行うか(第2引数 'set')
  integer :: shp(2)
  double precision :: t, t0, tend, dt
  double precision :: spacing(2), origin(2)
  double precision, allocatable :: h(:), z(:)
  double precision, allocatable :: hbad(:)

  if (command_argument_count() < 1) then
    write(*, '(a)') "usage: test_encflow_bmi parameterfile [set]"
    stop 2
  end if
  call get_command_argument(1, fn)
  do_set = .false.
  if (command_argument_count() >= 2) then
    getopt: block
      character(len=16) :: arg2
      call get_command_argument(2, arg2)
      do_set = (trim(arg2) == "set")
    end block getopt
  end if

  ! ---- initialize と基本情報 ----
  call chk(model%initialize(trim(fn)), "initialize")
  call chk(model%get_component_name(cname), "get_component_name")
  call chk(model%get_input_item_count(icount), "get_input_item_count")
  call chk(model%get_output_item_count(ocount), "get_output_item_count")
  call chk(model%get_output_var_names(onames), "get_output_var_names")
  write(*, '(a,a)') "bmi: component = ", trim(cname)
  write(*, '(a,i0,a,i0)') "bmi: input vars = ", icount, ", output vars = ", ocount
  do i = 1, ocount
    call chk(model%get_var_units(trim(onames(i)), units), "get_var_units")
    write(*, '(a,a,a,a,a)') "bmi:   output: ", trim(onames(i)), " [", trim(units), "]"
  end do

  ! ---- 格子情報の整合 ----
  call chk(model%get_grid_shape(0, shp), "get_grid_shape")
  call chk(model%get_grid_size(0, gsize), "get_grid_size")
  call chk(model%get_grid_spacing(0, spacing), "get_grid_spacing")
  call chk(model%get_grid_origin(0, origin), "get_grid_origin")
  ny = shp(1)
  nx = shp(2)
  write(*, '(a,i0,a,i0,a,i0)') "bmi: grid shape [ny, nx] = ", ny, " x ", nx, ", size = ", gsize
  write(*, '(a,2f12.3)') "bmi: grid spacing [dy, dx] = ", spacing
  write(*, '(a,2f14.3)') "bmi: grid origin  [y0, x0] = ", origin
  if (gsize /= nx * ny) call die("grid size /= nx*ny")

  ! ---- 時間情報 ----
  call chk(model%get_start_time(t0), "get_start_time")
  call chk(model%get_end_time(tend), "get_end_time")
  call chk(model%get_time_step(dt), "get_time_step")
  nstep = nint((tend - t0) / dt)
  write(*, '(a,f10.3,a,f12.3,a,f8.4,a,i0)') &
    "bmi: t0 = ", t0, ", tend = ", tend, ", dt = ", dt, ", nsteps = ", nstep

  allocate(h(gsize), z(gsize))

  ! ---- 誤用の検査(FAILURE が返ること。状態は変更されない) ----
  call chkf(model%get_value_double("no_such__variable", h), "get unknown name")
  allocate(hbad(gsize - 1))
  call chkf(model%get_value_double("surface_water__depth", hbad), "get with wrong size")
  call chkf(model%update_until(t0 - dt), "update_until into the past")
  call chkf(model%set_value_double("no_such__variable", h), "set unknown name")
  call chkf(model%set_value_double("surface_water__depth", hbad), "set h with wrong size")
  call chkf(model%set_value_double( &
    "atmosphere_water__precipitation_leq-volume_flux", hbad), "set pre with wrong size")

  ! ---- 前半は update_until、後半は update で最後まで進める ----
  nhalf = nstep / 2
  call chk(model%update_until(t0 + dt * dble(nhalf)), "update_until (half)")
  call chk(model%get_current_time(t), "get_current_time")
  call chk(model%get_value_double("surface_water__depth", h), "get_value h")
  write(*, '(a,f10.3,a,es13.6,a,i0)') &
    "bmi: t = ", t, "  max h = ", maxval(h), "  at flat index ", maxloc(h, dim=1)

  ! ---- 同値 set の不変性(第2引数 'set' 指定時のみ) ----
  ! いま get した h・z をそのまま set して継続する。結果(Log)は
  ! set なしの実行と一致するはず。MPI では get の有効値は rank0 のみ、
  ! set の scatter 元も rank0 なので、このまま全ランクで呼べばよい
  if (do_set) then
    call chk(model%get_value_double("land_surface__elevation", z), "get_value z (half)")
    call chk(model%set_value_double("land_surface__elevation", z), "set z (same value)")
    call chk(model%set_value_double("surface_water__depth", h), "set h (same value)")
    write(*, '(a)') "bmi: same-value set of h and z staged (invariance check)"
  end if

  do
    call chk(model%get_current_time(t), "get_current_time")
    if (t >= tend) exit
    call chk(model%update(), "update")
  end do

  ! ---- 終了時刻到達後の update は FAILURE ----
  call chkf(model%update(), "update beyond end time")

  call chk(model%get_value_double("surface_water__depth", h), "get_value h (final)")
  call chk(model%get_value_double("land_surface__elevation", z), "get_value z")
  write(*, '(a,f10.3)') "bmi: final t = ", t
  write(*, '(a,es13.6,a,es13.6)') "bmi: final max h = ", maxval(h), &
    ",  max z = ", maxval(z)
  ! 速さと流速成分(導出量)の整合: max|(ux,uy)| <= max vv(+丸め)
  call chk(model%get_value_double("surface_water_flow__speed", z), "get_value speed")
  call chk(model%get_value_double("surface_water__x_component_of_velocity", h), &
           "get_value ux")
  write(*, '(a,es13.6,a,es13.6)') "bmi: final max speed = ", maxval(z), &
    ",  max |ux| = ", maxval(abs(h))
  if (maxval(abs(h)) > maxval(z) * (1.0d0 + 1.0d-12)) call die("|ux| exceeds speed")

  call chk(model%finalize(), "finalize")
  write(*, '(a)') "bmi: all checks passed"

contains

  subroutine chk(status, what)
    integer, intent(in) :: status
    character(len=*), intent(in) :: what
    if (status /= BMI_SUCCESS) then
      write(*, '(a,a,a,i0,a)') "bmi: FAILED: ", what, " (status = ", status, ")"
      stop 1
    end if
  end subroutine chk

  subroutine chkf(status, what)
    ! 誤用が BMI_FAILURE になることの検査
    integer, intent(in) :: status
    character(len=*), intent(in) :: what
    if (status /= BMI_FAILURE) then
      write(*, '(a,a,a,i0,a)') "bmi: FAILED (expected failure): ", what, &
        " (status = ", status, ")"
      stop 1
    end if
  end subroutine chkf

  subroutine die(what)
    character(len=*), intent(in) :: what
    write(*, '(a,a)') "bmi: FAILED: ", what
    stop 1
  end subroutine die

end program test_bmi
