module list_geomorph
  ! 地形変化条件設定ファイル(namelist)の読み込み。
  ! この層は生の値(未指定 = 型宣言のデフォルトが番兵)を運ぶだけで、
  ! 解釈・補完・検証は m_geomorph が行う(list_* 層の共通契約)
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_geomorph
  public :: list_geomorph_read

  type t_list_geomorph
    ! --- 実行制御 ---
    real :: dt_geomorph = 0.0        ! 地形変化の更新時間間隔 (s)。0なら毎ステップ
    real :: morfac = 1.0             ! 加速係数(地形時間の加速。全プロセス共通)

    ! --- プロセス別フラグ(排他選択ではなく重ね合わせ。0:無効) ---
    ! 各プロセスは独立に有効化でき、calc は有効なものを順に適用する
    integer :: f_creep = 0           ! 斜面クリープ(線形拡散)(0:無効, 1:有効)
    real :: creep_d = 0.0            ! クリープ拡散係数 (m2/s)

    integer :: f_fluvial = 0         ! 掃流砂 Exner(河床の浸食・堆積)(0:無効, 1:有効)
    integer :: f_qbform = 1          ! 流砂量式(1:芦田・道上, 2:MPM)
    real :: fluv_d50 = 0.0           ! 代表粒径 (m)。f_fluvial=1 で必須
    real :: fluv_tausc = 0.05        ! 限界無次元掃流力 τ*c
    real :: fluv_porosity = 0.4      ! 河床の空隙率 λ
    real :: fluv_sgrav = 1.65        ! 土粒子の水中比重 s = (ρs - ρ)/ρ
    real :: fluv_dzmax = 0.05        ! 1エッジ・1更新の河床変動上限 (m)
    real :: fluv_diagratio = 0.5857864376  ! 斜め方向の通過幅配分(= 2/(2+√2)。
                                     ! m_swflow_enc の p_diagratio と同値の既定)

    ! 将来のプロセス追加はここにフラグとパラメータを足す
    ! (例: f_suspend 浮遊砂, f_wash 斜面浸食, f_badland 崩壊性浸食)
  end type

contains


!----------------------------------------------------------------------
! 地形変化条件設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_geomorph_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_geomorph), intent(out) :: list
  integer :: un, ios

  real :: dt_geomorph
  real :: morfac
  integer :: f_creep
  real :: creep_d
  integer :: f_fluvial
  integer :: f_qbform
  real :: fluv_d50
  real :: fluv_tausc
  real :: fluv_porosity
  real :: fluv_sgrav
  real :: fluv_dzmax
  real :: fluv_diagratio

  namelist /list_geomorph/ dt_geomorph, morfac, f_creep, creep_d, &
                           f_fluvial, f_qbform, fluv_d50, fluv_tausc, &
                           fluv_porosity, fluv_sgrav, fluv_dzmax, fluv_diagratio

  ! 型宣言のデフォルトを namelist 変数の初期値にする
  dt_geomorph = list%dt_geomorph
  morfac = list%morfac
  f_creep = list%f_creep
  creep_d = list%creep_d
  f_fluvial = list%f_fluvial
  f_qbform = list%f_qbform
  fluv_d50 = list%fluv_d50
  fluv_tausc = list%fluv_tausc
  fluv_porosity = list%fluv_porosity
  fluv_sgrav = list%fluv_sgrav
  fluv_dzmax = list%fluv_dzmax
  fluv_diagratio = list%fluv_diagratio

  call par_info("reading list_geomorph in " // trim(p%fn_geomorph))
  open(newunit=un, file=trim(p%fn_geomorph), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: " // trim(p%fn_geomorph))
  read(un, nml=list_geomorph, iostat=ios)
  if (ios /= 0) call par_stop("error in reading list_geomorph")
  close(un)

  list%dt_geomorph = dt_geomorph
  list%morfac = morfac
  list%f_creep = f_creep
  list%creep_d = creep_d
  list%f_fluvial = f_fluvial
  list%f_qbform = f_qbform
  list%fluv_d50 = fluv_d50
  list%fluv_tausc = fluv_tausc
  list%fluv_porosity = fluv_porosity
  list%fluv_sgrav = fluv_sgrav
  list%fluv_dzmax = fluv_dzmax
  list%fluv_diagratio = fluv_diagratio

end subroutine

end module
