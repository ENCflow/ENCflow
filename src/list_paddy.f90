module list_paddy
  ! 田んぼダム(水田の落水口の流出抑制)の設定ファイル(fn_paddy の namelist)の読み込み専任
  ! (層契約 §12)。生の値を t_list_paddy に運ぶだけで、解釈・検証・既定値の適用・
  ! 導出は m_paddy の init が行う(developer.md §119、docs/paddy_plan.md)。
  !   &list_paddy : 有効化・水田面積率と取組率(分布か一様)・区画面積・畦畔高・事前の湛水深・
  !                 減水深と、落水口の装置(種類 1 = 取組なしの通常の落水口、2 = 田んぼダム。
  !                 配列の添字)
  ! 未指定の番兵は実数 −9999、整数 −9999。グループ不在は全番兵のまま(init が判定)。
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_paddy
  public :: list_paddy_read
  public :: pd_nclass

  integer, parameter :: maxpathlen = 256
  integer, parameter :: pd_nclass = 2         ! 落水口の種類の数(1: 通常、2: 田んぼダム)

  type t_list_paddy
    integer :: f_paddy = 1                          ! 0 で書いたまま一時無効化
    character(len=maxpathlen) :: fn_pd_frac = ""    ! 水田面積率の分布(セル面積に対する割合 0〜1)
    real :: pd_frac = -9999.0                       ! 水田面積率の一様値(fn_pd_frac と排他)
    character(len=maxpathlen) :: fn_pd_adopt = ""   ! 取組率の分布(水田面積のうち田んぼダムの割合 0〜1)
    real :: pd_adopt = -9999.0                      ! 取組率の一様値(fn_pd_adopt と排他。未指定 = 0)
    real :: pd_aplot = -9999.0                      ! 代表区画面積 (m2。落水口 1 か所あたりの水田面積)
    real :: pd_hlev = -9999.0                       ! 畦畔高 (m。田面から)
    real :: pd_h0 = -9999.0                         ! 事前の湛水深 (m。未指定 = 種類ごとの流れ始める高さ)
    real :: pd_perc_mmd = -9999.0                   ! 減水深 (mm/d。系外へ)
    integer :: f_pd_exchange = -9999                ! 地表と水田の水のやり取り 0: 片方向(雨だけ)、
                                                    !   1: 双方向(二室化。未指定 = 0。developer.md §119.6)
    integer :: pd_dev_type(1:pd_nclass) = -9999     ! 装置の型 0: 水位調整板だけ, 1: 機能分離型, 2: 機能一体型
    real :: pd_board_h(1:pd_nclass) = -9999.0       ! 水位調整板の天端の高さ (m。田面から)
    real :: pd_board_w(1:pd_nclass) = -9999.0       ! 水位調整板の幅(堰幅) (m)
    integer :: pd_open_type(1:pd_nclass) = -9999    ! 穴の形 1: 円, 2: 長方形, 3: 三角(V 字)
    real :: pd_open_d(1:pd_nclass) = -9999.0        ! 円の穴の径 (m)
    real :: pd_open_b(1:pd_nclass) = -9999.0        ! 長方形の穴の幅 (m)
    real :: pd_open_e(1:pd_nclass) = -9999.0        ! 長方形の穴の高さ (m)
    real :: pd_open_ang(1:pd_nclass) = -9999.0      ! 三角の穴(V 字の切欠き)の角度 (度)
    real :: pd_open_z(1:pd_nclass) = -9999.0        ! 穴の下端(V 字は頂点)の高さ (m。田面から)
    real :: pd_plate_h(1:pd_nclass) = -9999.0       ! 流出量調整板の天端の高さ (m。型 1 の越流。未指定 = なし)
    real :: pd_plate_w(1:pd_nclass) = -9999.0       ! 流出量調整板の越流の幅 (m。未指定 = 水位調整板の幅)
    real :: pd_cw(1:pd_nclass) = -9999.0            ! 堰の流量係数 C
    real :: pd_co(1:pd_nclass) = -9999.0            ! 穴の流量係数 C
  end type

contains


