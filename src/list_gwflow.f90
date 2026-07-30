module list_gwflow
  ! 地下水条件設定ファイル(namelist)の読み込み。
  ! この層は生の値を運ぶだけで、解釈・検証・モデル束縛は m_gwflow が行う。
  ! 各モデル固有の設定グループ(&list_gwflow_bucket 等)は、選択された
  ! モデルの init が同じファイルから自分で読む(このモジュールは関知しない)
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_gwflow
  public :: list_gwflow_read

  type t_list_gwflow
    integer :: f_gwmodel = 0         ! 地下水モデル(0:なし, 1:バケツ)
                                     ! fn_gwflow を書いたまま 0 で一時無効化できる
    real :: dt_gwflow = 0.0          ! 地下水計算の更新時間間隔 (s)。0なら毎ステップ
  end type

contains


!----------------------------------------------------------------------
! 地下水条件設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_gwflow_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_gwflow), intent(out) :: list
  integer :: un, ios

  integer :: f_gwmodel
  real :: dt_gwflow

  namelist /list_gwflow/ f_gwmodel, dt_gwflow

  f_gwmodel = list%f_gwmodel
  dt_gwflow = list%dt_gwflow

  call par_info("reading list_gwflow in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow, iostat=ios)
  if (ios /= 0) call par_stop("error in reading list_gwflow")
  close(un)

  list%f_gwmodel = f_gwmodel
  list%dt_gwflow = dt_gwflow

end subroutine

end module
