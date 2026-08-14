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
  !   実座標指定(flxytype=1)は §36 の新仕様(2026-08-14): 線分が
  !   かすめる各セルのセル内線分成分で積算する(mode=1。旧方式の
  !   重み求積とは別物。1セル内の短い測線も定義される)。
  ! 実座標の解釈(プローブ・測線共通。§36): x 東・y 北が正。
  !   地理参照(hdr/GeoTIFF 由来)があれば絶対座標、なければ領域南西端
  !   原点のローカル座標。解決したセル番号を初期化時に表示する。
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
  use iso_fortran_env, only : real64
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
    ! 実座標指定(mode=1。§36): 測線の線分がかすめる各セル k について
    ! セル内の線分成分から前計算した係数で Q = Σ am(k)·m + an(k)·n を
    ! 積算する(内部座標系(y 南向き)の成分 (u,v) に対し am=−v, an=u。
    ! 軸平行・全幅のとき DDA の踏面と厳密に一致し、一様流で任意の
    ! 傾き・長さに厳密。符号規約は DDA と同じ「進行方向右側が正」)
    integer :: mode = 0                    ! 0: セル番号指定(DDA), 1: 実座標指定(線分積算)
    real :: am(1:ncellmax)                 ! mode=1: セル k の m の係数 (m)
    real :: an(1:ncellmax)                 ! mode=1: セル k の n の係数 (m)
    real :: tp                             ! 最大流量の発生時刻(s)
    real(real64) :: lcum = 0.0_real64      ! 累積負荷 (kg。wq 有効時のみ更新。§30)
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
subroutine m_record_init(r, p, g, s)
  type(t_record), intent(out) :: r
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s       ! wq_active(追加列ヘッダの判定)
  type(t_list_record) :: list
  integer :: pbxytype
  real, allocatable :: pbxy(:,:)
  integer :: flxyfile
  integer :: flxytype
  real :: flxy(1:4,1:nflmax) = -9.999e33   ! 未設定番兵(絶対座標の負値と衝突しない値)

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
  real :: xi, yi
  logical :: absol
  character(len=80) :: fn_pb
  character(len=4) :: cun
  character(len=1024) :: msg

  !---- プローブ数をカウント ----
  npb = 0
  !do i = 1, size(pbxy, 2)
  do i = 1, ubound(pbxy, 2)
    if (pbxy(1,i) < -1.0e30) exit   ! 有効なデータが無い場合は終了
                                    ! (番兵は -9.999e33。実座標の大きな負値=
                                    !  平面直角座標系の西側・南側と衝突させない。§36)
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
      ! 実座標指定(x 東・y 北が正。地理参照があれば絶対座標、
      ! なければ南西端原点のローカル座標。§36)
      x = pbxy(1,i)
      y = pbxy(2,i)
      call resolve_xy(x, y, xi, yi, ix, iy, absol)
      if (absol) then
        call par_info(" probe "//itoa(i)//": absolute coordinates -> cell (" &
                      //itoa(ix)//","//itoa(iy)//")")
      else
        call par_info(" probe "//itoa(i)//": local coordinates (SW origin) -> cell (" &
                      //itoa(ix)//","//itoa(iy)//")")
      end if
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
    if (s%wq_active) then
      write(un, '("# t(hour), t(min), z(m), h(m), u(m/s), v(m/s), |V|(m/s), q(m2/s), hg(m), hs(m), sd(m), C(mg/L), cq(g/m2)")')
    else
      write(un, '("# t(hour), t(min), z(m), h(m), u(m/s), v(m/s), |V|(m/s), q(m2/s), hg(m), hs(m), sd(m)")')
    end if
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
    if (flxy(1,i) < -1.0e30) exit   ! 有効なデータが無い場合は終了(番兵は同上)
    nfl = nfl + 1
  end do
  r%nfl = nfl
  if (nfl < 1) return

  if (flxytype /= 0 .and. flxytype /= 1) then
    call par_abort("m_record: flxytype は 0(セル番号指定)か 1(実座標指定)です: " &
                   //itoa(flxytype))
  end if

  !---- 測線情報を保存 ----
  allocate(r%flux(1:nfl))
  do i = 1, nfl
    if (flxytype == 1) then
      ! 実座標指定(mode=1。§36): セル内線分成分の積算方式
      call set_flux_segment(i)
      cycle
    end if
    ! セル番号指定(両端セルの中心を結ぶ DDA 階段面)
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
      ! 1セルのみの計測は「どの向きの面で測るか」が決められないため
      ! セル番号指定では定義できない(2026-08-14 に warning+無視から
      ! エラーへ格上げ。§36)
      call par_abort("m_record: flux "//itoa(i)//" の両端が同一セルです。" &
                     //"1セル内の計測は向きが定義できないため、実座標指定" &
                     //"(flxytype=1)で測線の向きと長さを与えてください(§36)")
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
    if (s%wq_active) then
      write(un, '("# t(hour), t(min), Q(m3/s), Hmax(m), Vmax(m/s), B(m)(=Q/Hmax/Vmax), L(g/s), Lcum(kg)")')
    else
      write(un, '("# t(hour), t(min), Q(m3/s), Hmax(m), Vmax(m/s), B(m)(=Q/Hmax/Vmax)")')
    end if
    r%flux(i)%un = un
  end do
end subroutine

!---------------------------------------------------------------------
! 実座標(x 東・y 北が正)をセル番号に解決する(§36)
!   地理参照(hdr/GeoTIFF 由来)があれば絶対座標、なければ領域南西端
!   原点のローカル座標として解釈する。返す xi, yi は内部ローカル座標
!   (北西原点・y 南向き, m)。範囲外は呼び出し側で検査する
!---------------------------------------------------------------------
subroutine resolve_xy(x, y, xi, yi, ix, iy, absol)
  real, intent(in) :: x, y
  real, intent(out) :: xi, yi
  integer, intent(out) :: ix, iy
  logical, intent(out) :: absol
  if (g%gr%active) then
    ! 絶対座標: 北西隅外縁からセル寸法(経緯度格子では度)で正規化して
    ! 内部座標 (m) へ換算する(投影格子では csx=dx なので恒等)
    absol = .true.
    xi = real((real(x, real64) - g%gr%xul) / g%gr%csx * real(g%dx, real64))
    yi = real((g%gr%yul - real(y, real64)) / g%gr%csy * real(g%dy, real64))
  else
    absol = .false.
    xi = x
    yi = g%ly - y
  end if
  ix = floor(xi / g%dx) + 1
  iy = floor(yi / g%dy) + 1
end subroutine

!---------------------------------------------------------------------
! 実座標指定の測線(mode=1。§36)を構築する
!   線分がかすめる各セルについて、セル内の線分成分 (u, v)(内部座標系
!   =y 南向き, m)から係数 am=−v, an=u を前計算する。軸平行・セル全幅
!   のとき DDA の踏面1枚と厳密に一致し、一様流では任意の位置・傾き・
!   長さに厳密。1セル内の短い測線も定義される
!---------------------------------------------------------------------
subroutine set_flux_segment(i)
  integer, intent(in) :: i
  integer :: ix0, iy0, ix1, iy1, ix, iy, ncell, nstep
  real :: x0, y0, x1, y1
  real :: xi0, yi0, xi1, yi1
  real :: dxs, dys, dxs1, dys1, tlen, t, tnx, tny, tnext, uc, vc
  logical :: absol, absol1
  character(len=1024) :: msg

  x0 = flxy(1,i)
  y0 = flxy(2,i)
  x1 = flxy(3,i)
  y1 = flxy(4,i)
  call resolve_xy(x0, y0, xi0, yi0, ix0, iy0, absol)
  call resolve_xy(x1, y1, xi1, yi1, ix1, iy1, absol1)

  if (ix0 < 1 .or. ix0 > g%nx .or. iy0 < 1 .or. iy0 > g%ny) then
    write(msg, '("error: point R of flux ",i0," is out of area.",2f15.2,2i7)') i, x0, y0, ix0, iy0
    call par_abort(trim(msg))
  end if
  if (ix1 < 1 .or. ix1 > g%nx .or. iy1 < 1 .or. iy1 > g%ny) then
    write(msg, '("error: point L of flux ",i0," is out of area.",2f15.2,2i7)') i, x1, y1, ix1, iy1
    call par_abort(trim(msg))
  end if
  if (g%x(ix0,iy0) < 1) then
    write(msg, '("warning: point R of flux ",i0," is not in valid area.",2f15.2,2i7)') i, x0, y0, ix0, iy0
    call par_info(trim(msg))
  end if
  if (g%x(ix1,iy1) < 1) then
    write(msg, '("warning: point L of flux ",i0," is not in valid area.",2f15.2,2i7)') i, x1, y1, ix1, iy1
    call par_info(trim(msg))
  end if

  ! 指定された実座標(利用者の座標系)をそのまま記録する
  r%flux(i)%xy0(1) = x0
  r%flux(i)%xy0(2) = y0
  r%flux(i)%xy0(3) = x1
  r%flux(i)%xy0(4) = y1
  r%flux(i)%ixy0(1) = ix0
  r%flux(i)%ixy0(2) = iy0
  r%flux(i)%ixy0(3) = ix1
  r%flux(i)%ixy0(4) = iy1
  r%flux(i)%tp = 0
  r%flux(i)%mode = 1
  r%flux(i)%major = 0
  r%flux(i)%ct = 0.0
  r%flux(i)%cr = 0.0
  r%flux(i)%nris = 0
  r%flux(i)%qmax = -1.

  dxs = xi1 - xi0
  dys = yi1 - yi0
  tlen = sqrt(dxs**2 + dys**2)
  if (tlen <= 0.0) then
    call par_abort("m_record: flux "//itoa(i)//" の両端が同一点です" &
                   //"(測線の向きが定義できません)")
  end if
  r%flux(i)%trlen = tlen

  ! 線分をセル境界で区切りながら走査する(内部座標系)
  ! 除数は安全値に差し替えておく(軸平行の測線で成分が厳密に 0 のとき、
  ! -Ofast の if 変換が不使用側の分岐の除算を投機実行して 0 除算トラップを
  ! 踏む実障害があった。差し替え値の商は使われない)
  dxs1 = dxs
  if (dxs1 == 0.0) dxs1 = 1.0
  dys1 = dys
  if (dys1 == 0.0) dys1 = 1.0
  ix = ix0
  iy = iy0
  t = 0.0
  ncell = 0
  do nstep = 1, g%nx + g%ny + 4
    ! 現在セルから出る位置(線分パラメータ t)を求める
    if (dxs > 0.0) then
      tnx = (real(ix) * g%dx - xi0) / dxs1
    else if (dxs < 0.0) then
      tnx = (real(ix - 1) * g%dx - xi0) / dxs1
    else
      tnx = 2.0
    end if
    if (dys > 0.0) then
      tny = (real(iy) * g%dy - yi0) / dys1
    else if (dys < 0.0) then
      tny = (real(iy - 1) * g%dy - yi0) / dys1
    else
      tny = 2.0
    end if
    tnext = min(min(tnx, tny), 1.0)
    ! セル内成分から係数を積む(空でない区間のみ)
    if (tnext > t) then
      uc = dxs * (tnext - t)
      vc = dys * (tnext - t)
      ncell = ncell + 1
      if (ncell > ncellmax) call par_abort("m_record: flux "//itoa(i)//" が長すぎます")
      r%flux(i)%ixy(1,ncell) = ix
      r%flux(i)%ixy(2,ncell) = iy
      r%flux(i)%am(ncell) = -vc
      r%flux(i)%an(ncell) = uc
      t = tnext
    end if
    if (tnext >= 1.0) exit
    ! 到達した境界を跨いで隣のセルへ進む
    if (tnx <= tny) then
      ix = ix + int(sign(1.0, dxs))
    else
      iy = iy + int(sign(1.0, dys))
    end if
    if (ix < 1 .or. ix > g%nx .or. iy < 1 .or. iy > g%ny) exit  ! 端点が外縁上の丸め保険
  end do
  r%flux(i)%ncell = ncell
  if (ncell < 1) then
    call par_abort("m_record: flux "//itoa(i)//" の測線がセルを通過しません")
  end if

  if (absol) then
    call par_info(" flux "//itoa(i)//": absolute coordinates -> cells (" &
                  //itoa(ix0)//","//itoa(iy0)//")-("//itoa(ix1)//","//itoa(iy1) &
                  //"), ncell="//itoa(ncell))
  else
    call par_info(" flux "//itoa(i)//": local coordinates (SW origin) -> cells (" &
                  //itoa(ix0)//","//itoa(iy0)//")-("//itoa(ix1)//","//itoa(iy1) &
                  //"), ncell="//itoa(ncell))
  end if
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

  flxy(:,:) = -9.999e33       ! パラメータファイルの情報を上書きして初期化する
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
  real :: wk(11, r%npb)    ! 点集約バッファ: z, h, u, v, |V|, q, hg, hs, sd
                           ! (+ wq 有効時のみ書く: C(mg/L), cq(g/m2))
  character(len=10) :: ffmt
  character(len=80) :: afmt
  integer, parameter :: iw_z = 1, iw_h = 2, iw_u = 3, iw_v = 4, iw_vv = 5, iw_qq = 6, &
                        iw_hg = 7, iw_hs = 8, iw_sd = 9, iw_cc = 10, iw_cq = 11
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
      if (allocated(s%sd)) then
        wk(iw_sd,ipb) = s%sd(ix,iy)
      else
        wk(iw_sd,ipb) = 0.0     ! sd 未確保(利用モジュールなし)= 従来の 0 と同値
      end if
      if (s%wq_active) then
        wk(iw_cc,ipb) = s%cqc(ix,iy)
        wk(iw_cq,ipb) = s%cq(ix,iy)
      end if
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
    if (s%wq_active) then
      write(un, '(a)', advance='no') ","
      write(un, afmt, advance='no') wk(iw_cc,ipb)
      write(un, '(a)', advance='no') ","
      write(un, afmt, advance='no') wk(iw_cq,ipb)
    end if
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
  real :: q, lq
  real :: hmax, vmax, b
  real, allocatable :: wk(:,:)   ! 点集約バッファ: (5, ncell) = m, n, h, |V|, C(mg/L)
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
    allocate(wk(5, ncell), source = 0.0)
    do i = 1, ncell
      ix = flx%ixy(1,i)
      iy = flx%ixy(2,i)
      if (dcp%js <= iy .and. iy <= dcp%je) then
        wk(1,i) = s%m(ix,iy)
        wk(2,i) = s%n(ix,iy)
        wk(3,i) = s%h(ix,iy)
        wk(4,i) = s%vv(ix,iy)
        if (s%wq_active) wk(5,i) = s%cqc(ix,iy)
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
    lq = 0.0
    hmax = 0.0
    vmax = 0.0
    b = 0.
    if (flx%mode == 1) then
      ! 実座標指定(§36): セル内線分成分の係数 am, an で積算
      do i = 1, ncell
        q = q + flx%am(i) * wk(1,i) + flx%an(i) * wk(2,i)
        lq = lq + (flx%am(i) * wk(1,i) + flx%an(i) * wk(2,i)) * wk(5,i)
        hmax = max(wk(3,i), hmax)
        vmax = max(wk(4,i), vmax)
      end do
    else
    do i = 1, ncell
      if (flx%major == 1) then
        q = q + wk(2,i) * flx%ct               ! x 長手: 踏面は n(y方向フラックス)
        lq = lq + wk(2,i) * flx%ct * wk(5,i)   ! 負荷 = 水フラックス×セル濃度(§30)
      else
        q = q + wk(1,i) * flx%ct               ! y 長手: 踏面は m(x方向フラックス)
        lq = lq + wk(1,i) * flx%ct * wk(5,i)
      end if
      hmax = max(wk(3,i), hmax)
      vmax = max(wk(4,i), vmax)
    end do
    do i = 1, flx%nris
      k = flx%irs(i)
      if (flx%major == 1) then
        q = q + 0.5 * (wk(1,k) + wk(1,k+1)) * flx%cr   ! 蹴上げは m
        lq = lq + 0.5 * (wk(1,k) * wk(5,k) + wk(1,k+1) * wk(5,k+1)) * flx%cr
      else
        q = q + 0.5 * (wk(2,k) + wk(2,k+1)) * flx%cr   ! 蹴上げは n
        lq = lq + 0.5 * (wk(2,k) * wk(5,k) + wk(2,k+1) * wk(5,k+1)) * flx%cr
      end if
    end do
    end if
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
    if (s%wq_active) then
      ! 負荷フラックス L (g/s) と累積負荷 (kg。記録間隔の矩形積分 = 近似)
      r%flux(ifl)%lcum = r%flux(ifl)%lcum + real(lq, real64) * real(p%dt_recrd, real64) / 1000.0_real64
      write(un, '(a)', advance='no') ","
      write(un, afmt, advance='no') lq
      write(un, '(a)', advance='no') ","
      write(un, afmt, advance='no') real(r%flux(ifl)%lcum)
    end if
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
