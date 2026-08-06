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

  integer, parameter :: maxpathlen = 256

  type t_list_channel
    character(len=maxpathlen) :: fn_bank = ""  ! 堤防高さ分布ファイル名(河道セルのみ有効。
                                               !   -900 以下は堤防なし。bank0 と排他)
    real :: bank0 = -9999.0                    ! 堤防高さの一律固定値(-900 以下は未指定。
                                               !   fn_bank と排他。全河道セルに適用)
    integer :: f_bank_datum = 0                ! 堤防高さの基準 (0:河床(掘込後), 1:堤内地セル標高, 2:絶対標高)
    integer :: f_bank_aggr = 0                 ! 天端の集約方法 (f_bank_datum=1 のみ。0:平均, 1:最小, 2:最大)
    integer :: f_bank_mode = 0                 ! 堤防の水理モード (0:越流のみ, 1:樋門(逆止弁), 2:強制排水)
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
  integer :: un
  integer :: ios
  character(len=1024) :: iom

  namelist /list_channel/ fn_bank, bank0, f_bank_datum, f_bank_aggr, f_bank_mode

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  fn_bank = list%fn_bank
  bank0 = list%bank0
  f_bank_datum = list%f_bank_datum
  f_bank_aggr = list%f_bank_aggr
  f_bank_mode = list%f_bank_mode

  call par_info("reading list_channel in "//trim(p%fn_channel))
  open(newunit=un, file=trim(p%fn_channel), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("fn_channel を開けません: "//trim(iom))
  read(un, nml=list_channel, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_channel 読込失敗: "//trim(iom))
  close(un)

  list%fn_bank = fn_bank
  list%bank0 = bank0
  list%f_bank_datum = f_bank_datum
  list%f_bank_aggr = f_bank_aggr
  list%f_bank_mode = f_bank_mode

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
