module list_swi
  ! 土壌雨量指数条件設定ファイル(namelist)の読み込み。
  ! この層は生の値を運ぶだけで、解釈・検証は m_swi が行う(list_* 層の
  ! 共通契約)。タンクモデルの定数は全国一律の原式固定(namelist に
  ! しない — developer.md §19.8・§49)
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_swi
  public :: list_swi_read

  type t_list_swi
    integer :: f_swi = 1             ! 土壌雨量指数(0:無効, 1:有効)。
                                     ! fn_swi を書いたまま 0 で一時無効化できる
    real :: swi0(1:3) = 0.0          ! 各タンクの初期貯留 S1,S2,S3 (mm)
                                     ! (先行降雨の効果。既定 0 = 乾燥開始)
  end type

contains


!----------------------------------------------------------------------
! 土壌雨量指数条件設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_swi_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_swi), intent(out) :: list
  integer :: un, ios

  integer :: f_swi
  real :: swi0(1:3)

  namelist /list_swi/ f_swi, swi0

  f_swi = list%f_swi
  swi0 = list%swi0

  call par_info("reading list_swi in " // trim(p%fn_swi))
  open(newunit=un, file=trim(p%fn_swi), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_swi: cannot open " // trim(p%fn_swi))
  read(un, nml=list_swi, iostat=ios)
  if (ios /= 0) call par_stop("list_swi: cannot read namelist")
  close(un)

  list%f_swi = f_swi
  list%swi0 = swi0

end subroutine

end module
