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
  public :: t_esri_hdr
  public :: georef_hdr_name
  public :: georef_parse_hdr
  public :: georef_read_hdr
  public :: georef_write_hdr
  public :: georef_est_cellsize_m

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
    logical :: is_geog = .false.         ! 経緯度(度単位)グリッドと推測されるか
  end type

  ! ESRI hdr の生の解析結果(数値の妥当性・対応可否の検証は呼び出し側で
  ! 行う。m_fileio は rank0 単独の文脈でも呼ばれるため par_stop できない)
  type t_esri_hdr
    integer :: ncols = 0
    integer :: nrows = 0
    integer :: nbands = 1
    integer :: nbits = 32
    integer :: skipbytes = 0
    character(len=16) :: layout = "BIL"
    character(len=16) :: byteorder = "I"
    character(len=16) :: pixeltype = ""    ! 未指定は空(FLOAT/SIGNEDINT/UNSIGNEDINT)
    logical :: seen_grid = .false.         ! NCOLS と NROWS が揃っているか
    logical :: seen_geo = .false.          ! XDIM, YDIM, ULXMAP, ULYMAP が揃っているか
    real(real64) :: xdim = 0.0_real64
    real(real64) :: ydim = 0.0_real64
    real(real64) :: ulxmap = 0.0_real64
    real(real64) :: ulymap = 0.0_real64
    logical :: has_nodata = .false.
    real(real64) :: nodata = 0.0_real64
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
  ! 区切りは / と \(achar(92))。バックスラッシュをリテラルで書くと
  ! nvfortran が既定で C 風エスケープと解釈するため文字コードで書く
  isep = max(index(fname, "/", back=.true.), index(fname, achar(92), back=.true.))
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
  type(t_esri_hdr) :: h
  integer :: stat
  character(len=512) :: msg

  call georef_parse_hdr(fname, h, stat, msg)
  if (stat /= 0) call par_stop(trim(msg))
  if (.not. h%seen_grid) then
    call par_stop("georef: hdr に NCOLS/NROWS がありません: "//trim(fname))
  end if
  if (.not. h%seen_geo) then
    call par_stop("georef: hdr に必須キー(NCOLS, NROWS, XDIM, YDIM, "// &
                  "ULXMAP, ULYMAP)が揃っていません: "//trim(fname))
  end if
  if (h%ncols <= 0 .or. h%nrows <= 0) then
    call par_stop("georef: NCOLS/NROWS が不正です: "//trim(fname))
  end if
  if (h%xdim <= 0.0_real64 .or. h%ydim <= 0.0_real64) then
    call par_stop("georef: XDIM/YDIM が不正です: "//trim(fname))
  end if

  ncols = h%ncols
  nrows = h%nrows
  gr%has_nodata = h%has_nodata
  gr%nodata = h%nodata

  ! ULXMAP/ULYMAP はセル中心 → 外縁に変換して保持
  gr%xul = h%ulxmap - 0.5_real64 * h%xdim
  gr%yul = h%ulymap + 0.5_real64 * h%ydim
  gr%csx = h%xdim
  gr%csy = h%ydim
  gr%active = .true.

  ! 経緯度(度単位)グリッドの推測。hdr は CRS を持たないため、
  ! セル寸法が 0.1 度未満かつ原点が経緯度の値域内、で判定する
  ! (投影座標系のメートル格子でこれを満たすのは、CRS 原点至近を
  ! 10cm 未満のセルで切った場合のみで、実用上は起こらない)。
  ! GeoTIFF では CRS タグから確定的に判定する
  gr%is_geog = (h%xdim < 0.1_real64 .and. h%ydim < 0.1_real64 .and. &
                abs(h%ulymap) <= 90.0_real64 .and. abs(h%ulxmap) <= 360.0_real64)

end subroutine


!----------------------------------------------------------------------
! ESRI hdr を解析して生の値を返す(検証は呼び出し側)
!   キーは大文字小文字を問わない。未知キーは無視。解析できない値のみ
!   stat/=0(メッセージ付き)で返す
!----------------------------------------------------------------------
subroutine georef_parse_hdr(fname, h, stat, msg)
  character(len=*), intent(in) :: fname
  type(t_esri_hdr), intent(out) :: h
  integer, intent(out) :: stat
  character(len=*), intent(out) :: msg

  integer :: un, ios
  character(len=1024) :: line
  character(:), allocatable :: key, val
  logical :: seen_nc, seen_nr, seen_xd, seen_yd, seen_ux, seen_uy

  stat = 0
  msg = ""
  seen_nc = .false.; seen_nr = .false.
  seen_xd = .false.; seen_yd = .false.
  seen_ux = .false.; seen_uy = .false.

  open(newunit=un, file=fname, status='old', iostat=ios)
  if (ios /= 0) then
    stat = 1
    msg = "georef: hdr を開けません: "//trim(fname)
    return
  end if

  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    call split_keyval(line, key, val)
    if (len(key) == 0) cycle
    select case (key)
      case ("NCOLS")
        if (.not. geti(h%ncols)) exit
        seen_nc = .true.
      case ("NROWS")
        if (.not. geti(h%nrows)) exit
        seen_nr = .true.
      case ("NBANDS")
        if (.not. geti(h%nbands)) exit
      case ("NBITS")
        if (.not. geti(h%nbits)) exit
      case ("SKIPBYTES")
        if (.not. geti(h%skipbytes)) exit
      case ("XDIM")
        if (.not. getr(h%xdim)) exit
        seen_xd = .true.
      case ("YDIM")
        if (.not. getr(h%ydim)) exit
        seen_yd = .true.
      case ("ULXMAP")
        if (.not. getr(h%ulxmap)) exit
        seen_ux = .true.
      case ("ULYMAP")
        if (.not. getr(h%ulymap)) exit
        seen_uy = .true.
      case ("LAYOUT")
        call upcase(val)
        h%layout = val
      case ("BYTEORDER")
        call upcase(val)
        h%byteorder = val
      case ("PIXELTYPE")
        call upcase(val)
        h%pixeltype = val
      case ("NODATA", "NODATA_VALUE")
        if (.not. getr(h%nodata)) exit
        h%has_nodata = .true.
      case default
        ! 未知キー(BANDROWBYTES, TOTALROWBYTES 等)は無視
    end select
  end do
  close(un)
  if (stat /= 0) return

  h%seen_grid = seen_nc .and. seen_nr
  h%seen_geo = seen_xd .and. seen_yd .and. seen_ux .and. seen_uy

contains

  logical function geti(v)
    integer, intent(out) :: v
    integer :: ios2
    read(val, *, iostat=ios2) v
    geti = (ios2 == 0)
    if (.not. geti) then
      stat = 1
      msg = "georef: "//key//" の値 '"//val//"' を整数として読めません: "//trim(fname)
    end if
  end function

  logical function getr(v)
    real(real64), intent(out) :: v
    integer :: ios2
    read(val, *, iostat=ios2) v
    getr = (ios2 == 0)
    if (.not. getr) then
      stat = 1
      msg = "georef: "//key//" の値 '"//val//"' を実数として読めません: "//trim(fname)
    end if
  end function

end subroutine


!----------------------------------------------------------------------
! 経緯度グリッドのセル寸法(度)を、領域中央緯度でのメートル寸法に概算する
!   WGS84 の「緯度1度あたりの子午線弧長」「経度1度あたりの平行圏弧長」の
!   標準近似式による。dx, dy の妥当性検査と画面表示用の概算であり、
!   測地計算の厳密さは要求しない
!----------------------------------------------------------------------
subroutine georef_est_cellsize_m(gr, ny, dxm, dym)
  type(t_georef), intent(in) :: gr
  integer, intent(in) :: ny                ! 行数(領域中央緯度の算出用)
  real(real64), intent(out) :: dxm, dym    ! 概算セル寸法(m)
  real(real64), parameter :: d2r = 3.14159265358979324_real64 / 180.0_real64
  real(real64) :: phi, mlat, mlon

  phi = (gr%yul - 0.5_real64 * ny * gr%csy) * d2r    ! 領域中央の緯度
  mlat = 111132.92_real64 - 559.82_real64 * cos(2*phi) &
         + 1.175_real64 * cos(4*phi) - 0.0023_real64 * cos(6*phi)
  mlon = 111412.84_real64 * cos(phi) - 93.5_real64 * cos(3*phi) &
         + 0.118_real64 * cos(5*phi)
  dxm = gr%csx * mlon
  dym = gr%csy * mlat
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
  ! 外縁 → セル中心(ULXMAP/ULYMAP)に戻して書く。
  ! 指数表記を解さない読み手を考慮して固定小数で書く(小数 12 桁は
  ! 経緯度で 1e-7 m 級、メートル座標で 1e-9 m 級の桁を保持する)
  write(un, '(a,1x,a)') "ULXMAP        ", ftoa(gr%xul + 0.5_real64 * gr%csx)
  write(un, '(a,1x,a)') "ULYMAP        ", ftoa(gr%yul - 0.5_real64 * gr%csy)
  write(un, '(a,1x,a)') "XDIM          ", ftoa(gr%csx)
  write(un, '(a,1x,a)') "YDIM          ", ftoa(gr%csy)
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
  ! Windows で作られた hdr(CRLF)対策: 行末の CR を除去
  ! (フォーマット読みが CR を落とすかは処理系依存のため明示的に行う)
  if (len(s) > 0) then
    if (s(len(s):len(s)) == achar(13)) s = trim(s(1:len(s)-1))
  end if
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
! 座標値の固定小数文字列化(小数 12 桁)
!   f0 編集は 1 未満の値で先頭のゼロを省く(.001 等)処理系があるため、
!   "0." 始まりをここで保証する
!----------------------------------------------------------------------
function ftoa(v) result(s)
  real(real64), intent(in) :: v
  character(:), allocatable :: s
  character(len=40) :: buf
  write(buf, '(f0.12)') v
  s = trim(adjustl(buf))
  if (s(1:1) == ".") then
    s = "0"//s
  else if (len(s) >= 2) then
    if (s(1:2) == "-.") s = "-0"//s(2:)
  end if
end function


end module
