!======================================================================
! nestcheck: 比 1:1・r_t=1 の自己ネスト恒等テスト(nesting_plan §9 の 4)
!   ./nestcheck cut  param_single.txt i0 j0 nxc nyc out.txt
!       単独格子を initialize し、初期水深 h の部分窓(親セル i0..i0+nxc-1 ×
!       j0..j0+nyc-1)を全有効桁(17 桁)で out.txt に書く(子の初期条件
!       fn_hinit。list-directed 読みで同一ビットに戻る)
!   ./nestcheck run  param_root.txt i0 j0 nb
!       ネスト系(ルート + 子 1 つ)を initialize → update ループで進め、
!       各ステップ後に子の内部(帯 nb を除く)の h, vv がルートの足元と
!       ビット一致するかを検査する(get_value の全域配列で比較)。
!       一方向では親は子の影響を受けないので、子の内部 == 親の同領域が
!       補間と帯の完全性の証明になる。MPI では全ランクが同じ呼び出しを行い
!       差の最大値を allreduce で共有する(終了コードが全ランクで一致)
!======================================================================
program nestcheck
  use m_main, only : m_main_initialize, m_main_update, m_main_finished, m_main_finalize, &
                     m_main_get_gridinfo, m_main_get_value, m_main_select, m_main_get_timeinfo
  use m_parallel, only : is_root, par_stop, par_info, par_allreduce_max
  implicit none
  character(len=256) :: mode, fn_param, fn_out, arg
  integer :: i0, j0, nxc, nyc, nb, ierr, un, i, j, nxp, nyp, nstep, nbad
  double precision :: dxp, dyp, xll, yll, t, t0, tend, dt
  real, allocatable :: hp(:,:), hc(:,:), vp(:,:), vc(:,:)
  real :: dmax_h, dmax_v, worst_h, worst_v
  character(len=256) :: msg

  if (command_argument_count() < 2) then
    print *, "usage: nestcheck cut param_single.txt i0 j0 nxc nyc out.txt | nestcheck run param_root.txt i0 j0 nb"
    stop 2
  end if
  call get_command_argument(1, mode)
  call get_command_argument(2, fn_param)

  select case (trim(mode))
  case ('cut')
    if (command_argument_count() < 7) stop 2
    call get_command_argument(3, arg); read(arg, *) i0
    call get_command_argument(4, arg); read(arg, *) j0
    call get_command_argument(5, arg); read(arg, *) nxc
    call get_command_argument(6, arg); read(arg, *) nyc
    call get_command_argument(7, fn_out)
    call m_main_initialize(fn_param)
    call m_main_get_gridinfo(nxp, nyp, dxp, dyp, xll, yll)
    allocate(hp(nxp, nyp))
    call m_main_get_value('h', hp, ierr)
    if (ierr /= 0) call par_stop("nestcheck: get_value('h') failed")
    if (is_root) then
      open(newunit=un, file=trim(fn_out), status='replace', action='write')
      do j = j0, j0 + nyc - 1
        write(un, '(*(es24.17))') (hp(i, j), i = i0, i0 + nxc - 1)
      end do
      close(un)
      print '(a,i0,a,i0,a,a)', "nestcheck: wrote initial depth window ", nxc, " x ", nyc, " to ", trim(fn_out)
    end if
    call m_main_finalize()

  case ('run')
    if (command_argument_count() < 5) stop 2
    call get_command_argument(3, arg); read(arg, *) i0
    call get_command_argument(4, arg); read(arg, *) j0
    call get_command_argument(5, arg); read(arg, *) nb
    call m_main_initialize(fn_param)          ! ルート + 子(fn_nest)
    call m_main_select(1)
    call m_main_get_gridinfo(nxp, nyp, dxp, dyp, xll, yll)
    call m_main_select(2)
    call m_main_get_gridinfo(nxc, nyc, dxp, dyp, xll, yll)
    call m_main_select(1)
    allocate(hp(nxp, nyp), vp(nxp, nyp), hc(nxc, nyc), vc(nxc, nyc))
    worst_h = 0.0; worst_v = 0.0; nstep = 0; nbad = 0
    call compare(dmax_h, dmax_v)
    call report(0, dmax_h, dmax_v)
    do while (.not. m_main_finished())
      call m_main_update()
      nstep = nstep + 1
      call compare(dmax_h, dmax_v)
      call m_main_get_timeinfo(t, t0, tend, dt)
      if (dmax_h > 0.0 .or. dmax_v > 0.0) nbad = nbad + 1
      worst_h = max(worst_h, dmax_h)
      worst_v = max(worst_v, dmax_v)
      if (mod(nstep, 20) == 0 .or. dmax_h > 0.0 .or. dmax_v > 0.0) call report(nstep, dmax_h, dmax_v)
    end do
    call m_main_finalize()
    if (is_root) then
      write(msg, '(a,i0,a,i0,a,es10.3,a,es10.3)') "nestcheck: steps = ", nstep, ", steps with mismatch = ", nbad, &
            ", max |dh| = ", worst_h, ", max |dvv| = ", worst_v
      print '(a)', trim(msg)
      if (nbad == 0) then
        print '(a)', "nestcheck: child interior == parent footprint at every step (IDENTICAL)"
        print '(a)', "=== nest identity PASS ==="
      else
        print '(a)', "=== nest identity FAIL ==="
      end if
    end if
    if (nbad > 0) stop 1
  case default
    print *, "nestcheck: unknown mode "//trim(mode)
    stop 2
  end select

contains

  subroutine compare(dh, dv)
    real, intent(out) :: dh, dv
    integer :: ic, jc, ip, jp
    real :: dvec(2)
    call m_main_select(1)
    call m_main_get_value('h', hp, ierr)
    call m_main_get_value('vv', vp, ierr)
    call m_main_select(2)
    call m_main_get_value('h', hc, ierr)
    call m_main_get_value('vv', vc, ierr)
    call m_main_select(1)
    dh = 0.0; dv = 0.0
    if (is_root) then
      do jc = nb + 1, nyc - nb
        jp = j0 + jc - 1
        do ic = nb + 1, nxc - nb
          ip = i0 + ic - 1
          dh = max(dh, abs(hc(ic, jc) - hp(ip, jp)))
          dv = max(dv, abs(vc(ic, jc) - vp(ip, jp)))
        end do
      end do
    end if
    dvec(1) = dh; dvec(2) = dv
    call par_allreduce_max(dvec)
    dh = dvec(1); dv = dvec(2)
  end subroutine

  subroutine report(n, dh, dv)
    integer, intent(in) :: n
    real, intent(in) :: dh, dv
    if (.not. is_root) return
    write(msg, '(a,i6,a,es10.3,a,es10.3)') "nestcheck: step ", n, "  max|dh| = ", dh, "  max|dvv| = ", dv
    print '(a)', trim(msg)
  end subroutine

end program
