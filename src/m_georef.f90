!======================================================================
! m_georef: 地理座標参照(georeference)の管理
!   ESRI BIL の .hdr(GDAL EHdr 互換)を読み書きし、格子の位置
!   (北西隅外縁座標・セル寸法)と CRS(EPSG コード)を保持する。
!
!   設計上の約束(docs/geotiff_plan.md §10):
!   - 座標値は実数精度切替(PREC)に依存させず常に real64 で保持する
!     (単精度ビルドでも投影座標・経緯度の精度を落とさないため)。
!   - 正本の座標表現は「北西隅セルの外縁」(xul, yul)。ESRI hdr の
!     ULXMAP/ULYMAP(北西隅セルの中心)とは読み書き時に相互変換する。
!     将来の GeoTIFF の ModelTiepoint(外縁)と同じ表現に揃えている。
!   - 対応する hdr は 1 バンド・32bit・LAYOUT=BIL・リトルエンディアン
!     (BYTEORDER I)のみ。対応範囲外は黙って誤読せず par_stop する。
!   - 書き込みはホストがリトルエンディアンである前提(既存の bil 出力と
!     同じ前提。対応環境の x86/arm/NEC VE はすべて該当)。
!   - エラー処理: hdr 読み込みは全ランクが同一ファイルを冗長に読む文脈
!     (m_geoinfo の probe)で呼ばれるため par_stop(collective)でよい。
!     書き込みは rank0 のみが呼ぶ。
!======================================================================
module m_georef
  use, intrinsic :: iso_fortran_env, only : real64
  use m_parallel, only : par_stop, par_abort
  use m_util, only : itoa
  implicit none
  private

  public :: t_georef
  public :: georef_hdr_name
  public :: georef_read_hdr
  public :: georef_write_hdr

  ! 出力 hdr の PIXELTYPE 指定
  integer, parameter, public :: e_pix_float = 1
  integer, parameter, public :: e_pix_int = 2

  ! init に早期 return 経路のある型から使われるため全成分デフォルト初期化(§13)
  type t_georef
    logical :: active = .false.          ! 地理座標を管理しているか
    real(real64) :: xul = 0.0_real64     ! 北西隅セル外縁の x 座標
    real(real64) :: yul = 0.0_real64     ! 北西隅セル外縁の y 座標
    real(real64) :: csx = 0.0_real64     ! セル寸法 x(> 0)
    real(real64) :: csy = 0.0_real64     ! セル寸法 y(> 0。南向きの幅)
    logical :: has_nodata = .false.      ! 入力 hdr に NODATA 指定があったか
    real(real64) :: nodata = 0.0_real64  ! その値(現状は保持のみ。GeoTIFF で使用予定)
    integer :: epsg = 0                  ! EPSG コード(0 = 不明。namelist 由来)
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! bil ファイル名から対応する hdr ファイル名を作る
!   最後の拡張子を .hdr に置き換える(拡張子が無ければ .hdr を付加)。
!   ディレクトリ名に含まれる '.' を拡張子と誤認しないこと
!----------------------------------------------------------------------
function georef_hdr_name(fname) result(hname)
  character(len=*), intent(in) :: fname
  character(:), allocatable :: hname
  integer :: idot, isep
  isep = max(index(fname, "/", back=.true.), index(fname, "\", back=.true.))
  idot = index(fname, ".", back=.true.)
  if (idot > isep + 1) then
    hname = fname(1:idot) // "hdr"
  else
    hname = trim(fname) // ".hdr"
  end if
end function


!----------------------------------------------------------------------
! ESRI hdr を読み込む
!   必須キー: NCOLS, NROWS, XDIM, YDIM, ULXMAP, ULYMAP
!   検査キー(あれば): NBANDS=1, NBITS=32, LAYOUT=BIL, BYTEORDER=I,
!     SKIPBYTES=0, PIXELTYPE=FLOAT(既存 bil 読みの前提と同じもののみ許す)
!   任意キー: NODATA / NODATA_VALUE(保持のみ)。未知キーは無視。
!   gr%epsg には触れない(namelist 由来の値を保持する)
!----------------------------------------------------------------------
subroutine georef_read_hdr(fname, gr, ncols, nrows)
  character(len=*), intent(in) :: fname
  type(t_georef), intent(inout) :: gr
  integer, intent(out) :: ncols, nrows
  integer :: un, ios
  character(len=1024) :: line
  character(:), allocatable :: key, val
  real(real64) :: xdim, ydim, ulxmap, ulymap, rv
  integer :: iv
  logical :: seen_nc, seen_nr, seen_xd, seen_yd, seen_ux, seen_uy

  ncols = 0
  nrows = 0
  xdim = 0.0_real64
  ydim = 0.0_real64
  ulxmap = 0.0_real64
  ulymap = 0.0_real64
  seen_nc = .false.; seen_nr = .false.
  seen_xd = .false.; seen_yd = .false.
  seen_ux = .false.; seen_uy = .false.

  open(newunit=un, file=fname, status='old', iostat=ios)
  if (ios /= 0) call par_stop("georef: hdr を開けません: "//trim(fname))

  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    call split_keyval(line, key, val)
    if (len(key) == 0) cycle
    select case (key)
      case ("NCOLS")
        ncols = to_int(fname, key, val);  seen_nc = .true.
      case ("NROWS")
        nrows = to_int(fname, key, val);  seen_nr = .true.
      case ("XDIM")
        xdim = to_real(fname, key, val);  seen_xd = .true.
      case ("YDIM")
        ydim = to_real(fname, key, val);  seen_yd = .true.
      case ("ULXMAP")
        ulxmap = to_real(fname, key, val);  seen_ux = .true.
      case ("ULYMAP")
        ulymap = to_real(fname, key, val);  seen_uy = .true.
      case ("NBANDS")
        iv = to_int(fname, key, val)
        if (iv /= 1) call par_stop("georef: NBANDS="//itoa(iv)// &
                       " は未対応です(1バンドのみ): "//trim(fname))
      case ("NBITS")
        iv = to_int(fname, key, val)
        if (iv /= 32) call par_stop("georef: NBITS="//itoa(iv)// &
                        " は未対応です(32bit のみ): "//trim(fname))
      case ("SKIPBYTES")
        iv = to_int(fname, key, val)
        if (iv /= 0) call par_stop("georef: SKIPBYTES="//itoa(iv)// &
                       " は未対応です: "//trim(fname))
      case ("LAYOUT")
        call upcase(val)
        if (val /= "BIL") call par_stop("georef: LAYOUT="//val// &
                            " は未対応です(BIL のみ): "//trim(fname))
      case ("BYTEORDER")
        call upcase(val)
        if (val /= "I") call par_stop("georef: BYTEORDER="//val// &
                          " は未対応です(I=リトルエンディアンのみ): "//trim(fname))
      case ("PIXELTYPE")
        call upcase(val)
        if (val /= "FLOAT") call par_stop("georef: PIXELTYPE="//val// &
                              " は未対応です(地盤高は FLOAT のみ): "//trim(fname))
      case ("NODATA", "NODATA_VALUE")
        rv = to_real(fname, key, val)
        gr%has_nodata = .true.
        gr%nodata = rv
      case default
        ! 未知キー(BANDROWBYTES, TOTALROWBYTES 等)は無視
    end select
  end do
  close(un)

  if (.not. (seen_nc .and. seen_nr .and. seen_xd .and. seen_yd .and. &
             seen_ux .and. seen_uy)) then
    call par_stop("georef: hdr に必須キー(NCOLS, NROWS, XDIM, YDIM, "// &
                  "ULXMAP, ULYMAP)が揃っていません: "//trim(fname))
  end if
  if (ncols <= 0 .or. nrows <= 0) then
    call par_stop("georef: NCOLS/NROWS が不正です: "//trim(fname))
  end if
  if (xdim <= 0.0_real64 .or. ydim <= 0.0_real64) then
    call par_stop("georef: XDIM/YDIM が不正です: "//trim(fname))
  end if

  ! ULXMAP/ULYMAP はセル中心 → 外縁に変換して保持
  gr%xul = ulxmap - 0.5_real64 * xdim
  gr%yul = ulymap + 0.5_real64 * ydim
  gr%csx = xdim
  gr%csy = ydim
  gr%active = .true.

end subroutine


!----------------------------------------------------------------------
! ESRI hdr を書き出す(rank0 専用。GDAL EHdr 互換のキーを出す)
!   e_pix: 対応する bil の画素型(e_pix_float / e_pix_int)。
!   既存の bil 出力は real32 / 既定 integer(32bit)なので NBITS は常に 32
!----------------------------------------------------------------------
subroutine georef_write_hdr(fname, gr, nx, ny, e_pix)
  character(len=*), intent(in) :: fname
  type(t_georef), intent(in) :: gr
  integer, intent(in) :: nx, ny
  integer, intent(in) :: e_pix
  integer :: un

  open(newunit=un, file=fname, status='replace')
  write(un, '(a)')          "BYTEORDER      I"
  write(un, '(a)')          "LAYOUT         BIL"
  write(un, '(a,1x,i0)')    "NROWS         ", ny
  write(un, '(a,1x,i0)')    "NCOLS         ", nx
  write(un, '(a)')          "NBANDS         1"
  write(un, '(a)')          "NBITS          32"
  write(un, '(a,1x,i0)')    "BANDROWBYTES  ", nx * 4
  write(un, '(a,1x,i0)')    "TOTALROWBYTES ", nx * 4
  select case (e_pix)
    case (e_pix_float)
      write(un, '(a)')      "PIXELTYPE      FLOAT"
    case (e_pix_int)
      write(un, '(a)')      "PIXELTYPE      SIGNEDINT"
    case default
      ! 書き込みは rank0 のみが呼ぶため collective な par_stop は使えない(§5)
      call par_abort("georef_write_hdr: 不正な e_pix "//itoa(e_pix))
  end select
  ! 外縁 → セル中心(ULXMAP/ULYMAP)に戻して書く
  write(un, '(a,1x,g0.15)') "ULXMAP        ", gr%xul + 0.5_real64 * gr%csx
  write(un, '(a,1x,g0.15)') "ULYMAP        ", gr%yul - 0.5_real64 * gr%csy
  write(un, '(a,1x,g0.15)') "XDIM          ", gr%csx
  write(un, '(a,1x,g0.15)') "YDIM          ", gr%csy
  close(un)

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! hdr の1行をキー(大文字化)と値文字列に分ける。空行・コメントはキー長0
!----------------------------------------------------------------------
subroutine split_keyval(line, key, val)
  character(len=*), intent(in) :: line
  character(:), allocatable, intent(out) :: key, val
  character(:), allocatable :: s
  integer :: i

  key = ""
  val = ""
  s = trim(adjustl(line))
  if (len(s) == 0) return
  if (s(1:1) == "#" .or. s(1:1) == ";") return
  ! 最初の空白・タブでキーと値に分ける
  do i = 1, len(s)
    if (s(i:i) == " " .or. s(i:i) == char(9)) exit
  end do
  key = s(1:i-1)
  call upcase(key)
  if (i <= len(s)) val = trim(adjustl(s(i:)))
end subroutine


!----------------------------------------------------------------------
subroutine upcase(s)
  character(:), allocatable, intent(inout) :: s
  integer :: i, c
  do i = 1, len(s)
    c = iachar(s(i:i))
    if (c >= iachar("a") .and. c <= iachar("z")) s(i:i) = achar(c - 32)
  end do
end subroutine


!----------------------------------------------------------------------
function to_int(fname, key, val) result(iv)
  character(len=*), intent(in) :: fname, key, val
  integer :: iv
  integer :: ios
  read(val, *, iostat=ios) iv
  if (ios /= 0) call par_stop("georef: "//key//" の値 '"//val// &
                              "' を整数として読めません: "//trim(fname))
end function


!----------------------------------------------------------------------
function to_real(fname, key, val) result(rv)
  character(len=*), intent(in) :: fname, key, val
  real(real64) :: rv
  integer :: ios
  read(val, *, iostat=ios) rv
  if (ios /= 0) call par_stop("georef: "//key//" の値 '"//val// &
                              "' を実数として読めません: "//trim(fname))
end function


end module
