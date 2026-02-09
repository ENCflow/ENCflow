module m_boundary
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use list_boundary, only : t_list_boundary, list_boundary_read
  implicit none
  private

  public :: t_boundary
  public :: m_boundary_init
  public :: m_boundary_dispose
  public :: m_boundary_makebdc


  type t_boundary
    integer :: nsrc                                ! 湧出しの数
    integer :: nsrcc                               ! 湧出しセル数
    integer, allocatable :: srccell(:,:)           ! 湧出しセルの座標　
    integer :: nsrcv                               ! 湧出し時系列のデータ数
    real, allocatable :: srcval(:,:)               ! 湧出し時系列値 (min, m3/s)
    logical :: initialized = .false.               ! 初期化済みフラグ
    real :: srcq                                   ! 現時刻の湧出し流量
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_boundary_init(b, p, g)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_boundary) :: list
  if (p%initialized) continue
  if (g%initialized) continue
  b%initialized = .true.

  !--- 境界条件パラメータ自体が設定されていない場合 ---
  if (len(trim(p%fn_boundary)) <= 0) then
    b%nsrc = 0
    return
  end if

  !---  境界条件パラメータファイルを読み込む ---
  call list_boundary_read(p, list)

  !--- 現時点では湧出し1個のみ ---
  b%nsrc = 1

  !--- 湧き出しセル指定ファイル名が存在する場合 ---
  !if (len(trim()) > 0) then
  !else
    block
      integer :: i
      integer :: n = 0
      do i = 1, ubound(list%srccell, 2)
        if (list%srccell(1,i) < 0) exit   ! 有効なデータが無い場合は終了
        n = n + 1
      end do
      allocate(b%srccell(1:2,1:n))
      b%srccell(1:2,1:n) = list%srccell(1:2,1:n)
      b%nsrcc = n
    end block
  !end if


  !--- 湧出し流量時系列ファイル名が存在する場合 ---
  if (len(trim(list%fn_srcval)) > 0) then
    block
      character(:), allocatable :: fname
      integer :: un, n, i
      real :: t, val
      fname = trim(p%dir_data)//"/"//trim(list%fn_srcval)
      open(newunit=un, file=trim(fname), status='old')
      n = 0
      do
        read(un, *, end=99)
        n = n + 1
      end do
      99 continue
      rewind(un)
      allocate(b%srcval(1:2,1:n))
      do i = 1, n
        read(un, *) t, val
        b%srcval(1,i) = t * 60
        b%srcval(2,i) = val
      end do
      close(1)
      !n = 4
      b%nsrcv = n
    end block
  else
    block
      integer :: i
      integer :: n = 0
      do i = 1, ubound(list%srcval, 2)
        if (list%srcval(1,i) < 0) exit   ! 有効なデータが無い場合は終了
        n = n + 1
      end do
      allocate(b%srcval(1:2,1:n))
      b%srcval(1,1:n) = list%srcval(1,1:n) * 60  ! 分を秒に換算
      b%srcval(2,1:n) = list%srcval(2,1:n)
      b%nsrcv = n
    end block
  end if

    block
      integer :: i
      do i = 1, b%nsrcv
        print *, i, b%srcval(:,i), b%nsrcv
      end do
    end block

  if (b%nsrcv == 0) b%nsrc = 0

  !print *, b%nsrcv
  !print *, b%srcval(1:2,1)
  !print *, b%srcval(1:2,2)

end subroutine


!----------------------------------------------------------------------
! 時刻tでの湧出し流量を計算
!----------------------------------------------------------------------
subroutine m_boundary_makebdc(b, p, s)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  if (b%initialized) continue
  if (p%initialized) continue
  if (s%initialized) continue

  !--- 湧出しが無い場合は何もしない ---
  if (b%nsrc <= 0) return

  !--- 現時刻での湧き出し流量を計算 ---
  call get_srcval(s%t, b%srcq)

  !--- セル1個・dtあたりに換算 ---
  b%srcq = b%srcq / (b%nsrcc * p%dx * p%dy) * p%dt
  !print *, s%t, b%srcq
  
contains
  !------------------------------------------------
  ! 時刻tでの湧出し流量を計算
  subroutine get_srcval(t, val)  
    real, intent(in) :: t
    real, intent(out) :: val
    real :: t0, t1, q0, q1
    integer :: k
    val = 9
    if (t <= b%srcval(1,1)) then             ! 最初の時刻よりも前の場合
      val = b%srcval(2,1)                    ! 最初の時刻の値
    else if (t > b%srcval(1,b%nsrcv)) then   ! 最後の時刻より後の場合　
      val = b%srcval(2,b%nsrcv)              ! 最後の時刻の値
    else
      do k = 2, b%nsrcv
        t1 = b%srcval(1,k)
        if (t < t1) then
          t0 = b%srcval(1,k-1)
          q0 = b%srcval(2,k-1)
          q1 = b%srcval(2,k)
          val = q0 + (t - t0) / (t1 - t0) * (q1 - q0)
          exit
        end if
      end do
    end if
  end subroutine
  !------------------------------------------------
end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_boundary_dispose(b)
  type(t_boundary), intent(inout) :: b
  if (b%initialized) continue
end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
