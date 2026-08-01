!======================================================================
! GeoTIFF リーダーの回帰テスト
!   - data_gtif/ : GDAL 生成の系統的変種(期待値は expected/)
!   - data_user/ : QGIS / ArcGIS Pro の実出力サンプル(期待値は
!                  expected_user/。README.md 参照)
!   値のビット一致、未対応形式(Deflate=Phase 2、BigTIFF=Phase 4)の
!   エラー停止、メタ情報(位置・CRS・nodata)を検査する。
!   実行は ./Run.sh(ビルドは同ディレクトリの Makefile)
!======================================================================
program test_gtif_reader
  use, intrinsic :: iso_fortran_env, only : real64
  use m_geotiff, only : t_gtif_info, gtif_inquire, gtif_read
  implicit none

  integer :: nfail = 0
  integer :: ntest = 0

  ! ---- GDAL 生成分(60x48) ----
  ! 実数読み(値のビット一致)
  call t_real("data_gtif/f32_none_strip.tif", "expected/f32.txt", 60, 48)
  call t_real("data_gtif/f32_none_tile.tif", "expected/f32.txt", 60, 48)
  call t_real("data_gtif/f32_lzw_strip.tif", "expected/f32.txt", 60, 48)
  call t_real("data_gtif/f32_lzw_pred3_strip.tif", "expected/f32.txt", 60, 48)
  call t_real("data_gtif/f32_packbits_strip.tif", "expected/f32.txt", 60, 48)
  call t_real("data_gtif/f32_none_strip_be.tif", "expected/f32.txt", 60, 48)
  call t_real("data_gtif/f32_none_strip_geo.tif", "expected/f32.txt", 60, 48)
  call t_real("data_gtif/f64_none_strip.tif", "expected/f64.txt", 60, 48)

  ! 整数読み
  call t_int("data_gtif/u8_none_strip.tif", "expected/u8.txt", 60, 48)
  call t_int("data_gtif/i16_lzw_pred2_strip.tif", "expected/i16.txt", 60, 48)
  call t_int("data_gtif/i16_none_strip_be.tif", "expected/i16.txt", 60, 48)
  call t_int("data_gtif/i32_none_strip.tif", "expected/i32.txt", 60, 48)
  call t_int("data_gtif/u32_lzw_strip.tif", "expected/u32.txt", 60, 48)

  ! 整数型 GeoTIFF の実数読み(型変換経路)
  call t_real("data_gtif/i32_none_strip.tif", "expected/i32.txt", 60, 48)
  call t_real("data_gtif/u8_none_strip.tif", "expected/u8.txt", 60, 48)

  ! 未対応・不整合はエラーになること
  call t_err_real("data_gtif/f32_deflate_strip.tif", 60, 48)
  call t_err_real("data_gtif/f32_deflate_pred3_tile.tif", 60, 48)
  call t_err_real("data_gtif/f32_deflate_bigtiff.tif", 60, 48)
  call t_err_int("data_gtif/u16_deflate_tile.tif", 60, 48)
  call t_err_int("data_gtif/f32_none_strip.tif", 60, 48)  ! 実数型を整数入力に使うのは誤り

  ! ---- QGIS / ArcGIS Pro の実出力(2451: 56x37, 4326: 56x30) ----
  call t_real("data_user/d2451_f32_arc_none.tif", "expected_user/d2451_f32.txt", 56, 37)
  call t_real("data_user/d2451_f32_arc_lzw.tif", "expected_user/d2451_f32.txt", 56, 37)
  call t_real("data_user/d2451_f32_qgis_std.tif", "expected_user/d2451_f32.txt", 56, 37)
  call t_int("data_user/d2451_i16_qgis_std.tif", "expected_user/d2451_i16.txt", 56, 37)
  call t_real("data_user/d4326_f32_arc_none.tif", "expected_user/d4326_f32.txt", 56, 30)
  call t_real("data_user/d4326_f32_arc_lzw.tif", "expected_user/d4326_f32.txt", 56, 30)
  call t_real("data_user/d4326_f32_qgis_std.tif", "expected_user/d4326_f32.txt", 56, 30)
  call t_int("data_user/d4326_i16_arc_none.tif", "expected_user/d4326_i16.txt", 56, 30)
  call t_int("data_user/d4326_i16_arc_lzw.tif", "expected_user/d4326_i16.txt", 56, 30)
  call t_int("data_user/d4326_i16_qgis_std.tif", "expected_user/d4326_i16.txt", 56, 30)
  call t_int("data_user/d4326_i8_qgis_std.tif", "expected_user/d4326_i8.txt", 56, 30)
  call t_int("data_user/d4326_i8_arc_lzw.tif", "expected_user/d4326_i8.txt", 56, 30)

  ! QGIS 高圧縮(Deflate)は Phase 2 まではエラー停止を検査
  call t_err_real("data_user/d2451_f32_qgis_deflate.tif", 56, 37)
  call t_err_int("data_user/d4326_i16_qgis_deflate.tif", 56, 30)

  ! ---- メタ情報(位置情報・CRS・nodata) ----
  call t_meta_gdal()
  call t_meta_user()

  print '(a,i0,a,i0,a)', "---- ", ntest - nfail, " / ", ntest, " PASS"
  if (nfail > 0) then
    print '(a)', "=== GeoTIFF リーダーテスト FAIL ==="
    stop 1
  end if
  print '(a)', "=== GeoTIFF リーダーテスト PASS ==="

contains

