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
    integer :: f_gwvertical = 0      ! 鉛直モデル(0:なし, 1:バケツ, 2:Green-Ampt)
                                     ! fn_gwflow を書いたまま 0 で一時無効化できる
    integer :: f_gwlateral = 0       ! 側方モデル(0:なし=鉛直のみ。1以降は予約・未実装)
                                     ! 未指定(=0)なら側方流動の資源は一切確保されない
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

  integer :: f_gwvertical
  integer :: f_gwlateral
  real :: dt_gwflow

  namelist /list_gwflow/ f_gwvertical, f_gwlateral, dt_gwflow

  f_gwvertical = list%f_gwvertical
  f_gwlateral = list%f_gwlateral
  dt_gwflow = list%dt_gwflow

  call par_info("reading list_gwflow in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow, iostat=ios)
  if (ios /= 0) call par_stop("error in reading list_gwflow")
  close(un)

  list%f_gwvertical = f_gwvertical
  list%f_gwlateral = f_gwlateral
  list%dt_gwflow = dt_gwflow

end subroutine

end module
