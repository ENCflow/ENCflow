!======================================================================
! uplift: 規定の底面運動(Hammack 型の区間隆起)をライブラリ API で与える
!   ドライバ(docs/nonhydrostatic_plan.md §16.4-1。計算本体の外)。
!     ./uplift param.txt [uplift.txt]
!   毎ステップの更新前に m_main_set_value('z') で底面 z(x, t) を
!   ステージングし(適用は update 冒頭)、|x − xc| < bh の区間を
!     z = z0 + zeta0 · r(t),  r(t) = (1 − cos(π t/tc))/2 (t < tc), 1 (t ≥ tc)
!   で持ち上げる。水柱 h は変えない(geomorph と同じ契約)ので水面
!   e = z + h がそのまま持ち上がる。MPI では全ランクが同じ呼び出しを
!   行い、z の値は rank0 のものが使われる(set_value の契約)。
!======================================================================
program uplift
  use m_main, only : m_main_initialize, m_main_update, m_main_finished, m_main_finalize, &
                     m_main_get_timeinfo, m_main_get_gridinfo, m_main_get_value, &
                     m_main_set_value, m_main_get_ierror
  use m_parallel, only : is_root, par_stop, par_info
  implicit none
  real, parameter :: pi = 3.14159265358979323846
  real :: xc = 500.0            ! 隆起区間の中心 x (m)
  real :: bh = 20.0             ! 隆起区間の半幅 b (m)
  real :: zeta0 = 0.2           ! 隆起量 ζ0 (m)
  real :: tc = 1.0              ! 隆起時間 t_c (s)
  namelist /list_uplift/ xc, bh, zeta0, tc
  character(len=256) :: fn_param, fn_up
  integer :: nx, ny, i, j, ierr, un, ios
  double precision :: t, t0, tend, dt, dx, dy, xll, yll
  real, allocatable :: z0(:,:), z(:,:)
  real :: r, x, tt

  if (command_argument_count() < 1) then
    print *, "usage: uplift param.txt [uplift.txt]"
    stop 2
  end if
  call get_command_argument(1, fn_param)
  fn_up = 'uplift.txt'
  if (command_argument_count() >= 2) call get_command_argument(2, fn_up)

  call m_main_initialize(fn_param)

  open(newunit=un, file=fn_up, status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("uplift: cannot open "//trim(fn_up))
  read(un, nml=list_uplift, iostat=ios)
  if (ios /= 0) call par_stop("uplift: cannot read namelist list_uplift from "//trim(fn_up))
  close(un)
  if (tc <= 0.0) call par_stop("uplift: tc must be > 0")

  call m_main_get_gridinfo(nx, ny, dx, dy, xll, yll)
  allocate(z0(nx, ny), z(nx, ny))
  call m_main_get_value('z', z0, ierr)
  if (ierr /= 0) call par_stop("uplift: get_value('z') failed")
  call par_info("uplift: xc = "//trim(r2s(xc))//" m, b = "//trim(r2s(bh))//" m, zeta0 = "// &
                trim(r2s(zeta0))//" m, tc = "//trim(r2s(tc))//" s")

  do while (.not. m_main_finished())
    call m_main_get_timeinfo(t, t0, tend, dt)
    tt = real(t + dt - t0)                 ! このステップの末尾の時刻で z を与える
    if (tt < tc) then
      r = 0.5 * (1.0 - cos(pi * tt / tc))
    else
      r = 1.0
    end if
    if (is_root) then
      do j = 1, ny
        do i = 1, nx
          x = (real(i) - 0.5) * real(dx)
          z(i,j) = z0(i,j)
          if (abs(x - xc) < bh) z(i,j) = z0(i,j) + zeta0 * r
        end do
      end do
    end if
    call m_main_set_value('z', z, ierr)
    if (ierr /= 0) call par_stop("uplift: set_value('z') refused (ierr = "//trim(r2s(real(ierr)))//")")
    call m_main_update()
  end do

  call m_main_finalize()
  if (m_main_get_ierror() > 0) stop 1

contains

  function r2s(v) result(s)
    real, intent(in) :: v
    character(len=32) :: s
    write(s, '(g0.6)') v
  end function

end program
