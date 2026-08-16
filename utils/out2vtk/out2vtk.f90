!-----------------------------------------------------------------------
! 計算結果の分布ファイルを ParaView 用 VTK 形式に変換する
! "out2vtk"
!-----------------------------------------------------------------------
!
! result/ の分布出力(txt / bil+hdr / GeoTIFF)と FILENUMBER.csv を読み、
! 3D 可視化(アニメーション)用の VTK ファイル群を書き出す。
!
!   terrain.vts      地形面(標高で持ち上げた曲面格子。テクスチャ座標付き
!                    なので QGIS で書き出した地図・衛星画像をドレープできる)
!   flood_XXXX.vts   各出力時刻の水面(z+H で持ち上げた曲面格子。
!                    水深 H ほか検出された変数を点データとして同梱)
!   flood.pvd        時系列コレクション(実時刻 t 秒がタイムラインになる)
!
! 実行時の引数は設定ファイル(namelist)1つ。省略時は全項目デフォルト:
!
!   $ ./out2vtk [out2vtk.nml]
!   $ ./out2vtk param.txt        # 計算のパラメータファイルを直接渡してもよい
!
! 引数のファイルに &out2vtk 群があれば設定ファイル、なければ計算の
! パラメータファイル(&list_sysparam 群)とみなして dir_result・
! outfn_suffix・格子情報(&list_geoinfo の nx, ny, dx, dy)を引き継ぐ。
! 設定ファイルの fn_param でパラメータファイルを併用指定してもよい。
! 設定項目は下記 &out2vtk を参照。使い方・ParaView の手順は README.md。
!
! 設計メモ:
! - 本体(m_output)には可視化専用形式を足さない方針(§0: 入出力は
!   単純形式・可視化は利用者側)のため後処理コンバータとする。
! - 格子寸法・地理参照は Z0000 の hdr / GeoTIFF から自動取得する。
!   txt 出力のみの場合は寸法をファイルから数え、セル寸法は namelist。
! - VTK は XML StructuredGrid(.vts)の appended raw binary。外部
!   ライブラリ不使用・リトルエンディアン前提(既存 bil 出力と同じ)。
! - 点データは float32。座標は float64(投影座標の桁落ち防止)。
!
!-----------------------------------------------------------------------
module m_out2vtk
  use, intrinsic :: iso_fortran_env, only : real32, real64, int64
  use, intrinsic :: ieee_arithmetic, only : ieee_value, ieee_quiet_nan
  use m_fileio, only : fileio_read_matrix, e_fmt_txt, e_fmt_bil, e_fmt_gtif
  use m_georef, only : t_georef, georef_read_hdr, georef_est_cellsize_m
  use m_geotiff, only : t_gtif_info, gtif_inquire
  use m_sysparam, only : t_sysparam, m_sysparam_init
  use list_geoinfo, only : t_list_geoinfo, list_geoinfo_read
  use m_sysdep_util, only : sysdep_mkdir
  implicit none
  private

  public :: out2vtk_run

  ! ---- 設定(namelist &out2vtk)------------------------------------
  character(len=256) :: fn_param = ""          ! 計算のパラメータファイル(任意。
                                               !   dir_result・格子情報を引き継ぐ)
  character(len=256) :: dir_result = ""        ! 分布出力のディレクトリ(空= result)
  character(len=256) :: dir_vtk = ""           ! VTK 出力先(空= dir_result/vtk)
  character(len=64) :: outfn_suffix = ""       ! 計算時の outfn_suffix と同じ値
  real(real64) :: hmin = 0.01_real64  ! 水膜閾値(m)。H < hmin の点の水面系
                                      ! 変数を NaN にする。0 で無効(全点出力)
  integer :: nx = 0, ny = 0           ! 格子数(0 = hdr/GeoTIFF/txt から自動)
  real(real64) :: csx = 0.0_real64    ! セル寸法(0 = 自動。地理参照が無い
  real(real64) :: csy = 0.0_real64    !   txt 出力ではデフォルト 1 m)
  character(len=8) :: vars(64) = ""   ! 同梱する変数の接頭辞リスト(空=検出全部)

  namelist /out2vtk/ fn_param, dir_result, dir_vtk, outfn_suffix, hmin, &
                     nx, ny, csx, csy, vars

  ! ---- 変数カタログ(m_output の出力接頭辞)-------------------------
  ! masked: 水面上の量(乾燥域では無意味)→ hmin で NaN マスクする。
  !   地表・地中の量(降雨・地下貯留・積雪等)はマスクしない。
  ! 整数フラグ(Ddd, Dda)は面の色分けに不向きなので対象外。
  type t_varcat
    character(len=4) :: prefix = ""
    logical :: masked = .false.
  end type
  type(t_varcat), parameter :: catalog(22) = [ &
    t_varcat("H",   .true.),  & ! 水深(最大水深)
    t_varcat("E",   .true.),  & ! 水位
    t_varcat("u",   .true.),  & ! x方向流速
    t_varcat("v",   .true.),  & ! y方向流速
    t_varcat("m",   .true.),  & ! x方向線流量
    t_varcat("n",   .true.),  & ! y方向線流量
    t_varcat("V",   .true.),  & ! 流速の絶対値(最大流速)
    t_varcat("Q",   .true.),  & ! 線流量の絶対値(最大流量)
    t_varcat("Qc",  .true.),  & ! 積算線流量
    t_varcat("Qd",  .true.),  & ! 流向(最大流量の流向)
    t_varcat("Fr",  .true.),  & ! フルード数
    t_varcat("Cn",  .true.),  & ! クーラン数
    t_varcat("C",   .true.),  & ! 輸送物質濃度
    t_varcat("Ht",  .true.),  & ! 最大水深の時刻
    t_varcat("Qt",  .true.),  & ! 最大流量の時刻
    t_varcat("Pr",  .false.), & ! 降雨強度
    t_varcat("Hrs", .false.), & ! ため池水深
    t_varcat("Hg",  .false.), & ! 地下貯留水深
    t_varcat("Hg2", .false.), & ! 風化基岩層の貯留水深
    t_varcat("Sw",  .false.), & ! 積雪水量
    t_varcat("Sd",  .false.), & ! 土層厚
    t_varcat("B",   .false.)]   ! 表面蓄積プール

  ! ---- 内部状態 ----------------------------------------------------
  type(t_georef) :: gr                  ! 地理参照(active でなければローカル座標)
  real(real64) :: dx = 1.0_real64       ! セル寸法(m。経緯度格子は概算換算)
  real(real64) :: dy = 1.0_real64
  real(real64), allocatable :: xc(:), yc(:)  ! セル中心座標(モデルの i, j 順)
  real(real32) :: vnan                  ! quiet NaN(マスク用)
  logical :: var_seen(22) = .false.     ! 変数ごとの「初回検出」表示済みフラグ

  ! VTK に書く点データ配列の束(名前と成分数、VTK 点順の平坦データ)
  type t_arr
    character(len=16) :: name = ""
    integer :: ncomp = 1
    real(real32), allocatable :: dat(:)
  end type

