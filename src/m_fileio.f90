module m_fileio
  use, intrinsic :: iso_fortran_env, only: real32, int8, int16, int32, int64
  use m_geotiff, only : gtif_read, gtif_write, t_gtif_info
  use m_georef, only : t_georef, t_esri_hdr, georef_hdr_name, georef_parse_hdr
  use m_util, only : itoa
  use m_parallel, only : par_abort

  implicit none
  private

  public :: fileio_read_matrix
  public :: fileio_write_matrix
  public :: fileio_un_open
  public :: fileio_un_read_matrix
  public :: fileio_write_rle
  public :: fileio_read_rle



  interface fileio_read_matrix
    procedure :: fileio_read_matrix_int
    procedure :: fileio_read_matrix_real
  end interface

  interface fileio_write_matrix
    procedure :: fileio_write_matrix_int
    procedure :: fileio_write_matrix_real
  end interface

  ! ゼロ抑制 RLE(save/restore 用。developer.md §7)
  interface fileio_write_rle
    procedure :: fileio_write_rle2
    procedure :: fileio_write_rle3
  end interface

  interface fileio_read_rle
    procedure :: fileio_read_rle2
    procedure :: fileio_read_rle3
  end interface

  ! RLE のゼロ判定に使う、既定 real と同サイズの整数 kind(PREC 連動)
  integer, parameter :: rle_ik = merge(int64, int32, storage_size(0.0) == 64)


  ! enumerator(値はビットフラグを兼ねる。f_output_mode はこのビット和)
  integer, parameter, public :: e_fmt_txt = 1
  integer, parameter, public :: e_fmt_bil = 2
  integer, parameter, public :: e_fmt_gtif = 4

contains

!----------------------------------------------------------------------
!----------------------------------------------------------------------
function fileio_un_open(fname, e_fmt) result(un)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: e_fmt
  integer :: un

  select case (e_fmt)
    case (e_fmt_txt)
      open(newunit=un, file=fname, status='old')
    case (e_fmt_bil)
      open(newunit=un,file=fname, form='unformatted', status='old', access='stream')
    case (e_fmt_gtif)
      un = -1
      call par_abort("GeoTIFF は逐次読み(precip の maplist)に使えません。txt か bil を指定してください")
    case default
      open(newunit=un, file=fname, status='old')
  end select

end function


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine fileio_un_read_matrix(un, nx, ny, a, e_fmt)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  real, intent(inout) :: a(1:nx,1:ny)
  integer, intent(in) :: e_fmt

  select case (e_fmt)
    case (e_fmt_txt)
      call read_textmatrix_real(un, nx, ny, a)
    case (e_fmt_bil)
      call read_bil_real(un, nx, ny, a)
    case default
      call read_textmatrix_real(un, nx, ny, a)
  end select

end subroutine



!======================================================================
!======================================================================
!======================================================================
!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine fileio_read_matrix_int(fname, nx, ny, a, e_fmt)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  integer, intent(inout) :: a(1:nx,1:ny)
  integer, intent(in) :: e_fmt
  integer :: un

  select case (e_fmt)
    case (e_fmt_txt)
      open(newunit=un, file=fname, status='old')
      call read_textmatrix_int(un, nx, ny, a)
      close(un)
    case (e_fmt_bil)
      call read_bil_int_file(fname, nx, ny, a)
    case (e_fmt_gtif)
      call read_gtif_int(fname, nx, ny, a)
    case default
      open(newunit=un, file=fname, status='old')
      call read_textmatrix_int(un, nx, ny, a)
      close(un)
  end select

