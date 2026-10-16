module m_fileio
  use, intrinsic :: iso_fortran_env, only: real32, int8, int16, int32, int64
  use m_geotiff, only : gtif_read, gtif_read_window, gtif_write, gtif_write_window, t_gtif_info
  use m_georef, only : t_georef, t_esri_hdr, georef_hdr_name, georef_parse_hdr
  use m_util, only : itoa
  use m_parallel, only : par_abort

  implicit none
  private

  public :: fileio_read_matrix
  public :: fileio_read_window
  public :: fileio_write_matrix
  public :: fileio_write_window
  public :: fileio_un_open
  public :: fileio_un_read_matrix
  public :: fileio_write_rle
  public :: fileio_read_rle



  interface fileio_read_matrix
    procedure :: fileio_read_matrix_int
    procedure :: fileio_read_matrix_real
  end interface

  interface fileio_read_window
    procedure :: fileio_read_window_int
    procedure :: fileio_read_window_real
  end interface

  interface fileio_write_matrix
    procedure :: fileio_write_matrix_int
    procedure :: fileio_write_matrix_real
  end interface

  interface fileio_write_window
    procedure :: fileio_write_window_int
    procedure :: fileio_write_window_real
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
! open の入口(§4 の iostat 化)。失敗は整ったメッセージで止める。
!   m_fileio は rank0 単独の文脈でも呼ばれるため par_abort(非 collective)
!----------------------------------------------------------------------
function open_old_text(fname) result(un)
  character(len=*), intent(in) :: fname
  integer :: un, ios
  character(len=512) :: iom
  open(newunit=un, file=fname, status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_abort("fileio: cannot open text file "//trim(fname)//": "//trim(iom))
end function

function open_old_stream(fname) result(un)
  character(len=*), intent(in) :: fname
  integer :: un, ios
  character(len=512) :: iom
  open(newunit=un, file=fname, form='unformatted', status='old', access='stream', &
       iostat=ios, iomsg=iom)
  if (ios /= 0) call par_abort("fileio: cannot open binary file "//trim(fname)//": "//trim(iom))
end function

function open_new_text(fname) result(un)
  character(len=*), intent(in) :: fname
  integer :: un, ios
  character(len=512) :: iom
  open(newunit=un, file=fname, status='replace', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_abort("fileio: cannot create text file "//trim(fname)//": "//trim(iom))
end function

function open_new_stream(fname) result(un)
  character(len=*), intent(in) :: fname
  integer :: un, ios
  character(len=512) :: iom
  open(newunit=un, file=fname, form='unformatted', status='replace', access='stream', &
       iostat=ios, iomsg=iom)
  if (ios /= 0) call par_abort("fileio: cannot create binary file "//trim(fname)//": "//trim(iom))
end function

!----------------------------------------------------------------------
! read の失敗(ファイル不足・書式不正)を整ったメッセージで止める
!----------------------------------------------------------------------
subroutine abort_read(un, iom, row)
  integer, intent(in) :: un
  character(len=*), intent(in) :: iom
  integer, intent(in), optional :: row
  character(len=1024) :: fname
  inquire(unit=un, name=fname)
  if (present(row)) then
    call par_abort("fileio: cannot read row "//itoa(row)//" of "//trim(fname) &
                   //" (file truncated or malformed): "//trim(iom))
  else
    call par_abort("fileio: file too short or unreadable: "//trim(fname)//": "//trim(iom))
  end if
end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
function fileio_un_open(fname, e_fmt) result(un)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: e_fmt
  integer :: un

  select case (e_fmt)
    case (e_fmt_txt)
      un = open_old_text(fname)
    case (e_fmt_bil)
      un = open_old_stream(fname)
    case (e_fmt_gtif)
      un = -1
      call par_abort("fileio: GeoTIFF cannot be used for sequential reads (precip maplist);" &
                     //" use txt or bil")
    case default
      un = open_old_text(fname)
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
      un = open_old_text(fname)
      call read_textmatrix_int(un, nx, ny, a)
      close(un)
    case (e_fmt_bil)
      call read_bil_int_file(fname, nx, ny, a)
    case (e_fmt_gtif)
      call read_gtif_int(fname, nx, ny, a)
    case default
      un = open_old_text(fname)
      call read_textmatrix_int(un, nx, ny, a)
      close(un)
  end select

end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
!----------------------------------------------------------------------
! 窓つき読み込み(全域 (nx, ny) の形式のファイルから、窓 (i1:i2, j1:j2) の
! 部分だけを a(i1:i2, j1:j2) に読む。a の確保範囲は窓以上なら何でもよい。
! メモリは 1 行分(text・bil)、または 1 ブロック分(GeoTIFF)。
! text は窓の最終行 j2 までを 1 行ずつ読んで窓の列を写す(j2 より後の行は
! 読まない)。bil は窓の行だけを位置指定で読む。GeoTIFF は窓に重なる
! strip/tile だけを復号する。窓 = 全域なら fileio_read_matrix と同じ値。
! developer.md §82)
!----------------------------------------------------------------------
subroutine fileio_read_window_int(fname, nx, ny, i1, i2, j1, j2, a, e_fmt)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny, i1, i2, j1, j2
  integer, intent(inout) :: a(i1:, j1:)
  integer, intent(in) :: e_fmt
  integer :: un

  call check_window(fname, nx, ny, i1, i2, j1, j2)
  select case (e_fmt)
    case (e_fmt_bil)
      call read_bil_int_window(fname, nx, ny, i1, i2, j1, j2, a)
    case (e_fmt_gtif)
      call read_gtif_int_window(fname, nx, ny, i1, i2, j1, j2, a)
    case default
      un = open_old_text(fname)
      call read_textwindow_int(un, nx, i1, i2, j1, j2, a)
      close(un)
  end select
end subroutine


subroutine fileio_read_window_real(fname, nx, ny, i1, i2, j1, j2, a, e_fmt)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny, i1, i2, j1, j2
  real, intent(inout) :: a(i1:, j1:)
  integer, intent(in) :: e_fmt
  integer :: un

  call check_window(fname, nx, ny, i1, i2, j1, j2)
  select case (e_fmt)
    case (e_fmt_bil)
      call read_bil_real_window(fname, nx, ny, i1, i2, j1, j2, a)
    case (e_fmt_gtif)
      call read_gtif_real_window(fname, nx, ny, i1, i2, j1, j2, a)
    case default
      un = open_old_text(fname)
      call read_textwindow_real(un, nx, i1, i2, j1, j2, a)
      close(un)
  end select
end subroutine


subroutine check_window(fname, nx, ny, i1, i2, j1, j2)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny, i1, i2, j1, j2
  if (i1 < 1 .or. i2 > nx .or. j1 < 1 .or. j2 > ny .or. i1 > i2 .or. j1 > j2) then
    call par_abort("fileio: window ("//itoa(i1)//":"//itoa(i2)//", "//itoa(j1)//":"//itoa(j2) &
                   //") is not inside the "//itoa(nx)//"x"//itoa(ny)//" grid: "//trim(fname))
  end if
end subroutine


! text の窓読み: 1 行バッファに行を読み、窓の列を写す。
! 行 j2 まで読めば足りるので、残りの行は読まない(読み込み時間は窓の下端まで)
subroutine read_textwindow_int(un, nx, i1, i2, j1, j2, a)
  integer, intent(in) :: un, nx, i1, i2, j1, j2
  integer, intent(inout) :: a(i1:, j1:)
  integer, allocatable :: row(:)        ! ヒープ(§40)
  integer :: j, ios
  character(len=512) :: iom
  allocate(row(1:nx))
  do j = 1, j2
    read(un, *, iostat=ios, iomsg=iom) row
    if (ios /= 0) call abort_read(un, iom, j)
    if (j >= j1) a(i1:i2, j) = row(i1:i2)
  end do
end subroutine


subroutine read_textwindow_real(un, nx, i1, i2, j1, j2, a)
  integer, intent(in) :: un, nx, i1, i2, j1, j2
  real, intent(inout) :: a(i1:, j1:)
  real, allocatable :: row(:)           ! ヒープ(§40)
  integer :: j, ios
  character(len=512) :: iom
  allocate(row(1:nx))
  do j = 1, j2
    read(un, *, iostat=ios, iomsg=iom) row
    if (ios /= 0) call abort_read(un, iom, j)
    if (j >= j1) a(i1:i2, j) = row(i1:i2)
  end do
end subroutine


! bil の窓読み(実数): hdr の型判定は read_bil_real_file と同じ。窓の行を
! 位置指定(stream の pos=)で 1 行ずつ読む
subroutine read_bil_real_window(fname, nx, ny, i1, i2, j1, j2, a)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny, i1, i2, j1, j2
  real, intent(inout) :: a(i1:, j1:)
  type(t_esri_hdr) :: h
  character(:), allocatable :: hname
  character(len=512) :: msg
  integer :: stat
  logical :: ex, is_float

  hname = georef_hdr_name(fname)
  inquire(file=hname, exist=ex)
  is_float = .true.
  if (ex) then
    call georef_parse_hdr(hname, h, stat, msg)
    if (stat /= 0) call par_abort(trim(msg))
    call check_bil_hdr(fname, h, nx, ny)
    is_float = trim(h%pixeltype) == "FLOAT" .or. &
               (len_trim(h%pixeltype) == 0 .and. h%nbits == 32)
    if (is_float .and. h%nbits /= 32) then
      call par_abort("fileio: bil real input supports NBITS=32 only (NBITS=" &
                     //itoa(h%nbits)//"; rewrite Float64 data as 32bit): "//trim(fname))
    end if
  end if

  if (is_float) then
    block
      real(real32), allocatable :: r(:)
      integer :: un, j, ios
      integer(int64) :: pos
      character(len=512) :: iom
      allocate(r(i1:i2))
      un = open_old_stream(fname)
      do j = j1, j2
        pos = (int(j - 1, int64) * nx + (i1 - 1)) * 4_int64 + 1_int64
        read(un, pos=pos, iostat=ios, iomsg=iom) r
        if (ios /= 0) call abort_read(un, iom, j)
        a(i1:i2, j) = r(i1:i2)
      end do
      close(un)
    end block
  else
    ! 整数型の bil → 実数へ変換(窓分の整数一時)
    block
      integer, allocatable :: b(:,:)
      allocate(b(i1:i2, j1:j2))
      call read_bil_int_typed_window(fname, h, nx, i1, i2, j1, j2, b)
      a(i1:i2, j1:j2) = real(b(i1:i2, j1:j2))
    end block
  end if
end subroutine


! bil の窓読み(整数): hdr があれば型対応、無ければ既定 integer の生読み
subroutine read_bil_int_window(fname, nx, ny, i1, i2, j1, j2, a)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny, i1, i2, j1, j2
  integer, intent(inout) :: a(i1:, j1:)
  type(t_esri_hdr) :: h
  character(:), allocatable :: hname
  character(len=512) :: msg
  integer :: stat
  logical :: ex

  hname = georef_hdr_name(fname)
  inquire(file=hname, exist=ex)
  if (.not. ex) then
    h%nbits = 32                            ! 従来動作: 既定 integer(32bit)の生読み
    h%pixeltype = ""
  else
    call georef_parse_hdr(hname, h, stat, msg)
    if (stat /= 0) call par_abort(trim(msg))
    call check_bil_hdr(fname, h, nx, ny)
    if (trim(h%pixeltype) == "FLOAT") then
      call par_abort("fileio: bil with PIXELTYPE=FLOAT cannot be used as integer input: " &
                     //trim(fname))
    end if
  end if
  call read_bil_int_typed_window(fname, h, nx, i1, i2, j1, j2, a)
end subroutine


! 整数 bil の窓読み(NBITS=8/16/32。read_bil_int_typed の行ストリーミング版)
subroutine read_bil_int_typed_window(fname, h, nx, i1, i2, j1, j2, a)
  character(len=*), intent(in) :: fname
  type(t_esri_hdr), intent(in) :: h
  integer, intent(in) :: nx, i1, i2, j1, j2
  integer, intent(inout) :: a(i1:, j1:)
  integer :: un, ios, j, bpb
  integer(int64) :: pos
  logical :: unsigned
  character(len=512) :: iom
  integer(int8), allocatable :: b1(:)
  integer(int16), allocatable :: b2(:)
  integer, allocatable :: b4(:)

  unsigned = bil_is_unsigned(h)
  select case (h%nbits)
    case (8)
      bpb = 1
      allocate(b1(i1:i2))
    case (16)
      bpb = 2
      allocate(b2(i1:i2))
    case (32)
      bpb = 4
      allocate(b4(i1:i2))
    case default
      call par_abort("fileio: bil integer input supports NBITS=8/16/32 only (NBITS=" &
                     //itoa(h%nbits)//"): "//trim(fname))
  end select
  un = open_old_stream(fname)
  do j = j1, j2
    pos = (int(j - 1, int64) * nx + (i1 - 1)) * bpb + 1_int64
    select case (bpb)
      case (1)
        read(un, pos=pos, iostat=ios, iomsg=iom) b1
        if (ios /= 0) call abort_read(un, iom, j)
        if (unsigned) then
          a(i1:i2, j) = iand(int(b1(i1:i2)), 255)
        else
          a(i1:i2, j) = int(b1(i1:i2))
        end if
      case (2)
        read(un, pos=pos, iostat=ios, iomsg=iom) b2
        if (ios /= 0) call abort_read(un, iom, j)
        if (unsigned) then
          a(i1:i2, j) = iand(int(b2(i1:i2)), 65535)
        else
          a(i1:i2, j) = int(b2(i1:i2))
        end if
      case default
        read(un, pos=pos, iostat=ios, iomsg=iom) b4
        if (ios /= 0) call abort_read(un, iom, j)
        if (unsigned .and. any(b4 < 0)) then
          call par_abort("fileio: unsigned 32bit bil value exceeds the default integer " &
                         //"range: "//trim(fname))
        end if
        a(i1:i2, j) = b4(i1:i2)
    end select
  end do
  close(un)
end subroutine


subroutine read_gtif_real_window(fname, nx, ny, i1, i2, j1, j2, a)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny, i1, i2, j1, j2
  real, intent(inout) :: a(i1:, j1:)
  integer :: stat
  character(len=512) :: msg
  call gtif_read_window(fname, nx, ny, i1, i2, j1, j2, a, stat, msg)
  if (stat /= 0) call par_abort("fileio: failed to read GeoTIFF as real: "//trim(msg))
end subroutine


subroutine read_gtif_int_window(fname, nx, ny, i1, i2, j1, j2, a)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny, i1, i2, j1, j2
  integer, intent(inout) :: a(i1:, j1:)
  integer :: stat
  character(len=512) :: msg
  call gtif_read_window(fname, nx, ny, i1, i2, j1, j2, a, stat, msg)
  if (stat /= 0) call par_abort("fileio: failed to read GeoTIFF as integer: "//trim(msg))
end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
!----------------------------------------------------------------------
! 窓つき書き出し(全域 (nx, ny) の形式のファイルを、窓 (i1:i2, j1:j2) の配列と
! 窓外の充填値 fill から行ストリーミングで書く。メモリは 1 行分。
! 窓 = 全域・fill = 0 なら fileio_write_matrix とバイト一致。developer.md §81)
!----------------------------------------------------------------------
subroutine fileio_write_window_int(fname, nx, ny, i1, i2, j1, j2, a, fill, e_fmt, gr)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny, i1, i2, j1, j2
  integer, intent(in) :: a(i1:, j1:)
  integer, intent(in) :: fill
  integer, intent(in) :: e_fmt
  type(t_georef), intent(in), optional :: gr   ! e_fmt_gtif で必須(座標管理)
  integer :: un, j
  integer, allocatable :: row(:)

  if (e_fmt == e_fmt_gtif) then
    call write_gtif_window_int(fname, nx, ny, i1, i2, j1, j2, a, fill, gr)
    return
  end if
  allocate(row(1:nx))
  if (e_fmt == e_fmt_bil) then
    un = open_new_stream(fname)
  else
    un = open_new_text(fname)
  end if
  do j = 1, ny
    row(:) = fill
    if (j >= j1 .and. j <= j2) row(i1:i2) = a(i1:i2, j)
    if (e_fmt == e_fmt_bil) then
      write(un) row
    else
      write(un,'(*(i8))') row
    end if
  end do
  close(un)
end subroutine

subroutine fileio_write_window_real(fname, nx, ny, i1, i2, j1, j2, a, fill, e_fmt, gr)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny, i1, i2, j1, j2
  real, intent(in) :: a(i1:, j1:)
  real, intent(in) :: fill
  integer, intent(in) :: e_fmt
  type(t_georef), intent(in), optional :: gr
  integer :: un, j
  real, allocatable :: row(:)
  real(real32), allocatable :: row32(:)

  select case (e_fmt)
    case (e_fmt_gtif)
      call write_gtif_window_real(fname, nx, ny, i1, i2, j1, j2, a, fill, gr)
    case (e_fmt_bil)
      un = open_new_stream(fname)
      allocate(row32(1:nx))
      do j = 1, ny
        row32(:) = real(fill, real32)
        if (j >= j1 .and. j <= j2) row32(i1:i2) = real(a(i1:i2, j), real32)
        write(un) row32
      end do
      close(un)
    case default
      un = open_new_text(fname)
      allocate(row(1:nx))
      do j = 1, ny
        row(:) = fill
        if (j >= j1 .and. j <= j2) row(i1:i2) = a(i1:i2, j)
        write(un,'(*(f12.4))') row
      end do
      close(un)
  end select
end subroutine

subroutine fileio_write_matrix_int(fname, nx, ny, a, e_fmt, gr)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  integer, intent(in) :: a(1:nx,1:ny)
  integer, intent(in) :: e_fmt
  type(t_georef), intent(in), optional :: gr   ! e_fmt_gtif で必須(座標管理)
  integer :: un

  select case (e_fmt)
    case (e_fmt_txt)
      un = open_new_text(fname)
      call write_textmatrix_int(un, nx, ny, a)
      close(un)
    case (e_fmt_bil)
      un = open_new_stream(fname)
      call write_bil_int(un, nx, ny, a)
      close(un)
    case (e_fmt_gtif)
      call write_gtif_int(fname, nx, ny, a, gr)
    case default
      un = open_new_text(fname)
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
      un = open_old_text(fname)
      call read_textmatrix_real(un, nx, ny, a)
      close(un)
    case (e_fmt_bil)
      call read_bil_real_file(fname, nx, ny, a)
    case (e_fmt_gtif)
      call read_gtif_real(fname, nx, ny, a)
    case default
      un = open_old_text(fname)
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
      un = open_new_text(fname)
      call write_textmatrix_real(un, nx, ny, a)
      close(un)
    case (e_fmt_bil)
      un = open_new_stream(fname)
      call write_bil_real(un, nx, ny, a)
      close(un)
    case (e_fmt_gtif)
      call write_gtif_real(fname, nx, ny, a, gr)
    case default
      un = open_new_text(fname)
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
  integer :: j, ios
  character(len=512) :: iom
  do j = 1, ny
    read(un, *, iostat=ios, iomsg=iom) a(1:nx,j)
    if (ios /= 0) call abort_read(un, iom, j)
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
  integer :: j, ios
  character(len=512) :: iom
  do j = 1, ny
    read(un, *, iostat=ios, iomsg=iom) a(1:nx,j)
    if (ios /= 0) call abort_read(un, iom, j)
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
  if (stat /= 0) call par_abort("fileio: failed to read GeoTIFF as real: "//trim(msg))
end subroutine

subroutine read_gtif_int(fname, nx, ny, a)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  integer, intent(inout) :: a(1:nx,1:ny)
  integer :: stat
  character(len=512) :: msg
  call gtif_read(fname, nx, ny, a, stat, msg)
  if (stat /= 0) call par_abort("fileio: failed to read GeoTIFF as integer: "//trim(msg))
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
  if (stat /= 0) call par_abort("fileio: failed to write GeoTIFF as real: "//trim(msg))
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
  if (stat /= 0) call par_abort("fileio: failed to write GeoTIFF as integer: "//trim(msg))
end subroutine

subroutine write_gtif_window_real(fname, nx, ny, i1, i2, j1, j2, a, fill, gr)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny, i1, i2, j1, j2
  real, intent(in) :: a(i1:, j1:)
  real, intent(in) :: fill
  type(t_georef), intent(in), optional :: gr
  type(t_gtif_info) :: info
  integer :: stat
  character(len=512) :: msg
  call gr2info(gr, info)
  call gtif_write_window(fname, nx, ny, i1, i2, j1, j2, a, fill, info, stat, msg)
  if (stat /= 0) call par_abort("fileio: failed to write GeoTIFF as real: "//trim(msg))
end subroutine

subroutine write_gtif_window_int(fname, nx, ny, i1, i2, j1, j2, a, fill, gr)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny, i1, i2, j1, j2
  integer, intent(in) :: a(i1:, j1:)
  integer, intent(in) :: fill
  type(t_georef), intent(in), optional :: gr
  type(t_gtif_info) :: info
  integer :: stat
  character(len=512) :: msg
  call gr2info(gr, info)
  call gtif_write_window(fname, nx, ny, i1, i2, j1, j2, a, fill, info, stat, msg)
  if (stat /= 0) call par_abort("fileio: failed to write GeoTIFF as integer: "//trim(msg))
end subroutine

subroutine gr2info(gr, info)
  type(t_georef), intent(in), optional :: gr
  type(t_gtif_info), intent(out) :: info
  if (.not. present(gr)) then
    call par_abort("fileio: GeoTIFF output requires georeferencing (georef not given)")
  end if
  if (.not. gr%active) then
    call par_abort("fileio: GeoTIFF output requires georeferencing" &
                   //" (give location info via bil+hdr or GeoTIFF input)")
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
    call par_abort("fileio: bil LAYOUT="//trim(h%layout)//" is not supported (BIL only): " &
                   //trim(fname))
  end if
  if (trim(h%byteorder) /= "I") then
    call par_abort("fileio: bil BYTEORDER="//trim(h%byteorder)// &
                   " is not supported (only I = little endian): "//trim(fname))
  end if
  if (h%skipbytes /= 0) then
    call par_abort("fileio: bil SKIPBYTES="//itoa(h%skipbytes)//" is not supported: "//trim(fname))
  end if
  if (h%nbands /= 1) then
    call par_abort("fileio: bil NBANDS="//itoa(h%nbands)//" is not supported (single band " &
                   //"only): "//trim(fname))
  end if
  if (h%seen_grid) then
    if (h%ncols /= nx .or. h%nrows /= ny) then
      call par_abort("fileio: bil grid size mismatch (hdr "//itoa(h%ncols)//"x"//itoa(h%nrows) &
                     //" / requested "//itoa(nx)//"x"//itoa(ny)//"): "//trim(fname))
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
  integer :: un, ios
  logical :: unsigned
  character(len=512) :: iom

  unsigned = bil_is_unsigned(h)
  un = open_old_stream(fname)
  select case (h%nbits)
    case (8)
      block
        ! 全域スケールの作業配列はヒープに置く(自動配列はスタック上限で
        ! 無言の Segmentation fault になる。developer.md §40)
        integer(int8), allocatable :: b(:,:)
        allocate(b(nx,ny))
        read(un, iostat=ios, iomsg=iom) b
        if (ios /= 0) call abort_read(un, iom)
        if (unsigned) then
          a(:,:) = iand(int(b(:,:)), 255)
        else
          a(:,:) = int(b(:,:))
        end if
      end block
    case (16)
      block
        integer(int16), allocatable :: b(:,:)  ! ヒープ(§40)
        allocate(b(nx,ny))
        read(un, iostat=ios, iomsg=iom) b
        if (ios /= 0) call abort_read(un, iom)
        if (unsigned) then
          a(:,:) = iand(int(b(:,:)), 65535)
        else
          a(:,:) = int(b(:,:))
        end if
      end block
    case (32)
      read(un, iostat=ios, iomsg=iom) a
      if (ios /= 0) call abort_read(un, iom)
      if (unsigned) then
        if (any(a < 0)) then
          call par_abort("fileio: unsigned 32bit bil value exceeds the default integer " &
                         //"range: "//trim(fname))
        end if
      end if
    case default
      call par_abort("fileio: bil integer input supports NBITS=8/16/32 only (NBITS=" &
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
    un = open_old_stream(fname)
    call read_bil_int(un, nx, ny, a)
    close(un)
    return
  end if

  call georef_parse_hdr(hname, h, stat, msg)
  if (stat /= 0) call par_abort(trim(msg))
  call check_bil_hdr(fname, h, nx, ny)
  if (trim(h%pixeltype) == "FLOAT") then
    call par_abort("fileio: bil with PIXELTYPE=FLOAT cannot be used as integer input: " &
                   //trim(fname))
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
    un = open_old_stream(fname)
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
      call par_abort("fileio: bil real input supports NBITS=32 only (NBITS=" &
                     //itoa(h%nbits)//"; rewrite Float64 data as 32bit): "//trim(fname))
    end if
    un = open_old_stream(fname)
    call read_bil_real(un, nx, ny, a)
    close(un)
  else
    ! 整数型の bil → 実数へ変換
    block
      integer, allocatable :: b(:,:)  ! ヒープ(§40)
      allocate(b(nx,ny))
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
  integer :: ios
  character(len=512) :: iom
  read(un, iostat=ios, iomsg=iom) a
  if (ios /= 0) call abort_read(un, iom)
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
  real(real32), allocatable :: r(:,:)  ! ヒープ(§40)
  integer :: ios
  character(len=512) :: iom
  allocate(r(1:nx,1:ny))
  read(un, iostat=ios, iomsg=iom) r
  if (ios /= 0) call abort_read(un, iom)
  a(:,:) = r(:,:)
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine write_bil_real(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  real, intent(in) :: a(1:nx,1:ny)
  real(real32), allocatable :: r(:,:)  ! ヒープ(§40)
  allocate(r(1:nx,1:ny))
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
    call par_abort("fileio: RLE element count mismatch (in save: " &
                   //itoa64(n_total)//" / target: "//itoa64(size(f, kind=int64))//")")
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