contains

!-----------------------------------------------------------------------
! 主処理
!-----------------------------------------------------------------------
subroutine out2vtk_run(fn_config)
  character(len=*), intent(in) :: fn_config

  integer, allocatable :: knums(:)      ! FILENUMBER.csv のファイル番号
  real(real64), allocatable :: ktimes(:)  ! 対応する時刻 t(s)
  real, allocatable :: zg(:,:)          ! 地形(Z0000)
  integer :: nk, un, ios
  character(len=512) :: iom

  vnan = ieee_value(0.0_real32, ieee_quiet_nan)

  ! 設定ファイル(省略可)。&out2vtk 群がなく &list_sysparam 群がある
  ! ファイルは計算のパラメータファイルとみなす
  if (len_trim(fn_config) > 0) then
    if (file_has_group(fn_config, "&out2vtk")) then
      open(newunit=un, file=trim(fn_config), status='old', action='read', &
           iostat=ios, iomsg=iom)
      if (ios /= 0) then
        print *, "out2vtk: cannot open config file: ", trim(fn_config)
        print *, trim(iom)
        stop 1
      end if
      read(un, nml=out2vtk, iostat=ios, iomsg=iom)
      if (ios /= 0) then
        print *, "out2vtk: error reading namelist &out2vtk: ", trim(iom)
        stop 1
      end if
      close(un)
    else if (file_has_group(fn_config, "&list_sysparam")) then
      fn_param = fn_config
    else
      print *, "out2vtk: no &out2vtk or &list_sysparam group in ", &
               trim(fn_config)
      stop 1
    end if
  end if

  ! パラメータファイルから dir_result・outfn_suffix・格子情報を引き継ぐ
  ! (&out2vtk での明示指定=デフォルト以外の値が優先)
  if (len_trim(fn_param) > 0) call inherit_param()
  if (len_trim(dir_result) == 0) dir_result = "result"
  if (len_trim(dir_vtk) == 0) dir_vtk = trim(dir_result)//"/vtk"

  call probe_grid()
  call setup_coords()
  call read_filenumber(knums, ktimes)
  nk = size(knums)

  print '(a,i0,a,i0)',    " grid      : nx=", nx, "  ny=", ny
  if (gr%active) then
    print '(a,2f16.4)',   " origin NW : ", gr%xul, gr%yul
  else
    print '(a)',          " georef    : none (local coordinates)"
  end if
  print '(a,2f12.4)',     " cellsize  : ", dx, dy
  print '(a,f8.4)',       " hmin (m)  : ", hmin
  print '(a,i0)',         " timesteps : ", nk

  call sysdep_mkdir(trim(dir_vtk))

  ! 地形面(Z0000 は k=0 で常に出力される)
  allocate(zg(1:nx,1:ny))
  call read_var("Z", 0, zg, ios)
  if (ios /= 0) then
    print *, "out2vtk: terrain file Z0000 not found in ", trim(dir_result)
    stop 1
  end if
  call write_terrain(zg)

  ! 各時刻の水面
  call write_flood_series(zg, knums, ktimes)

  print '(a)', " done: "//trim(dir_vtk)//"/flood.pvd"
