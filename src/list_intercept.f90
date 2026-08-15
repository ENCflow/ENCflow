module list_intercept
  ! 降雨遮断条件設定ファイル(namelist)の読み込み。
  ! この層は生の値を運ぶだけで、解釈・検証・モデル束縛は m_intercept が行う。
  ! 各モデル固有の設定グループ(&list_intercept_fixed 等)は、選択された
  ! モデルの init が同じファイルから自分で読む(このモジュールは関知しない)
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_intercept
  public :: list_intercept_read

  type t_list_intercept
    integer :: f_icmodel = 0         ! 遮断モデル(0:なし, 1:固定遮断率, 2:初期損失)
                                     ! fn_intercept を書いたまま 0 で一時無効化できる
  end type

contains


!----------------------------------------------------------------------
! 降雨遮断条件設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_intercept_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_intercept), intent(out) :: list
  integer :: un, ios

  integer :: f_icmodel

  namelist /list_intercept/ f_icmodel

  f_icmodel = list%f_icmodel

  call par_info("reading list_intercept in " // trim(p%fn_intercept))
  open(newunit=un, file=trim(p%fn_intercept), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_intercept: cannot open " // trim(p%fn_intercept))
  read(un, nml=list_intercept, iostat=ios)
  if (ios /= 0) call par_stop("list_intercept: cannot read namelist")
  close(un)

  list%f_icmodel = f_icmodel

end subroutine

end module
