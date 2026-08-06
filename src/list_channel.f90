module list_channel
  ! 河道条件設定ファイル(fn_channel)の読み込み層。
  !   河道の水理構造モデル(堤防=仮想壁面、将来のサブグリッド河道幅)の
  !   パラメータをここに集約する(developer.md §18)。
  !   線引き: セルの地形・物性を作る量(fn_rw, depth_rw, rn0_rw 等)は
  !   list_geoinfo / エッジの通水構造と水理モードは本ファイル。
  !   有効化は fn_channel の有無(fn_* 慣習)。fn_channel には fn_rw が必須。
  !   解釈・検証・構築は消費側の init(m_geoinfo: 天端 zbank の構築 /
  !   m_swflow_enc: 水理モードの束縛)が行う。list_* は読むだけ(§12)
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public :: t_list_channel
  public :: list_channel_read
  public :: nbrsmax, nbrvmax

  integer, parameter :: maxpathlen = 256
  integer, parameter :: nbrsmax = 100    ! 破堤サイトの最大数
  integer, parameter :: nbrvmax = 200    ! 1サイトあたりの時系列最大データ数

  type t_list_channel
    character(len=maxpathlen) :: fn_bank = ""  ! 堤防高さ分布ファイル名(河道セルのみ有効。
                                               !   -900 以下は堤防なし。bank0 と排他)
    real :: bank0 = -9999.0                    ! 堤防高さの一律固定値(-900 以下は未指定。
                                               !   fn_bank と排他。全河道セルに適用)
    integer :: f_bank_datum = 0                ! 堤防高さの基準 (0:河床(掘込後), 1:堤内地セル標高, 2:絶対標高)
    integer :: f_bank_aggr = 0                 ! 天端の集約方法 (f_bank_datum=1 のみ。0:平均, 1:最小, 2:最大)
    integer :: f_bank_mode = 0                 ! 堤防の水理モード (0:越流のみ, 1:樋門(逆止弁), 2:強制排水)
    integer :: f_bank_opening = 1              ! 堤防時の開口補正 (0:なし, 1:塞がれた斜め開口の
                                               !   シェアを河道—河道法線エッジへ振り替える。既定)
    character(len=maxpathlen) :: fn_width = "" ! 河道幅分布ファイル名 (m。河道セルのみ有効、
                                               !   0 以下は幅情報なし=解像扱い。指定で
                                               !   サブグリッド河道が有効化。fn_bank / bank0
                                               !   無指定なら高さ0・堤内地標高基準の堤防を自動有効化)
    integer :: f_channel_advection = 1         ! 河道セルを含むエッジの移流項 (1:通常, 0:落とす)
    ! ---- &list_channel_breach(破堤。グループ不在=破堤なし)----
    ! 大配列は allocatable 成分とし、グループが存在した場合のみ確保・充填
    ! する(固定長成分はローカル変数のスタックあふれの元。list_boundary の教訓)
    logical :: present_breach = .false.        ! グループが存在したか
    integer, allocatable :: br_cell(:,:)       ! サイトのセル対 (1:4, サイト) = ic, jc, il, jl
                                               !   (河道セル, 堤内地セル。8近傍で隣接)
    real, allocatable :: br_series(:,:,:)      ! 天端割合の時系列 (1:2, 点, サイト)
                                               !   = (時刻 min, 割合 0〜1)。1=天端高, 0=堤内地盤高
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 河道条件設定ファイルを読み込む
!   fn_channel 未指定時は呼び出し側が読み込みをスキップし、型の
!   デフォルト値(すべて無効)が使われる
!----------------------------------------------------------------------
subroutine list_channel_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_channel), intent(inout) :: list
  character(len=maxpathlen) :: fn_bank   ! 堤防高さ分布ファイル名
  real :: bank0                          ! 堤防高さの一律固定値
  integer :: f_bank_datum                ! 堤防高さの基準
  integer :: f_bank_aggr                 ! 天端の集約方法
  integer :: f_bank_mode                 ! 堤防の水理モード
  integer :: f_bank_opening              ! 堤防時の開口補正
  character(len=maxpathlen) :: fn_width  ! 河道幅分布ファイル名
  integer :: f_channel_advection         ! 河道セルを含むエッジの移流項
  integer :: un
  integer :: ios
  character(len=1024) :: iom

  namelist /list_channel/ fn_bank, bank0, f_bank_datum, f_bank_aggr, f_bank_mode, &
                          f_bank_opening, fn_width, f_channel_advection

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  fn_bank = list%fn_bank
  bank0 = list%bank0
  f_bank_datum = list%f_bank_datum
  f_bank_aggr = list%f_bank_aggr
  f_bank_mode = list%f_bank_mode
  f_bank_opening = list%f_bank_opening
  fn_width = list%fn_width
  f_channel_advection = list%f_channel_advection

  call par_info("reading list_channel in "//trim(p%fn_channel))
  open(newunit=un, file=trim(p%fn_channel), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("fn_channel を開けません: "//trim(iom))
  read(un, nml=list_channel, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_channel 読込失敗: "//trim(iom))
  call read_breach(un, list)
  close(un)

  list%fn_bank = fn_bank
  list%bank0 = bank0
  list%f_bank_datum = f_bank_datum
  list%f_bank_aggr = f_bank_aggr
  list%f_bank_mode = f_bank_mode
  list%f_bank_opening = f_bank_opening
  list%fn_width = fn_width
  list%f_channel_advection = f_channel_advection

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! &list_channel_breach を読む(不在なら present_breach を偽のまま返す)
!   解釈・検証(隣接性・マスク・時系列の単調性等)は
!   m_swflow_enc_channel の breach_init が行う(list_* は読むだけ)
!----------------------------------------------------------------------
subroutine read_breach(un, list)
  integer, intent(in) :: un
  type(t_list_channel), intent(inout) :: list
  integer :: br_cell(1:4, 1:nbrsmax)
  real :: br_series(1:2, 1:nbrvmax, 1:nbrsmax)
  integer :: ios
  character(len=1024) :: iom
  namelist /list_channel_breach/ br_cell, br_series

  br_cell = -9999
  br_series = -9999.0

  rewind(un)
  read(un, nml=list_channel_breach, iostat=ios, iomsg=iom)
  if (ios > 0) call par_stop("list_channel_breach 読込失敗: "//trim(iom))
  if (ios < 0) return              ! グループ不在(破堤なし)
  list%present_breach = .true.

  list%br_cell = br_cell
  list%br_series = br_series

end subroutine

end module
