!======================================================================
! m_geomorph の submodule: 側岸侵食(f_berode)と安息角崩落(f_repose)
!   蛇行発達への拡張の段 2(docs/meander_plan.md §3.3、developer.md §84.4)。
!   親モジュールの型・定数・共有作業領域(flv/wrk/bnk)・apply_edge_flux
!   にはホスト結合でアクセスする(単段参照。§13)。
!
!   側岸侵食(bank_edge_pass): calc_fluvial のループ 1 の後に呼ばれ、
!     河岸面エッジ = 湿潤セル w(h > dd)と、その水面 z_w + h_w 以上の地盤を
!     もつ隣接セル b(乾燥でも冠水でもよい)の間のエッジ(§84.2 で掃流砂を
!     遮断した面そのもの)に、河岸 b → 脚部 w の固体流量を共有スクラッチ
!     wrk%q に**加算**する。後退速度は超過掃流力型
!       E_b = K_b·max(τ*_w/τ*c,b − 1, 0)^m   [m/s]
!     (τ*_w は脚部セル w のセル値 = 近傍流速の代理。河岸面と河床面の
!     せん断応力の違いは K_b に吸収)。水没河岸高は min(z_b − z_w, h_w) = h_w
!     なので、エッジの固体流量は q = E_b·h_w·wl(k)/poroi。削った土砂は脚部
!     セルに堆積し(保存的)、以後の掃流砂が運ぶ。適用は apply_edge_flux
!     (供給量制限が b の可動層 sd に効く)。堤防エッジ(bank_active 時の
!     rw 不一致)は河岸侵食も遮断する。
!   安息角崩落(calc_repose): 隣接セル間の勾配 (z_c − z_n)/dist_k が
!     tanφ_r を超えた分の高さ差 excess について、1 更新に relax·excess/2/8
!     の高さ(8 方向同時の合計が relax·excess_max/2 を超えない = 行き過ぎ
!     なし)を高い側から低い側へ移す。乾湿を問わない(乾いた砂山・掘削面・
!     河岸脚部の崩落土砂)。1 更新 1 スイープ(崩落は地形時間で 1 セルずつ
!     伝播)。流量は独自の 2 ループで wrk%q に書き(全成分上書き、x<=0 の
!     近傍へ向く面スロットも 0 に)、apply_edge_flux で適用する。
!   どちらも 1 エッジ・1 更新の変動を fluv_dzmax で頭打ちにする(クリップは
!   流量段階 = 保存則は保たれる。発動数は dispose で報告)。
!======================================================================
submodule(m_geomorph) m_geomorph_bank
  use m_parallel, only : par_info, par_stop, dcp
  use m_util, only : rtoa
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_bank(gm, p, g, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_geomorph), intent(in) :: list
  real :: phi
  real, parameter :: deg = acos(-1.0) / 180.0

  if (gm%f_berode > 0) then
    ! 校正値だが文献の既定がないため明示指定を要求(§84.4)
    if (list%berode_kb <= 0.0) then
      call par_stop("list_geomorph: f_berode=1 requires berode_kb > 0 (bank erodibility, m/s)")
    end if
    if (list%berode_tausc <= 0.0) call par_stop("list_geomorph: berode_tausc must be > 0")
    if (list%berode_m <= 0.0) call par_stop("list_geomorph: berode_m must be > 0")
    gm%bnk%kb = list%berode_kb
    gm%bnk%tausc = list%berode_tausc
    gm%bnk%pm = list%berode_m
    call par_info("geomorph: bank erosion on (K_b = " // rtoa(list%berode_kb) &
                  // " m/s, tausc_b = " // rtoa(list%berode_tausc) &
                  // ", m = " // rtoa(list%berode_m) // ")")
    ! 崩落土塊による遮蔽(§84.17): 脚部の崖錐 ht が h_cover で河岸面を完全に遮蔽する
    if (list%berode_hcover < 0.0) call par_stop("list_geomorph: berode_hcover must be >= 0")
    if (list%berode_hcover > 0.0) then
      if (gm%f_rockfall <= 0 .or. list%rf_bank <= 0) then
        call par_stop("list_geomorph: berode_hcover > 0 requires f_rockfall=1 with rf_bank=1 (slump-block talus)")
      end if
      gm%bnk%hcover = list%berode_hcover
      call par_info("geomorph: bank erosion shielded by slump-block talus (h_cover = " &
                    // rtoa(list%berode_hcover) // " m)")
    end if
  end if

  if (gm%f_repose > 0) then
    ! 既定 30°(表層崩壊の安定解析の慣用値 slide_phi と同じ。§62)
    phi = gm_param("repose_phi", list%repose_phi, 30.0, " deg")
    if (phi <= 0.0 .or. phi >= 90.0) call par_stop("list_geomorph: repose_phi must be in (0,90) deg")
    if (list%repose_relax <= 0.0 .or. list%repose_relax > 1.0) then
      call par_stop("list_geomorph: repose_relax must be in (0,1]")
    end if
    gm%bnk%tanphi = tan(phi * deg)
    gm%bnk%relax = list%repose_relax
    ! fluvial なしでも動けるように、dzmax と共有スクラッチ・供給量制限係数を
    ! ここで整える(fluvial ありなら init_fluvial が済ませている)
    if (gm%dzmax <= 0.0) then
      if (list%fluv_dzmax <= 0.0) call par_stop("list_geomorph: fluv_dzmax must be > 0")
      gm%dzmax = list%fluv_dzmax
    end if
    call require_work(gm, g)
    if (.not. allocated(gm%flv%fdon)) then
      allocate(gm%flv%fdon(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 1.0)
    end if
  end if

  ! 近傍セル中心間距離(k=1: 斜め, 2: y 法線, 3: 斜め, 4: x 法線)とセル面積
  gm%bnk%dist(1) = sqrt(g%dx**2 + g%dy**2)
  gm%bnk%dist(2) = g%dy
  gm%bnk%dist(3) = gm%bnk%dist(1)
  gm%bnk%dist(4) = g%dx
  gm%bnk%area = g%dx * g%dy
end subroutine


!----------------------------------------------------------------------
! 側岸侵食のエッジパス(calc_fluvial のループ 1 の直後。wrk%q に加算)
!   書き手は所有者一意(k=1..4、帯界面は je+1 行の冗長計算)。読みは時刻 n の
!   h, u, v, vv, z(ハロは calc_fluvial 冒頭の交換で最新)
!----------------------------------------------------------------------
module subroutine bank_edge_pass(gm, p, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt, iw, jw, ib, jb, nbank, nbclip
  real :: sgn, hw, hhe, taus, tscb, eb, qs, dzb, vbank
  logical :: okc, okbank

  nbank = 0
  nbclip = 0
  vbank = 0.0
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) reduction(+: nbank, nbclip, vbank) &
  !$omp   private(i, j, k, in, jn, iw, jw, ib, jb, okc, okbank, sgn, hw, hhe, taus, tscb, eb, qs, dzb)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      if (.not. okc) cycle
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) cycle
        if (g%sw(in,jn) > 0) cycle
        ! 堤防(仮想壁面)エッジは河岸侵食も遮断(護岸・築堤の表現)
        okbank = .true.
        if (g%bank_active) okbank = ((g%rw(i,j) > 0) .eqv. (g%rw(in,jn) > 0))
        if (.not. okbank) cycle
        ! 河岸面の向き: 脚部 w(湿潤)と河岸 b(地盤 >= w の水面)
        if (s%h(i,j) > p%dd .and. s%z(in,jn) >= s%z(i,j) + s%h(i,j)) then
          iw = i;  jw = j;  ib = in; jb = jn
          sgn = -1.0                               ! b = 近傍 → 脚部 = 自セル(c→n 正なので負)
        else if (s%h(in,jn) > p%dd .and. s%z(i,j) >= s%z(in,jn) + s%h(in,jn)) then
          iw = in; jw = jn; ib = i;  jb = j
          sgn = 1.0                                ! b = 自セル → 脚部 = 近傍
        else
          cycle
        end if
        if (s%vv(iw,jw) <= 0.0) cycle
        ! 非侵食の河岸(可動層 sd <= 0 = 岩盤・非侵食の陸地)は後退しない。供給量制限
        ! (apply_edge_flux。fdon = 0)が流束を 0 にするので結果は同じだが、ここで
        ! 飛ばして台帳(nbank・nbclip・vbank)に「仮想の侵食」を数えない(§84.14)
        if (s%sd(ib,jb) <= 0.0) cycle
        hw = s%h(iw,jw)
        hhe = max(hw, p%dv)
        ! 脚部セルの無次元掃流力(calc_fluvial と同じマニング閉じ・有効掃流力比)
        taus = gm%flv%taufac * g%rn(iw,jw)**2 * s%vv(iw,jw)**2 &
               / (gm%sgrav * gm%d50 * hhe**(1.0/3.0))
        ! 崩落土塊による遮蔽(§84.17): 脚部の崖錐 ht の分だけ河岸面に届く掃流力を減らす
        ! (Asahi ら 2013 式 (27)〜(28) の K = 1 − A_chunk/(D_chunk B) の格子版)
        if (gm%bnk%hcover > 0.0) then
          taus = taus * max(1.0 - s%ht(iw,jw) / gm%bnk%hcover, 0.0)
        end if
        ! 定着(§84.6、§84.13): 河岸セル b の定着度で限界掃流力を τ*c,b (1 + c_τ,b a_b)
        ! に上げる(a = 0 なら乗算せず厳密に不変。c_τ,b は fix_ctau_bank、既定は c_τ)
        tscb = gm%bnk%tausc
        if (gm%f_fixation > 0) then
          if (s%fx(ib,jb) > 0.0) tscb = tscb * (1.0 + gm%fix%ctaub * s%fx(ib,jb))
        end if
        if (taus <= tscb) cycle
        eb = gm%bnk%kb * (taus / tscb - 1.0)**gm%bnk%pm   ! 後退速度 (m/s)
        qs = eb * hw * gm%flv%wl(k) / gm%poroi                    ! 固体流量 (m3/s)
        ! 1 エッジ・1 更新の河岸の低下量を dzmax で頭打ち(流量段階 = 保存則は保つ)
        dzb = qs * dts * gm%wrk%ainv * gm%poroi
        if (dzb > gm%dzmax) then
          qs = qs * (gm%dzmax / dzb)
          dzb = gm%dzmax
          nbclip = nbclip + 1
        end if
        gm%wrk%q(k, i+die(k), j+dje(k)) = gm%wrk%q(k, i+die(k), j+dje(k)) + sgn * qs
        nbank = nbank + 1
        if (j <= dcp%je) vbank = vbank + dzb * gm%bnk%area   ! 台帳は自帯の書き手だけ
      end do
    end do
  end do
  !$omp end parallel do
  gm%bnk%nbank = gm%bnk%nbank + nbank
  gm%bnk%nbclip = gm%bnk%nbclip + nbclip
  gm%bnk%vbank = gm%bnk%vbank + vbank
end subroutine


!----------------------------------------------------------------------
! 安息角崩落(独立の 2 ループ。z・sd のハロは呼び出し側が最新化済み)
!----------------------------------------------------------------------
module subroutine calc_repose(gm, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt, nrep, nrclip
  real :: gq, dzc, lim, excess, dzm, vrep, qfac
  logical :: okc, oks

  nrep = 0
  nrclip = 0
  vrep = 0.0
  ! 高さ差 → 固体流量の換算: 1 更新・1 エッジで relax·excess/2/8 の高さ
  qfac = gm%bnk%relax * 0.5 / 8.0 * gm%bnk%area / (dts * gm%poroi)
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) reduction(+: nrep, nrclip, vrep) &
  !$omp   private(i, j, k, in, jn, okc, oks, gq, dzc, lim, excess, dzm)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        gq = 0.0                                   ! 必ず上書き(書き手の契約)
        if (okc .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            dzc = s%z(i,j) - s%z(in,jn)
            lim = gm%bnk%tanphi * gm%bnk%dist(k)
            ! 高い側(供給側)が非侵食(sd <= 0)なら崩落しない。供給量制限が流束を
            ! 0 にするので結果は同じだが、台帳(nrep・nrclip・vrep)に数えない(§84.14)
            if (dzc > 0.0) then
              oks = (s%sd(i,j) > 0.0)
            else
              oks = (s%sd(in,jn) > 0.0)
            end if
            if (abs(dzc) > lim .and. oks) then
              excess = abs(dzc) - lim
              gq = sign(qfac * excess, dzc)        ! 高い側 → 低い側(c→n 正)
              dzm = qfac * excess * dts * gm%wrk%ainv * gm%poroi
              if (dzm > gm%dzmax) then
                gq = gq * (gm%dzmax / dzm)
                dzm = gm%dzmax
                nrclip = nrclip + 1
              end if
              nrep = nrep + 1
              if (j <= dcp%je) vrep = vrep + dzm * gm%bnk%area
            end if
          end if
        end if
        gm%wrk%q(k, i+die(k), j+dje(k)) = gq
      end do
      ! 域外(x<=0)に向く面スロットは 0(fluvial の開境界書き込みの残りを消す)
      do k = 5, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) gm%wrk%q(ke(k), i+die(k), j+dje(k)) = 0.0
      end do
    end do
  end do
  !$omp end parallel do
  gm%bnk%nrep = gm%bnk%nrep + nrep
  gm%bnk%nrclip = gm%bnk%nrclip + nrclip
  gm%bnk%vrep = gm%bnk%vrep + vrep

  call apply_edge_flux(gm, g, s, dts)
end subroutine

end submodule