subroutine load_expected(ef, nx, ny, e)
  character(len=*), intent(in) :: ef
  integer, intent(in) :: nx, ny
  real, intent(out) :: e(nx,ny)
  integer :: un, j
  open(newunit=un, file=ef, status='old')
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

subroutine t_real(fn, ef, nx, ny)
  character(len=*), intent(in) :: fn, ef
  integer, intent(in) :: nx, ny
  real :: a(nx,ny), e(nx,ny)
  integer :: stat
  character(len=512) :: msg
  call load_expected(ef, nx, ny, e)
  a = 0.0
  call gtif_read(fn, nx, ny, a, stat, msg)
  if (stat /= 0) then
    call report("real "//fn, .false., msg)
  else
    call report("real "//fn, all(a == e), "値が期待値とビット一致しません")
  end if
end subroutine

subroutine t_int(fn, ef, nx, ny)
  character(len=*), intent(in) :: fn, ef
  integer, intent(in) :: nx, ny
  integer :: a(nx,ny)
  real :: e(nx,ny)
  integer :: stat
  character(len=512) :: msg
  call load_expected(ef, nx, ny, e)
  a = 0
  call gtif_read(fn, nx, ny, a, stat, msg)
  if (stat /= 0) then
    call report("int  "//fn, .false., msg)
  else
    call report("int  "//fn, all(real(a) == e), "値が期待値と一致しません")
  end if
end subroutine

subroutine t_err_real(fn, nx, ny)
  character(len=*), intent(in) :: fn
  integer, intent(in) :: nx, ny
  real :: a(nx,ny)
  integer :: stat
  character(len=512) :: msg
  call gtif_read(fn, nx, ny, a, stat, msg)
  call report("err  "//fn, stat /= 0, "エラーになるべき入力が成功しました")
  if (stat /= 0) print '(a)', "      ("//trim(msg)//")"
end subroutine

subroutine t_err_int(fn, nx, ny)
  character(len=*), intent(in) :: fn
  integer, intent(in) :: nx, ny
  integer :: a(nx,ny)
  integer :: stat
  character(len=512) :: msg
  call gtif_read(fn, nx, ny, a, stat, msg)
  call report("err  "//fn, stat /= 0, "エラーになるべき入力が成功しました")
  if (stat /= 0) print '(a)', "      ("//trim(msg)//")"
end subroutine

subroutine t_meta_gdal()
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
         .and. abs(info%yul - (35.90_real64 + 48*cs_geo)) < tol
    msg = "メタ情報(経緯度)が期待と一致しません"
  end if
  call report("meta data_gtif/f32_none_strip_geo.tif", ok, msg)

  ! 投影(メートル)
  call gtif_inquire("data_gtif/f32_none_strip.tif", info, stat, msg)
  ok = (stat == 0)
  if (ok) then
    ok = info%has_georef .and. (.not. info%is_geog) .and. info%epsg == 6677 &
         .and. (.not. info%has_nodata) &
         .and. info%csx == 100.0_real64 .and. info%csy == 100.0_real64 &
         .and. info%xul == -20000.0_real64 &
         .and. info%yul == -80000.0_real64 + 48*100.0_real64
    msg = "メタ情報(投影)が期待と一致しません"
  end if
  call report("meta data_gtif/f32_none_strip.tif", ok, msg)

  ! 未対応圧縮でもメタ情報は取れること(m_geoinfo の probe が使う)
  call gtif_inquire("data_gtif/f32_deflate_strip.tif", info, stat, msg)
  ok = (stat == 0)
  if (ok) then
    ok = (info%nx == 60 .and. info%ny == 48 .and. info%has_georef)
    msg = "メタ情報(Deflate)が期待と一致しません"
  end if
  call report("meta data_gtif/f32_deflate_strip.tif", ok, msg)
end subroutine

subroutine t_meta_user()
  type(t_gtif_info) :: info
  integer :: stat
  character(len=512) :: msg
  logical :: ok

  ! ArcGIS(投影 2451)。GeographicType=4612 と ProjectedCSType=2451 を
  ! 併記する ArcGIS 固有のキー構成で、投影側の 2451 を採ること
  call gtif_inquire("data_user/d2451_f32_arc_none.tif", info, stat, msg)
  ok = (stat == 0)
  if (ok) then
    ok = info%has_georef .and. (.not. info%is_geog) .and. info%epsg == 2451 &
         .and. info%csx == 1000.0_real64 .and. info%csy == 1000.0_real64
    msg = "メタ情報(ArcGIS 2451)が期待と一致しません"
  end if
  call report("meta data_user/d2451_f32_arc_none.tif", ok, msg)

  ! QGIS(経緯度 4326)
  call gtif_inquire("data_user/d4326_f32_qgis_std.tif", info, stat, msg)
  ok = (stat == 0)
  if (ok) then
    ok = info%has_georef .and. info%is_geog .and. info%epsg == 4326
    msg = "メタ情報(QGIS 4326)が期待と一致しません"
  end if
  call report("meta data_user/d4326_f32_qgis_std.tif", ok, msg)

  ! GDAL_NODATA が指数表記の実数でも読めること(QGIS の既定 nodata)
  call gtif_inquire("data_user/d2451_i16_qgis_std.tif", info, stat, msg)
  ok = (stat == 0)
  if (ok) then
    ok = info%has_nodata .and. (info%nodata < -1.0e38_real64)
    msg = "メタ情報(実数 nodata)が期待と一致しません"
  end if
  call report("meta data_user/d2451_i16_qgis_std.tif", ok, msg)
end subroutine

end program