end subroutine


!-----------------------------------------------------------------------
! ファイル中に namelist 群(例 "&out2vtk")の開始行があるか
!   行頭(空白は許す)の群名のみ数える。大文字小文字は区別しない
!-----------------------------------------------------------------------
logical function file_has_group(fname, group)
  character(len=*), intent(in) :: fname, group
  character(len=1024) :: line
  integer :: un, ios

  file_has_group = .false.
  open(newunit=un, file=trim(fname), status='old', action='read', iostat=ios)
  if (ios /= 0) then
    print *, "out2vtk: cannot open file: ", trim(fname)
    stop 1
  end if
  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    line = adjustl(line)
    if (lower(line(1:len_trim(group))) == lower(group)) then
      file_has_group = .true.
      exit
    end if
  end do
  close(un)
end function


!-----------------------------------------------------------------------
! 小文字化(ASCII のみ)
!-----------------------------------------------------------------------
function lower(s) result(t)
  character(len=*), intent(in) :: s
  character(len=len(s)) :: t
  integer :: i, c
  t = s
  do i = 1, len(s)
    c = iachar(s(i:i))
    if (c >= iachar('A') .and. c <= iachar('Z')) t(i:i) = achar(c + 32)
  end do
end function


!-----------------------------------------------------------------------
! 計算のパラメータファイルから設定を引き継ぐ
!   dir_result・outfn_suffix と、&list_geoinfo の nx, ny, dx, dy。
!   &out2vtk で明示された(デフォルト以外の)値には触れない
!-----------------------------------------------------------------------
subroutine inherit_param()
  type(t_sysparam) :: p
  type(t_list_geoinfo) :: glist

  print '(a)', " param     : "//trim(fn_param)
  call m_sysparam_init(p, trim(fn_param))
  call list_geoinfo_read(p, glist)

  if (len_trim(dir_result) == 0) dir_result = p%dir_result
  if (len_trim(outfn_suffix) == 0) outfn_suffix = p%outfn_suffix
  if (nx == 0) nx = glist%nx
  if (ny == 0) ny = glist%ny
  ! セル寸法の指定は dx, dy のほか領域長 lx, ly でも可能(解決は
  ! m_geoinfo の仕事だが、ここでは単純な除算で足りる)
  if (csx <= 0.0_real64) then
    if (glist%dx > 0.0) then
      csx = real(glist%dx, real64)
    else if (glist%lx > 0.0 .and. glist%nx > 0) then
      csx = real(glist%lx, real64) / glist%nx
    end if
  end if
  if (csy <= 0.0_real64) then
    if (glist%dy > 0.0) then
      csy = real(glist%dy, real64)
    else if (glist%ly > 0.0 .and. glist%ny > 0) then
      csy = real(glist%ly, real64) / glist%ny
    end if
  end if
end subroutine


