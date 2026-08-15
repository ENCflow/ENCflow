!======================================================================
module list_record
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public :: t_list_record
  public :: list_record_read

  integer, parameter :: npbmax = 1000
  integer, parameter :: nflmax = 1000


  type t_list_record
    ! プローブ計測の座標指定タイプ
    !  0:セル番号(1からカウント)で指定
    !  1:実座標で指定(x 東・y 北が正。地理参照(hdr/GeoTIFF 由来)が
    !    あれば絶対座標、なければ領域南西端原点のローカル座標 (m)。
    !    解決されたセル番号を初期化時に表示する。§36)
    integer :: pbxytype = 0
    ! プローブの座標 (x, y, 番号)
    real :: pbxy(1:2,1:npbmax) = -9.999e33   ! 未設定番兵(§36)
    ! フラックス計測の座標指定タイプ
    !  0:セル番号(1からカウント)で指定。両端セル中心を結ぶ DDA 階段面。
    !    両端に同一セルは指定不可(向きが定義できないためエラー)
    !  1:実座標で指定(座標の解釈は pbxytype=1 と同じ。§36)。線分が
    !    かすめる各セルのセル内線分成分で積算し、1セル内の短い測線も
    !    計測できる(向きと長さは実座標から決まる)
    integer :: flxytype = 0
    ! 測線の座標設定方法
    !  0:設定ファイル内のflxyで指定
    !  1:測線情報ファイルから読み込み(CSV形式)
    integer :: flxyfile = 0                    ! フラックスの測線の座標指定法
    ! 測線の始点終点 (右岸x, 右岸y, 左岸x, 左岸y, 番号)
    real :: flxy(1:4,1:nflmax) = -9.999e33     ! フラックスの測線の座標(番兵は同上)
    ! 測線情報ファイル名
    !  ファイルの中身はカンマまたは空白区切りで
    !   右岸x, 右岸y, 左岸x, 左岸y
    character(len=256) :: fn_flxy
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! レコード設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_record_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_record), intent(inout) :: list
  integer :: pbxytype
  real :: pbxy(1:2,1:npbmax)
  integer :: flxyfile
  character(:), allocatable :: fn_flxy
  integer :: flxytype
  real :: flxy(1:4,1:nflmax)
  integer :: un
  integer :: ios
  character(len=1024) :: iom
  namelist /list_record/ pbxytype, pbxy, flxyfile, fn_flxy, flxytype, flxy

  pbxytype = list%pbxytype
  pbxy = list%pbxy
  flxyfile = list%flxyfile
  fn_flxy = list%fn_flxy
  flxytype = list%flxytype
  flxy = list%flxy

  !---- 設定ファイルを読み込む ----
  call par_info("reading list_record in "//trim(p%fn_record))
  open(newunit=un, file=trim(p%fn_record), status='old')
  read(un, nml=list_record, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_record: failed to read namelist: "//trim(iom))
  close(un)

  list%pbxytype = pbxytype
  list%pbxy = pbxy
  list%flxyfile = flxyfile
  list%fn_flxy = fn_flxy
  list%flxytype = flxytype
  list%flxy = flxy

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
