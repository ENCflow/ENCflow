!**********************************************************************
!
! ネスト格子(子格子)の設定 &list_nest を読む(docs/nesting_plan.md §4)
!   子格子のパラメータファイルに書く。読むだけで解釈・検証は m_nest(§12)
!
!**********************************************************************
module list_nest
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public :: t_list_nest, list_nest_read

  type t_list_nest
    integer :: nest_bc = 2        ! 親→子 (1: 水位のみ, 2: 水位+エッジ量〔既定〕, 3: Flather 面, 4: スポンジ)
    integer :: nest_fb = 2        ! 子→親 (0: なし=一方向, 1: h/m/n の面積平均, 2: 湿潤判定付き平均〔既定〕, 3: +保存修正)
    integer :: nest_nb = 0        ! 境界帯の幅(セル。0 = 自動: 移流スキームのステンシルから m_nest が決める)
    integer :: nest_ns = 4        ! スポンジの幅(セル。nest_bc = 4 のとき帯の内側に置く緩和帯)
  end type

contains

!----------------------------------------------------------------------
! 子格子のパラメータファイル fn から &list_nest を読む。
! グループがなければ既定値のまま(ファイル末尾まで見つからない = iostat<0)
!----------------------------------------------------------------------
subroutine list_nest_read(fn, list)
  character(len=*), intent(in) :: fn
  type(t_list_nest), intent(inout) :: list
  integer :: nest_bc, nest_fb, nest_nb, nest_ns
  integer :: un, ios
  character(len=1024) :: iom
  namelist /list_nest/ nest_bc, nest_fb, nest_nb, nest_ns

  nest_bc = list%nest_bc
  nest_fb = list%nest_fb
  nest_nb = list%nest_nb
  nest_ns = list%nest_ns

  call par_info("reading list_nest in "//trim(fn))
  open(newunit=un, file=trim(fn), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_nest: cannot open "//trim(fn)//": "//trim(iom))
  read(un, nml=list_nest, iostat=ios, iomsg=iom)
  if (ios > 0) call par_stop("list_nest: failed to read namelist: "//trim(iom))
  close(un)

  list%nest_bc = nest_bc
  list%nest_fb = nest_fb
  list%nest_nb = nest_nb
  list%nest_ns = nest_ns
end subroutine

end module