end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine fileio_write_matrix_int(fname, nx, ny, a, e_fmt, gr)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  integer, intent(in) :: a(1:nx,1:ny)
  integer, intent(in) :: e_fmt
  type(t_georef), intent(in), optional :: gr   ! e_fmt_gtif で必須(座標管理)
  integer :: un

  select case (e_fmt)
    case (e_fmt_txt)
      open(newunit=un, file=fname, status='replace')
      call write_textmatrix_int(un, nx, ny, a)
      close(un)
    case (e_fmt_bil)
      open(newunit=un,file=fname, form='unformatted', status='replace', access='stream')
      call write_bil_int(un, nx, ny, a)
      close(un)
    case (e_fmt_gtif)
      call write_gtif_int(fname, nx, ny, a, gr)
    case default
      open(newunit=un, file=fname, status='replace')
      call write_textmatrix_int(un, nx, ny, a)
      close(un)
  end select

end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine fileio_read_matrix_real(fname, nx, ny, a, e_fmt)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  real, intent(inout) :: a(1:nx,1:ny)
  integer, intent(in) :: e_fmt
  integer :: un

  select case (e_fmt)
    case (e_fmt_txt)
      open(newunit=un, file=fname, status='old')
      call read_textmatrix_real(un, nx, ny, a)
      close(un)
    case (e_fmt_bil)
      call read_bil_real_file(fname, nx, ny, a)
    case (e_fmt_gtif)
      call read_gtif_real(fname, nx, ny, a)
    case default
      open(newunit=un, file=fname, status='old')
      call read_textmatrix_real(un, nx, ny, a)
      close(un)
  end select

end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine fileio_write_matrix_real(fname, nx, ny, a, e_fmt, gr)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  real, intent(in) :: a(1:nx,1:ny)
  integer, intent(in) :: e_fmt
  type(t_georef), intent(in), optional :: gr   ! e_fmt_gtif で必須(座標管理)
  integer :: un

  select case (e_fmt)
    case (e_fmt_txt)
      open(newunit=un, file=fname, status='replace')
      call write_textmatrix_real(un, nx, ny, a)
      close(un)
    case (e_fmt_bil)
      open(newunit=un,file=fname, form='unformatted', status='replace', access='stream')
      call write_bil_real(un, nx, ny, a)
      close(un)
    case (e_fmt_gtif)
      call write_gtif_real(fname, nx, ny, a, gr)
    case default
      open(newunit=un, file=fname, status='replace')
      call write_textmatrix_real(un, nx, ny, a)
      close(un)
  end select

