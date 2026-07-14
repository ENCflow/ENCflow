!**********************************************************************
!
! 摩擦項の計算に必要な 1/h^(4/3) または 1/h^(7/3) を計算する
!
!**********************************************************************
module m_ffactor
  use m_parallel, only : par_stop
  implicit none
  private

  !--------------------------------------------------------------------
  ! パブリックルーチンの宣言
  !--------------------------------------------------------------------
  public :: m_ffactor_init
  public :: m_ffactor_calc
  public :: m_ffactor_dispose


  !--------------------------------------------------------------------
  ! モジュール内の共有変数
  !--------------------------------------------------------------------
  ! 摩擦項中の水深のべき乗 (4/3 または 7/3)
  real :: powf

  ! 高速摩擦項計算のためのテーブルの宣言と定義
  integer :: ff_nn                           ! テーブルのサイズ
  real, allocatable :: ff_h(:)               ! 水深
  real, allocatable :: ff_f(:)               ! 1/h^(4/3) または 1/h^(7/3)
  real, allocatable :: ff_a0(:)              ! h(i)からh(i+1/2)までの近似直線の傾き
  real, allocatable :: ff_a1(:)              ! h(i+1/2)からh(i+1)までの近似直線の傾き

  ! 高速摩擦項計算ルーチンの切り替えためのインターフェース宣言とポインタの定義
  interface
    function procedure_ffactor(h) result(f)
      real, intent(in) :: h
      real :: f
    end function
  end interface
  procedure(procedure_ffactor), pointer :: p_ffactor => ffactor_uninitialized


contains
 
!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_ffactor_init(level, hmin, hmax, mode)
  integer, intent(in) :: level
  real, intent(in) :: hmin, hmax
  character(len=2), intent(in) :: mode
  character(len=256) :: msg

  if (mode == 'uv' .or. mode == 'UV') then
    powf = 4. / 3.
  else if (mode == 'mn' .or. mode == 'MN') then
    powf = 7. / 3.
  else
    write(msg,'(a,i0)') "ffactor_init: unknown mode", mode
    call par_stop(msg)
  end if

  if (hmin <= 0) then
    write(msg,'(a,i0)') "ffactor_init: hmin is out of range", hmin
    call par_stop(msg)
  end if
  if (hmax <= hmin) then
    write(msg,'(a,i0)') "ffactor_init: hmax is out of range", hmax
    call par_stop(msg)
  end if

  if (level < 0 .or. level > 5) then
    write(msg,'(a,i0)') "ffactor_init: level is out of range", level
    call par_stop(msg)
  end if

  if (level > 0) then
    p_ffactor => ffactor_fast
    call init_ffactor_fast(level, hmin, hmax)
  else
    p_ffactor => ffactor_strict
  end if
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
function m_ffactor_calc(h) result(f)
  real, intent(in) :: h
  real :: f
  f = p_ffactor(h)
end function


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine m_ffactor_dispose
  if (allocated(ff_h)) deallocate(ff_h)
  if (allocated(ff_f)) deallocate(ff_f)
  if (allocated(ff_a0)) deallocate(ff_a0)
  if (allocated(ff_a1)) deallocate(ff_a1)
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 摩擦項の高速計算用ルーチンの初期化
!----------------------------------------------------------------------
subroutine init_ffactor_fast(level, hmin, hmax)
  integer, intent(in) :: level
  real, intent(in) :: hmin, hmax
  integer :: fflevel
  real :: c, c0, c1, dc
  real :: h, h0, h1, hc
  real :: f, f0, f1, fc
  integer :: i

  fflevel = max(4, min(8, (9 - level)))     ! 4 <= fflevel <= 8
  ff_nn = 2**fflevel                         ! 16 <= ff_nn <= 256
  allocate(ff_h(1:ff_nn))
  allocate(ff_f(1:ff_nn))
  allocate(ff_a0(1:ff_nn))
  allocate(ff_a1(1:ff_nn))

  ! テーブルはlog(h)が等間隔になる様に作成
  c0 = log(hmin)
  c1 = log(hmax)
  dc = (c1 - c0) / (ff_nn - 1)
  ! hとfを計算
  do i = 1, ff_nn
    c = c0 + dc * (i - 1)
    h = exp(c)
    f = ffactor_strict(h)
    ff_h(i) = h
    ff_f(i) = f
  end do
  ! 各区間の中点を挟んだ前後をそれぞれ直線で近似
  do i = 1, ff_nn - 1
    h0 = ff_h(i)
    f0 = ff_f(i)
    h1 = ff_h(i+1)
    f1 = ff_f(i+1)
    hc = (h0 + h1) / 2
    fc = ffactor_strict(hc)
    ! 区間前半の近似直線の傾きa0と後半の傾きa1を保存
    ff_a0(i) = (fc - f0) / (hc - h0)
    ff_a1(i) = (f1 - fc) / (h1 - hc)
  end do
  ff_a0(ff_nn) = ff_a0(ff_nn-1)
  ff_a1(ff_nn) = ff_a1(ff_nn-1)
end subroutine


!----------------------------------------------------------------------
! 摩擦項の高速計算用ルーチン
!----------------------------------------------------------------------
function ffactor_fast(h) result(f)
  real, intent(in) :: h
  real :: f, f0, f1
  integer :: i, j
  ! 地表面流れの計算では水深の浅い領域が大部分なので浅い方から線形探索する
  ! (テーブルが小さいため二分木探索など工夫しても速くならず逆に遅くなる)
  ! 判定回数を減らすためにテーブル下端からひとつ飛ばしで水深を検索する
  ! テーブルの範囲外h<h(1)の場合はi=2に、h>h(nn)の場合はi=nnとする
  ! その場合fは線形に補外した値となる
  do i = 3, ff_nn, 2
    if (h <= ff_h(i)) exit
  end do
  if (i > ff_nn) then
    i = ff_nn
  else
    ! ひとつ下のテーブルと比較して位置を確定
    j = i - 1
    if (h <= ff_h(j)) i = j
  end if
  ! この時点でhはh(i-1)とh(i)の間に存在する
  ! 区間前半の近似直線による近似値と後半の直線による近似値を計算
  f1 = ff_f(i)   + ff_a1(i)   * (h - ff_h(i))
  f0 = ff_f(i-1) + ff_a0(i-1) * (h - ff_h(i-1))
  ! 厳密解の曲線が下に凸なのでf0とf1のうち大きな方を採用
  ! 水深がテーブル上端よりも極端に大きい場合に線形補外でfが負値にならないよう
  ! max(f,0.0)が必要
  f = max(max(f0, f1), 0.)
end function


!----------------------------------------------------------------------
! 摩擦項の厳密計算用ルーチン
!----------------------------------------------------------------------
function ffactor_strict(h) result(f)
  real, intent(in) :: h
  real :: f
  f = 1 / h**(powf)
end function


!----------------------------------------------------------------------
! 未初期化時に呼ばれるルーチン
!----------------------------------------------------------------------
function ffactor_uninitialized(h) result(f)
  real, intent(in) :: h
  real :: f
  f = 1 / h**(powf)
  call par_stop("ffactor: uninitialized")
  stop
end function


end module
