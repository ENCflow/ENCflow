!======================================================================
! GeoTIFF リーダーの回帰テスト
!   data_gtif/ の資産(README.md)を読み、expected/ の期待値とビット一致を
!   検査する。未対応形式(Deflate=Phase 2、BigTIFF=Phase 4)と型不整合は
!   「メッセージ付きでエラーになること」を検査する。
!   実行は ./Run.sh(ビルドは同ディレクトリの Makefile)
!======================================================================
program test_gtif_reader
  use m_geotiff, only : t_gtif_info, gtif_inquire, gtif_read
  implicit none

  integer, parameter :: nx = 60, ny = 48
  integer :: nfail = 0
  integer :: ntest = 0

  ! 実数読み(値のビット一致)
  call t_real("f32_none_strip.tif", "f32.txt")
  call t_real("f32_none_tile.tif", "f32.txt")
  call t_real("f32_lzw_strip.tif", "f32.txt")
  call t_real("f32_lzw_pred3_strip.tif", "f32.txt")
  call t_real("f32_packbits_strip.tif", "f32.txt")
  call t_real("f32_none_strip_be.tif", "f32.txt")
  call t_real("f32_none_strip_geo.tif", "f32.txt")
  call t_real("f64_none_strip.tif", "f64.txt")

  ! 整数読み
  call t_int("u8_none_strip.tif", "u8.txt")
  call t_int("i16_lzw_pred2_strip.tif", "i16.txt")
  call t_int("i16_none_strip_be.tif", "i16.txt")
  call t_int("i32_none_strip.tif", "i32.txt")
  call t_int("u32_lzw_strip.tif", "u32.txt")

  ! 整数型 GeoTIFF の実数読み(型変換経路)
  call t_real("i32_none_strip.tif", "i32.txt")
  call t_real("u8_none_strip.tif", "u8.txt")

  ! 未対応・不整合はエラーになること
  call t_err_real("f32_deflate_strip.tif")
  call t_err_real("f32_deflate_pred3_tile.tif")
  call t_err_real("f32_deflate_bigtiff.tif")
  call t_err_int("u16_deflate_tile.tif")
  call t_err_int("f32_none_strip.tif")       ! 実数型を整数入力に使うのは誤り

  ! メタ情報(位置情報・CRS・nodata)
  call t_meta()

  print '(a,i0,a,i0,a)', "---- ", ntest - nfail, " / ", ntest, " PASS"
  if (nfail > 0) then
    print '(a)', "=== GeoTIFF リーダーテスト FAIL ==="
    stop 1
  end if
  print '(a)', "=== GeoTIFF リーダーテスト PASS ==="

contains

subroutine load_expected(ef, e)
  character(len=*), intent(in) :: ef
  real, intent(out) :: e(nx,ny)
  integer :: un, j
  open(newunit=un, file="expected/"//ef, status='old')
  do j = 1, ny
    read(un, *) e(1:nx,j)
  end do
  close(un)
end subroutine

subroutine report(name, ok, msg)
  character(len=*), intent(in) :: name
  logical, intent(in) :: ok
  character(len=*), intent(in) :: msg
  ntest = ntest + 1
  if (ok) then
    print '(a)', "PASS: "//name
  else
    nfail = nfail + 1
    print '(a)', "FAIL: "//name//"  "//trim(msg)
  end if
end subroutine

subroutine t_real(fn, ef)
  character(len=*), intent(in) :: fn, ef
  real :: a(nx,ny), e(nx,ny)
  integer :: stat
  character(len=512) :: msg
  call load_expected(ef, e)
  a = 0.0
  call gtif_read("data_gtif/"//fn, nx, ny, a, stat, msg)
  if (stat /= 0) then
    call report("real "//fn, .false., msg)
  else
    call report("real "//fn, all(a == e), "値が期待値とビット一致しません")
  end if
end subroutine

subroutine t_int(fn, ef)
  character(len=*), intent(in) :: fn, ef
  integer :: a(nx,ny)
  real :: e(nx,ny)
  integer :: stat
  character(len=512) :: msg
  call load_expected(ef, e)
  a = 0
  call gtif_read("data_gtif/"//fn, nx, ny, a, stat, msg)
  if (stat /= 0) then
    call report("int  "//fn, .false., msg)
  else
    call report("int  "//fn, all(real(a) == e), "値が期待値と一致しません")
  end if
end subroutine

subroutine t_err_real(fn)
  character(len=*), intent(in) :: fn
  real :: a(nx,ny)
  integer :: stat
  character(len=512) :: msg
  call gtif_read("data_gtif/"//fn, nx, ny, a, stat, msg)
  call report("err  "//fn, stat /= 0, "エラーになるべき入力が成功しました")
  if (stat /= 0) print '(a)', "      ("//trim(msg)//")"
end subroutine

subroutine t_err_int(fn)
  character(len=*), intent(in) :: fn
  integer :: a(nx,ny)
  integer :: stat
  character(len=512) :: msg
  call gtif_read("data_gtif/"//fn, nx, ny, a, stat, msg)
  call report("err  "//fn, stat /= 0, "エラーになるべき入力が成功しました")
  if (stat /= 0) print '(a)', "      ("//trim(msg)//")"
end subroutine

subroutine t_meta()
  use, intrinsic :: iso_fortran_env, only : real64
  type(t_gtif_info) :: info
  integer :: stat
  character(len=512) :: msg
  logical :: ok
  real(real64), parameter :: cs_geo = 1.0_real64 / 900.0_real64   ! 4 秒格子
  real(real64), parameter :: tol = 1.0e-9_real64

  ! 経緯度・nodata 付き
  call gtif_inquire("data_gtif/f32_none_strip_geo.tif", info, stat, msg)
  ok = (stat == 0)
  if (ok) then
    ok = info%has_georef .and. info%is_geog .and. info%epsg == 6668 &
         .and. info%is_real .and. info%has_nodata &
         .and. info%nodata == -9999.0_real64 &
         .and. abs(info%csx - cs_geo) < tol &
         .and. abs(info%xul - 138.625_real64) < tol &
         .and. abs(info%yul - (35.90_real64 + ny*cs_geo)) < tol
    msg = "メタ情報(経緯度)が期待と一致しません"
  end if
  call report("meta f32_none_strip_geo.tif", ok, msg)

  ! 投影(メートル)
  call gtif_inquire("data_gtif/f32_none_strip.tif", info, stat, msg)
  ok = (stat == 0)
  if (ok) then
    ok = info%has_georef .and. (.not. info%is_geog) .and. info%epsg == 6677 &
         .and. (.not. info%has_nodata) &
         .and. info%csx == 100.0_real64 .and. info%csy == 100.0_real64 &
         .and. info%xul == -20000.0_real64 &
         .and. info%yul == -80000.0_real64 + ny*100.0_real64
    msg = "メタ情報(投影)が期待と一致しません"
  end if
  call report("meta f32_none_strip.tif", ok, msg)

  ! 未対応圧縮でもメタ情報は取れること(m_geoinfo の probe が使う)
  call gtif_inquire("data_gtif/f32_deflate_strip.tif", info, stat, msg)
  ok = (stat == 0)
  if (ok) then
    ok = (info%nx == nx .and. info%ny == ny .and. info%has_georef)
    msg = "メタ情報(Deflate)が期待と一致しません"
  end if
  call report("meta f32_deflate_strip.tif", ok, msg)
end subroutine

end program
