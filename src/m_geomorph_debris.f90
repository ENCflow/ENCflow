!======================================================================
! m_geomorph の submodule: 土石流の E-D 交換(f_debris。高橋型平衡濃度)
!   移流本体は m_swflow_enc のステップ内輸送(advect_scalar)が担い
!   (sed_active は f_debris でも立つ)、ここは河床との侵食・堆積のみ。
!   設計全文は docs/debris_plan.md §2.2。
!
!   平衡濃度 C∞(勾配領域で切替。C は混合体積濃度 hs/(h+hs)):
!     tanθ >  0.138        : C∞ = tanθ / (s(tanφ − tanθ))(石礫型。導出式)
!     0.03 < tanθ ≤ 0.138 : C∞ = 6.7・C∞d²(未成熟)
!     tanθ ≤ 0.03         : C∞ = 0(掃流域は堆積側に一本化。第3領域式は
!                            文献照合後に追加 — debris_plan.md §1)
!     上限 C∞ ≤ 0.9C*(C* = 1−λ)
!   【要文献照合】閾値 0.138 / 0.03、係数 6.7、上限 0.9C* は高橋理論の
!   慣用値。原典(Takahashi 2007 等)との照合完了までこの注記を残すこと。
!
!   交換速度(河床深さレート、×|V|。形は高橋(1992)系【要文献照合】):
!     侵食(C < C∞): i_e = δe・(C∞−C)/(C*−C∞)・|V|
!     堆積(C > C∞): i_d = δd・(C∞−C)/C*・|V|(負)
!   fx(hs への固体柱状量)= C*・i・dtw。可動層クランプ(侵食 ≤ sd)、
!   浮遊量クランプ(堆積 ≤ hs)、z・sd の共動更新、gwflow 容量引き渡し、
!   乾燥セル(h ≤ dd)の全量繰り入れは calc_suspend と同一規約。
!   間隙水の授受は無視(suspend と同じ近似。水相は独立に保存)。
!
!   停止条件の切替(f_dbstop):
!     0: なし(∝|V| の E-D のみ = Kanako 相当。|V|→0 で交換凍結)
!     1: 低速凝集 — vv < db_vstop かつ C > C∞ のセルで、平衡濃度までの
!        超過分をレート db_wstop(河床深さ換算)で河床へ転換する。
!        停止土塊が z へ固定され天然ダムの地形になる(数値的閉包で
!        あり文献式ではない — debris_plan.md §2.2)
!
!   勾配は 8 近傍への最急降下勾配(地形勾配。流向非依存 = 速度 0 でも
!   定義される)。時刻 n の s%z(自セル+近傍。ハロはステップ頭交換で
!   最新)を読むため、本プロセスは m_geomorph_calc の先頭で適用される。
!   morfac は 1 に限定(init で検証。イベント計算)。
!======================================================================
submodule(m_geomorph) m_geomorph_debris
  use m_parallel, only : par_stop, dcp, par_halo_cell
  use m_swflow_enc, only : m_swflow_enc_set_debris
  use m_fileio, only : fileio_read_matrix
  implicit none

  ! 勾配領域の閾値と係数(【要文献照合】高橋理論の慣用値。原式固定で
  ! namelist にしない — developer.md §19.8 の原則2)
  real, parameter :: db_tan1 = 0.138     ! 石礫型/未成熟の境界 tanθ
  real, parameter :: db_tan2 = 0.03      ! 未成熟/掃流の境界 tanθ
  real, parameter :: db_immat = 6.7      ! 未成熟領域の係数(C∞ = 6.7 C∞d²)
  real, parameter :: db_cfrac = 0.9      ! C∞ の上限係数(C∞ ≤ 0.9 C*)

  ! 高橋・中川(1991)新砂防 44(3) の定数(原式固定。f_dbed=3)
  real, parameter :: tk_ab = 0.02        ! a_i・sinα_i(式(2)(15)の 0.02)
  real, parameter :: tk_p = 1.0 / 3.0    ! 堆積の慣性係数の定数 p(式(27)。採用値)

contains

