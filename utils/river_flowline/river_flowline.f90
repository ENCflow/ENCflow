!----------------------------------------------------------------------
! 河道マスクを標高の落水線に載せ直す
! "river_flowline"
!----------------------------------------------------------------------
!
! 河道マスク(list_geoinfo の fn_rw)を、標高データの落水線(標高が決める
! 流下の道筋)に載せ直す前処理ユーティリティ(developer.md §109)。
!
! 河川の中心線をラスタにした河道マスクは、標高の谷線から 1 セルずれる所が
! ある。ずれたセルは谷壁のセルで、河道の粗度(rn0_rw)や掘り込み(depth_rw)が
! 谷壁に付き、谷線の上のセルには付かない。このプログラムは、河道マスクの
! 各セルから標高の落水線をたどり、通ったセルを新しい河道マスクにする。
! 計算本体は河道マスクを読むだけで、載せ直しはしない(前処理は utils・GIS 側。
! 方針 12)。
!
! 使い方:
!   $ ./river_flowline parameterfile zfile maskfile riverfile outfile [accfile]
!
!   1. parameterfile: 計算に使うシステムパラメータファイル。
!      f_input_mode と、fn_geoinfo 経由の nx, ny を本体と同じ解釈で読む
!      (lu2mask と同じ。nx, ny の指定方法も本体と同じ)。
!   2. zfile: 標高(窪地処理済み。fn_z と同じ)のパス。
!   3. maskfile: 領域マスク(fn_mask と同じ。0 より大きい値が計算するセル)の
!      パス。全域を使うなら '-'。
!   4. riverfile: 元の河道マスク(fn_rw と同じ。0 より大きい値が河道セル)の
!      パス。
!   5. outfile: 載せ直した河道マスク(0 / 1)の出力先。
!   6. accfile: 落水線の集水面積(セル数。自セルを含む)の出力先(省略可。
!      確認と図化用)。
!   パスは書いたとおりの場所を読み書きする(dir_data は付けない)。
!
! 入出力の形式は f_input_mode に従う(1:text, 2:bil, 4:GeoTIFF)。
!   - text: namelist の nx, ny 指定が必須。出力は、1 行に 1 行分の値を空白
!     1 つで区切って書く(本体の読み込みは並び指定なので、そのまま読める)。
!   - bil: riverfile と同じ場所に hdr があれば nx, ny を補完・検査し、出力にも
!     hdr を併記する(4 バイト整数)。hdr が無ければ namelist の nx, ny が必須。
!   - GeoTIFF: 格子数は riverfile の自己記述から補完・検査する。位置情報
!     タグを出力に引き継ぐ(無ければ GeoTIFF では書けないので停止する)。
!
! 手順:
!   1. 落水線を決める。各セルの流下先は 8 近傍の最急勾配のセル(D8。
!      O'Callaghan & Mark 1984)。自分より低い隣がないセル(窪地処理で埋めた
!      平坦面、残った窪地)は、領域の縁のセルから標高の低い順にセルを取り出して
!      隣へ広げる Priority-Flood(Barnes ら 2014)で、先に取り出された隣を
!      流下先にする。領域の縁のセルで自分より低い隣がないものが、落水線の
!      終点(流出先)になる。
!   2. 元の河道マスクの各セルから落水線を終点までたどり、通ったセルを河道に
!      する。出発したセル自身は、ほかの河道セルからの落水線が通るときだけ
!      河道になる(谷線から外れたセルは河道から外れる。各河道の最上流の
!      1 セルも外れる)。
!
! できないこと: 落水線は標高だけで決まる(幅 1 セル。8 近傍でつながる)。
! 川幅が格子幅より広い河道や湖は、落水線が通るセルだけが河道になる(元の
! マスクが面で塗ってあるところは、各セルからの落水線が通る範囲が残る)。
! 平坦面の中の落水線は Priority-Flood の取り出し順で決まり、地形の情報を
! 持たない。載せ直したマスクは GIS 等で元のマスク・標高と重ねて確かめること。
! 落水線の手続きは examples/source_area/make_catchment.py と同じ(流出先を
! 領域の縁のセルにした点だけが違う)。
!
! 文献:
!   Barnes, R., Lehman, C. and Mulla, D. (2014): Priority-flood: An optimal
!     depression-filling and watershed-labeling algorithm for digital
!     elevation models. Computers & Geosciences, 62, 117-127.
!   O'Callaghan, J. F. and Mark, D. M. (1984): The extraction of drainage
!     networks from digital elevation data. Computer Vision, Graphics, and
!     Image Processing, 28(3), 323-344.
!----------------------------------------------------------------------
module m_river_flowline
  implicit none
  private
  public :: flow_tree, remap_river, accumulate_area, median_drop

  ! 8 近傍(北西から東へ、行ごと。j は北から南)。流下先が同じ勾配のときは
  ! この並びで先のものを採る
  integer, parameter :: dki(1:8) = [-1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: dkj(1:8) = [-1, -1, -1,  0,  0,  1,  1,  1]

  ! 最小ヒープ(キーは (値, 通し番号) の辞書式。同じ値は先に入れたものが先に出る)
  type t_heap
    integer :: n = 0
    real, allocatable :: key(:)
    integer, allocatable :: seq(:)
    integer, allocatable :: cell(:)
  end type

contains

!----------------------------------------------------------------------
! 落水線の木を作る
!   rcv   : 各セルの流下先の通し番号 (j-1)*nx + i(終点と領域外は 0)
!   order : Priority-Flood が取り出した順のセルの通し番号。溢れる高さ zfill の
!           低い順で、流下先は必ず自分より先に並ぶ(下流から上流への処理順)
!   nflat : 自分より低い隣がないセルの数(流下先を Priority-Flood が決めたセルと
!           終点)
!----------------------------------------------------------------------
subroutine flow_tree(nx, ny, z, valid, rcv, order, nflat)
  integer, intent(in) :: nx, ny
  real, intent(in) :: z(1:nx,1:ny)
  logical, intent(in) :: valid(1:nx,1:ny)
  integer, intent(out) :: rcv(1:nx,1:ny)
  integer, allocatable, intent(out) :: order(:)
  integer, intent(out) :: nflat
  real, allocatable :: zfill(:,:)       ! 取り出したときの水位(窪地は溢れる高さ)
  logical, allocatable :: seen(:,:)
  type(t_heap) :: hp
  real :: dist(1:8)
  real :: zc, zlast, s, best
  integer :: nvalid, cnt, npop
  integer :: i, j, k, in, jn, c

  nvalid = count(valid)
  allocate(order(1:nvalid))
  allocate(zfill(1:nx,1:ny), source = 0.0)
  allocate(seen(1:nx,1:ny), source = .false.)
  allocate(hp%key(1:nvalid), hp%seq(1:nvalid), hp%cell(1:nvalid))
  rcv(:,:) = 0

  ! --- Priority-Flood: 縁のセル(8 近傍に領域外か格子の外がある)から標高の低い順に広げる。
  !     平坦面と残った窪地の流下先(先に取り出された隣)が決まる ---
  cnt = 0
  do j = 1, ny
    do i = 1, nx
      if (.not. valid(i,j)) cycle
      if (.not. is_edge(i, j)) cycle
      seen(i,j) = .true.
      call heap_push(hp, z(i,j), cnt, (j - 1) * nx + i)
      cnt = cnt + 1
    end do
  end do
  npop = 0
  zlast = -huge(zlast)
  do while (hp%n > 0)
    call heap_pop(hp, zc, c)
    ! 取り出す水位は単調に上がる(下の処理順の前提)。崩れたら手続きの誤り
    if (zc < zlast) error stop "river_flowline: internal error (priority-flood order)"
    zlast = zc
    j = (c - 1) / nx + 1
    i = c - (j - 1) * nx
    zfill(i,j) = zc
    npop = npop + 1
    order(npop) = c
    do k = 1, 8
      in = i + dki(k)
      jn = j + dkj(k)
      if (in < 1 .or. in > nx .or. jn < 1 .or. jn > ny) cycle
      if (seen(in,jn) .or. .not. valid(in,jn)) cycle
      seen(in,jn) = .true.
      rcv(in,jn) = c
      call heap_push(hp, max(z(in,jn), zc), cnt, (jn - 1) * nx + in)
      cnt = cnt + 1
    end do
  end do
  if (npop /= nvalid) error stop "river_flowline: internal error (cells not reached)"

  ! --- D8: 自分より低い隣のうち勾配が最大のセルへ(あれば Priority-Flood の流下先を置き換える)。
  !     勾配は溢れる高さ zfill で測る ---
  do k = 1, 8
    dist(k) = sqrt(real(dki(k)**2 + dkj(k)**2))
  end do
  nflat = 0
  do j = 1, ny
    do i = 1, nx
      if (.not. valid(i,j)) cycle
      best = 0.0
      do k = 1, 8
        in = i + dki(k)
        jn = j + dkj(k)
        if (in < 1 .or. in > nx .or. jn < 1 .or. jn > ny) cycle
        if (.not. valid(in,jn)) cycle
        s = (zfill(i,j) - zfill(in,jn)) / dist(k)
        if (s > best) then
          best = s
          rcv(i,j) = (jn - 1) * nx + in
        end if
      end do
      if (best <= 0.0) nflat = nflat + 1
    end do
  end do

contains

  ! 領域の縁のセルか(8 近傍に領域外か格子の外がある)
  logical function is_edge(ci, cj)
    integer, intent(in) :: ci, cj
    integer :: kk, ei, ej
    is_edge = .true.
    do kk = 1, 8
      ei = ci + dki(kk)
      ej = cj + dkj(kk)
      if (ei < 1 .or. ei > nx .or. ej < 1 .or. ej > ny) return
      if (.not. valid(ei,ej)) return
    end do
    is_edge = .false.
  end function

end subroutine


!----------------------------------------------------------------------
! 元の河道マスクの各セルから落水線をたどり、通ったセル(出発セルは含めない)を
! 新しい河道マスクにする
!----------------------------------------------------------------------
subroutine remap_river(nx, ny, river, rcv, new)
  integer, intent(in) :: nx, ny
  logical, intent(in) :: river(1:nx,1:ny)
  integer, intent(in) :: rcv(1:nx,1:ny)
  logical, intent(out) :: new(1:nx,1:ny)
  integer :: i, j, ic, jc, c

  new(:,:) = .false.
  do j = 1, ny
    do i = 1, nx
      if (.not. river(i,j)) cycle
      c = rcv(i,j)
      do while (c > 0)
        jc = (c - 1) / nx + 1
        ic = c - (jc - 1) * nx
        if (new(ic,jc)) exit          ! ここから下流は、先にたどった落水線で済んでいる
        new(ic,jc) = .true.
        c = rcv(ic,jc)
      end do
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 落水線の集水面積(セル数。自セルを含む)。上流から下流へ(order の逆順に)足し込む
!----------------------------------------------------------------------
subroutine accumulate_area(nx, ny, valid, rcv, order, acc)
  integer, intent(in) :: nx, ny
  logical, intent(in) :: valid(1:nx,1:ny)
  integer, intent(in) :: rcv(1:nx,1:ny)
  integer, intent(in) :: order(:)
  integer, intent(out) :: acc(1:nx,1:ny)
  integer :: n, c, r, i, j, ir, jr

  acc(:,:) = merge(1, 0, valid)
  do n = size(order), 1, -1
    c = order(n)
    j = (c - 1) / nx + 1
    i = c - (j - 1) * nx
    r = rcv(i,j)
    if (r <= 0) cycle
    jr = (r - 1) / nx + 1
    ir = r - (jr - 1) * nx
    acc(ir,jr) = acc(ir,jr) + acc(i,j)
  end do
end subroutine


!----------------------------------------------------------------------
! 河道から外したセル(元の河道マスクにあって、載せ直したマスクにない)が、
! 流下先のセルより高い分の中央値 (m)。流下先のないセル(終点)は数えない。
! 該当するセルがなければ 0
!----------------------------------------------------------------------
function median_drop(nx, ny, z, river, new, rcv) result(med)
  integer, intent(in) :: nx, ny
  real, intent(in) :: z(1:nx,1:ny)
  logical, intent(in) :: river(1:nx,1:ny), new(1:nx,1:ny)
  integer, intent(in) :: rcv(1:nx,1:ny)
  real :: med
  type(t_heap) :: hp
  real :: v, vprev
  integer :: n, i, j, r, ir, jr, m, c

  med = 0.0
  n = count(river .and. .not. new .and. rcv > 0)
  if (n == 0) return
  allocate(hp%key(1:n), hp%seq(1:n), hp%cell(1:n))
  m = 0
  do j = 1, ny
    do i = 1, nx
      if (.not. river(i,j) .or. new(i,j)) cycle
      r = rcv(i,j)
      if (r <= 0) cycle
      jr = (r - 1) / nx + 1
      ir = r - (jr - 1) * nx
      call heap_push(hp, z(i,j) - z(ir,jr), m, 0)
      m = m + 1
    end do
  end do
  ! 小さい順に半分まで取り出す(偶数個なら中央の 2 つの平均)
  v = 0.0
  vprev = 0.0
  do m = 1, n / 2 + 1
    vprev = v
    call heap_pop(hp, v, c)
  end do
  if (mod(n, 2) == 1) then
    med = v
  else
    med = 0.5 * (vprev + v)
  end if
end function


!----------------------------------------------------------------------
! 最小ヒープ(2 分木を配列に持つ)。(値, 通し番号) の小さい順に取り出す
!----------------------------------------------------------------------
subroutine heap_push(hp, key, seq, cell)
  type(t_heap), intent(inout) :: hp
  real, intent(in) :: key
  integer, intent(in) :: seq, cell
  integer :: k, kp

  hp%n = hp%n + 1
  k = hp%n
  do while (k > 1)
    kp = k / 2
    if (.not. before(key, seq, hp%key(kp), hp%seq(kp))) exit
    hp%key(k) = hp%key(kp)
    hp%seq(k) = hp%seq(kp)
    hp%cell(k) = hp%cell(kp)
    k = kp
  end do
  hp%key(k) = key
  hp%seq(k) = seq
  hp%cell(k) = cell
end subroutine

subroutine heap_pop(hp, key, cell)
  type(t_heap), intent(inout) :: hp
  real, intent(out) :: key
  integer, intent(out) :: cell
  real :: lkey
  integer :: lseq, lcell, k, kc

  key = hp%key(1)
  cell = hp%cell(1)
  ! 末尾の要素を根から沈める
  lkey = hp%key(hp%n)
  lseq = hp%seq(hp%n)
  lcell = hp%cell(hp%n)
  hp%n = hp%n - 1
  k = 1
  do
    kc = 2 * k
    if (kc > hp%n) exit
    if (kc < hp%n) then
      if (before(hp%key(kc+1), hp%seq(kc+1), hp%key(kc), hp%seq(kc))) kc = kc + 1
    end if
    if (.not. before(hp%key(kc), hp%seq(kc), lkey, lseq)) exit
    hp%key(k) = hp%key(kc)
    hp%seq(k) = hp%seq(kc)
    hp%cell(k) = hp%cell(kc)
    k = kc
  end do
  if (hp%n > 0) then
    hp%key(k) = lkey
    hp%seq(k) = lseq
    hp%cell(k) = lcell
  end if
end subroutine

! (a, sa) が (b, sb) より先か
pure logical function before(a, sa, b, sb)
  real, intent(in) :: a, b
  integer, intent(in) :: sa, sb
  if (a < b) then
    before = .true.
  else if (a > b) then
    before = .false.
  else
    before = sa < sb
  end if
end function

end module m_river_flowline


!======================================================================
!======================================================================
program river_flowline
  use m_river_flowline, only : flow_tree, remap_river, accumulate_area, median_drop
  use m_sysparam, only : t_sysparam, m_sysparam_init
  use list_geoinfo, only : t_list_geoinfo, list_geoinfo_read
  use m_fileio, only : fileio_read_matrix, fileio_write_matrix, e_fmt_bil, e_fmt_gtif
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
  real, allocatable :: z(:,:)                      ! 標高
  integer, allocatable :: iw(:,:)                  ! 整数ラスタの読み書き用
  logical, allocatable :: valid(:,:)               ! 領域(計算するセル)
  logical, allocatable :: river(:,:)               ! 元の河道マスク(領域の中)
  logical, allocatable :: new(:,:)                 ! 載せ直した河道マスク
  integer, allocatable :: rcv(:,:)                 ! 流下先の通し番号(終点・領域外は 0)
  integer, allocatable :: order(:)                 ! 下流から上流への処理順
  character(:), allocatable :: fn_sysparam, fn_z, fn_mask, fn_river, fn_out, fn_acc
  integer :: nvalid, nflat, nend, nriver, nnew, nkeep, noff, nadd, nout
  real :: med

  call get_args(fn_sysparam, fn_z, fn_mask, fn_river, fn_out, fn_acc)

  call par_init()
  call m_sysparam_init(p, fn_sysparam)
  call list_geoinfo_read(p, list)

  ! nx, ny の確定と地理座標参照の取得(元の河道マスクのファイル自身から補完する)
  call probe_grid(p, list, fn_river, nx, ny, gr)
  print '(a,i0,a,i0)', "grid: ", nx, " x ", ny

  ! 標高・領域マスク・元の河道マスクの読み込み(本体と同じ読み方)
  allocate(z(1:nx,1:ny), source = 0.0)
  print '(a)', "reading " // fn_z
  call fileio_read_matrix(fn_z, nx, ny, z, p%f_input_mode)
  allocate(iw(1:nx,1:ny), source = 0)
  allocate(valid(1:nx,1:ny), source = .true.)
  if (fn_mask /= "-") then
    print '(a)', "reading " // fn_mask
    call fileio_read_matrix(fn_mask, nx, ny, iw, p%f_input_mode)
    valid(:,:) = iw(:,:) > 0
  end if
  print '(a)', "reading " // fn_river
  call fileio_read_matrix(fn_river, nx, ny, iw, p%f_input_mode)
  nout = count(iw > 0 .and. .not. valid)
  allocate(river(1:nx,1:ny))
  river(:,:) = iw(:,:) > 0 .and. valid(:,:)

  nvalid = count(valid)
  if (nvalid == 0) call par_stop("river_flowline: the domain mask has no cell to compute")

  ! 落水線の木と、載せ直した河道マスク
  allocate(rcv(1:nx,1:ny))
  call flow_tree(nx, ny, z, valid, rcv, order, nflat)
  allocate(new(1:nx,1:ny))
  call remap_river(nx, ny, river, rcv, new)

  ! 載せ直した河道マスクの書き出し(入力と同じ形式)
  iw(:,:) = merge(1, 0, new)
  call write_raster(fn_out, iw)

  ! 落水線の集水面積(セル数)
  if (len(fn_acc) > 0) then
    call accumulate_area(nx, ny, valid, rcv, order, iw)
    call write_raster(fn_acc, iw)
  end if

  ! 載せ直しの内訳
  nend = count(valid .and. rcv <= 0)
  nriver = count(river)
  nnew = count(new)
  nkeep = count(river .and. new)
  noff = count(river .and. .not. new)
  nadd = count(new .and. .not. river)
  med = median_drop(nx, ny, z, river, new, rcv)
  print '(a,i0,a,i0,a,f0.2,a,i0)', "domain ", nvalid, " cells, cells without a lower neighbour ", nflat, &
        " (", 100.0 * real(nflat) / real(nvalid), " %), flowline end points ", nend
  print '(a,i0,a,i0,a)', "original channel mask ", nriver, " cells -> re-mapped channel mask ", nnew, " cells"
  print '(a,i0,a,i0,a,i0,a,f0.1,a,i0)', "  on the flowlines ", nkeep, " (", &
        nint(100.0 * real(nkeep) / real(max(nriver, 1))), " % of the original), removed ", noff, &
        " (median ", med, " m above the receiving cell), added ", nadd
  if (nout > 0) then
    print '(a,i0,a)', "  ", nout, " channel cells outside the domain mask were not used"
  end if

  call par_finalize()

contains

!----------------------------------------------------------------------
! コマンドライン引数の取得
!----------------------------------------------------------------------
subroutine get_args(fn_sysparam, fn_z, fn_mask, fn_river, fn_out, fn_acc)
  character(:), allocatable, intent(out) :: fn_sysparam, fn_z, fn_mask, fn_river, fn_out, fn_acc
  character(:), allocatable :: s
  integer :: argc

  argc = command_argument_count()
  if (argc < 5 .or. argc > 6) then
    call get_arg(0, s)
    print '(a)', "usage: " // s // " parameterfile zfile maskfile riverfile outfile [accfile]"
    print '(a)', "  maskfile: '-' to use the whole grid"
    stop 1
  end if

  call get_arg(1, fn_sysparam)
  call get_arg(2, fn_z)
  call get_arg(3, fn_mask)
  call get_arg(4, fn_river)
  call get_arg(5, fn_out)
  if (argc >= 6) then
    call get_arg(6, fn_acc)
  else
    fn_acc = ""
  end if
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
! 整数ラスタの書き出し(入力と同じ形式)
!   text は、1 行に 1 行分の値を空白 1 つで区切って書く(桁をそろえる
!   fileio の text 形式より小さい。本体の読み込みは並び指定なので読める)。
!   bil で座標が分かっていれば hdr を併記する(lu2mask・m_output と同じ流儀)
!----------------------------------------------------------------------
subroutine write_raster(fname, a)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: a(1:nx,1:ny)
  integer :: un, j, ios
  character(len=512) :: iom

  print '(a)', "writing " // fname
  select case (p%f_input_mode)
    case (e_fmt_gtif)
      if (.not. gr%active) then
        call par_stop("river_flowline: GeoTIFF output requires georeference tags in "//fn_river)
      end if
      call fileio_write_matrix(fname, nx, ny, a, e_fmt_gtif, gr)
    case (e_fmt_bil)
      call fileio_write_matrix(fname, nx, ny, a, e_fmt_bil)
      if (gr%active) then
        print '(a)', "writing " // georef_hdr_name(fname)
        call georef_write_hdr(georef_hdr_name(fname), gr, nx, ny, e_pix_int)
      end if
    case default
      open(newunit=un, file=fname, status='replace', iostat=ios, iomsg=iom)
      if (ios /= 0) call par_stop("river_flowline: cannot create text file "//fname//": "//trim(iom))
      do j = 1, ny
        write(un, '(*(i0,:,1x))') a(1:nx,j)
      end do
      close(un)
  end select
end subroutine

!----------------------------------------------------------------------
! nx, ny の確定と地理座標参照の取得
!   lu2mask の probe_grid と同じ流儀を、元の河道マスクのファイルに適用する:
!   ファイル(bil の hdr / GeoTIFF のタグ)から得た格子数で namelist の
!   未指定分を補完し、両方あれば無言でどちらかを優先せず整合を検査する。
!   座標参照が取れた場合は出力(hdr 併記・GeoTIFF タグ)に引き継ぐ
!----------------------------------------------------------------------
subroutine probe_grid(p, list, fn_ref, nx, ny, gr)
  type(t_sysparam), intent(in) :: p
  type(t_list_geoinfo), intent(in) :: list
  character(len=*), intent(in) :: fn_ref
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
    fn_hdr = georef_hdr_name(fn_ref)
    inquire(file=fn_hdr, exist=ex)
    if (ex) then
      print '(a)', "reading " // fn_hdr
      call georef_read_hdr(fn_hdr, gr, ncols, nrows)
    end if

  else if (p%f_input_mode == e_fmt_gtif) then
    call gtif_inquire(fn_ref, tinfo, stat, msg)
    if (stat /= 0) call par_stop("river_flowline: cannot read GeoTIFF: "//trim(msg))
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
          call par_stop("river_flowline: epsg("//itoa(list%epsg)//") does not match the GeoTIFF CRS(" &
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
      call par_stop("river_flowline: nx("//itoa(nx)//") does not match the channel mask file (" &
                    //itoa(ncols)//")")
    end if
  end if
  if (nrows > 0) then
    if (ny <= 0) then
      ny = nrows
    else if (ny /= nrows) then
      call par_stop("river_flowline: ny("//itoa(ny)//") does not match the channel mask file (" &
                    //itoa(nrows)//")")
    end if
  end if
  if (nx <= 0 .or. ny <= 0) then
    call par_stop("river_flowline: cannot determine nx, ny " &
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

end program river_flowline
