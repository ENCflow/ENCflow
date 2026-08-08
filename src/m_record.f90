!======================================================================
module m_record
  ! ================= MPI 化の方針(改良時に読むこと) =================
  ! 計測ロジック(整形・総和・最大値更新・出力)はすべて rank0 上の
  ! 逐次コードのまま維持している。MPI 対応は「セル値の取得」だけを
  ! 点集約バッファ経由に差し替える方式:
  !   (1) 全ランクが所有セル(dcp%js <= iy <= dcp%je)の値をバッファに
  !       格納する(他ランクの要素は 0 のまま)
  !   (2) par_reduce_points で rank0 に総和集約する。各要素の所有者は
  !       ちょうど1ランクなので「総和=所有値」でビット厳密
  !   (3) rank0 が従来ロジックでバッファから読んで整形・出力する
  ! 計測に新しい量を足す手順: 格納ループに1行(wk(k,i) = s%新量(ix,iy))、
  ! バッファの第1次元を +1、読み出し側で wk(k,i) を参照する。この3点だけ。
  ! 注意: (1)(2) は collective なので is_root ガードより前に置くこと。
  !       所有判定に halo 行(jsh..js-1 等)を含めると二重計上になる。
  ! ==================================================================
  ! フラックス測線は DDA 階段面方式(§24。2026-08-08 変更): セル番号で
  !   指定した両端セルの中心を結ぶ DDA セル列の「踏面+蹴上げ」に沿って
  !   セル中心の m, n を符号付きで積算する(一様流で任意の傾きに厳密)。
  !   実座標指定(flxytype=1)は廃止(検出して停止)。
  ! サブグリッド河道(fn_width。§18)との契約:
  !   フラックス測線の実流量は、m, n が「流量をセル幅に
  !   塗り広げたセル平均」であることに依存する(河道セルを完全横断する
  !   測線で Q = 河道実流量が厳密に復元される)。m, n を河道内流速側に
  !   正規化してはならない(正規化されるのは u, v のみ。m_swflow_enc の
  !   cwx/cwy 参照)。また測線は河道セル群を完全に横断させること。
  ! 構造物転送(ポンプ・カルバート・分水。§22)は m, n に乗らないため
  !   測線では計測されない(貯水池の流入計測等では収支方式と併用する)。
  ! ====================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_parallel, only : is_root
  use m_util, only : itoa
  use m_sysdep_util, only : sysdep_mkdir
  use list_record, only : t_list_record, list_record_read
  use m_parallel, only : is_root, par_info, par_abort, dcp, par_reduce_points
  implicit none
  private

  public :: t_record
  public :: m_record_init
  public :: m_record_dispose
  public :: m_record_probe
  public :: m_record_flux
  public :: m_record_summary

  integer, parameter :: ncellmax = 1000
  integer, parameter :: nflmax = 1000


  type t_probe
    real :: xy(1:2)                        ! 測点の実座標(m)
    integer :: ixy(1:2)                    ! 測点のセルの座標
    real :: z                              ! 測点の標高
    real :: tp                             ! 最大流量の発生時刻(s)
    real :: qmax                           ! 最大流量
    real :: hmax                           ! 最大流量のときの水深
    integer :: un                          ! 出力ファイルの装置番号
  end type

  type t_flux
    ! DDA 階段面方式(§24。2026-08-08 変更): 両端セルの中心を結ぶ直線を
    ! 長手軸方向に1セルずつ走査し(短手セル番号は中心線の最近傍)、
    ! 短手方向に重複のないセル列(踏面)を作る。計測面は
    !   踏面: 各セル内の長手軸に平行な線分(幅=長手セル幅)
    !   蹴上げ: 隣接踏面セルの短手段差を繋ぐ線分(幅=短手セル幅)
    ! の階段で、踏面は短手方向フラックス、蹴上げは長手方向フラックス
    ! (段差を挟む踏面2セルの平均)を符号付きで積算する。一様流では
    ! 任意の傾きで厳密(踏面のみの方式は cos^2θ に過小評価する)。
    ! 縦横の直線測線では旧方式(重み付き平均×測線長)と解析的に同値。
    ! 符号は旧方式と同じ「始点から終点に向かって右側が正」
    ! (連続系の法線 (−Δy, Δx)/L との内積に一致)
    real :: trlen                          ! 測線の長さ(m。両端セルの外縁まで延長した
                                           !   直線長。報告用=計測には使わない)
    real :: xy0(1:4)                       ! 測線の両端セル中心の実座標(m)
    integer :: ixy0(1:4)                   ! 測線の両端点のセルの座標
    integer :: major = 1                   ! 長手軸 (1:x, 2:y)
    real :: ct = 0.0                       ! 踏面の係数(法線符号×長手セル幅 m)
    real :: cr = 0.0                       ! 蹴上げの係数(法線符号×短手セル幅 m)
    integer :: ncell                       ! 踏面セルの数
    integer :: ixy(1:2,1:ncellmax)         ! 踏面セルの座標(走査順)
    integer :: nris = 0                    ! 蹴上げの数
    integer :: irs(1:ncellmax)             ! 蹴上げ k は踏面セル irs(k) と irs(k)+1 の間
    real :: tp                             ! 最大流量の発生時刻(s)
    real :: qmax                           ! 最大流量
    real :: hmax                           ! 最大流量のときの水深
    integer :: un                          ! 出力ファイルの装置番号
  end type

  type t_record
    logical :: initialized = .false.
    real :: ss0                            ! 領域内の水の総量の初期値
    real :: ss                             ! 領域内の水の総量
    integer :: npb                         ! プローブ計測の測点の数
    type(t_probe), allocatable :: probe(:) ! プローブ計測の測点の情報
    integer :: nfl                         ! フラックス計測の測線の数
    type(t_flux), allocatable :: flux(:)   ! フラックス計測の測線の情報
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! レコード構造体を初期化
!----------------------------------------------------------------------
subroutine m_record_init(r, p, g)
  type(t_record), intent(out) :: r
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_record) :: list
  integer :: pbxytype
  real, allocatable :: pbxy(:,:)
  integer :: flxyfile
  integer :: flxytype
  real :: flxy(1:4,1:nflmax) = -9999

  ! リスト構築・検証は全ランクが冗長に実行する(全ランクが所有セルを
  ! 判定できるようにするため。§11 の「静的データは全ランク保持」)。
  ! ファイルの open とヘッダ出力だけ rank0 に限定する(set_probe/set_flux 内)

  if (len_trim(p%fn_record) > 0) then
    !---- 設定ファイルを読み込む ----
    call list_record_read(p, list)
    pbxytype = list%pbxytype
    pbxy = list%pbxy
    flxyfile = list%flxyfile
    flxytype = list%flxytype

    !---- フラックスの測線データをセット ----
    if (flxyfile > 0) then
      call read_flxy(p, list%fn_flxy, flxy)
    else
      flxy = list%flxy
    end if

    !---- 設定ファイルの情報を構造体に保存 ----
    call set_probe
    call set_flux
    !call set_probe(p)
    !call set_flux(p)
  else
    r%npb = 0
    r%nfl = 0
  end if

  !---- 初期値をセット ---
  r%ss0 = 0.0
  r%ss = 0.0

  r%initialized = .true.

