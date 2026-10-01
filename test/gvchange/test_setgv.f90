program test_setgv
  ! 空隙率変更手続き m_state_set_gv の単体検定(developer.md §63.1 A2)
  !   小さな帯状態を直接組み立てて手続きを呼び、
  !     (1) 体積保存: 柱状量 × gv が全量(h, hs, hrs, hd, cq, hss)で変更前後に
  !         機械精度(相対 1e-15)で一致する
  !     (2) 導出量: lm = gv + (1−gv)·cm、e = z + h、af が gv の因子だけ比例する
  !     (3) 無変更セルは不変、gv_new == gv_old は no-op(ビット不変)
  !     (4) 未確保の任意台帳(wd, hbd 等)があっても落ちない(allocated 判定)
  !   を検定する。計算本体(時間ループ)は回さない。
  use m_sysparam, only : t_sysparam
  use m_state, only : t_state, m_state_set_gv
  implicit none
  type(t_sysparam) :: p
  type(t_state) :: s
  integer, parameter :: nx = 3, ny = 3
  integer :: i, j, nfail
  real :: v0(nx,ny), v0s(nx,ny), v0r(nx,ny), v0d(nx,ny), v0c(nx,ny), v0ss(nx,ny)
  real :: h_keep, gv_keep, lm_keep, af_keep, e_keep
  real :: cm, tol

  nfail = 0
  cm = 2.0
  p%cm = cm
  tol = 1.0e-14

  allocate(s%h(nx,ny), s%hs(nx,ny), s%hrs(nx,ny), s%gv(nx,ny), s%lm(nx,ny), s%af(nx,ny), &
           s%e(nx,ny), s%z(nx,ny), s%hd(nx,ny), s%cq(nx,ny), s%hss(nx,ny))
  do j = 1, ny
    do i = 1, nx
      s%z(i,j) = 0.1 * i - 0.05 * j
      s%h(i,j) = 1.234 + 0.01 * i + 0.001 * j
      s%hs(i,j) = 0.0123 * i
      s%hrs(i,j) = 0.5 * j
      s%hd(i,j) = 0.02 + 0.001 * i
      s%cq(i,j) = 12.5 * j
      s%hss(i,j) = 0.3
      s%gv(i,j) = 0.7 - 0.05 * i + 0.02 * j
      s%lm(i,j) = s%gv(i,j) + (1.0 - s%gv(i,j)) * cm
      s%af(i,j) = s%gv(i,j) * 0.8         ! 河道幅・湿潤率の因子 0.8 を仮置き
      s%e(i,j) = s%z(i,j) + s%h(i,j)
    end do
  end do
  v0 = s%h * s%gv;  v0s = s%hs * s%gv;  v0r = s%hrs * s%gv
  v0d = s%hd * s%gv;  v0c = s%cq * s%gv;  v0ss = s%hss * s%gv

  ! --- (3) no-op: gv_new == gv_old はビット不変 ---
  h_keep = s%h(2,2); gv_keep = s%gv(2,2); lm_keep = s%lm(2,2); af_keep = s%af(2,2); e_keep = s%e(2,2)
  call m_state_set_gv(p, s, 2, 2, s%gv(2,2))
  if (s%h(2,2) /= h_keep .or. s%gv(2,2) /= gv_keep .or. s%lm(2,2) /= lm_keep &
      .or. s%af(2,2) /= af_keep .or. s%e(2,2) /= e_keep) then
    print '(a)', "(3) no-op          : FAIL (state changed for gv_new == gv_old)"
    nfail = nfail + 1
  else
    print '(a)', "(3) no-op          : PASS"
  end if

  ! --- 中央セルと隅セルの gv を上げる ---
  call m_state_set_gv(p, s, 2, 2, 0.95)
  call m_state_set_gv(p, s, 1, 3, 1.0)

  ! --- (1) 体積保存(変更セル)と不変(他セル) ---
  do j = 1, ny
    do i = 1, nx
      call chk("h   ", i, j, s%h(i,j) * s%gv(i,j), v0(i,j))
      call chk("hs  ", i, j, s%hs(i,j) * s%gv(i,j), v0s(i,j))
      call chk("hrs ", i, j, s%hrs(i,j) * s%gv(i,j), v0r(i,j))
      call chk("hd  ", i, j, s%hd(i,j) * s%gv(i,j), v0d(i,j))
      call chk("cq  ", i, j, s%cq(i,j) * s%gv(i,j), v0c(i,j))
      call chk("hss ", i, j, s%hss(i,j) * s%gv(i,j), v0ss(i,j))
    end do
  end do
  if (s%gv(2,2) /= 0.95 .or. s%gv(1,3) /= 1.0 .or. s%gv(3,1) /= 0.7 - 0.15 + 0.02) then
    print '(a)', "(1) gv values      : FAIL"
    nfail = nfail + 1
  end if
  print '(a,i0,a)', "(1) volume balance : ", nfail, " failure(s) so far (0 = PASS)"

  ! --- (2) 導出量 ---
  do j = 1, ny
    do i = 1, nx
      call chk("lm  ", i, j, s%lm(i,j), s%gv(i,j) + (1.0 - s%gv(i,j)) * cm)
      call chk("e   ", i, j, s%e(i,j), s%z(i,j) + s%h(i,j))
      call chk("af  ", i, j, s%af(i,j), s%gv(i,j) * 0.8)
    end do
  end do
  print '(a,i0,a)', "(2) derived fields : ", nfail, " failure(s) so far (0 = PASS)"

  if (nfail == 0) then
    print '(a)', "== gvchange 検定: PASS =="
  else
    print '(a,i0,a)', "== gvchange 検定: FAIL (", nfail, " checks) =="
    error stop 1
  end if

contains

  subroutine chk(label, i, j, a, b)
    character(len=*), intent(in) :: label
    integer, intent(in) :: i, j
    real, intent(in) :: a, b
    real :: d
    d = abs(a - b)
    if (d > tol * max(abs(a), abs(b), 1.0e-30)) then
      print '(a,a,2i3,2es24.16)', "    FAIL ", label, i, j, a, b
      nfail = nfail + 1
    end if
  end subroutine

end program