!-----------------------------------------------------------------------
! 格子寸法と地理参照を Z0000 から確定する
!   優先順: bil+hdr → GeoTIFF → txt(寸法を数える)。namelist の
!   nx, ny, csx, csy は「自動取得できないときの補完」および検算に使う
!-----------------------------------------------------------------------
subroutine probe_grid()
  character(:), allocatable :: base
  type(t_gtif_info) :: info
  integer :: pnx, pny, stat
  character(len=256) :: msg
  logical :: ex

  base = trim(dir_result)//"/Z0000"//trim(outfn_suffix)
  pnx = 0; pny = 0

  inquire(file=base//".hdr", exist=ex)
  if (ex) then
    call georef_read_hdr(base//".hdr", gr, pnx, pny)
    gr%active = .true.
  else
    inquire(file=base//".tif", exist=ex)
    if (ex) then
      call gtif_inquire(base//".tif", info, stat, msg)
      if (stat /= 0) then
        print *, "out2vtk: cannot read GeoTIFF: ", trim(msg)
        stop 1
      end if
      pnx = info%nx; pny = info%ny
      if (info%has_georef) then
        gr%active = .true.
        gr%xul = info%xul; gr%yul = info%yul
        gr%csx = info%csx; gr%csy = info%csy
        gr%epsg = info%epsg
        gr%is_geog = info%is_geog
      end if
    else
      inquire(file=base//".txt", exist=ex)
      if (ex) call probe_txt_dims(base//".txt", pnx, pny)
    end if
  end if

  ! namelist との突き合わせ(指定があれば検算、無ければ補完)
  if (pnx > 0) then
    if (nx > 0 .and. nx /= pnx .or. ny > 0 .and. ny /= pny) then
      print '(a,2i6,a,2i6)', " out2vtk: grid size mismatch: namelist", &
        nx, ny, " vs file", pnx, pny
      stop 1
    end if
    nx = pnx; ny = pny
  end if
  if (nx <= 0 .or. ny <= 0) then
    print *, "out2vtk: cannot determine grid size. ", &
             "set nx, ny in the config file"
    stop 1
  end if
end subroutine


!-----------------------------------------------------------------------
! txt 分布ファイルの寸法(列数・行数)を数える
!-----------------------------------------------------------------------
subroutine probe_txt_dims(fname, pnx, pny)
  character(len=*), intent(in) :: fname
  integer, intent(out) :: pnx, pny
  character(len=:), allocatable :: line
  integer :: un, ios, i, n, linelen
  logical :: intok

  ! 1行目を長さ無制限で読む(分布 txt は1行が長大になりうる)
  open(newunit=un, file=fname, status='old', action='read')
  line = ""
  block
    use, intrinsic :: iso_fortran_env, only : iostat_eor
    character(len=65536) :: buf
    integer :: sz
    do
      read(un, '(a)', advance='no', iostat=ios, size=sz) buf
      if (sz > 0) line = line // buf(1:sz)
      if (ios /= 0) exit                 ! iostat_eor = 行末、その他 = EOF等
    end do
  end block
  linelen = len(line)

  ! 空白区切りのトークン数 = 列数
  n = 0
  intok = .false.
  do i = 1, linelen
    if (line(i:i) /= ' ') then
      if (.not. intok) n = n + 1
      intok = .true.
    else
      intok = .false.
    end if
  end do
  pnx = n

  ! 行数を数える
  pny = 1
  do
    read(un, '(a1)', iostat=ios)
    if (ios /= 0) exit
    pny = pny + 1
  end do
  close(un)
end subroutine


!-----------------------------------------------------------------------
! セル中心座標を作る
!   投影座標系: 実座標(m)。経緯度格子・地理参照なし: ローカル座標(m)
!   (南西端外縁 = 原点、x 東向き正・y 北向き正。本体の実座標指定と同じ)
!-----------------------------------------------------------------------
subroutine setup_coords()
  integer :: i, j

  if (gr%active .and. .not. gr%is_geog) then
    dx = gr%csx; dy = gr%csy
  else if (gr%active) then
    ! 経緯度格子は中央緯度でメートルに概算換算し、ローカル座標にする
    call georef_est_cellsize_m(gr, ny, dx, dy)
    print '(a)', " note: geographic grid; using local metric coordinates"
  else
    if (csx > 0.0_real64) dx = csx
    if (csy > 0.0_real64) then
      dy = csy
    else if (csx > 0.0_real64) then
      dy = csx
    end if
  end if

  allocate(xc(nx), yc(ny))
  if (gr%active .and. .not. gr%is_geog) then
    do i = 1, nx
      xc(i) = gr%xul + (i - 0.5_real64) * dx
    end do
    do j = 1, ny
      yc(j) = gr%yul - (j - 0.5_real64) * dy
    end do
  else
    do i = 1, nx
      xc(i) = (i - 0.5_real64) * dx
    end do
    do j = 1, ny
      yc(j) = (ny - j + 0.5_real64) * dy   ! j=1 が北端(y 最大)
    end do
  end if
end subroutine


!-----------------------------------------------------------------------
! FILENUMBER.csv を読む
!   形式: "# No., time, t(s), it" のヘッダ + "k,<ctime>,t,it" の行。
!   分布出力と統計量出力が同じ番号で2行書くことがあるため重複は除く
!-----------------------------------------------------------------------
subroutine read_filenumber(knums, ktimes)
  integer, allocatable, intent(out) :: knums(:)
  real(real64), allocatable, intent(out) :: ktimes(:)
  character(len=1024) :: line
  integer :: un, ios, n, k, i1, i2
  real(real64) :: t
  character(len=512) :: iom

  open(newunit=un, file=trim(dir_result)//"/FILENUMBER.csv", &
       status='old', action='read', iostat=ios, iomsg=iom)
  if (ios /= 0) then
    print *, "out2vtk: cannot open ", trim(dir_result), "/FILENUMBER.csv"
    print *, trim(iom)
    stop 1
  end if

  allocate(knums(0), ktimes(0))
  n = 0
  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    line = adjustl(line)
    if (len_trim(line) == 0 .or. line(1:1) == '#') cycle
    ! 第1フィールド = 番号、第3フィールド = t(s)
    i1 = index(line, ',')
    if (i1 <= 1) cycle
    read(line(1:i1-1), *, iostat=ios) k
    if (ios /= 0) cycle
    i2 = index(line(i1+1:), ',')          ! 第2フィールド(日時文字列)を跳ばす
    if (i2 <= 0) cycle
    i2 = i1 + i2
    read(line(i2+1:), *, iostat=ios) t    ! 第3フィールド以降の先頭が t
    if (ios /= 0) cycle
    if (n > 0) then
      if (any(knums(1:n) == k)) cycle     ! 重複番号(統計量の行)は除く
    end if
    knums = [knums(1:n), k]
    ktimes = [ktimes(1:n), t]
    n = n + 1
  end do
  close(un)

  if (n == 0) then
    print *, "out2vtk: no entries in FILENUMBER.csv"
    stop 1
  end if
end subroutine


!-----------------------------------------------------------------------
! 分布ファイル1つを読む(bil → tif → txt の順に探す)
!   ios: 0 = 読めた、1 = 見つからない
!-----------------------------------------------------------------------
subroutine read_var(prefix, k, a, ios)
  character(len=*), intent(in) :: prefix
  integer, intent(in) :: k
  real, intent(inout) :: a(1:nx,1:ny)
  integer, intent(out) :: ios
  character(:), allocatable :: base
  character(len=4) :: snum
  logical :: ex

  write(snum, '(i4.4)') k
  base = trim(dir_result)//"/"//trim(prefix)//snum//trim(outfn_suffix)

  inquire(file=base//".bil", exist=ex)
  if (ex) then
    call fileio_read_matrix(base//".bil", nx, ny, a, e_fmt_bil)
    ios = 0; return
  end if
  inquire(file=base//".tif", exist=ex)
  if (ex) then
    call fileio_read_matrix(base//".tif", nx, ny, a, e_fmt_gtif)
    ios = 0; return
  end if
  inquire(file=base//".txt", exist=ex)
  if (ex) then
    call fileio_read_matrix(base//".txt", nx, ny, a, e_fmt_txt)
    ios = 0; return
  end if
  ios = 1
end subroutine


!-----------------------------------------------------------------------
! 地形面 terrain.vts を書く(点データ: Z、テクスチャ座標付き)
!-----------------------------------------------------------------------
subroutine write_terrain(zg)
  real, intent(in) :: zg(1:nx,1:ny)
  type(t_arr) :: arrs(2)
  real(real64), allocatable :: pts(:)

  call pack_points(zg, pts)
  arrs(1)%name = "Z"
  arrs(1)%ncomp = 1
  call pack_scalar(zg, arrs(1)%dat)
  call make_tcoords(arrs(2))

  call vtk_write_vts(trim(dir_vtk)//"/terrain.vts", pts, arrs, &
                     scalars="Z", tcoords="TCoords")
  print '(a)', " wrote: "//trim(dir_vtk)//"/terrain.vts"
end subroutine


!-----------------------------------------------------------------------
! 水面の時系列 flood_XXXX.vts と flood.pvd を書く
!   特番 9999(統計量: 最大水深等)は時系列ではなく summary.vts に、
!   9998(最終状態の再掲)は時系列と重複するため出力しない
!-----------------------------------------------------------------------
subroutine write_flood_series(zg, knums, ktimes)
  real, intent(in) :: zg(1:nx,1:ny)
  integer, intent(in) :: knums(:)
  real(real64), intent(in) :: ktimes(:)

  character(len=4) :: snum
  character(len=18) :: stime
  integer, allocatable :: kw(:)         ! 実際に書けた時刻の添字
  integer :: ik, nw
  logical :: ok

  allocate(kw(0))
  nw = 0
  do ik = 1, size(knums)
    if (knums(ik) >= 9998) cycle
    write(snum, '(i4.4)') knums(ik)
    call write_flood_one(zg, knums(ik), &
                         trim(dir_vtk)//"/flood_"//snum//".vts", ok)
    if (.not. ok) then
      print '(a,i4.4,a)', " skip: H", knums(ik), " not found"
      cycle
    end if
    nw = nw + 1
    kw = [kw(1:nw-1), ik]
  end do

  ! 統計量(最大水深 H・最大流速 V・最大流量 Q と発生時刻等)
  if (any(knums == 9999)) then
    call write_flood_one(zg, 9999, trim(dir_vtk)//"/summary.vts", ok)
    if (ok) print '(a)', " wrote: "//trim(dir_vtk)//"/summary.vts (maxima)"
  end if

  if (nw == 0) then
    print *, "out2vtk: no water depth (H) files found; no animation written"
    return
  end if

  ! 時系列コレクション
  block
    integer :: un, i
    open(newunit=un, file=trim(dir_vtk)//"/flood.pvd", status='replace')
    write(un, '(a)') '<?xml version="1.0"?>'
    write(un, '(a)') '<VTKFile type="Collection" version="0.1" byte_order="LittleEndian">'
    write(un, '(a)') '  <Collection>'
    do i = 1, nw
      write(snum, '(i4.4)') knums(kw(i))
      ! f0.3 は 0 未満で先頭ゼロを略す処理系があるため固定幅で書いて詰める
      write(stime, '(f18.3)') ktimes(kw(i))
      write(un, '(a)') '    <DataSet timestep="'//trim(adjustl(stime))// &
        '" group="" part="0" file="flood_'//snum//'.vts"/>'
    end do
    write(un, '(a)') '  </Collection>'
    write(un, '(a)') '</VTKFile>'
    close(un)
  end block
  print '(a,i0,a)', " wrote: ", nw, " timesteps -> "//trim(dir_vtk)//"/flood.pvd"
end subroutine


!-----------------------------------------------------------------------
! 1時刻分の水面 .vts を書く(ok = H ファイルが見つかり出力できた)
!-----------------------------------------------------------------------
subroutine write_flood_one(zg, k, fname, ok)
  real, intent(in) :: zg(1:nx,1:ny)
  integer, intent(in) :: k
  character(len=*), intent(in) :: fname
  logical, intent(out) :: ok

  real, allocatable :: h(:,:), zk(:,:), wse(:,:), wk(:,:), uu(:,:), vv(:,:)
  logical, allocatable :: dry(:,:)
  type(t_arr), allocatable :: arrs(:)
  real(real64), allocatable :: pts(:)
  integer :: iv, na, ios
  logical :: have_u, have_v

  ok = .false.
  allocate(h(1:nx,1:ny), zk(1:nx,1:ny), wse(1:nx,1:ny), wk(1:nx,1:ny))
  allocate(uu(1:nx,1:ny), vv(1:nx,1:ny))
  allocate(dry(1:nx,1:ny))

  call read_var("H", k, h, ios)
  if (ios /= 0) return

  ! 地形は当該時刻の Z があればそれを使う(地形変化の計算)
  call read_var("Z", k, zk, ios)
  if (ios /= 0) zk = zg

  wse = zk + h
  dry = (h < real(hmin))               ! hmin=0 なら全点 .false.

  ! 変数の束を組み立てる(H, WSE + 検出された変数 + velocity)
  allocate(arrs(size(catalog) + 3))
  arrs(1)%name = "H"
  arrs(1)%ncomp = 1
  call pack_scalar_masked(h, dry, .true., arrs(1)%dat)
  arrs(2)%name = "WSE"
  arrs(2)%ncomp = 1
  call pack_scalar_masked(wse, dry, .true., arrs(2)%dat)
  na = 2

  have_u = .false.
  have_v = .false.
  do iv = 1, size(catalog)
    if (catalog(iv)%prefix == "H") cycle          ! 上で処理済み
    if (.not. var_selected(catalog(iv)%prefix)) cycle
    call read_var(trim(catalog(iv)%prefix), k, wk, ios)
    if (ios /= 0) cycle
    if (.not. var_seen(iv)) then
      print '(a)', " var: "//trim(catalog(iv)%prefix)
      var_seen(iv) = .true.
    end if
    na = na + 1
    arrs(na)%name = trim(catalog(iv)%prefix)
    arrs(na)%ncomp = 1
    call pack_scalar_masked(wk, dry, catalog(iv)%masked, arrs(na)%dat)
    if (catalog(iv)%prefix == "u") then
      uu = wk
      have_u = .true.
    end if
    if (catalog(iv)%prefix == "v") then
      vv = wk
      have_v = .true.
    end if
  end do

  ! u, v が揃えば流速ベクトル(x 東向き正・y 北向き正・z 成分 0)
  if (have_u .and. have_v) then
    na = na + 1
    arrs(na)%name = "velocity"
    arrs(na)%ncomp = 3
    call pack_vector_masked(uu, vv, dry, arrs(na)%dat)
  end if

  call pack_points(wse, pts)
  call vtk_write_vts(fname, pts, arrs(1:na), scalars="H", vectors="velocity")
  ok = .true.
end subroutine


!-----------------------------------------------------------------------
! vars 指定(空なら全変数)に含まれるか
!-----------------------------------------------------------------------
logical function var_selected(prefix)
  character(len=*), intent(in) :: prefix
  integer :: i
  var_selected = .true.
  if (all(len_trim(vars) == 0)) return
  var_selected = .false.
  do i = 1, size(vars)
    if (trim(vars(i)) == trim(prefix)) then
      var_selected = .true.
      return
    end if
  end do
end function


!-----------------------------------------------------------------------
! 点座標を VTK 点順(x 早回り・y 昇順 = 南→北)に詰める
!   zsurf が面の高さ(地形 or 水面)
!-----------------------------------------------------------------------
subroutine pack_points(zsurf, pts)
  real, intent(in) :: zsurf(1:nx,1:ny)
  real(real64), allocatable, intent(out) :: pts(:)
  integer :: i, j, n

  allocate(pts(3*nx*ny))
  n = 0
  do j = ny, 1, -1              ! モデルの j=ny(南)から。y 昇順になる
    do i = 1, nx
      pts(n+1) = xc(i)
      pts(n+2) = yc(j)
      pts(n+3) = real(zsurf(i,j), real64)
      n = n + 3
    end do
  end do
end subroutine


!-----------------------------------------------------------------------
! スカラー場を VTK 点順の float32 に詰める(マスクなし)
!-----------------------------------------------------------------------
subroutine pack_scalar(a, dat)
  real, intent(in) :: a(1:nx,1:ny)
  real(real32), allocatable, intent(out) :: dat(:)
  integer :: i, j, n
  allocate(dat(nx*ny))
  n = 0
  do j = ny, 1, -1
    do i = 1, nx
      n = n + 1
      dat(n) = real(a(i,j), real32)
    end do
  end do
end subroutine


!-----------------------------------------------------------------------
! スカラー場を詰める(masked のとき乾燥点を NaN にする)
!-----------------------------------------------------------------------
subroutine pack_scalar_masked(a, dry, masked, dat)
  real, intent(in) :: a(1:nx,1:ny)
  logical, intent(in) :: dry(1:nx,1:ny)
  logical, intent(in) :: masked
  real(real32), allocatable, intent(out) :: dat(:)
  integer :: i, j, n
  allocate(dat(nx*ny))
  n = 0
  do j = ny, 1, -1
    do i = 1, nx
      n = n + 1
      if (masked .and. dry(i,j)) then
        dat(n) = vnan
      else
        dat(n) = real(a(i,j), real32)
      end if
    end do
  end do
end subroutine


!-----------------------------------------------------------------------
! ベクトル場 (u, v, 0) を詰める(乾燥点は NaN)
!-----------------------------------------------------------------------
subroutine pack_vector_masked(u, v, dry, dat)
  real, intent(in) :: u(1:nx,1:ny), v(1:nx,1:ny)
  logical, intent(in) :: dry(1:nx,1:ny)
  real(real32), allocatable, intent(out) :: dat(:)
  integer :: i, j, n
  allocate(dat(3*nx*ny))
  n = 0
  do j = ny, 1, -1
    do i = 1, nx
      if (dry(i,j)) then
        dat(n+1) = vnan; dat(n+2) = vnan; dat(n+3) = vnan
      else
        dat(n+1) = real(u(i,j), real32)
        dat(n+2) = real(v(i,j), real32)
        dat(n+3) = 0.0_real32
      end if
      n = n + 3
    end do
  end do
end subroutine


!-----------------------------------------------------------------------
! テクスチャ座標(格子外縁を 0..1 に正規化。t=1 が北端 = 画像上端)
!-----------------------------------------------------------------------
subroutine make_tcoords(arr)
  type(t_arr), intent(out) :: arr
  integer :: i, j, n
  arr%name = "TCoords"
  arr%ncomp = 2
  allocate(arr%dat(2*nx*ny))
  n = 0
  do j = ny, 1, -1
    do i = 1, nx
      arr%dat(n+1) = real((i - 0.5_real64) / nx, real32)
      arr%dat(n+2) = real((ny - j + 0.5_real64) / ny, real32)
      n = n + 2
    end do
  end do
end subroutine


!-----------------------------------------------------------------------
! VTK XML StructuredGrid(.vts)を書く
!   appended raw binary(リトルエンディアン前提。既存 bil 出力と同じ)。
!   ヘッダは UInt64 のバイト数プレフィクス。点座標 Float64・点データ Float32
!-----------------------------------------------------------------------
subroutine vtk_write_vts(fname, pts, arrs, scalars, vectors, tcoords)
  character(len=*), intent(in) :: fname
  real(real64), intent(in) :: pts(:)
  type(t_arr), intent(in) :: arrs(:)
  character(len=*), intent(in), optional :: scalars, vectors, tcoords

  integer :: un, ia
  integer(int64) :: offset, nbytes
  character(len=1024) :: buf
  character(:), allocatable :: attr

  open(newunit=un, file=fname, status='replace', access='stream', &
       form='unformatted')

  call puts(un, '<?xml version="1.0"?>' // new_line('a'))
  call puts(un, '<VTKFile type="StructuredGrid" version="1.0"' // &
                ' byte_order="LittleEndian" header_type="UInt64">' // new_line('a'))
  write(buf, '(a,i0,a,i0,a)') '  <StructuredGrid WholeExtent="0 ', nx-1, &
    ' 0 ', ny-1, ' 0 0">'
  call puts(un, trim(buf) // new_line('a'))
  write(buf, '(a,i0,a,i0,a)') '    <Piece Extent="0 ', nx-1, ' 0 ', ny-1, ' 0 0">'
  call puts(un, trim(buf) // new_line('a'))

  ! 点データ(既定の色付け対象などの属性指定)
  attr = ''
  if (present(scalars)) then
    if (any_arr(arrs, scalars)) attr = attr//' Scalars="'//scalars//'"'
  end if
  if (present(vectors)) then
    if (any_arr(arrs, vectors)) attr = attr//' Vectors="'//vectors//'"'
  end if
  if (present(tcoords)) then
    if (any_arr(arrs, tcoords)) attr = attr//' TCoords="'//tcoords//'"'
  end if
  call puts(un, '      <PointData'//attr//'>' // new_line('a'))

  offset = 0
  do ia = 1, size(arrs)
    write(buf, '(a,i0,a,i0,a)') '        <DataArray type="Float32" Name="' // &
      trim(arrs(ia)%name) // '" NumberOfComponents="', arrs(ia)%ncomp, &
      '" format="appended" offset="', offset, '"/>'
    call puts(un, trim(buf) // new_line('a'))
    offset = offset + 8 + 4_int64 * size(arrs(ia)%dat, kind=int64)
  end do
  call puts(un, '      </PointData>' // new_line('a'))

  call puts(un, '      <Points>' // new_line('a'))
  write(buf, '(a,i0,a)') '        <DataArray type="Float64" Name="Points"' // &
    ' NumberOfComponents="3" format="appended" offset="', offset, '"/>'
  call puts(un, trim(buf) // new_line('a'))
  call puts(un, '      </Points>' // new_line('a'))

  call puts(un, '    </Piece>' // new_line('a'))
  call puts(un, '  </StructuredGrid>' // new_line('a'))
  call puts(un, '  <AppendedData encoding="raw">' // new_line('a'))
  call puts(un, '   _')

  do ia = 1, size(arrs)
    nbytes = 4_int64 * size(arrs(ia)%dat, kind=int64)
    write(un) nbytes, arrs(ia)%dat
  end do
  nbytes = 8_int64 * size(pts, kind=int64)
  write(un) nbytes, pts

  call puts(un, new_line('a') // '  </AppendedData>' // new_line('a'))
  call puts(un, '</VTKFile>' // new_line('a'))
  close(un)
end subroutine


!-----------------------------------------------------------------------
! ストリーム装置に文字列を書く
!-----------------------------------------------------------------------
subroutine puts(un, s)
  integer, intent(in) :: un
  character(len=*), intent(in) :: s
  write(un) s
end subroutine


!-----------------------------------------------------------------------
! 名前の配列が束に含まれるか
!-----------------------------------------------------------------------
logical function any_arr(arrs, name)
  type(t_arr), intent(in) :: arrs(:)
  character(len=*), intent(in) :: name
  integer :: i
  any_arr = .false.
  do i = 1, size(arrs)
    if (trim(arrs(i)%name) == name) then
      any_arr = .true.
      return
    end if
  end do
end function

end module


!-----------------------------------------------------------------------
program out2vtk_prog
  use m_out2vtk, only : out2vtk_run
  implicit none
  character(len=256) :: fn_config
  integer :: na

  na = command_argument_count()
  fn_config = ""
  if (na >= 1) call get_command_argument(1, fn_config)

  print '(a)', "out2vtk: convert ENCflow outputs to VTK for ParaView"
  call out2vtk_run(trim(fn_config))
end program
