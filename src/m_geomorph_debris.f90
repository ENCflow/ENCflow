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
  use m_parallel, only : par_stop, dcp
  use m_swflow_enc, only : m_swflow_enc_set_debris
  use m_fileio, only : fileio_read_matrix
  implicit none

  ! 勾配領域の閾値と係数(【要文献照合】高橋理論の慣用値。原式固定で
  ! namelist にしない — developer.md §19.8 の原則2)
  real, parameter :: db_tan1 = 0.138     ! 石礫型/未成熟の境界 tanθ
  real, parameter :: db_tan2 = 0.03      ! 未成熟/掃流の境界 tanθ
  real, parameter :: db_immat = 6.7      ! 未成熟領域の係数(C∞ = 6.7 C∞d²)
  real, parameter :: db_cfrac = 0.9      ! C∞ の上限係数(C∞ ≤ 0.9 C*)

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
    call par_stop("list_geomorph: db_phi が小さすぎます(tanφ > 0.138 が必要。" &
                  // "土砂の内部摩擦角は通常 30〜40 deg)")
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

  ! 抵抗則(実体は m_swflow_enc。パラメータをここで検証して渡す。
  ! 初期化順序: geomorph init は swflow init より前 — m_main 参照)
  select case (list%f_dbres)
    case (0)      ! マニングのみ(E-D の単独検証用)
      continue
    case (1)      ! クーロン+マニング合成(推奨)
      if (list%db_vstop <= 0.0) then
        call par_stop("list_geomorph: f_dbres=1 requires db_vstop > 0(降伏判定の閾値)")
      end if
    case (2)      ! 高橋ダイラタント(予約)
      call par_stop("list_geomorph: f_dbres=2(高橋ダイラタント)は未実装です" &
                    // "(係数の文献照合待ち — debris_plan.md §1)")
    case default
      call par_stop("list_geomorph: f_dbres must be 0(Manning) or 1(Coulomb+Manning)")
  end select
  gm%f_dbres = list%f_dbres
  call m_swflow_enc_set_debris(gm%f_dbres, gm%db_tanphi, gm%sgrav, gm%db_vstop)

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
      call par_stop("list_geomorph: db_relsat must be in [0, 1]")
    end if
    gm%f_release = 1
    gm%db_reltime = list%db_reltime
    gm%db_relsat = list%db_relsat
    call read_release(p, g, trim(list%fn_dbinit))
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
    call par_stop("list_geomorph: fn_dbinit の崩壊深に負値があります: "//fname)
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
  real :: tanth, cinf, cc, hm, fx, dzb, cap, fxg, hseq

  ! --- パス1: 交換量の計算(時刻 n の状態のみを読む) ---
  !$omp parallel do schedule(static) private(i, j, tanth, cinf, cc, hm, fx, hseq)
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
        ! 最急降下勾配(時刻 n の z。本プロセスは calc の先頭で適用)
        tanth = slope8(g, s, i, j)
        cinf = ceq_debris(gm, tanth)
        ! 混合体積濃度 C = hs/(h+hs)(希薄極限で hs/h に漸近)
        hm = s%h(i,j) + max(s%hs(i,j), 0.0)
        cc = 0.0
        if (s%hs(i,j) > 0.0) cc = s%hs(i,j) / hm
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
  !$omp parallel do schedule(static) private(i, j, fx, dzb, cap, fxg)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      fx = dbr%fx(i,j)
      if (fx == 0.0) cycle
      s%hs(i,j) = s%hs(i,j) + fx
      ! 共動更新(z と sd が同じ Δz で動く → 帯水層底 (z - sd) は不変)
      dzb = -fx * gm%morfac * gm%poroi
      s%z(i,j) = s%z(i,j) + dzb
      s%sd(i,j) = s%sd(i,j) + dzb
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
