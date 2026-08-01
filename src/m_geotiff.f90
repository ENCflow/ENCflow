!======================================================================
! m_geotiff: GeoTIFF リーダー(書き込みは Phase 3 で追加予定)
!   対応範囲(docs/geotiff_plan.md §2, §8。QGIS/ArcGIS 産の1バンドを想定):
!   - classic TIFF(BigTIFF は Phase 4)。両バイト順(II/MM)
!   - 画素型: u8 / i16 / u16 / i32 / u32 / f32 / f64(1 バンドのみ)
!   - 圧縮: 無圧縮 / PackBits / LZW(Deflate は Phase 2)
!   - predictor: 1 / 2(水平差分)/ 3(浮動小数点)
!   - 配置: strip / tile(端数タイルは有効域のみ取り込む)
!   - 位置情報: ModelPixelScale + ModelTiepoint、GeoKey の EPSG、
!     GDAL_NODATA。行順は北→南(既存の txt/bil と同じ並びで格納)
!   対応範囲外は黙って誤読せず、メッセージ付きの stat/=0 で返す。
!
!   設計上の約束(§6.1):
!   - ENCflow 本体のどのモジュールにも依存しない(m_geotiff_codec のみ)。
!     エラーは stat とメッセージで返し、abort は呼び出し側が決める。
!   - 座標値は real64。正本は「北西隅セルの外縁」(m_georef と同じ表現。
!     GTRasterTypeGeoKey=PixelIsPoint はセル中心指定なので読み時に変換)
!======================================================================
module m_geotiff
  use, intrinsic :: iso_fortran_env, only : int8, int16, int32, int64, real32, real64
  use m_geotiff_codec, only : gtc_packbits_decode, gtc_lzw_decode, &
                              gtc_undo_predictor2, gtc_undo_predictor3
  implicit none
  private

  public :: t_gtif_info
  public :: gtif_inquire
  public :: gtif_read

  ! 読み取りメタ情報(gtif_inquire / gtif_read が返す)
  type t_gtif_info
    integer :: nx = 0
    integer :: ny = 0
    logical :: is_real = .false.         ! 実数系(SampleFormat=float)か
    logical :: has_nodata = .false.
    real(real64) :: nodata = 0.0_real64
    logical :: has_georef = .false.
    real(real64) :: xul = 0.0_real64     ! 北西隅セル外縁の x 座標
    real(real64) :: yul = 0.0_real64     ! 北西隅セル外縁の y 座標
    real(real64) :: csx = 0.0_real64     ! セル寸法 x
    real(real64) :: csy = 0.0_real64     ! セル寸法 y(> 0。南向きの幅)
    integer :: epsg = 0                  ! 0 = 不明/ユーザー定義
    logical :: is_geog = .false.         ! 経緯度(度単位)か
  end type

  interface gtif_read
    procedure :: gtif_read_real
    procedure :: gtif_read_int
  end interface

  ! IFD エントリ(値/オフセット部は生 4 バイトで保持し、必要時に解釈)
  type t_ent
    integer :: tag = 0
    integer :: typ = 0
    integer(int64) :: cnt = 0
    integer(int8) :: raw(4) = 0
  end type

  ! 解析済み TIFF(内部)
  type t_tif
    integer :: un = -1
    logical :: be = .false.              ! ビッグエンディアン(MM)か
    integer :: nx = 0, ny = 0
    integer :: comp = 1                  ! Compression
    integer :: pred = 1                  ! Predictor
    integer :: bits = 0                  ! BitsPerSample
    integer :: sfmt = 1                  ! SampleFormat(1:uint, 2:int, 3:float)
    logical :: tiled = .false.
    integer :: bw = 0, bh = 0            ! ブロック(strip/tile)の幅・高さ
    integer(int64), allocatable :: off(:), cnt(:)
    type(t_gtif_info) :: info
  end type

  ! TIFF タグ型のバイトサイズ(1:BYTE 2:ASCII 3:SHORT 4:LONG 5:RATIONAL
  !  6:SBYTE 7:UNDEF 8:SSHORT 9:SLONG 10:SRATIONAL 11:FLOAT 12:DOUBLE)
  integer, parameter :: typesize(12) = [1, 1, 2, 4, 8, 1, 1, 2, 4, 8, 4, 8]

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! メタ情報のみ取得する(画素は読まない。圧縮方式が未対応でも成功する)
!----------------------------------------------------------------------
subroutine gtif_inquire(fname, info, stat, msg)
  character(len=*), intent(in) :: fname
  type(t_gtif_info), intent(out) :: info
  integer, intent(out) :: stat
  character(len=*), intent(out) :: msg

  type(t_tif) :: t

  call open_parse(fname, t, stat, msg)
  info = t%info
  if (t%un >= 0) close(t%un)
