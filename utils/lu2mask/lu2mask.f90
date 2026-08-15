!----------------------------------------------------------------------
! 土地利用データからマスク(0/1 ラスタ)を生成する
! "lu2mask"
!----------------------------------------------------------------------
!
! 土地利用ファイル(list_geoinfo の fn_luse)を読み、指定した土地利用
! コードのセルを 1、それ以外を 0 とするラスタを書き出す。
! 生成したファイルは list_geoinfo の fn_sw(海域マスク)・fn_rw(河道
! マスク)・fn_seaside(海側マスク)等にそのまま指定できる。
! 本体へのマスク自動生成の組み込みは行わない、との設計判断に基づく
! 前処理ユーティリティ(developer.md §40)。
!
! 使い方:
!   $ ./lu2mask parameterfile maskfile code1 [code2 ...]
!
!   1. parameterfile: 計算に使うシステムパラメータファイル。
!      dir_data・f_input_mode と、fn_geoinfo 経由の nx, ny, fn_luse を
!      本体と同じ解釈で読む(nx, ny の指定方法も本体と同じ)。
!   2. maskfile: 書き出すマスクのパス(書いたとおりの場所に出力する。
!      fn_sw 等は dir_data 相対で参照されるため、通常は dir_data 内を
!      指定する)。
!   3. code: マスクを 1 にする土地利用コード(整数)。複数指定可。
!
! 入出力の形式は f_input_mode に従う(1:text, 2:bil, 4:GeoTIFF)。
!   - bil: fn_luse と同じ場所に hdr があれば nx, ny を補完・検査し、
!     出力にも hdr を併記する。hdr が無ければ namelist の nx, ny が必須。
!   - GeoTIFF: 格子数はファイルの自己記述から補完・検査する。位置情報
!     タグがあれば出力にも引き継ぐ(無ければ GeoTIFF では書けないので
!     停止する)。
!   - text: namelist の nx, ny 指定が必須。
!
! 生成したマスクは GIS 等で必ず目視確認してから使うこと。特に:
!   - 海域マスク: 流出河川のない湖沼を海域(=排水先)にしたい場合は
!     生成後に手を入れる(utils/modify_sealand の例を参照)。
!   - 河道マスク: 国土数値情報の「河川地及び湖沼」のような土地利用
!     コードは湖沼・河川敷を含み、fn_rw が想定する河道線(1セル幅の
!     澪筋)とは一致しない。fn_rw 用途には河川中心線のラスタ化(GIS)を
!     推奨する(developer.md §40)。
!----------------------------------------------------------------------
program lu2mask
  use m_sysparam, only : t_sysparam, m_sysparam_init
  use list_geoinfo, only : t_list_geoinfo, list_geoinfo_read
  use m_fileio, only : fileio_read_matrix, fileio_write_matrix, &
                       e_fmt_txt, e_fmt_bil, e_fmt_gtif
  use m_georef, only : t_georef, georef_hdr_name, georef_read_hdr, &
                       georef_write_hdr, e_pix_int
  use m_geotiff, only : t_gtif_info, gtif_inquire
  use m_parallel, only : par_init, par_finalize, par_stop
  use m_util, only : itoa
  implicit none

  type(t_sysparam) :: p
  type(t_list_geoinfo) :: list
  type(t_georef) :: gr
  integer :: nx, ny
  integer, allocatable :: codes(:)                 ! マスク対象の土地利用コード
  integer, allocatable :: ncells(:)                ! コードごとの該当セル数
  integer, allocatable :: lu(:,:)                  ! 土地利用データ
  integer, allocatable :: mask(:,:)                ! 生成するマスク
  character(:), allocatable :: fn_sysparam, fn_out, fn_luse
  integer :: i, j, k, nhit

  call get_args(fn_sysparam, fn_out, codes)

  call par_init()
  call m_sysparam_init(p, fn_sysparam)
  call list_geoinfo_read(p, list)

  if (len_trim(list%fn_luse) == 0) then
    call par_stop("lu2mask: fn_luse is not set in list_geoinfo ("//trim(p%fn_geoinfo)//")")
  end if
  fn_luse = trim(p%dir_data) // "/" // trim(list%fn_luse)

  ! nx, ny の確定と地理座標参照の取得(fn_luse 自身から補完する)
  call probe_grid(p, list, fn_luse, nx, ny, gr)
  print '(a,i0,a,i0)', "grid: ", nx, " x ", ny

  ! 土地利用データの読み込み
  allocate(lu(1:nx,1:ny), source = 0)
  print '(a)', "reading " // fn_luse
  call fileio_read_matrix(fn_luse, nx, ny, lu, p%f_input_mode)

  ! マスクの生成(コードごとの該当セル数も数えて表示する)
  allocate(mask(1:nx,1:ny), source = 0)
  allocate(ncells(1:size(codes)), source = 0)
  do j = 1, ny
    do i = 1, nx
      do k = 1, size(codes)
        if (lu(i,j) == codes(k)) then
          mask(i,j) = 1
          ncells(k) = ncells(k) + 1
          exit
        end if
      end do
    end do
  end do

  nhit = 0
  do k = 1, size(codes)
    if (ncells(k) > 0) then
      print '(a,i0,a,i0,a)', " code ", codes(k), ": ", ncells(k), " cells"
    else
      ! 該当ゼロはコードの取り違えの可能性が高いので目立たせる
      print '(a,i0,a)', " code ", codes(k), ": 0 cells (WARNING: not found in the land-use data)"
    end if
    nhit = nhit + ncells(k)
  end do
  print '(a,i0,a,i0,a)', "masked ", nhit, " / ", nx * ny, " cells"
  if (nhit == 0) then
    call par_stop("lu2mask: no cell matched the given code(s); nothing to write")
  end if

  ! マスクの書き出し(入力と同じ形式)
  print '(a)', "writing " // fn_out
  if (p%f_input_mode == e_fmt_gtif) then
    if (.not. gr%active) then
      call par_stop("lu2mask: GeoTIFF output requires georeference tags in "//fn_luse)
    end if
    call fileio_write_matrix(fn_out, nx, ny, mask, e_fmt_gtif, gr)
  else
    call fileio_write_matrix(fn_out, nx, ny, mask, p%f_input_mode)
    ! bil で座標が分かっている場合は hdr を併記する(m_output と同じ流儀)
    if (p%f_input_mode == e_fmt_bil .and. gr%active) then
      print '(a)', "writing " // georef_hdr_name(fn_out)
      call georef_write_hdr(georef_hdr_name(fn_out), gr, nx, ny, e_pix_int)
    end if
  end if

  call par_finalize()

contains

!----------------------------------------------------------------------
! コマンドライン引数の取得
!----------------------------------------------------------------------
subroutine get_args(fn_sysparam, fn_out, codes)
  character(:), allocatable, intent(out) :: fn_sysparam, fn_out
  integer, allocatable, intent(out) :: codes(:)
  character(:), allocatable :: s
  integer :: argc, i, ios

  argc = command_argument_count()
  if (argc < 3) then
    call get_arg(0, s)
    print '(a)', "usage: " // s // " parameterfile maskfile code1 [code2 ...]"
    stop 1
  end if

  call get_arg(1, fn_sysparam)
  call get_arg(2, fn_out)
  allocate(codes(1:argc-2))
  do i = 3, argc
    call get_arg(i, s)
    read(s, *, iostat=ios) codes(i-2)
    if (ios /= 0) then
      print '(a)', "lu2mask: invalid land-use code: " // s
      stop 1
    end if
  end do
end subroutine

!----------------------------------------------------------------------
! i 番目の引数を可変長文字列で取得する
!----------------------------------------------------------------------
subroutine get_arg(i, s)
  integer, intent(in) :: i
  character(:), allocatable, intent(out) :: s
  integer :: l
  call get_command_argument(number=i, length=l)
  allocate(character(l) :: s)
  call get_command_argument(number=i, value=s)
end subroutine

!----------------------------------------------------------------------
! nx, ny の確定と地理座標参照の取得
!   m_geoinfo の probe_georef と同じ流儀を fn_luse に適用する:
!   ファイル(bil の hdr / GeoTIFF のタグ)から得た格子数で namelist の
!   未指定分を補完し、両方あれば無言でどちらかを優先せず整合を検査する。
!   座標参照が取れた場合は出力(hdr 併記・GeoTIFF タグ)に引き継ぐ
!----------------------------------------------------------------------
subroutine probe_grid(p, list, fn_luse, nx, ny, gr)
  type(t_sysparam), intent(in) :: p
  type(t_list_geoinfo), intent(in) :: list
  character(len=*), intent(in) :: fn_luse
  integer, intent(out) :: nx, ny
  type(t_georef), intent(out) :: gr
  type(t_gtif_info) :: tinfo
  character(:), allocatable :: fn_hdr
  integer :: ncols, nrows, stat
  character(len=512) :: msg
  logical :: ex

  nx = list%nx
  ny = list%ny
  gr%epsg = list%epsg
  ncols = 0
  nrows = 0

  if (p%f_input_mode == e_fmt_bil) then
    fn_hdr = georef_hdr_name(fn_luse)
    inquire(file=fn_hdr, exist=ex)
    if (ex) then
      print '(a)', "reading " // fn_hdr
      call georef_read_hdr(fn_hdr, gr, ncols, nrows)
    end if

  else if (p%f_input_mode == e_fmt_gtif) then
    call gtif_inquire(fn_luse, tinfo, stat, msg)
    if (stat /= 0) call par_stop("lu2mask: cannot read GeoTIFF: "//trim(msg))
    ncols = tinfo%nx
    nrows = tinfo%ny
    if (tinfo%has_georef) then
      gr%active = .true.
      gr%xul = tinfo%xul
      gr%yul = tinfo%yul
      gr%csx = tinfo%csx
      gr%csy = tinfo%csy
      gr%is_geog = tinfo%is_geog
      gr%has_nodata = tinfo%has_nodata
      gr%nodata = tinfo%nodata
      if (tinfo%epsg /= 0) then
        if (list%epsg == 0) then
          gr%epsg = tinfo%epsg
        else if (list%epsg /= tinfo%epsg) then
          call par_stop("lu2mask: epsg("//itoa(list%epsg)//") does not match the GeoTIFF CRS(" &
                        //itoa(tinfo%epsg)//")")
        end if
      end if
    end if
  end if

  ! 格子数: 未指定なら補完、指定済みなら一致検査
  if (ncols > 0) then
    if (nx <= 0) then
      nx = ncols
    else if (nx /= ncols) then
      call par_stop("lu2mask: nx("//itoa(nx)//") does not match the land-use file (" &
                    //itoa(ncols)//")")
    end if
  end if
  if (nrows > 0) then
    if (ny <= 0) then
      ny = nrows
    else if (ny /= nrows) then
      call par_stop("lu2mask: ny("//itoa(ny)//") does not match the land-use file (" &
                    //itoa(nrows)//")")
    end if
  end if
  if (nx <= 0 .or. ny <= 0) then
    call par_stop("lu2mask: cannot determine nx, ny " &
                  //"(set nx, ny in list_geoinfo, or use bil+hdr / GeoTIFF input)")
  end if

  ! 経緯度格子で CRS が決まらない場合は WGS84 を仮定する(probe_georef
  ! と同じ仮定。GeoTIFF 出力の CRS タグにのみ効く)
  if (gr%active .and. gr%is_geog .and. gr%epsg == 0) then
    gr%epsg = 4326
    print '(a)', "assuming WGS84 (EPSG:4326) for the geographic grid " &
                 //"(set epsg in list_geoinfo to record the exact CRS)"
  end if

end subroutine

end program