!----------------------------------------------------------------------
! 土石流 E-D の初期化(検証と距離テーブル。エッジ作業領域は不要)
!----------------------------------------------------------------------
module subroutine init_debris(gm, p, g, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_geomorph), intent(in) :: list
  integer :: k
  real, parameter :: deg2rad = acos(-1.0) / 180.0

  if (list%db_phi <= 0.0 .or. list%db_phi >= 90.0) then
    call par_stop("list_geomorph: f_debris requires db_phi in (0, 90) deg")
  end if
  gm%db_tanphi = tan(list%db_phi * deg2rad)
  ! 石礫型領域(tanθ > 0.138)で分母 tanφ − tanθ が定義されるための下限
  if (gm%db_tanphi <= db_tan1) then
    call par_stop("list_geomorph: db_phi is too small, tan(phi) > 0.138 is required " &
                  // "(internal friction angle of sediment is usually 30-40 deg)")
  end if
  if (list%db_delte <= 0.0) call par_stop("list_geomorph: db_delte must be > 0")
  if (list%db_deltd <= 0.0) call par_stop("list_geomorph: db_deltd must be > 0")
  gm%db_delte = list%db_delte
  gm%db_deltd = list%db_deltd
  ! C* = 1 − λ(空隙率は土砂プロセス共有の fluv_porosity。新パラメータに
  ! しない — 物理パラメータの共有原則 §19.8)
  gm%db_cstar = 1.0 / gm%poroi

  select case (list%f_dbstop)
    case (0)      ! なし
      continue
    case (1)      ! 低速凝集
      if (list%db_vstop <= 0.0) then
        call par_stop("list_geomorph: f_dbstop=1 requires db_vstop > 0")
      end if
      if (list%db_wstop <= 0.0) then
        call par_stop("list_geomorph: f_dbstop=1 requires db_wstop > 0")
      end if
    case default
      call par_stop("list_geomorph: f_dbstop must be 0(none) or 1(low-velocity settling)")
  end select
  gm%f_dbstop = list%f_dbstop
  gm%db_vstop = list%db_vstop
  gm%db_wstop = list%db_wstop

  ! E-D 式の選択
  !   2 = 江頭・芦田1992: E = |V|・C*・tan(θ−θe)。追加パラメータなし。
  !       典拠: Egashira & Ashida (1992), Morpho2DH Solver Manual 式(5)-(7)
  !   3 = 高橋・中川1991: 飽和床侵食(式12)+慣性係数付き堆積(式27)。
  !       レートは δe/δd・q_T/d_L(db_d50 必須)。
  !       典拠: 高橋・中川, 新砂防 44(3), 1991, 12-19
  select case (list%f_dbed)
    case (1, 2)
      gm%f_dbed = list%f_dbed
    case (3)
      if (list%db_d50 <= 0.0) then
        call par_stop("list_geomorph: f_dbed=3 requires db_d50 > 0(レート q_T/d_L の粒径)")
      end if
      gm%f_dbed = list%f_dbed
    case default
      call par_stop("list_geomorph: f_dbed must be 1(simplified), 2(Egashira-Ashida)" &
                    // " or 3(Takahashi-Nakagawa 1991)")
  end select

  ! 抵抗則(実体は m_swflow_enc。パラメータをここで検証して渡す。
  ! 初期化順序: geomorph init は swflow init より前 — m_main 参照)
  select case (list%f_dbres)
    case (0)      ! マニングのみ(E-D の単独検証用)
      continue
    case (1)      ! クーロン+マニング合成
      if (list%db_vstop <= 0.0) then
        call par_stop("list_geomorph: f_dbres=1 requires db_vstop > 0 (yield threshold)")
      end if
    case (2)      ! 江頭構成則(τy + 層流抵抗。江頭ら1989 式(25)/Morpho2DH 式(17)(19))
      if (list%db_vstop <= 0.0) then
        call par_stop("list_geomorph: f_dbres=2 requires db_vstop > 0(降伏判定の閾値)")
      end if
      if (list%db_d50 <= 0.0) then
        call par_stop("list_geomorph: f_dbres=2 requires db_d50 > 0(層流抵抗の h/d)")
      end if
      if (list%db_erest <= 0.0 .or. list%db_erest > 1.0) then
        call par_stop("list_geomorph: f_dbres=2 requires db_erest in (0, 1]" &
                      // "(粒子の反発係数。材料固有値 — 文献に既定なし)")
      end if
      if (list%db_cmin <= 0.0 .or. list%db_cmin >= gm%db_cstar) then
        call par_stop("list_geomorph: db_cmin must be in (0, C*)")
      end if
    case (3)      ! 高橋・中川1991 石礫型(式(22)-(25)。tanα'=0.45, A'=4 は原式固定)
      if (list%db_vstop <= 0.0) then
        call par_stop("list_geomorph: f_dbres=3 requires db_vstop > 0(降伏判定の閾値)")
      end if
      if (list%db_d50 <= 0.0) then
        call par_stop("list_geomorph: f_dbres=3 requires db_d50 > 0(抵抗則の d_L/h)")
      end if
      if (list%db_cmin <= 0.0 .or. list%db_cmin >= gm%db_cstar) then
        call par_stop("list_geomorph: db_cmin must be in (0, C*)")
      end if
    case default
      call par_stop("list_geomorph: f_dbres must be 0(Manning), 1(Coulomb+Manning)," &
                    // " 2(Egashira) or 3(Takahashi-Nakagawa 1991)")
  end select
  gm%f_dbres = list%f_dbres
  gm%db_d50v = list%db_d50
  gm%db_erest = list%db_erest
  gm%db_cmin = list%db_cmin
  call m_swflow_enc_set_debris(gm%f_dbres, gm%db_tanphi, gm%sgrav, gm%db_vstop, &
                               gm%db_cstar, gm%db_cmin, gm%db_d50v, gm%db_erest)

  ! 間隙水の連行(f_dbwet。高橋・中川1991 式(5)の源泉 i{c*+(1−c*)s_b} 形)
  select case (list%f_dbwet)
    case (0)
      continue
    case (1)
      if (list%db_satbed < 0.0 .or. list%db_satbed > 1.0) then
        call par_stop("list_geomorph: db_satbed must be in [0, 1]")
      end if
      ! gwflow との併用は不可: 侵食時の間隙水放出は gwflow 併用時は
      ! 容量超過引き渡し(hg → h)が担っており、二重計上になる。
      ! (gw_active は gwflow init 後に確定するため、ここでは設定ファイル
      !  指定の有無で判定する。fn_gwflow を書いたまま f_gwvertical=0 で
      !  無効化している構成もエラーになるが、メッセージで案内する)
      if (len_trim(p%fn_gwflow) > 0) then
        call par_stop("list_geomorph: f_dbwet=1 は gwflow と併用できません" &
                      // "(侵食時の間隙水放出が容量引き渡しと二重計上になります。" &
                      // " fn_gwflow の指定を外してください)")
      end if
    case default
      call par_stop("list_geomorph: f_dbwet must be 0(ignore) or 1(saturated-bed entrainment)")
  end select
  gm%f_dbwet = list%f_dbwet
  gm%db_lamsb = (1.0 - gm%db_cstar) * list%db_satbed    ! λ・s_b(λ = 1−C*)

  ! 8近傍距離テーブル(最急降下勾配用)
  do k = 1, 8
    dbr%dist8(k) = sqrt((din(k) * g%dx)**2 + (djn(k) * g%dy)**2)
  end do

  ! E-D 交換量の作業領域(2パス構造。calc_debris ヘッダ参照)
  if (.not. allocated(dbr%fx)) then
    allocate(dbr%fx(1:g%nx, dcp%js:dcp%je), source = 0.0)
  end if

  ! --- 瞬時流動化(f_release)。fn_dbinit の有無で有効化 ---
  if (len_trim(list%fn_dbinit) > 0) then
    if (list%db_relsat < 0.0 .or. list%db_relsat > 1.0) then
      call par_stop("list_geomorph: fn_dbinit requires db_relsat in [0, 1]")
    end if
    gm%f_release = 1
    gm%db_reltime = list%db_reltime
    gm%db_relsat = list%db_relsat
    call read_release(p, g, trim(list%fn_dbinit))
  end if

  ! --- 無限長斜面安定判定(f_slide) ---
  if (list%f_slide > 0) then
    if (list%f_slide /= 1) call par_stop("list_geomorph: f_slide must be 0 or 1")
    if (list%slide_c < 0.0) call par_stop("list_geomorph: slide_c must be >= 0")
    if (list%slide_phi <= 0.0 .or. list%slide_phi >= 90.0) then
      call par_stop("list_geomorph: f_slide requires slide_phi in (0, 90) deg")
    end if
    if (list%slide_gamma <= 0.0) then
      call par_stop("list_geomorph: f_slide requires slide_gamma > 0 (N/m3)")
    end if
    if (list%db_relsat < 0.0 .or. list%db_relsat > 1.0) then
      call par_stop("list_geomorph: f_slide requires db_relsat in [0, 1]")
    end if
    gm%f_slide = 1
    gm%sl_c = list%slide_c
    gm%sl_tanphi = tan(list%slide_phi * deg2rad)
    gm%sl_gamma = list%slide_gamma
    gm%db_relsat = list%db_relsat      ! gwflow 無効時の間隙水付与(release と共有)
    if (.not. allocated(dbr%sld)) then
      allocate(dbr%sld(1:g%nx, dcp%js:dcp%je), source = .false.)
    end if
  end if
end subroutine


!----------------------------------------------------------------------
! 崩壊深分布ファイルを読み帯を切り出す(全ランク冗長の全域読み。
! read_hinit と同じ流儀。負値は設定誤りとして停止)
!----------------------------------------------------------------------
subroutine read_release(p, g, fname)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fname
  real, allocatable :: wk(:,:)
  allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
  call fileio_read_matrix(trim(p%dir_data)//"/"//fname, g%nx, g%ny, wk, p%f_input_mode)
  if (minval(wk) < 0.0) then
    call par_stop("list_geomorph: fn_dbinit release depth has negative values: "//fname)
  end if
  allocate(dbr%rel(1:g%nx, dcp%js:dcp%je), source = wk(1:g%nx, dcp%js:dcp%je))
end subroutine


!----------------------------------------------------------------------
! 土石流の侵食・堆積(2パス構造)
!   パス1: 時刻 n の z(自セル+近傍の最急降下勾配)から交換量 fx を
!          dbr%fx に計算する(s への書き込みなし)
!   パス2: fx を適用する(書き込みは自セルに閉じる。近傍読みなし)
!   1パスのその場更新は「slope8 の近傍 z 読み vs 他スレッドの z 書き」の
!   OpenMP データ競合になる(np=4 の state.dat 非決定で実検出)。
!   suspend/wash は近傍を読まないため1パスで安全 — この差に注意
!----------------------------------------------------------------------
module subroutine calc_debris(gm, p, g, s, dtw)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw       ! 実効時間刻み(morfac=1 を init で保証済み)
  integer :: i, j
  real :: tanth, cinf, cc, hm, fx, dzb, cap, fxg, hseq, dhw
  real :: tanthc, sinthc, vcr, fac

  ! --- f_dbed=3 の流動面勾配は近傍の h・hs を読む。両者のハロは
  !     ステップ頭交換のままで、swflow が帯内を更新済み = 帯界面で
  !     古い(calc_fluvial の冒頭交換と同じ構図。np=2 の state.dat
  !     不一致で実検出)。ここで最新化する(判定は namelist 由来で
  !     全ランク同一 = collective 安全。z は交換済みで不要) ---
  if (gm%f_dbed == 3) then
    call par_halo_cell(s%h)
    call par_halo_cell(s%hs)
  end if

  ! --- 斜面安定のパス1: Fs 評価(時刻 n の z。E-D パス2 より前に評価する
  !     ことで、勾配読みが帯内更新とハロの不整合を起こさない) ---
  if (gm%f_slide > 0) call slide_pass1(gm, p, g, s)

  ! --- パス1: 交換量の計算(時刻 n の状態のみを読む) ---
  !$omp parallel do schedule(static) private(i, j, tanth, cinf, cc, hm, fx, hseq, &
  !$omp                                      tanthc, sinthc, vcr, fac)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      dbr%fx(i,j) = 0.0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) <= p%dd) then
        ! 乾燥セル: 浮遊分を全量河床へ(calc_suspend と同一の閉じ)
        if (s%hs(i,j) <= 0.0) cycle
        fx = -s%hs(i,j)
      else
        ! 混合体積濃度 C = hs/(h+hs)(希薄極限で hs/h に漸近)
        hm = s%h(i,j) + max(s%hs(i,j), 0.0)
        cc = 0.0
        if (s%hs(i,j) > 0.0) cc = s%hs(i,j) / hm
        if (gm%f_dbed == 2) then
          ! 江頭・芦田(1992): E = |V|・C*・tan(θ−θe)(流向の河床勾配。
          ! 侵食・堆積が1本の式で連続。Morpho2DH 式(5)-(7))
          if (s%vv(i,j) > 0.0) then
            tanth = slope_flow(g, s, i, j)
            fx = gm%db_cstar * s%vv(i,j) &
                 * tan(atan(tanth) - atan(gm%sgrav * cc / (gm%sgrav * cc + 1.0) &
                                          * gm%db_tanphi)) * dtw
            if (fx > 0.0) then
              ! 可動層クランプ(河床側は ×morfac・poroi で減るため換算して制限)
              fx = min(fx, s%sd(i,j) / (gm%morfac * gm%poroi))
            end if
          else
            ! 静止セルは E-D なし(E ∝ |V|)。停止判定用の勾配は地形勾配
            tanth = slope8(g, s, i, j)
            fx = 0.0
          end if
          ! 停止条件(f_dbstop=1)の平衡濃度は同式の逆関数(勾配→濃度)
          cinf = ceq_egashira(gm, tanth)
        else if (gm%f_dbed == 3) then
          ! 高橋・中川(1991)新砂防 44(3)。単一粒径・飽和床形
          ! (多粒径の式(12)(27)は単一粒径 ρm=ρ, c_L=c_T=C, c*DL=C* で
          !  以下に帰着する — debris_plan.md §1)
          if (s%vv(i,j) > 0.0) then
            ! 流速ベクトル方向の流動面(z+h+hs)勾配(式(26))
            tanth = slope_flow_surf(g, s, i, j)
            cinf = ceq_egashira(gm, tanth)   ! 式(11)(13)の単一粒径形(上限 0.9C*)
            if (cc < cinf) then
              ! 飽和床の侵食(式(12): δe・(C∞−C)/(C*−C∞)・q_T/d_L。
              ! 固体換算 fx = C*・i・dtw)
              fx = gm%db_cstar * gm%db_delte * (cinf - cc) / (gm%db_cstar - cinf) &
                   * s%vv(i,j) * hm / gm%db_d50v * dtw
              fx = min(fx, s%sd(i,j) / (gm%morfac * gm%poroi))
            else
              ! 堆積(式(27): δd・(1−V/(p・vc))⁴・(C∞−C)/C*・q_T/d_L。
              ! vc は限界速度(式(15))、tanθc は限界勾配(式(16))。
              ! 慣性係数が負(V ≥ p・vc)の間は堆積しない(慣性走行)
              fx = 0.0
              if (cc > 0.0) then
                tanthc = gm%sgrav * cc / (gm%sgrav * cc + 1.0) * gm%db_tanphi
                sinthc = tanthc / sqrt(1.0 + tanthc**2)
                vcr = 0.4 / gm%db_d50v &
                      * sqrt(p%gg * sinthc / tk_ab * (cc + (1.0 - cc) / (gm%sgrav + 1.0))) &
                      * ((gm%db_cstar / cc)**(1.0/3.0) - 1.0) * hm**1.5
                if (vcr > 0.0) then
                  fac = 1.0 - s%vv(i,j) / (tk_p * vcr)
                  if (fac > 0.0) then
                    fx = gm%db_deltd * fac**4 * (cinf - cc) &
                         * s%vv(i,j) * hm / gm%db_d50v * dtw
                  end if
                end if
              end if
            end if
          else
            ! 静止セルは E-D なし(レート ∝ q_T)。停止判定用の勾配は地形勾配
            tanth = slope8(g, s, i, j)
            cinf = ceq_egashira(gm, tanth)
            fx = 0.0
          end if
        else
          ! 高橋型: 平衡濃度 C∞(θ) への緩和(最急降下勾配。時刻 n の z)
          tanth = slope8(g, s, i, j)
          cinf = ceq_debris(gm, tanth)
          if (cc < cinf) then
            ! 侵食(C* − C∞ ≥ 0.1C* が上限 0.9C* により保証される)
            fx = gm%db_cstar * gm%db_delte * (cinf - cc) / (gm%db_cstar - cinf) &
                 * s%vv(i,j) * dtw
            ! 可動層クランプ(河床側は ×morfac・poroi で減るため換算して制限)
            fx = min(fx, s%sd(i,j) / (gm%morfac * gm%poroi))
          else
            ! 堆積(C*・δd・(C∞−C)/C* = δd・(C∞−C))
            fx = gm%db_deltd * (cinf - cc) * s%vv(i,j) * dtw
          end if
        end if
        ! 停止条件(低速凝集): 低速かつ過飽和なら平衡までの超過分を
        ! レート db_wstop(河床深さ)で河床へ(f_dbstop=1)
        if (gm%f_dbstop == 1) then
          if (s%vv(i,j) < gm%db_vstop .and. cc > cinf) then
            ! 平衡濃度に対応する浮遊量 hs_eq = C∞・h/(1−C∞)
            hseq = cinf * s%h(i,j) / (1.0 - cinf)
            fx = fx - min(max(s%hs(i,j) - hseq, 0.0), &
                          gm%db_wstop * gm%db_cstar * dtw)
          end if
        end if
        if (fx < 0.0) fx = max(fx, -max(s%hs(i,j), 0.0))    ! 堆積は浮遊量まで
      end if
      dbr%fx(i,j) = fx
    end do
  end do
  !$omp end parallel do

  ! --- パス2: 適用(書き込みは自セルに閉じる) ---
  !$omp parallel do schedule(static) private(i, j, fx, dzb, cap, fxg, dhw)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      fx = dbr%fx(i,j)
      if (fx == 0.0) cycle
      s%hs(i,j) = s%hs(i,j) + fx
      ! 共動更新(z と sd が同じ Δz で動く → 帯水層底 (z - sd) は不変)
      dzb = -fx * gm%morfac * gm%poroi
      s%z(i,j) = s%z(i,j) + dzb
      s%sd(i,j) = s%sd(i,j) + dzb
      ! 間隙水の連行(f_dbwet=1。高橋・中川1991 式(5)の源泉
      ! i{c*+(1−c*)s_b} の水側。
      ! gwflow 併用は init で排除済み):
      !   侵食(Δz<0): λ・s_b・|Δz| の間隙水を地表水 h へ放出(飽和床)
      !   堆積(Δz>0): 同量を埋没(地表水の範囲で。不足分は不飽和堆積)
      if (gm%f_dbwet == 1) then
        dhw = -gm%db_lamsb * dzb
        if (dhw < 0.0) dhw = max(dhw, -max(s%h(i,j), 0.0))
        s%h(i,j) = s%h(i,j) + dhw
      end if
      ! 浸食で地下水容量が現在の貯留を下回ったら、超過分を地表水へ渡す
      ! (calc_suspend と同じ整合。反対称適用)
      if (s%gw_active) then
        cap = s%sd(i,j) * g%sy0
        if (s%hg(i,j) > cap) then
          fxg = s%hg(i,j) - cap
          s%hg(i,j) = cap
          s%h(i,j) = s%h(i,j) + fxg
        end if
      end if
    end do
  end do
  !$omp end parallel do

  ! --- 斜面安定のパス2: Fs < 1 のセルの土層を全層流動化 ---
  if (gm%f_slide > 0) call slide_pass2(gm, g, s)

end subroutine


!----------------------------------------------------------------------
! 無限長斜面安定の評価(パス1)
!   Fs = (c' + (γt・sd − γw・hw)・cos²θ・tanφs) / (γt・sd・sinθ・cosθ)
!   (有効応力のクーロン則。斜面平行浸透の間隙水圧 u = γw・hw・cos²θ。
!    導出式で経験定数なし — debris_plan.md §2.5)
!   hw = 飽和厚 = min(hg/sy0, sd)(gwflow 有効時。無効なら 0 = 静的判定)。
!   近似(文書化): セル独立の無限長斜面(側方支持なし)、浅層崩壊限定、
!   γt は湿潤・飽和一律。tanθ ≈ 0 は駆動なし = 判定対象外。
!   γw = 1000・g(淡水の単位体積重量)
!----------------------------------------------------------------------
subroutine slide_pass1(gm, p, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: tanth, cos2, w, hw, u, fs
  real :: fsmin_loc
  real, parameter :: rhow = 1000.0          ! 水の密度 (kg/m3。淡水)

  fsmin_loc = huge(1.0)
  !$omp parallel do schedule(static) private(i, j, tanth, cos2, w, hw, u, fs) &
  !$omp reduction(min: fsmin_loc)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      dbr%sld(i,j) = .false.
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%sd(i,j) <= 0.0) cycle
      tanth = slope8(g, s, i, j)
      if (tanth <= 1.0e-6) cycle              ! 駆動なし(Fs=∞ 扱い)
      cos2 = 1.0 / (1.0 + tanth**2)
      w = gm%sl_gamma * s%sd(i,j)             ! 単位面積の土塊重量 (N/m2)
      hw = 0.0
      if (s%gw_active .and. g%sy0 > 0.0) hw = min(s%hg(i,j) / g%sy0, s%sd(i,j))
      u = rhow * p%gg * hw                    ! γw・hw(cos²θ は下で共通に乗算)
      fs = (gm%sl_c + (w - u) * cos2 * gm%sl_tanphi) / (w * tanth * cos2)
      if (fs < fsmin_loc) fsmin_loc = fs
      if (fs < 1.0) dbr%sld(i,j) = .true.
    end do
  end do
  !$omp end parallel do
  if (fsmin_loc < dbr%fsmin) dbr%fsmin = fsmin_loc
end subroutine


!----------------------------------------------------------------------
! 斜面崩壊セルの全層流動化(パス2。書き込みは自セルに閉じる)
!   転換は release_debris と同じ台帳整合の fluidize
!----------------------------------------------------------------------
subroutine slide_pass2(gm, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: dd, cap, fxg

  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (.not. dbr%sld(i,j)) cycle
      dd = s%sd(i,j)
      if (dd <= 0.0) cycle
      s%hs(i,j) = s%hs(i,j) + dd / gm%poroi   ! 固体分 (1−λ)・D
      s%z(i,j) = s%z(i,j) - dd
      s%sd(i,j) = 0.0                          ! 岩盤露出(堆積で再生すれば再判定)
      dbr%nslide = dbr%nslide + 1
      if (s%gw_active) then
        ! 容量 0 になった帯水の全量を地表へ(容量超過引き渡しの極限)
        cap = 0.0
        if (s%hg(i,j) > cap) then
          fxg = s%hg(i,j) - cap
          s%hg(i,j) = cap
          s%h(i,j) = s%h(i,j) + fxg
        end if
      else
        s%h(i,j) = s%h(i,j) + (1.0 - 1.0 / gm%poroi) * gm%db_relsat * dd
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 瞬時流動化(f_release)の発火判定と適用
!   発火は時刻交差(前回の geomorph 呼び出し時刻 < db_reltime ≤ 現時刻)で
!   1回だけ。呼び出しは it の絶対格子(idt_geomorph の倍数)上にあるため、
!   リスタート後も交差判定だけで再発火しない(新規保存状態なし)。
!   最初の呼び出し(it−idt ≤ 0 = それ以前に呼び出しなし)は t0 以前の
!   指定も拾う。判定材料は全ランク同一(collective 安全)。
!   転換(台帳整合の fluidize。debris_plan.md §2.5):
!     hs += (1−λ)・D、z −= D、sd −= D(固体台帳 Δhs = −(1−λ)Δz が構造的に閉合)
!     水: gw_active なら容量超過引き渡し(間隙水は hg から出る)、
!         無効なら h += λ・relsat・D(シナリオ的な間隙水付与)
!----------------------------------------------------------------------
module subroutine release_debris(gm, p, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: tprev, dd, fx, cap, fxg

  if (.not. allocated(dbr%rel)) return          ! この run で発火済み
  if (gm%db_reltime > s%t) return
  if (s%it - gm%idt_geomorph > 0) then
    tprev = p%t0 + p%dt * (s%it - gm%idt_geomorph)
    if (gm%db_reltime <= tprev) return          ! 前回呼び出し以前に発火済み
  end if

  ! --- 発火: 帯内の崩壊深 > 0 のセルを流動化する(セル局所) ---
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      dd = dbr%rel(i,j)
      if (dd <= 0.0) cycle
      if (dd > s%sd(i,j)) then
        dd = s%sd(i,j)                          ! 可動層クランプ(dispose で報告)
        dbr%nrelclip = dbr%nrelclip + 1
        if (dd <= 0.0) cycle
      end if
      fx = dd / gm%poroi                        ! 固体分 (1−λ)・D
      s%hs(i,j) = s%hs(i,j) + fx
      s%z(i,j) = s%z(i,j) - dd
      s%sd(i,j) = s%sd(i,j) - dd
      if (s%gw_active) then
        ! 間隙水は地下水から出る(容量超過引き渡し。suspend と同じ整合)
        cap = s%sd(i,j) * g%sy0
        if (s%hg(i,j) > cap) then
          fxg = s%hg(i,j) - cap
          s%hg(i,j) = cap
          s%h(i,j) = s%h(i,j) + fxg
        end if
      else
        ! gwflow 無効: 飽和度 relsat の間隙水をシナリオ的に付与
        s%h(i,j) = s%h(i,j) + (1.0 - 1.0 / gm%poroi) * gm%db_relsat * dd
      end if
    end do
  end do

  deallocate(dbr%rel)                           ! 発火は1回だけ
end subroutine


!----------------------------------------------------------------------
! 8近傍への最急降下勾配 tanθ(下限 0。領域外・海近傍は対象外)
!----------------------------------------------------------------------
pure function slope8(g, s, i, j) result(tanth)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  real :: tanth
  integer :: k, in, jn
  real :: sl
  tanth = 0.0
  do k = 1, 8
    in = i + din(k)
    jn = j + djn(k)
    if (g%x(in,jn) <= 0) cycle
    if (g%sw(in,jn) > 0) cycle
    sl = (s%z(i,j) - s%z(in,jn)) / dbr%dist8(k)
    if (sl > tanth) tanth = sl
  end do
end function


!----------------------------------------------------------------------
! 流向の河床勾配 tanθ(Morpho2DH 式(6): sinθ = (u sinθx + v sinθy)/|V|)
!   θx, θy は時刻 n の z の中央差分(片側フォールバック。近傍が領域外・
!   海なら自セル値で代用 = 勾配 0 側に倒す)。流向が上り勾配なら負を返す
!   (江頭・芦田式の堆積側)。|V| = 0 は呼び出し側で除外済み
!----------------------------------------------------------------------
pure function slope_flow(g, s, i, j) result(tanth)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  real :: tanth
  real :: zl, zr, dl, sinthx, sinthy, sinth
  real, parameter :: smax = 0.999

  ! x 方向の河床勾配角 θx(下り正)。近傍マスク(sw)の読みは x 番兵
  ! ガードの内側で(.and. は短絡評価が保証されない — §12 の帯確保規則の系。
  ! -fcheck np=2 で実検出)
  zl = s%z(i,j); zr = s%z(i,j); dl = 0.0
  if (g%x(i-1,j) > 0) then
    if (g%sw(i-1,j) <= 0) then
      zl = s%z(i-1,j); dl = dl + g%dx
    end if
  end if
  if (g%x(i+1,j) > 0) then
    if (g%sw(i+1,j) <= 0) then
      zr = s%z(i+1,j); dl = dl + g%dx
    end if
  end if
  sinthx = 0.0
  if (dl > 0.0) sinthx = sin(atan((zl - zr) / dl))
  ! y 方向の河床勾配角 θy(下り正)
  zl = s%z(i,j); zr = s%z(i,j); dl = 0.0
  if (g%x(i,j-1) > 0) then
    if (g%sw(i,j-1) <= 0) then
      zl = s%z(i,j-1); dl = dl + g%dy
    end if
  end if
  if (g%x(i,j+1) > 0) then
    if (g%sw(i,j+1) <= 0) then
      zr = s%z(i,j+1); dl = dl + g%dy
    end if
  end if
  sinthy = 0.0
  if (dl > 0.0) sinthy = sin(atan((zl - zr) / dl))

  sinth = (s%u(i,j) * sinthx + s%v(i,j) * sinthy) / s%vv(i,j)
  sinth = max(-smax, min(smax, sinth))
  tanth = sinth / sqrt(1.0 - sinth**2)
end function


!----------------------------------------------------------------------
! 流速ベクトル方向の流動面勾配 tanθ(高橋・中川1991 式(26)):
!   tanθ = (u sinθ'x + v sinθ'y) / √(u²cos²θ'x + v²cos²θ'y)
!   θ' は流動面(z + h + hs)の傾斜角(中央差分・片側フォールバック。
!   近傍マスクの読みは x 番兵ガードのネスト内側 — §12/§28 の規約)。
!   |V| = 0 は呼び出し側で除外済み
!----------------------------------------------------------------------
pure function slope_flow_surf(g, s, i, j) result(tanth)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  real :: tanth
  real :: el, er, dl, thx, thy, sx_, cx_, sy_, cy_, den

  ! x 方向の流動面勾配角 θ'x(下り正)
  el = surf(s, i, j); er = el; dl = 0.0
  if (g%x(i-1,j) > 0) then
    if (g%sw(i-1,j) <= 0) then
      el = surf(s, i-1, j); dl = dl + g%dx
    end if
  end if
  if (g%x(i+1,j) > 0) then
    if (g%sw(i+1,j) <= 0) then
      er = surf(s, i+1, j); dl = dl + g%dx
    end if
  end if
  thx = 0.0
  if (dl > 0.0) thx = atan((el - er) / dl)
  ! y 方向の流動面勾配角 θ'y(下り正)
  el = surf(s, i, j); er = el; dl = 0.0
  if (g%x(i,j-1) > 0) then
    if (g%sw(i,j-1) <= 0) then
      el = surf(s, i, j-1); dl = dl + g%dy
    end if
  end if
  if (g%x(i,j+1) > 0) then
    if (g%sw(i,j+1) <= 0) then
      er = surf(s, i, j+1); dl = dl + g%dy
    end if
  end if
  thy = 0.0
  if (dl > 0.0) thy = atan((el - er) / dl)

  sx_ = sin(thx); cx_ = cos(thx)
  sy_ = sin(thy); cy_ = cos(thy)
  den = sqrt((s%u(i,j) * cx_)**2 + (s%v(i,j) * cy_)**2)
  tanth = 0.0
  if (den > 0.0) tanth = (s%u(i,j) * sx_ + s%v(i,j) * sy_) / den
end function


!----------------------------------------------------------------------
! 流動面標高(z + h + hs。hs の負値はクランプ)
!----------------------------------------------------------------------
pure function surf(s, i, j) result(e)
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  real :: e
  e = s%z(i,j) + s%h(i,j) + max(s%hs(i,j), 0.0)
end function


!----------------------------------------------------------------------
! 江頭の平衡濃度(平衡勾配式 tanθe = sC/(sC+1)・tanφ の逆関数。
! 石礫型 C∞ 式(高橋・中川1991 式(11)(13)の単一粒径形)と同形 —
! 独立導出の一致。上限 0.9C* は高橋側と共通。f_dbed=2, 3 が共用)
!----------------------------------------------------------------------
pure function ceq_egashira(gm, tanth) result(cinf)
  type(t_geomorph), intent(in) :: gm
  real, intent(in) :: tanth
  real :: cinf
  cinf = 0.0
  if (tanth <= 0.0) return
  if (tanth >= gm%db_tanphi) then
    cinf = db_cfrac * gm%db_cstar
  else
    cinf = min(tanth / (gm%sgrav * (gm%db_tanphi - tanth)), db_cfrac * gm%db_cstar)
  end if
end function


!----------------------------------------------------------------------
! 高橋型の平衡濃度 C∞(勾配領域で切替。ヘッダの【要文献照合】参照)
!----------------------------------------------------------------------
pure function ceq_debris(gm, tanth) result(cinf)
  type(t_geomorph), intent(in) :: gm
  real, intent(in) :: tanth
  real :: cinf
  real :: cinfd, cmax
  cinf = 0.0
  if (tanth <= db_tan2) return                  ! 掃流域: 堆積側に一本化
  cmax = db_cfrac * gm%db_cstar
  if (tanth >= gm%db_tanphi) then
    cinf = cmax
    return
  end if
  cinfd = tanth / (gm%sgrav * (gm%db_tanphi - tanth))   ! 石礫型(導出式)
  if (tanth > db_tan1) then
    cinf = min(cinfd, cmax)
  else
    cinf = min(db_immat * cinfd**2, cmax)               ! 未成熟
  end if
end function

end submodule