end subroutine


!----------------------------------------------------------------------
! 全域読み(実数)。整数型の GeoTIFF も実数へ変換して読める
!----------------------------------------------------------------------
subroutine gtif_read_real(fname, nx, ny, a, stat, msg, info)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  real, intent(inout) :: a(1:nx,1:ny)
  integer, intent(out) :: stat
  character(len=*), intent(out) :: msg
  type(t_gtif_info), intent(out), optional :: info

  type(t_tif) :: t
  integer :: idum(1,1)

  call open_parse(fname, t, stat, msg)
  if (stat == 0) call check_dims(t, nx, ny, fname, stat, msg)
  if (stat == 0) call decode_blocks(t, .true., a, idum, fname, stat, msg)
  if (present(info)) info = t%info
  if (t%un >= 0) close(t%un)
end subroutine


!----------------------------------------------------------------------
! 全域読み(整数)。実数型の GeoTIFF はエラー(丸めの黙認をしない)
!----------------------------------------------------------------------
subroutine gtif_read_int(fname, nx, ny, a, stat, msg, info)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  integer, intent(inout) :: a(1:nx,1:ny)
  integer, intent(out) :: stat
  character(len=*), intent(out) :: msg
  type(t_gtif_info), intent(out), optional :: info

  type(t_tif) :: t
  real :: rdum(1,1)

  call open_parse(fname, t, stat, msg)
  if (stat == 0) call check_dims(t, nx, ny, fname, stat, msg)
  if (stat == 0) then
    if (t%sfmt == 3) then
      call set_err(stat, msg, "実数型の GeoTIFF は整数入力に使えません: "//trim(fname))
    end if
  end if
  if (stat == 0) call decode_blocks(t, .false., rdum, a, fname, stat, msg)
  if (present(info)) info = t%info
  if (t%un >= 0) close(t%un)
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

subroutine set_err(stat, msg, text)
  integer, intent(out) :: stat
  character(len=*), intent(out) :: msg
  character(len=*), intent(in) :: text
  stat = 1
  msg = text
end subroutine


subroutine check_dims(t, nx, ny, fname, stat, msg)
  type(t_tif), intent(in) :: t
  integer, intent(in) :: nx, ny
  character(len=*), intent(in) :: fname
  integer, intent(out) :: stat
  character(len=*), intent(out) :: msg
  stat = 0
  msg = ""
  if (t%nx /= nx .or. t%ny /= ny) then
    call set_err(stat, msg, "格子数が一致しません(ファイル "//itoa(t%nx)//"x" &
                 //itoa(t%ny)//" / 要求 "//itoa(nx)//"x"//itoa(ny)//"): "//trim(fname))
  end if
end subroutine


!----------------------------------------------------------------------
! ファイルを開いてヘッダ・IFD・タグを解析し、t を構築する
!   画素データには触れない(圧縮方式の対応可否は decode_blocks で検査)
!----------------------------------------------------------------------
subroutine open_parse(fname, t, stat, msg)
  character(len=*), intent(in) :: fname
  type(t_tif), intent(out) :: t
  integer, intent(out) :: stat
  character(len=*), intent(out) :: msg

  integer(int8) :: h(8)
  integer :: ios, nent, i, magic
  integer(int64) :: ifdoff, nblocks, ntx, nty
  type(t_ent), allocatable :: ents(:)
  integer(int64), allocatable :: iv(:)
  real(real64), allocatable :: dv(:)
  integer :: spp, photo, rastertype, modeltype
  integer(int64) :: rps

  stat = 0
  msg = ""

  open(newunit=t%un, file=fname, form='unformatted', access='stream', &
       status='old', iostat=ios)
  if (ios /= 0) then
    t%un = -1
    call set_err(stat, msg, "GeoTIFF を開けません: "//trim(fname))
    return
  end if

  ! --- ヘッダ(バイト順・magic・IFD オフセット) ---
  read(t%un, pos=1, iostat=ios) h
  if (ios /= 0) then
    call set_err(stat, msg, "GeoTIFF ヘッダを読めません: "//trim(fname))
    return
  end if
  if (h(1) == iachar("I") .and. h(2) == iachar("I")) then
    t%be = .false.
  else if (h(1) == iachar("M") .and. h(2) == iachar("M")) then
    t%be = .true.
  else
    call set_err(stat, msg, "TIFF ではありません(バイト順識別子が不正): "//trim(fname))
    return
  end if
  magic = int(bytes_u(h(3:4), t%be))
  if (magic == 43) then
    call set_err(stat, msg, "BigTIFF は未対応です(Phase 4 で対応予定): "//trim(fname))
    return
  else if (magic /= 42) then
    call set_err(stat, msg, "TIFF ではありません(magic="//itoa(magic)//"): "//trim(fname))
    return
  end if
  ifdoff = bytes_u(h(5:8), t%be)

  ! --- 先頭 IFD のエントリ表(後続 IFD = オーバービュー等は読まない) ---
  block
    integer(int8) :: b2(2), b12(12)
    read(t%un, pos=ifdoff+1, iostat=ios) b2
    if (ios /= 0) then
      call set_err(stat, msg, "IFD を読めません: "//trim(fname))
      return
    end if
    nent = int(bytes_u(b2, t%be))
    allocate(ents(nent))
    do i = 1, nent
      read(t%un, pos=ifdoff+3+(i-1)*12, iostat=ios) b12
      if (ios /= 0) then
        call set_err(stat, msg, "IFD エントリを読めません: "//trim(fname))
        return
      end if
      ents(i)%tag = int(bytes_u(b12(1:2), t%be))
      ents(i)%typ = int(bytes_u(b12(3:4), t%be))
      ents(i)%cnt = bytes_u(b12(5:8), t%be)
      ents(i)%raw = b12(9:12)
    end do
  end block

  ! --- 必須・既定付きタグ ---
  t%nx = int(tag_int1(ents, 256, t%be, 0_int64))
  t%ny = int(tag_int1(ents, 257, t%be, 0_int64))
  if (t%nx <= 0 .or. t%ny <= 0) then
    call set_err(stat, msg, "ImageWidth/ImageLength がありません: "//trim(fname))
    return
  end if
  spp = int(tag_int1(ents, 277, t%be, 1_int64))
  if (spp /= 1) then
    call set_err(stat, msg, "多バンド("//itoa(spp)//"バンド)は未対応です(1バンドのみ): "//trim(fname))
    return
  end if
  photo = int(tag_int1(ents, 262, t%be, 1_int64))
  if (photo > 1) then
    call set_err(stat, msg, "PhotometricInterpretation="//itoa(photo)// &
                 " は未対応です(グレースケールのみ): "//trim(fname))
    return
  end if
  t%bits = int(tag_int1(ents, 258, t%be, 1_int64))
  t%sfmt = int(tag_int1(ents, 339, t%be, 1_int64))
  t%comp = int(tag_int1(ents, 259, t%be, 1_int64))
  t%pred = int(tag_int1(ents, 317, t%be, 1_int64))
  select case (t%bits)
    case (8, 16, 32)
      if (t%sfmt == 3 .and. t%bits /= 32) then
        call set_err(stat, msg, "実数 "//itoa(t%bits)//"bit は未対応です: "//trim(fname))
        return
      end if
    case (64)
      if (t%sfmt /= 3) then
        call set_err(stat, msg, "整数 64bit は未対応です: "//trim(fname))
        return
      end if
    case default
      call set_err(stat, msg, "BitsPerSample="//itoa(t%bits)//" は未対応です: "//trim(fname))
      return
  end select
  if (t%sfmt < 1 .or. t%sfmt > 3) then
    call set_err(stat, msg, "SampleFormat="//itoa(t%sfmt)//" は未対応です: "//trim(fname))
    return
  end if

  ! --- strip / tile の配置 ---
  if (find_ent(ents, 322) > 0) then
    t%tiled = .true.
    t%bw = int(tag_int1(ents, 322, t%be, 0_int64))
    t%bh = int(tag_int1(ents, 323, t%be, 0_int64))
    if (t%bw <= 0 .or. t%bh <= 0) then
      call set_err(stat, msg, "TileWidth/TileLength が不正です: "//trim(fname))
      return
    end if
    call tag_ints(t%un, ents, 324, t%be, t%off, stat)
    if (stat == 0) call tag_ints(t%un, ents, 325, t%be, t%cnt, stat)
    if (stat /= 0) then
      call set_err(stat, msg, "TileOffsets/TileByteCounts を読めません: "//trim(fname))
      return
    end if
    ntx = (t%nx + t%bw - 1) / t%bw
    nty = (t%ny + t%bh - 1) / t%bh
    nblocks = ntx * nty
  else
    t%tiled = .false.
    t%bw = t%nx
    rps = tag_int1(ents, 278, t%be, 4294967295_int64)
    t%bh = int(min(rps, int(t%ny, int64)))
    call tag_ints(t%un, ents, 273, t%be, t%off, stat)
    if (stat /= 0) then
      call set_err(stat, msg, "StripOffsets を読めません: "//trim(fname))
      return
    end if
    nblocks = (t%ny + t%bh - 1) / t%bh
    if (find_ent(ents, 279) > 0) then
      call tag_ints(t%un, ents, 279, t%be, t%cnt, stat)
      if (stat /= 0) then
        call set_err(stat, msg, "StripByteCounts を読めません: "//trim(fname))
        return
      end if
    else if (t%comp == 1) then             ! 無圧縮なら計算で補える
      allocate(t%cnt(nblocks))
      do i = 1, int(nblocks)
        t%cnt(i) = int(t%bw, int64) * min(t%bh, t%ny - (i-1)*t%bh) * (t%bits/8)
      end do
    else
      call set_err(stat, msg, "StripByteCounts がありません: "//trim(fname))
      return
    end if
  end if
  if (size(t%off, kind=int64) /= nblocks .or. size(t%cnt, kind=int64) /= nblocks) then
    call set_err(stat, msg, "strip/tile の数がタグと一致しません: "//trim(fname))
    return
  end if

  ! --- メタ情報 ---
  t%info%nx = t%nx
  t%info%ny = t%ny
  t%info%is_real = (t%sfmt == 3)

  ! GDAL_NODATA(ASCII)
  block
    character(:), allocatable :: s
    real(real64) :: v
    call tag_ascii(t%un, ents, 42113, t%be, s, stat)
    stat = 0                               ! 読めなければ無いものとして扱う
    if (allocated(s)) then
      if (len_trim(s) > 0) then
        read(s, *, iostat=ios) v
        if (ios == 0) then
          t%info%has_nodata = .true.
          t%info%nodata = v
        end if
      end if
    end if
  end block

  ! 位置情報: ModelPixelScale + ModelTiepoint
  ! (ModelTransformation のみのファイルは位置情報なしとして扱う)
  rastertype = 1
  modeltype = 0
  if (find_ent(ents, 33550) > 0 .and. find_ent(ents, 33922) > 0) then
    call tag_dbls(t%un, ents, 33550, t%be, dv, stat)
    if (stat /= 0 .or. size(dv) < 2) then
      call set_err(stat, msg, "ModelPixelScaleTag を読めません: "//trim(fname))
      return
    end if
    t%info%csx = dv(1)
    t%info%csy = dv(2)
    call tag_dbls(t%un, ents, 33922, t%be, dv, stat)
    if (stat /= 0 .or. size(dv) < 6) then
      call set_err(stat, msg, "ModelTiepointTag を読めません: "//trim(fname))
      return
    end if
    if (t%info%csx > 0.0_real64 .and. t%info%csy > 0.0_real64) then
      ! タイポイント(ラスタ座標 i,j → モデル座標 x,y)を北西隅外縁に換算
      t%info%xul = dv(4) - dv(1) * t%info%csx
      t%info%yul = dv(5) + dv(2) * t%info%csy
      t%info%has_georef = .true.
    end if
  end if

  ! GeoKey(CRS)。EPSG と経緯度判定に使う
  if (find_ent(ents, 34735) > 0) then
    call tag_ints(t%un, ents, 34735, t%be, iv, stat)
    if (stat /= 0 .or. size(iv) < 4) then
      call set_err(stat, msg, "GeoKeyDirectoryTag を読めません: "//trim(fname))
      return
    end if
    do i = 1, int(iv(4))                   ! iv(1:4) はヘッダ、以降 4 要素/キー
      if (4*i + 4 > size(iv)) exit
      block
        integer :: keyid, loc, val
        keyid = int(iv(4*i+1))
        loc = int(iv(4*i+2))
        val = int(iv(4*i+4))
        if (loc == 0) then                 ! 値が直接入っているキーのみ使う
          select case (keyid)
            case (1024)                    ! GTModelTypeGeoKey
              modeltype = val
            case (1025)                    ! GTRasterTypeGeoKey
              rastertype = val
            case (2048)                    ! GeographicTypeGeoKey
              if (modeltype == 2 .and. val > 0 .and. val < 32767) t%info%epsg = val
            case (3072)                    ! ProjectedCSTypeGeoKey
              if (val > 0 .and. val < 32767) t%info%epsg = val
          end select
        end if
      end block
    end do
  end if

  ! PixelIsPoint(=2)はタイポイントがセル中心を指すので外縁に半セルずらす
  if (t%info%has_georef .and. rastertype == 2) then
    t%info%xul = t%info%xul - 0.5_real64 * t%info%csx
    t%info%yul = t%info%yul + 0.5_real64 * t%info%csy
  end if

  ! 経緯度判定: CRS が地理系ならそれを正、無ければ hdr と同じヒューリスティック
  if (modeltype == 2) then
    t%info%is_geog = .true.
  else if (modeltype == 1) then
    t%info%is_geog = .false.
  else if (t%info%has_georef) then
    t%info%is_geog = (t%info%csx < 0.1_real64 .and. t%info%csy < 0.1_real64 .and. &
                      abs(t%info%yul) <= 90.0_real64 .and. abs(t%info%xul) <= 360.0_real64)
  end if

end subroutine


!----------------------------------------------------------------------
! 全ブロック(strip/tile)を復号して出力配列に展開する
!   want_real: .true. なら ar へ、.false. なら ai へ書く
!----------------------------------------------------------------------
subroutine decode_blocks(t, want_real, ar, ai, fname, stat, msg)
  type(t_tif), intent(in) :: t
  logical, intent(in) :: want_real
  real, intent(inout) :: ar(:,:)
  integer, intent(inout) :: ai(:,:)
  character(len=*), intent(in) :: fname
  integer, intent(out) :: stat
  character(len=*), intent(out) :: msg

  integer(int8), allocatable :: ubuf(:), cbuf(:)
  integer(int64) :: nblocks, need, pos
  integer :: ib, ntx, bx, by, rows, cols, r, c, gx, gy, bpb, ios
  integer(int64) :: v
  real(real64) :: rv
  logical :: be_eff

  stat = 0
  msg = ""

  ! 圧縮方式の対応可否(メタ取得は許すが、画素読みはここで検査)
  select case (t%comp)
    case (1, 5, 32773)                     ! 無圧縮 / LZW / PackBits
    case (8, 32946)
      call set_err(stat, msg, "Deflate 圧縮は未対応です(Phase 2 で対応予定): "//trim(fname))
      return
    case (6, 7)
      call set_err(stat, msg, "JPEG 系圧縮は対象外です: "//trim(fname))
      return
    case default
      call set_err(stat, msg, "Compression="//itoa(t%comp)//" は未対応です: "//trim(fname))
      return
  end select
  if (t%pred < 1 .or. t%pred > 3) then
    call set_err(stat, msg, "Predictor="//itoa(t%pred)//" は未対応です: "//trim(fname))
    return
  end if
  if (t%pred == 3 .and. t%sfmt /= 3) then
    call set_err(stat, msg, "整数への Predictor=3 は未対応です: "//trim(fname))
    return
  end if

  bpb = t%bits / 8
  ntx = (t%nx + t%bw - 1) / t%bw
  nblocks = size(t%off, kind=int64)
  allocate(ubuf(int(t%bw, int64) * t%bh * bpb))

  do ib = 1, int(nblocks)
    bx = mod(ib-1, ntx)                    ! tile は左→右、上→下の順
    by = (ib-1) / ntx
    cols = min(t%bw, t%nx - bx*t%bw)
    rows = min(t%bh, t%ny - by*t%bh)
    if (t%tiled) then
      need = int(t%bw, int64) * t%bh * bpb ! tile は端数でも常にフルサイズ
    else
      need = int(t%bw, int64) * rows * bpb
    end if
    if (t%off(ib) == 0) then
      call set_err(stat, msg, "スパース(未書き込みブロック)は未対応です: "//trim(fname))
      return
    end if

    select case (t%comp)
      case (1)
        if (t%cnt(ib) < need) then
          call set_err(stat, msg, "ブロック"//itoa(ib)//"のバイト数が不足しています: "//trim(fname))
          return
        end if
        read(t%un, pos=t%off(ib)+1, iostat=ios) ubuf(1:need)
        if (ios /= 0) then
          call set_err(stat, msg, "ブロック"//itoa(ib)//"を読めません: "//trim(fname))
          return
        end if
      case default
        if (allocated(cbuf)) deallocate(cbuf)
        allocate(cbuf(t%cnt(ib)))
        read(t%un, pos=t%off(ib)+1, iostat=ios) cbuf
        if (ios /= 0) then
          call set_err(stat, msg, "ブロック"//itoa(ib)//"を読めません: "//trim(fname))
          return
        end if
        if (t%comp == 5) then
          call gtc_lzw_decode(cbuf, ubuf(1:need), stat)
        else
          call gtc_packbits_decode(cbuf, ubuf(1:need), stat)
        end if
        if (stat /= 0) then
          call set_err(stat, msg, "ブロック"//itoa(ib)//"の復号に失敗しました(圧縮データ破損): " &
                       //trim(fname))
          return
        end if
    end select

    ! predictor 復元(行幅はブロック幅)
    be_eff = t%be
    if (t%pred == 2) then
      call gtc_undo_predictor2(ubuf(1:need), t%bw, int(need/(int(t%bw,int64)*bpb)), bpb, t%be)
    else if (t%pred == 3) then
      call gtc_undo_predictor3(ubuf(1:need), t%bw, int(need/(int(t%bw,int64)*bpb)), bpb)
      be_eff = .true.                      ! 復元後はビッグエンディアン並び
    end if

    ! 有効域を出力配列へ(TIFF の行 1 = 北端。既存 txt/bil と同じ並び)
    do r = 1, rows
      gy = by*t%bh + r
      do c = 1, cols
        gx = bx*t%bw + c
        pos = (int(r-1, int64)*t%bw + (c-1)) * bpb
        if (want_real) then
          call sample_real(ubuf, pos, t%bits, t%sfmt, be_eff, rv)
          ar(gx, gy) = real(rv)
        else
          call sample_int(ubuf, pos, t%bits, t%sfmt, be_eff, v)
          if (v > int(huge(0), int64) .or. v < -int(huge(0), int64) - 1) then
            call set_err(stat, msg, "値 "//i64toa(v)//" が既定 integer の範囲外です: "//trim(fname))
            return
          end if
          ai(gx, gy) = int(v)
        end if
      end do
    end do
  end do

end subroutine


!----------------------------------------------------------------------
! 1 サンプルの取り出し(pos は ubuf 内の 0 始まりバイト位置)
!----------------------------------------------------------------------
subroutine sample_int(buf, pos, bits, sfmt, be, v)
  integer(int8), intent(in) :: buf(:)
  integer(int64), intent(in) :: pos
  integer, intent(in) :: bits, sfmt
  logical, intent(in) :: be
  integer(int64), intent(out) :: v

  v = bytes_u(buf(pos+1:pos+bits/8), be)   ! ゼロ拡張(符号なし解釈)
  if (sfmt == 2) then                      ! 符号付きは幅に応じて符号拡張
    select case (bits)
      case (8)
        if (v > 127_int64) v = v - 256_int64
      case (16)
        if (v > 32767_int64) v = v - 65536_int64
      case (32)
        if (v > 2147483647_int64) v = v - 4294967296_int64
    end select
  end if
end subroutine


subroutine sample_real(buf, pos, bits, sfmt, be, v)
  integer(int8), intent(in) :: buf(:)
  integer(int64), intent(in) :: pos
  integer, intent(in) :: bits, sfmt
  logical, intent(in) :: be
  real(real64), intent(out) :: v

  integer(int64) :: u

  if (sfmt == 3) then
    u = bytes_u(buf(pos+1:pos+bits/8), be)
    if (bits == 32) then
      v = real(transfer(int(u, int32), 0.0_real32), real64)
    else                                   ! 64bit: ビット列を int64 に集める
      u = bytes_u64(buf(pos+1:pos+8), be)
      v = transfer(u, 0.0_real64)
    end if
  else
    call sample_int(buf, pos, bits, sfmt, be, u)
    v = real(u, real64)
  end if
end subroutine


!----------------------------------------------------------------------
! バイト列 → 符号なし整数(int64 にゼロ拡張。n <= 4)
!----------------------------------------------------------------------
pure function bytes_u(b, be) result(v)
  integer(int8), intent(in) :: b(:)
  logical, intent(in) :: be
  integer(int64) :: v
  integer :: k
  v = 0
  if (be) then
    do k = 1, size(b)
      v = ior(ishft(v, 8), int(iand(int(b(k), int32), 255), int64))
    end do
  else
    do k = size(b), 1, -1
      v = ior(ishft(v, 8), int(iand(int(b(k), int32), 255), int64))
    end do
  end if
end function

! 8 バイト版(int64 のビットパターンとして集める。f64 用)
pure function bytes_u64(b, be) result(v)
  integer(int8), intent(in) :: b(8)
  logical, intent(in) :: be
  integer(int64) :: v
  integer :: k
  v = 0
  if (be) then
    do k = 1, 8
      v = ior(ishft(v, 8), int(iand(int(b(k), int32), 255), int64))
    end do
  else
    do k = 8, 1, -1
      v = ior(ishft(v, 8), int(iand(int(b(k), int32), 255), int64))
    end do
  end if
end function


!----------------------------------------------------------------------
! タグアクセス(IFD エントリ表から)
!----------------------------------------------------------------------
pure function find_ent(ents, tag) result(idx)
  type(t_ent), intent(in) :: ents(:)
  integer, intent(in) :: tag
  integer :: idx, i
  idx = 0
  do i = 1, size(ents)
    if (ents(i)%tag == tag) then
      idx = i
      return
    end if
  end do
end function


! スカラー整数タグ(なければ default)。値はインライン格納のみを想定
! (SHORT/LONG の count=1 は常に 4 バイト内に収まる。インライン値は
!  値フィールドの先頭側に詰められるので、型サイズ分をバイト順で解釈)
pure function tag_int1(ents, tag, be, default) result(v)
  type(t_ent), intent(in) :: ents(:)
  integer, intent(in) :: tag
  logical, intent(in) :: be
  integer(int64), intent(in) :: default
  integer(int64) :: v
  integer :: i
  v = default
  i = find_ent(ents, tag)
  if (i == 0) return
  select case (ents(i)%typ)
    case (3, 8)                            ! SHORT / SSHORT
      v = bytes_u(ents(i)%raw(1:2), be)
    case (1, 6)                            ! BYTE / SBYTE
      v = bytes_u(ents(i)%raw(1:1), be)
    case default                           ! LONG / SLONG
      v = bytes_u(ents(i)%raw(1:4), be)
  end select
end function


! 整数配列タグ(BYTE/SHORT/LONG)。インライン・オフセット両対応
subroutine tag_ints(un, ents, tag, be, v, stat)
  integer, intent(in) :: un
  type(t_ent), intent(in) :: ents(:)
  integer, intent(in) :: tag
  logical, intent(in) :: be
  integer(int64), allocatable, intent(out) :: v(:)
  integer, intent(out) :: stat

  integer :: i, k, esz, ios
  integer(int64) :: n, off
  integer(int8), allocatable :: b(:)

  stat = 1
  i = find_ent(ents, tag)
  if (i == 0) return
  if (ents(i)%typ < 1 .or. ents(i)%typ > 12) return
  esz = typesize(ents(i)%typ)
  if (esz > 4) return                      ! 整数タグは 1/2/4 バイト型のみ
  n = ents(i)%cnt
  if (n <= 0) return
  allocate(b(n*esz))
  if (n*esz <= 4) then
    b(1:n*esz) = ents(i)%raw(1:n*esz)
  else
    off = bytes_u(ents(i)%raw, be)
    read(un, pos=off+1, iostat=ios) b
    if (ios /= 0) return
  end if
  allocate(v(n))
  do k = 1, int(n)
    v(k) = bytes_u(b((k-1)*esz+1:k*esz), be)
  end do
  stat = 0
end subroutine


! DOUBLE 配列タグ(GeoTIFF の座標タグ用。常にオフセット格納)
subroutine tag_dbls(un, ents, tag, be, v, stat)
  integer, intent(in) :: un
  type(t_ent), intent(in) :: ents(:)
  integer, intent(in) :: tag
  logical, intent(in) :: be
  real(real64), allocatable, intent(out) :: v(:)
  integer, intent(out) :: stat

  integer :: i, k, ios
  integer(int64) :: n, off
  integer(int8), allocatable :: b(:)

  stat = 1
  i = find_ent(ents, tag)
  if (i == 0) return
  if (ents(i)%typ /= 12) return            ! DOUBLE のみ
  n = ents(i)%cnt
  if (n <= 0) return
  allocate(b(n*8))
  off = bytes_u(ents(i)%raw, be)
  read(un, pos=off+1, iostat=ios) b
  if (ios /= 0) return
  allocate(v(n))
  do k = 1, int(n)
    v(k) = transfer(bytes_u64(b((k-1)*8+1:k*8), be), 0.0_real64)
  end do
  stat = 0
end subroutine


! ASCII タグ(GDAL_NODATA 用)。インライン・オフセット両対応
subroutine tag_ascii(un, ents, tag, be, s, stat)
  integer, intent(in) :: un
  type(t_ent), intent(in) :: ents(:)
  integer, intent(in) :: tag
  logical, intent(in) :: be
  character(:), allocatable, intent(out) :: s
  integer, intent(out) :: stat

  integer :: i, k, ios
  integer(int64) :: n, off
  integer(int8), allocatable :: b(:)

  stat = 1
  i = find_ent(ents, tag)
  if (i == 0) return
  n = ents(i)%cnt
  if (n <= 0) return
  allocate(b(n))
  if (n <= 4) then
    b(1:n) = ents(i)%raw(1:n)
  else
    off = bytes_u(ents(i)%raw, be)
    read(un, pos=off+1, iostat=ios) b
    if (ios /= 0) return
  end if
  allocate(character(len=int(n)) :: s)
  do k = 1, int(n)
    if (b(k) == 0) then                    ! NUL 終端
      s = s(1:k-1)
      exit
    end if
    s(k:k) = achar(iand(int(b(k), int32), 255))
  end do
  stat = 0
end subroutine


!----------------------------------------------------------------------
! 数値の文字列化(本体に依存しないためモジュール私有で持つ)
!----------------------------------------------------------------------
pure function itoa(i) result(s)
  integer, intent(in) :: i
  character(:), allocatable :: s
  character(len=16) :: buf
  write(buf, '(i0)') i
  s = trim(buf)
end function

pure function i64toa(i) result(s)
  integer(int64), intent(in) :: i
  character(:), allocatable :: s
  character(len=24) :: buf
  write(buf, '(i0)') i
  s = trim(buf)
end function

end module