end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine read_textmatrix_int(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  integer, intent(inout) :: a(1:nx,1:ny)
  integer :: j
  do j = 1, ny
    read(un, *) a(1:nx,j)
  enddo
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine write_textmatrix_int(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  integer, intent(in) :: a(1:nx,1:ny)
  integer :: j
  do j = 1, ny
    write(un,'(*(i8))') a(1:nx,j)
  enddo
end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine read_textmatrix_real(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  real, intent(inout) :: a(1:nx,1:ny)
  integer :: j
  do j = 1, ny
    read(un, *) a(1:nx,j)
  enddo
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine write_textmatrix_real(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  real, intent(in) :: a(1:nx,1:ny)
  integer :: j
  do j = 1, ny
    write(un,'(*(f12.4))') a(1:nx,j)
  enddo
end subroutine

!----------------------------------------------------------------------
! GeoTIFF 読み書き(m_geotiff の stat 返しをエラー停止に変換する層)
!   読みは全ランク冗長の場合と rank0 のみの場合があり、書きは rank0 のみ
!   なので、collective でない par_abort を使う(m_fileio の他のエラーと同じ)
!----------------------------------------------------------------------
subroutine read_gtif_real(fname, nx, ny, a)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  real, intent(inout) :: a(1:nx,1:ny)
  integer :: stat
  character(len=512) :: msg
  call gtif_read(fname, nx, ny, a, stat, msg)
  if (stat /= 0) call par_abort("GeoTIFF 読込失敗: "//trim(msg))
end subroutine

subroutine read_gtif_int(fname, nx, ny, a)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  integer, intent(inout) :: a(1:nx,1:ny)
  integer :: stat
  character(len=512) :: msg
  call gtif_read(fname, nx, ny, a, stat, msg)
  if (stat /= 0) call par_abort("GeoTIFF 読込失敗: "//trim(msg))
end subroutine


!----------------------------------------------------------------------
! t_georef(座標管理)を m_geotiff のメタ情報に写して書く。
! 座標未管理での GeoTIFF 出力は初期化時に par_stop 済みのはずだが、
! 直接呼び出しに備えてここでも検査する
!----------------------------------------------------------------------
subroutine write_gtif_real(fname, nx, ny, a, gr)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  real, intent(in) :: a(1:nx,1:ny)
  type(t_georef), intent(in), optional :: gr
  type(t_gtif_info) :: info
  integer :: stat
  character(len=512) :: msg
  call gr2info(gr, info)
  call gtif_write(fname, nx, ny, a, info, stat, msg)
  if (stat /= 0) call par_abort("GeoTIFF 出力失敗: "//trim(msg))
end subroutine

subroutine write_gtif_int(fname, nx, ny, a, gr)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  integer, intent(in) :: a(1:nx,1:ny)
  type(t_georef), intent(in), optional :: gr
  type(t_gtif_info) :: info
  integer :: stat
  character(len=512) :: msg
  call gr2info(gr, info)
  call gtif_write(fname, nx, ny, a, info, stat, msg)
  if (stat /= 0) call par_abort("GeoTIFF 出力失敗: "//trim(msg))
end subroutine

subroutine gr2info(gr, info)
  type(t_georef), intent(in), optional :: gr
  type(t_gtif_info), intent(out) :: info
  if (.not. present(gr)) then
    call par_abort("GeoTIFF 出力には座標管理(georef)が必要です")
  end if
  if (.not. gr%active) then
    call par_abort("GeoTIFF 出力には座標管理が必要です" &
                   //"(bil+hdr 入力か GeoTIFF 入力で位置情報を与えてください)")
  end if
  info%has_georef = .true.
  info%xul = gr%xul
  info%yul = gr%yul
  info%csx = gr%csx
  info%csy = gr%csy
  info%epsg = gr%epsg
  info%is_geog = gr%is_geog
end subroutine


!======================================================================
! bil 読み(sidecar hdr による型対応。docs/geotiff_plan.md §10)
!   bil と同じ場所の .hdr があれば NBITS/PIXELTYPE を見て読み分ける:
!   - 整数入力: 8/16/32bit × 符号付き/なし(既定 integer へ拡張)。
!     PIXELTYPE 未指定は 32bit=符号付き(従来互換)、8/16bit=符号なし
!     (ESRI の既定)とみなす
!   - 実数入力: 32bit FLOAT のみ。整数型の bil は実数へ変換して読める
!     (GeoTIFF と同じ扱い)。64bit は明示エラー
!   - 格子数(NCOLS/NROWS)が hdr にあれば照合する
!   hdr が無ければ従来どおりの生読み(整数=既定 integer、実数=real32)。
!   書き出しは従来どおり 32bit 固定
!======================================================================

!----------------------------------------------------------------------
! hdr の対応範囲と格子数の検査(bil 読み共通)
!----------------------------------------------------------------------
subroutine check_bil_hdr(fname, h, nx, ny)
  character(len=*), intent(in) :: fname
  type(t_esri_hdr), intent(in) :: h
  integer, intent(in) :: nx, ny

  if (trim(h%layout) /= "BIL") then
    call par_abort("bil: LAYOUT="//trim(h%layout)//" は未対応です(BIL のみ): "//trim(fname))
  end if
  if (trim(h%byteorder) /= "I") then
    call par_abort("bil: BYTEORDER="//trim(h%byteorder)// &
                   " は未対応です(I=リトルエンディアンのみ): "//trim(fname))
  end if
  if (h%skipbytes /= 0) then
    call par_abort("bil: SKIPBYTES="//itoa(h%skipbytes)//" は未対応です: "//trim(fname))
  end if
  if (h%nbands /= 1) then
    call par_abort("bil: NBANDS="//itoa(h%nbands)//" は未対応です(1バンドのみ): "//trim(fname))
  end if
  if (h%seen_grid) then
    if (h%ncols /= nx .or. h%nrows /= ny) then
      call par_abort("bil: 格子数が一致しません(hdr "//itoa(h%ncols)//"x"//itoa(h%nrows) &
                     //" / 要求 "//itoa(nx)//"x"//itoa(ny)//"): "//trim(fname))
    end if
  end if
end subroutine


!----------------------------------------------------------------------
! hdr の型情報から符号なしかどうかを決める(整数系のみで呼ぶ)
!----------------------------------------------------------------------
function bil_is_unsigned(h) result(unsigned)
  type(t_esri_hdr), intent(in) :: h
  logical :: unsigned
  if (trim(h%pixeltype) == "SIGNEDINT") then
    unsigned = .false.
  else if (trim(h%pixeltype) == "UNSIGNEDINT") then
    unsigned = .true.
  else
    ! 未指定: 32bit は従来運用(符号付き)、8/16bit は ESRI の既定(符号なし)
    unsigned = (h%nbits /= 32)
  end if
end function


!----------------------------------------------------------------------
! 型対応の整数読み(コア)。hdr 検査済みの h に従って読む
!----------------------------------------------------------------------
subroutine read_bil_int_typed(fname, h, nx, ny, a)
  character(len=*), intent(in) :: fname
  type(t_esri_hdr), intent(in) :: h
  integer, intent(in) :: nx, ny
  integer, intent(inout) :: a(1:nx,1:ny)
  integer :: un
  logical :: unsigned

  unsigned = bil_is_unsigned(h)
  open(newunit=un, file=fname, form='unformatted', status='old', access='stream')
  select case (h%nbits)
    case (8)
      block
        integer(int8) :: b(nx,ny)
        read(un) b
        if (unsigned) then
          a(:,:) = iand(int(b(:,:)), 255)
        else
          a(:,:) = int(b(:,:))
        end if
      end block
    case (16)
      block
        integer(int16) :: b(nx,ny)
        read(un) b
        if (unsigned) then
          a(:,:) = iand(int(b(:,:)), 65535)
        else
          a(:,:) = int(b(:,:))
        end if
      end block
    case (32)
      read(un) a
      if (unsigned) then
        if (any(a < 0)) then
          call par_abort("bil: 符号なし 32bit の値が既定 integer の範囲を超えています: "//trim(fname))
        end if
      end if
    case default
      call par_abort("bil: 整数は NBITS=8/16/32 のみ対応です(NBITS=" &
                     //itoa(h%nbits)//"): "//trim(fname))
  end select
  close(un)
end subroutine


!----------------------------------------------------------------------
! 整数入力(hdr があれば型対応、無ければ従来の生読み)
!----------------------------------------------------------------------
subroutine read_bil_int_file(fname, nx, ny, a)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  integer, intent(inout) :: a(1:nx,1:ny)
  type(t_esri_hdr) :: h
  character(:), allocatable :: hname
  character(len=512) :: msg
  integer :: un, stat
  logical :: ex

  hname = georef_hdr_name(fname)
  inquire(file=hname, exist=ex)
  if (.not. ex) then
    ! 従来動作: 既定 integer(32bit)の生読み
    open(newunit=un, file=fname, form='unformatted', status='old', access='stream')
    call read_bil_int(un, nx, ny, a)
    close(un)
    return
  end if

  call georef_parse_hdr(hname, h, stat, msg)
  if (stat /= 0) call par_abort(trim(msg))
  call check_bil_hdr(fname, h, nx, ny)
  if (trim(h%pixeltype) == "FLOAT") then
    call par_abort("bil: 実数型(PIXELTYPE=FLOAT)の bil は整数入力に使えません: "//trim(fname))
  end if
  call read_bil_int_typed(fname, h, nx, ny, a)
end subroutine


!----------------------------------------------------------------------
! 実数入力(hdr があれば型検査、無ければ従来の real32 生読み)
!   整数型の bil は実数へ変換して読む(GeoTIFF と同じ扱い)
!----------------------------------------------------------------------
subroutine read_bil_real_file(fname, nx, ny, a)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  real, intent(inout) :: a(1:nx,1:ny)
  type(t_esri_hdr) :: h
  character(:), allocatable :: hname
  character(len=512) :: msg
  integer :: un, stat
  logical :: ex

  hname = georef_hdr_name(fname)
  inquire(file=hname, exist=ex)
  if (.not. ex) then
    ! 従来動作: real32 の生読み
    open(newunit=un, file=fname, form='unformatted', status='old', access='stream')
    call read_bil_real(un, nx, ny, a)
    close(un)
    return
  end if

  call georef_parse_hdr(hname, h, stat, msg)
  if (stat /= 0) call par_abort(trim(msg))
  call check_bil_hdr(fname, h, nx, ny)

  if (trim(h%pixeltype) == "FLOAT" .or. &
      (len_trim(h%pixeltype) == 0 .and. h%nbits == 32)) then
    ! 実数: 32bit のみ(未指定+32bit は従来どおり FLOAT とみなす)
    if (h%nbits /= 32) then
      call par_abort("bil: 実数は NBITS=32 のみ対応です(NBITS=" &
                     //itoa(h%nbits)//"。Float64 なら 32bit で書き出し直してください): "//trim(fname))
    end if
    open(newunit=un, file=fname, form='unformatted', status='old', access='stream')
    call read_bil_real(un, nx, ny, a)
    close(un)
  else
    ! 整数型の bil → 実数へ変換
    block
      integer :: b(nx,ny)
      call read_bil_int_typed(fname, h, nx, ny, b)
      a(:,:) = real(b(:,:))
    end block
  end if
end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine read_bil_int(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  integer, intent(inout) :: a(1:nx,1:ny)
  read(un) a
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine write_bil_int(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  integer, intent(in) :: a(1:nx,1:ny)
  write(un) a
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine read_bil_real(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  real, intent(inout) :: a(1:nx,1:ny)
  real(real32) :: r(1:nx,1:ny)
  read(un) r
  a(:,:) = r(:,:)
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine write_bil_real(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  real, intent(in) :: a(1:nx,1:ny)
  real(real32) :: r(1:nx,1:ny)
  r(:,:) = real(a(:,:), kind=real32)
  write(un) r
end subroutine


!======================================================================
! ゼロ抑制 RLE(save/restore 用)
!   形式(1配列=1ストリーム、3レコード):
!     [n_total, nrun](int64)/ runs(2,nrun)(int64)/ packed(:)(real)
!   runs(1,r) = ゼロ連長、runs(2,r) = 続くリテラル連長。
!   圧縮対象は全ビット0(+0.0)のみ。-0.0 はリテラル側に落として
!   ビット保存を保証する(値比較 a==0.0 は -0.0 も真になるため
!   ビット比較で判定する。§7)。カウント類は 100m 全国級の要素数
!   (>2^31 に迫る)に備えて int64。
!   復元は rank0 のみが呼ぶため、整合エラーは par_abort(局所)を使う
!======================================================================

!----------------------------------------------------------------------
! 全ビット0(+0.0)か判定する(-0.0 は偽)
!----------------------------------------------------------------------
pure logical function rle_is_pzero(x)
  real, intent(in) :: x
  rle_is_pzero = (transfer(x, 0_rle_ik) == 0_rle_ik)
end function


!----------------------------------------------------------------------
! 1次元配列をゼロ抑制 RLE で書く(コア)
!----------------------------------------------------------------------
subroutine rle_encode_write(un, f)
  integer, intent(in) :: un
  real, intent(in) :: f(:)
  integer(int64) :: n, i, r, k, nrun, nd
  integer(int64), allocatable :: runs(:,:)
  real, allocatable :: packed(:)

  n = size(f, kind=int64)

  ! パス1: ラン数と非ゼロ総数を数える
  nrun = 0
  nd = 0
  i = 1
  do while (i <= n)
    nrun = nrun + 1
    do while (i <= n)                  ! ゼロ連
      if (.not. rle_is_pzero(f(i))) exit
      i = i + 1
    end do
    do while (i <= n)                  ! リテラル連
      if (rle_is_pzero(f(i))) exit
      nd = nd + 1
      i = i + 1
    end do
  end do

  ! パス2: ラン表と詰めデータを充填する
  allocate(runs(2, nrun))
  allocate(packed(nd))
  i = 1
  k = 0
  do r = 1, nrun
    runs(1, r) = 0
    do while (i <= n)                  ! ゼロ連
      if (.not. rle_is_pzero(f(i))) exit
      runs(1, r) = runs(1, r) + 1
      i = i + 1
    end do
    runs(2, r) = 0
    do while (i <= n)                  ! リテラル連
      if (rle_is_pzero(f(i))) exit
      k = k + 1
      packed(k) = f(i)
      runs(2, r) = runs(2, r) + 1
      i = i + 1
    end do
  end do

  write(un) n, nrun
  write(un) runs
  write(un) packed                     ! nd=0 でも空レコードを書く(read と対)
end subroutine


!----------------------------------------------------------------------
! ゼロ抑制 RLE を読んで1次元配列に展開する(コア)
!----------------------------------------------------------------------
subroutine rle_read_decode(un, f)
  integer, intent(in) :: un
  real, intent(out) :: f(:)
  integer(int64) :: n_total, nrun, r, i, k, nd
  integer(int64), allocatable :: runs(:,:)
  real, allocatable :: packed(:)

  read(un) n_total, nrun
  if (n_total /= size(f, kind=int64)) then
    call par_abort("fileio_read_rle: 要素数が一致しません(save 内: " &
                   //itoa64(n_total)//" / 展開先: "//itoa64(size(f, kind=int64))//")")
  end if
  allocate(runs(2, nrun))
  read(un) runs
  nd = sum(runs(2, :))
  allocate(packed(nd))
  read(un) packed                      ! nd=0 でも空レコードを読む(write と対)

  f(:) = 0.0                           ! ゼロ部は +0.0 で埋める(圧縮対象は +0.0 のみ)
  i = 1
  k = 1
  do r = 1, nrun
    i = i + runs(1, r)
    if (runs(2, r) > 0) then
      f(i:i+runs(2,r)-1) = packed(k:k+runs(2,r)-1)
      i = i + runs(2, r)
      k = k + runs(2, r)
    end if
  end do
end subroutine


!----------------------------------------------------------------------
! int64 用の itoa(m_util の itoa は既定整数のためここに私有で持つ)
!----------------------------------------------------------------------
pure function itoa64(i) result(s)
  integer(int64), intent(in) :: i
  character(:), allocatable :: s
  character(len=32) :: buf
  write(buf, '(i0)') i
  s = trim(buf)
end function


!----------------------------------------------------------------------
! RLE 書き込み(2次元/3次元。内部で1次元に読み替える)
!----------------------------------------------------------------------
subroutine fileio_write_rle2(un, a)
  integer, intent(in) :: un
  real, intent(in), target, contiguous :: a(:,:)
  real, pointer :: f(:)
  f(1:size(a)) => a
  call rle_encode_write(un, f)
end subroutine

subroutine fileio_write_rle3(un, a)
  integer, intent(in) :: un
  real, intent(in), target, contiguous :: a(:,:,:)
  real, pointer :: f(:)
  f(1:size(a)) => a
  call rle_encode_write(un, f)
end subroutine


!----------------------------------------------------------------------
! RLE 読み込み(2次元/3次元。内部で1次元に読み替える)
!----------------------------------------------------------------------
subroutine fileio_read_rle2(un, a)
  integer, intent(in) :: un
  real, intent(out), target, contiguous :: a(:,:)
  real, pointer :: f(:)
  f(1:size(a)) => a
  call rle_read_decode(un, f)
end subroutine

subroutine fileio_read_rle3(un, a)
  integer, intent(in) :: un
  real, intent(out), target, contiguous :: a(:,:,:)
  real, pointer :: f(:)
  f(1:size(a)) => a
  call rle_read_decode(un, f)
end subroutine


end module
