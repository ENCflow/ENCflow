module list_bedmotion
  ! ========= 規定底面運動設定ファイルの読み込み(&list_bedmotion) =========
  ! list_* は namelist を読むだけ。解釈・検証・導出(スナップショット表の
  ! 読み込み、時刻の換算、整合検査)は m_bedmotion の init が行う
  ! (developer.md §12)。設計は docs/bedmotion_plan.md
  ! =====================================================================
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_bedmotion
  public :: list_bedmotion_read

  integer, parameter :: maxpathlen = 256

  type t_list_bedmotion
    integer :: f_bedmotion = 1               ! 0 でファイルを残したまま一時無効化
    character(len=maxpathlen) :: fn_bmlist = ""  ! スナップショット表(時刻 ファイル名。dir_data 相対)
    integer :: f_bminterp = 1                ! 時間補間 (1: 線形, 0: 階段 = 直前のスナップショットを保持)
    real :: bm_tscale = 1.0                  ! 表の時刻の単位 (s。60 で分、3600 で時)
  end type

contains

!----------------------------------------------------------------------
! 規定底面運動設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_bedmotion_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_bedmotion), intent(inout) :: list

  integer :: f_bedmotion, f_bminterp
  real :: bm_tscale
  character(len=maxpathlen) :: fn_bmlist
  integer :: un, ios
  character(len=1024) :: iom

  namelist /list_bedmotion/ f_bedmotion, fn_bmlist, f_bminterp, bm_tscale

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  f_bedmotion = list%f_bedmotion
  fn_bmlist = list%fn_bmlist
  f_bminterp = list%f_bminterp
  bm_tscale = list%bm_tscale

  call par_info("reading list_bedmotion in "//trim(p%fn_bedmotion))
  open(newunit=un, file=trim(p%fn_bedmotion), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_bedmotion: cannot open "//trim(p%fn_bedmotion)//": "//trim(iom))
  read(un, nml=list_bedmotion, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_bedmotion: cannot read namelist: "//trim(iom))
  close(un)

  list%f_bedmotion = f_bedmotion
  list%fn_bmlist = fn_bmlist
  list%f_bminterp = f_bminterp
  list%bm_tscale = bm_tscale

end subroutine

end module