contains
!---------------------------------------------------------------------
subroutine set_probe
!subroutine set_probe(p)
!  type(t_sysparam), intent(in) :: p
  integer :: npb, un
  integer :: i, ix, iy
  real :: x, y
  character(len=80) :: fn_pb
  character(len=4) :: cun
  character(len=1024) :: msg

  !---- プローブ数をカウント ----
  npb = 0
  !do i = 1, size(pbxy, 2)
  do i = 1, ubound(pbxy, 2)
    if (pbxy(1,i) < -999) exit   ! 有効なデータが無い場合は終了
    npb = npb + 1
  end do
  r%npb = npb
  if (npb < 1) return

  !---- プローブ情報を保存 ----
  allocate(r%probe(1:npb))
  do i = 1, npb
    if (pbxytype == 0) then
      ! 設定ファイルでセルの座標を指定
      ix = nint(pbxy(1,i))
      iy = nint(pbxy(2,i))
      x = (ix - 0.5) * g%dx 
      y = (iy - 0.5) * g%dy
    else
      ! 設定ファイルで実座標を指定
      x = pbxy(1,i)
      y = pbxy(2,i)
      ix = int(x / g%dx) + 1
      iy = int(y / g%dy) + 1
    end if
    if (ix < 1 .or. ix > g%nx .or. iy < 1 .or. iy > g%ny) then
      write(msg, '("error: probe ",i0," is out of area.",2f15.2,2i7)') i, x, y, ix, iy
      call par_abort(trim(msg))
    end if
    if (g%x(ix,iy) < 1) then
      write(msg, '("error: probe ",i0," is not in valid area.",2f15.2,2i7)') i, x, y, ix, iy
      call par_abort(trim(msg))
    end if
    r%probe(i)%xy(1) = x
    r%probe(i)%xy(2) = y
    r%probe(i)%ixy(1) = ix
    r%probe(i)%ixy(2) = iy
    r%probe(i)%z = g%z(ix,iy)
    r%probe(i)%tp = 0
    r%probe(i)%qmax = -1.
  end do

  !---- プローブ出力ファイルを初期化(rank0 のみ)----
  if (.not. is_root) return
  call sysdep_mkdir(trim(p%dir_result)//"/probes")
  do i = 1, r%npb
    ix = r%probe(i)%ixy(1)
    iy = r%probe(i)%ixy(2)
    write(cun, '(i4.4)') i
    fn_pb = trim(p%dir_result)//"/probes/"//"probe"//cun//trim(p%outfn_suffix)//".csv"
    open(newunit=un, file=trim(fn_pb), status='replace')
    write(un, '("# probe number =,",i3)') i
    write(un, '("# x(m) =,",f14.3)') r%probe(i)%xy(1)
    write(un, '("# y(m) =,",f14.3)') r%probe(i)%xy(2)
    write(un, '("# z(m) =,",f14.3)') r%probe(i)%z
    write(un, '("# ix =,",i7)') r%probe(i)%ixy(1)
    write(un, '("# iy =,",i7)') r%probe(i)%ixy(2)
    write(un, '("# t(hour), t(min), z(m), h(m), u(m/s), v(m/s), |V|(m/s), q(m2/s), hg(m), hs(m), sd(m)")')
    r%probe(i)%un = un
  end do
end subroutine

!---------------------------------------------------------------------
!
!---------------------------------------------------------------------
subroutine set_flux
  ! DDA 階段面方式(t_flux のコメントと §24 参照)。
  ! 測線はセル番号指定(flxytype=0)のみ。実座標指定(flxytype=1)は
  ! 廃止(斜め測線で重み求積が不安定だった旧方式の仕様。検出して停止)
  integer :: nfl, un
  integer :: i, ix0, iy0, ix1, iy1
  real :: x0, y0, x1, y1
  integer :: adx, ady, sd, ncell, nris, k, ix, iy, ish
  real :: t, ext
  character(len=80) :: fn_fl
  character(len=4) :: cun
  character(len=1024) :: msg

  !---- フラックス計測の測線数をカウント ----
  nfl = 0
  do i = 1, ubound(flxy, 2)
    if (flxy(1,i) < -999) exit   ! 有効なデータが無い場合は終了
    nfl = nfl + 1
  end do
  r%nfl = nfl
  if (nfl < 1) return

  if (flxytype /= 0) then
    call par_abort("m_record: 測線の実座標指定(flxytype=1)は廃止されました。" &
                   //"セル番号指定(flxytype=0)へ移行してください" &
                   //"(測線は両端セル中心を結ぶ DDA セル列=階段面で定義されます。§24)")
  end if

  !---- 測線情報を保存 ----
  allocate(r%flux(1:nfl))
  do i = 1, nfl
    ! セルの座標指定のみ(両端セルの中心を結ぶ)
    ix0 = nint(flxy(1,i))
    iy0 = nint(flxy(2,i))
    ix1 = nint(flxy(3,i))
    iy1 = nint(flxy(4,i))
    x0 = (ix0 - 0.5) * g%dx
    y0 = (iy0 - 0.5) * g%dy
    x1 = (ix1 - 0.5) * g%dx
    y1 = (iy1 - 0.5) * g%dy
    if (ix0 < 1 .or. ix0 > g%nx .or. iy0 < 1 .or. iy0 > g%ny) then
      write(msg, '("error: point R of flux ",i0," is out of area.",2f15.2,2i7)') i, x0, y0, ix0, iy0
      call par_abort(trim(msg))
    end if
    if (ix1 < 1 .or. ix1 > g%nx .or. iy1 < 1 .or. iy1 > g%ny) then
      write(msg, '("error: point L flux ",i0," is out of area.",2f15.2,2i7)') i, x1, y1, ix1, iy1
      call par_abort(trim(msg))
    end if
    if (g%x(ix0,iy0) < 1) then
      write(msg, '("warning: point R of flux ",i0," is not in valid area.",2f15.2,2i7)') i, x0, y0, ix0, iy0
      call par_info(trim(msg))
    end if
    if (g%x(ix1,iy1) < 1) then
      write(msg, '("warning: point L flux ",i0," is not in valid area.",2f15.2,2i7)') i, x1, y1, ix1, iy1
      call par_info(trim(msg))
    end if

    r%flux(i)%xy0(1) = x0
    r%flux(i)%xy0(2) = y0
    r%flux(i)%xy0(3) = x1
    r%flux(i)%xy0(4) = y1
    r%flux(i)%ixy0(1) = ix0
    r%flux(i)%ixy0(2) = iy0
    r%flux(i)%ixy0(3) = ix1
    r%flux(i)%ixy0(4) = iy1
    r%flux(i)%tp = 0

    if (ix0 == ix1 .and. iy0 == iy1) then
      call par_info("warning: point A == point B then IGNORE, flux No."//itoa(i))
      r%flux(i)%ncell = 0       ! これを1でなく0にしておく
      r%flux(i)%nris = 0
      r%flux(i)%trlen = 0.0
      r%flux(i)%qmax = 0.
      cycle
    end if

    adx = abs(ix1 - ix0)
    ady = abs(iy1 - iy0)
    ncell = 0
    if (adx >= ady) then
      ! x が長手(ちょうど 45 度も x 長手とする: DDA セル列は y 長手と
      ! 同一の対角列になり、踏面+蹴上げの合計も一致するため選択は不問)
      r%flux(i)%major = 1
      sd = sign(1, ix1 - ix0)
      do k = 0, adx
        ix = ix0 + sd * k
        t = real(k) / real(adx)
        iy = iy0 + nint(t * (iy1 - iy0))   ! 中心線の最近傍の短手セル番号
        ncell = ncell + 1
        if (ncell > ncellmax) call par_abort("m_record: flux "//itoa(i)//" が長すぎます")
        r%flux(i)%ixy(1,ncell) = ix
        r%flux(i)%ixy(2,ncell) = iy
      end do
      ! 法線は旧方式と同じ (−Δy, Δx)/L との内積に一致させる:
      !   踏面(x 平行)の法線 y 成分 = sign(Δx)、蹴上げ(y 平行)の
      !   法線 x 成分 = −sign(Δy)
      r%flux(i)%ct = real(sign(1, ix1 - ix0)) * g%dx
      r%flux(i)%cr = -real(sign(1, iy1 - iy0)) * g%dy
      ext = real(adx + 1) * g%dx   ! 長手方向の全幅(両端セルの外縁まで)
      r%flux(i)%trlen = ext * sqrt(1.0 + (real(ady) / real(adx))**2)
    else
      ! y が長手
      r%flux(i)%major = 2
      sd = sign(1, iy1 - iy0)
      do k = 0, ady
        iy = iy0 + sd * k
        t = real(k) / real(ady)
        ix = ix0 + nint(t * (ix1 - ix0))
        ncell = ncell + 1
        if (ncell > ncellmax) call par_abort("m_record: flux "//itoa(i)//" が長すぎます")
        r%flux(i)%ixy(1,ncell) = ix
        r%flux(i)%ixy(2,ncell) = iy
      end do
      ! 踏面(y 平行)の法線 x 成分 = −sign(Δy)、蹴上げ(x 平行)の
      ! 法線 y 成分 = sign(Δx)
      r%flux(i)%ct = -real(sign(1, iy1 - iy0)) * g%dy
      r%flux(i)%cr = real(sign(1, ix1 - ix0)) * g%dx
      ext = real(ady + 1) * g%dy
      r%flux(i)%trlen = ext * sqrt(1.0 + (real(adx) / real(ady))**2)
    end if
    r%flux(i)%ncell = ncell

    ! 蹴上げ: 連続する踏面セルの短手番号の段差(DDA では 0 か ±1)
    nris = 0
    ish = 3 - r%flux(i)%major    ! 短手成分の添字 (major=1 → 2, major=2 → 1)
    do k = 1, ncell - 1
      if (r%flux(i)%ixy(ish,k+1) /= r%flux(i)%ixy(ish,k)) then
        nris = nris + 1
        r%flux(i)%irs(nris) = k
      end if
    end do
    r%flux(i)%nris = nris
    r%flux(i)%qmax = -1.
  end do

  !---- フラックス計測出力ファイルを初期化(rank0 のみ)----
  if (.not. is_root) return
  call sysdep_mkdir(trim(p%dir_result)//"/fluxes")
  do i = 1, r%nfl
    write(cun, '(i4.4)') i
    fn_fl = trim(p%dir_result)//"/fluxes/"//"flux"//cun//trim(p%outfn_suffix)//".csv"
    open(newunit=un, file=trim(fn_fl), status='replace')
    write(un, '("# flux transect number =,",i3)') i
    write(un, '("# xR, yR, xL, yL(m) =,",f14.3,",",f14.3,",",f14.3,",",f14.3)') r%flux(i)%xy0(1:4)
    write(un, '("# ixR, iyR, ixL, iyL =,",i7,",",i7,",",i7,",",i7)') r%flux(i)%ixy0(1:4)
    write(un, '("# length of transect(m) =,",f14.3)') r%flux(i)%trlen
    write(un, '("# t(hour), t(min), Q(m3/s), Hmax(m), Vmax(m/s), B(m)(=Q/Hmax/Vmax)")')
    r%flux(i)%un = un
  end do
end subroutine

end subroutine m_record_init

!----------------------------------------------------------------------
! フラックスの測線ファイルを読み込む
!----------------------------------------------------------------------
subroutine read_flxy(p, fn_flxy, flxy)
  type(t_sysparam), intent(in) :: p
  character(len=*), intent(in) :: fn_flxy
  real, intent(inout) :: flxy(1:4,1:nflmax)
  character(:), allocatable :: fname
  integer :: un
  integer :: i, n
  integer :: ios

  fname = trim(p%dir_data)//"/"//trim(fn_flxy)
  open(newunit=un, file=fname, status='old')

  n = 0
  do
    read(un, * , iostat=ios)
    if (ios < 0) exit
    n = n + 1
  end do
  rewind(un)

  if (n > nflmax) then
    call par_abort("Error: too many flux transect"//itoa(n))
  end if

  flxy(:,:) = -9999           ! パラメータファイルの情報を上書きして初期化する
  call par_info(" reading "//fname)
  do i = 1, n
    read(un, *) flxy(1,i), flxy(2,i), flxy(3,i), flxy(4,i)
  end do
  close(un)

end subroutine


!----------------------------------------------------------------------
! レコード構造体を破棄
!----------------------------------------------------------------------
subroutine m_record_dispose(r)
  type(t_record), intent(inout) :: r
  integer :: i

  ! ファイルを開いているのは rank0 のみ。リストは全ランクが保持している
  if (is_root) then
    do i = 1, r%npb
      close(r%probe(i)%un)
    end do
    do i = 1, r%nfl
      close(r%flux(i)%un)
    end do
  end if
  if (allocated(r%probe)) deallocate(r%probe)
  if (allocated(r%flux)) deallocate(r%flux)
end subroutine

!----------------------------------------------------------------------
! プローブ計測の情報を記録
!----------------------------------------------------------------------
subroutine m_record_probe(r, p, s)
  type(t_record), intent(inout) :: r
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  integer :: ipb, un
  integer :: ix, iy
  real :: wk(9, r%npb)     ! 点集約バッファ: z, h, u, v, |V|, q, hg, hs, sd
  character(len=10) :: ffmt
  character(len=80) :: afmt
  integer, parameter :: iw_z = 1, iw_h = 2, iw_u = 3, iw_v = 4, iw_vv = 5, iw_qq = 6, &
                        iw_hg = 7, iw_hs = 8, iw_sd = 9
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  if (r%npb <= 0) return

  ! --- 全ランク: 所有セルの値を詰めて rank0 に点集約(collective) ---
  wk = 0.0
  do ipb = 1, r%npb
    ix = r%probe(ipb)%ixy(1)
    iy = r%probe(ipb)%ixy(2)
    if (dcp%js <= iy .and. iy <= dcp%je) then
      wk(iw_z,ipb) = s%z(ix,iy)
      wk(iw_h,ipb) = s%h(ix,iy)
      wk(iw_u,ipb) = s%u(ix,iy)
      wk(iw_v,ipb) = s%v(ix,iy)
      wk(iw_vv,ipb) = s%vv(ix,iy)
      wk(iw_qq,ipb) = s%qq(ix,iy)
      wk(iw_hg,ipb) = s%hg(ix,iy)
      wk(iw_hs,ipb) = s%hs(ix,iy)
      wk(iw_sd,ipb) = s%sd(ix,iy)
    end if
  end do
  call par_reduce_points(wk)

  ! --- 以下は従来の逐次ロジック(セル値の参照だけ wk 経由) ---
  if (.not. is_root) return

  do ipb = 1, r%npb
    un = r%probe(ipb)%un
    !if (p%dble_precision) then
    !  ffmt = 'f22.16'
    !else
      ffmt = "f14.5"
    !end if
    afmt = "("//trim(ffmt)//")"
    write(un, afmt, advance='no') s%t / 3600
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') s%t / 60
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(iw_z,ipb)
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(iw_h,ipb)
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(iw_u,ipb)
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(iw_v,ipb)
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(iw_vv,ipb)
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(iw_qq,ipb)
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(iw_hg,ipb)
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(iw_hs,ipb)
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(iw_sd,ipb)
    write(un, *)
    if (wk(iw_qq,ipb) > r%probe(ipb)%qmax) then
      r%probe(ipb)%tp = s%t / 60.
      r%probe(ipb)%qmax = wk(iw_qq,ipb)
      r%probe(ipb)%hmax = wk(iw_h,ipb)
    end if
  end do
end subroutine

!----------------------------------------------------------------------
! フラックス計測の情報を記録
!----------------------------------------------------------------------
subroutine m_record_flux(r, p, s)
  type(t_record), intent(inout) :: r
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  integer :: ifl, un, ncell
  integer :: i, k, ix, iy
  real :: q
  real :: hmax, vmax, b
  real, allocatable :: wk(:,:)   ! 点集約バッファ: (4, ncell) = m, n, h, |V|
  character(len=10) :: ffmt
  character(len=80) :: afmt
  type(t_flux) :: flx
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  if (r%nfl <= 0) return

  do ifl = 1, r%nfl
    flx = r%flux(ifl)
    un = flx%un
    ncell = flx%ncell

    ! --- 全ランク: 測線上の所有セルの値を詰めて rank0 に点集約(collective) ---
    allocate(wk(4, ncell), source = 0.0)
    do i = 1, ncell
      ix = flx%ixy(1,i)
      iy = flx%ixy(2,i)
      if (dcp%js <= iy .and. iy <= dcp%je) then
        wk(1,i) = s%m(ix,iy)
        wk(2,i) = s%n(ix,iy)
        wk(3,i) = s%h(ix,iy)
        wk(4,i) = s%vv(ix,iy)
      end if
    end do
    call par_reduce_points(wk)

    ! --- 以下は従来の逐次ロジック(セル値の参照だけ wk 経由) ---
    if (.not. is_root) then
      deallocate(wk)
      cycle
    end if

    ! DDA 階段面の積算(§24): 踏面=短手方向フラックス×係数 ct、
    ! 蹴上げ=長手方向フラックス(段差を挟む踏面2セルの平均)×係数 cr。
    ! 係数は set_flux が法線符号×セル幅で前計算済み
    q = 0.0
    hmax = 0.0
    vmax = 0.0
    b = 0.
    do i = 1, ncell
      if (flx%major == 1) then
        q = q + wk(2,i) * flx%ct               ! x 長手: 踏面は n(y方向フラックス)
      else
        q = q + wk(1,i) * flx%ct               ! y 長手: 踏面は m(x方向フラックス)
      end if
      hmax = max(wk(3,i), hmax)
      vmax = max(wk(4,i), vmax)
    end do
    do i = 1, flx%nris
      k = flx%irs(i)
      if (flx%major == 1) then
        q = q + 0.5 * (wk(1,k) + wk(1,k+1)) * flx%cr   ! 蹴上げは m
      else
        q = q + 0.5 * (wk(2,k) + wk(2,k+1)) * flx%cr   ! 蹴上げは n
      end if
    end do
    deallocate(wk)
    if (hmax * vmax > 0.0) b = abs(q / hmax / vmax)

    ffmt = "f13.4"
    afmt = "("//trim(ffmt)//")"
    write(un, afmt, advance='no') s%t / 3600
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') s%t / 60
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') q
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') hmax
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') vmax
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') b
    write(un, *)
    if (q > r%flux(ifl)%qmax) then
      r%flux(ifl)%tp = s%t / 60.
      r%flux(ifl)%qmax = q
      r%flux(ifl)%hmax = hmax
    end if
  end do

end subroutine


!----------------------------------------------------------------------
! 最大流量の一覧を出力
!----------------------------------------------------------------------
subroutine m_record_summary(r, p)
  type(t_record), intent(in) :: r
  type(t_sysparam), intent(in) :: p
  integer :: un
  integer :: i
  character(len=80) :: fn_smry

  if (.not. is_root) return

  if (r%npb <= 0 .and. r%nfl <= 0) return

  fn_smry = trim(p%dir_result)//"/"//"summary"//trim(p%outfn_suffix)//".csv"
  open(newunit=un, file=trim(fn_smry), status='replace')
  write(un, '("# type, No., t(hour), t(min), Qmax(m3/s), Hmax(m), ixR, iyR, ixL, iyL")')
  do i = 1, r%npb
    write(un, '(a,i5,a,f11.5,a,f14.5,a,f14.5,a,f12.5,a,i7,a,i7)') &
            "probe,", i, ",", r%probe(i)%tp / 60.0, ",", r%probe(i)%tp, ",", &
            r%probe(i)%qmax, ",", r%probe(i)%hmax, ",", &
            r%probe(i)%ixy(1), ",", r%probe(i)%ixy(2)
  end do
  do i = 1, r%nfl
    write(un, '(a,i5,a,f11.5,a,f14.5,a,f14.5,a,f12.5,a,i7,a,i7,a,i7,a,i7)') &
            "flux,", i, ",", r%flux(i)%tp / 60.0, ",", r%flux(i)%tp, ",", &
            r%flux(i)%qmax, ",", r%flux(i)%hmax, ",", &
            r%flux(i)%ixy0(1), ",", r%flux(i)%ixy0(2), ",", &
            r%flux(i)%ixy0(3), ",", r%flux(i)%ixy0(4)
  end do

  close(un)
end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