!----------------------------------------------------------------------
! 設定ファイルを読み込む(グループ不在可。構文エラーは停止)
!----------------------------------------------------------------------
subroutine list_paddy_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_paddy), intent(out) :: list
  integer :: un, ios
  character(len=256) :: msg

  integer :: f_paddy
  character(len=maxpathlen) :: fn_pd_frac, fn_pd_adopt
  real :: pd_frac, pd_adopt, pd_aplot, pd_hlev, pd_h0, pd_perc_mmd
  integer :: f_pd_exchange
  integer :: pd_dev_type(1:pd_nclass), pd_open_type(1:pd_nclass)
  real :: pd_board_h(1:pd_nclass), pd_board_w(1:pd_nclass)
  real :: pd_open_d(1:pd_nclass), pd_open_b(1:pd_nclass), pd_open_e(1:pd_nclass)
  real :: pd_open_ang(1:pd_nclass), pd_open_z(1:pd_nclass)
  real :: pd_plate_h(1:pd_nclass), pd_plate_w(1:pd_nclass)
  real :: pd_cw(1:pd_nclass), pd_co(1:pd_nclass)

  namelist /list_paddy/ f_paddy, fn_pd_frac, pd_frac, fn_pd_adopt, pd_adopt, pd_aplot, pd_hlev, pd_h0, &
                        pd_perc_mmd, f_pd_exchange, pd_dev_type, pd_board_h, pd_board_w, pd_open_type, pd_open_d, pd_open_b, &
                        pd_open_e, pd_open_ang, pd_open_z, pd_plate_h, pd_plate_w, pd_cw, pd_co

  f_paddy = list%f_paddy
  fn_pd_frac = list%fn_pd_frac
  pd_frac = list%pd_frac
  fn_pd_adopt = list%fn_pd_adopt
  pd_adopt = list%pd_adopt
  pd_aplot = list%pd_aplot
  pd_hlev = list%pd_hlev
  pd_h0 = list%pd_h0
  pd_perc_mmd = list%pd_perc_mmd
  f_pd_exchange = list%f_pd_exchange
  pd_dev_type = list%pd_dev_type
  pd_board_h = list%pd_board_h
  pd_board_w = list%pd_board_w
  pd_open_type = list%pd_open_type
  pd_open_d = list%pd_open_d
  pd_open_b = list%pd_open_b
  pd_open_e = list%pd_open_e
  pd_open_ang = list%pd_open_ang
  pd_open_z = list%pd_open_z
  pd_plate_h = list%pd_plate_h
  pd_plate_w = list%pd_plate_w
  pd_cw = list%pd_cw
  pd_co = list%pd_co

  call par_info("reading list_paddy in " // trim(p%fn_paddy))
  open(newunit=un, file=trim(p%fn_paddy), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_paddy: cannot open " // trim(p%fn_paddy))
  read(un, nml=list_paddy, iostat=ios, iomsg=msg)
  if (ios > 0) call par_stop("list_paddy: cannot read namelist: " // trim(msg))
  close(un)

  list%f_paddy = f_paddy
  list%fn_pd_frac = fn_pd_frac
  list%pd_frac = pd_frac
  list%fn_pd_adopt = fn_pd_adopt
  list%pd_adopt = pd_adopt
  list%pd_aplot = pd_aplot
  list%pd_hlev = pd_hlev
  list%pd_h0 = pd_h0
  list%pd_perc_mmd = pd_perc_mmd
  list%f_pd_exchange = f_pd_exchange
  list%pd_dev_type = pd_dev_type
  list%pd_board_h = pd_board_h
  list%pd_board_w = pd_board_w
  list%pd_open_type = pd_open_type
  list%pd_open_d = pd_open_d
  list%pd_open_b = pd_open_b
  list%pd_open_e = pd_open_e
  list%pd_open_ang = pd_open_ang
  list%pd_open_z = pd_open_z
  list%pd_plate_h = pd_plate_h
  list%pd_plate_w = pd_plate_w
  list%pd_cw = pd_cw
  list%pd_co = pd_co

end subroutine

end module
