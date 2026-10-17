!======================================================================
! m_geomorph の submodule: 掃流砂 Exner(f_fluvial)
!   親モジュールの型・定数・共有作業領域(flv/wrk)・require_work には
!   ホスト結合でアクセスする(単段参照。§13)。サブグリッド河道幅の
!   係数と開境界の面判定は m_swflow_enc から直接 use する
!   (protected 読み取り専用。STG では geomorph 自体が par_stop する
!   ため ENC 私有への依存で問題ない)
!======================================================================
submodule(m_geomorph) m_geomorph_fluvial
  use m_parallel, only : par_info, par_stop, dcp, par_halo_cell
  use m_swflow_enc, only : chn, bcs, bc_open_face
  use m_util, only : rtoa
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_fluvial(gm, p, g, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_geomorph), intent(in) :: list
  real :: lpx, lpy, ldx, ldy, dr
  real :: d50                          ! 既定適用後の有効値(§62)

  ! --- パラメータ検証 ---
  d50 = gm_param("fluv_d50", list%fluv_d50, 0.01, " m")   ! 砂礫床の中庸(§62)
  if (d50 <= 0.0) call par_stop("list_geomorph: f_fluvial requires fluv_d50 > 0")
  if (list%fluv_tausc <= 0.0) call par_stop("list_geomorph: fluv_tausc must be > 0")
  if (list%fluv_dzmax <= 0.0) call par_stop("list_geomorph: fluv_dzmax must be > 0")
  if (list%fluv_diagratio < 0.0 .or. list%fluv_diagratio > 1.0) then
    call par_stop("list_geomorph: fluv_diagratio must be in [0,1]")
  end if
  if (list%f_qbform < 1 .or. list%f_qbform > 2) then
    call par_stop("list_geomorph: f_qbform must be 1(Ashida-Michiue) or 2(MPM)")
  end if

  if (list%fluv_bcfeed < 0 .or. list%fluv_bcfeed > 1) then
    call par_stop("list_geomorph: fluv_bcfeed must be 0(no feed) or 1(equilibrium feed)")
  end if

  gm%f_qbform = list%f_qbform
  gm%d50 = d50
  gm%tausc = list%fluv_tausc
  gm%dzmax = list%fluv_dzmax
  gm%f_bcfeed = list%fluv_bcfeed

  ! --- 有効掃流力の分離と流砂方向補正(§84.3) ---
  if (list%fluv_taufac <= 0.0 .or. list%fluv_taufac > 1.0) then
    call par_stop("list_geomorph: fluv_taufac must be in (0,1]")
  end if
  gm%flv%taufac = list%fluv_taufac
  if (list%fluv_slope < 0 .or. list%fluv_slope > 1) then
    call par_stop("list_geomorph: fluv_slope must be 0 or 1")
  end if
  if (list%f_secflow < 0 .or. list%f_secflow > 1) then
    call par_stop("list_geomorph: f_secflow must be 0(none) or 1(equilibrium)")
  end if
  gm%flv%f_slope = (list%fluv_slope > 0)
  gm%flv%f_sec = (list%f_secflow > 0)
  gm%flv%f_dir = (gm%flv%f_slope .or. gm%flv%f_sec)
  if (gm%flv%f_slope) then
    ! 式固有の係数だが文献照合が済むまで既定は置かない(明示指定を要求。§84.3)
    if (list%fluv_mus <= 0.0 .or. list%fluv_muk <= 0.0) then
      call par_stop("list_geomorph: fluv_slope=1 requires fluv_mus > 0 and fluv_muk > 0 " &
                    // "(static/kinetic friction coefficients of the Hasegawa-type slope term)")
    end if
    gm%flv%gcoef = 1.0 / sqrt(list%fluv_mus * list%fluv_muk)
    call par_info("geomorph: bed-slope direction term on (mus = " // rtoa(list%fluv_mus) &
                  // ", muk = " // rtoa(list%fluv_muk) // ")")
  end if
  if (gm%flv%f_sec) then
    if (list%sec_nstar <= 0.0) then
      call par_stop("list_geomorph: f_secflow=1 requires sec_nstar > 0 " &
                    // "(coefficient of the near-bed transverse velocity ratio r = N* h kappa)")
    end if
    if (list%sec_rmax <= 0.0) call par_stop("list_geomorph: sec_rmax must be > 0")
    if (list%sec_vmin < 0.0) call par_stop("list_geomorph: sec_vmin must be >= 0")
    gm%flv%nstar = list%sec_nstar
    gm%flv%rmax = list%sec_rmax
    gm%flv%vmin = list%sec_vmin
    call par_info("geomorph: equilibrium secondary-flow direction term on (N* = " &
                  // rtoa(list%sec_nstar) // ", rmax = " // rtoa(list%sec_rmax) &
                  // ", vmin = " // rtoa(list%sec_vmin) // " m/s)")
  end if

  ! --- 8近傍の通過幅と方向余弦(m_gwflow_lateral と同一の配分則) ---
  dr = sqrt(g%dx**2 + g%dy**2)
  if (g%dy > g%dx) then
    lpy = 1 - (g%dx / g%dy)**2 * list%fluv_diagratio
    ldy = list%fluv_diagratio / 2 * (g%dx / g%dy)**2
    lpx = 1 - list%fluv_diagratio
    ldx = list%fluv_diagratio / 2
  else
    lpy = 1 - list%fluv_diagratio
    ldy = list%fluv_diagratio / 2
    lpx = 1 - (g%dy / g%dx)**2 * list%fluv_diagratio
    ldx = list%fluv_diagratio / 2 * (g%dy / g%dx)**2
  end if
  ! 通過幅(k=1: 斜め, k=2: y法線, k=3: 斜め, k=4: x法線。k=5..8 は
  ! 対向方位で同幅。k>=5 は開境界面の書き手が使う)
  gm%flv%wl(1) = sqrt((ldy * g%dy)**2 + (ldx * g%dx)**2)
  gm%flv%wl(2) = lpx * g%dx
  gm%flv%wl(3) = gm%flv%wl(1)
  gm%flv%wl(4) = lpy * g%dy
  gm%flv%wl(5) = gm%flv%wl(4)
  gm%flv%wl(6) = gm%flv%wl(3)
  gm%flv%wl(7) = gm%flv%wl(2)
  gm%flv%wl(8) = gm%flv%wl(1)
  ! k軸方向の近傍セル中心間距離の逆数(河床勾配項の直接差分用)
  gm%flv%rdist(1) = 1.0 / dr;  gm%flv%rdist(2) = 1.0 / g%dy
  gm%flv%rdist(3) = 1.0 / dr;  gm%flv%rdist(4) = 1.0 / g%dx
  gm%flv%rdist(5:8) = gm%flv%rdist(4:1:-1)
  ! k軸方向(中心→近傍)の単位ベクトル
  gm%flv%ex(1) = -g%dx / dr;  gm%flv%ey(1) = -g%dy / dr
  gm%flv%ex(2) = 0.0;         gm%flv%ey(2) = -1.0
  gm%flv%ex(3) = g%dx / dr;   gm%flv%ey(3) = -g%dy / dr
  gm%flv%ex(4) = -1.0;        gm%flv%ey(4) = 0.0
  gm%flv%ex(5) = 1.0;         gm%flv%ey(5) = 0.0
  gm%flv%ex(6) = -g%dx / dr;  gm%flv%ey(6) = g%dy / dr
  gm%flv%ex(7) = 0.0;         gm%flv%ey(7) = 1.0
  gm%flv%ex(8) = g%dx / dr;   gm%flv%ey(8) = g%dy / dr

  ! 流砂量の次元化係数(無次元流砂量 → m2/s)
  gm%flv%qbcoef = sqrt(gm%sgrav * p%gg * gm%d50**3)

  call require_work(gm, g)
  ! 供給量制限係数(帯±ハロ。1 = 制限なし。自帯以外は交換で埋まる)
  allocate(gm%flv%fdon(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 1.0)
  ! 二次流の横断流速比(帯±ハロ。有効時のみ)
  if (gm%flv%f_sec) allocate(gm%flv%rsec(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
end subroutine


!----------------------------------------------------------------------
module subroutine calc_fluvial(gm, p, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt
  real :: gq, ue, vve, hhe, rne, taus, qbs, qb, sdup, dze, winvd
  real :: dirp, ubar, vbar, dxv, dyv, re, gam
  real :: afx, tsce
  integer :: nclip, nfix
  logical :: okc, okbank

  nclip = 0
  nfix = 0

  ! --- ステップ頭のハロ交換(m_gwflow_lateral と同じ「冒頭に置く」理由) ---
  ! 界面エッジの冗長計算(ハロ行 je+1 の書き手)が読む u, v, vv, h は
  ! swflow・gwflow が帯のみを更新するため、ステップ頭交換のままでは
  ! 前ステップの値に古びている。ここで交換しないと隣接ランクと異なる
  ! 入力から同一エッジを計算し、反対称性(=土砂体積保存)が壊れる
  ! (np=2 の保存則検定で実検出したバグ)。z, sd のハロは本モジュール
  ! calc 末尾の交換で維持されているため不要
  call par_halo_cell(s%h)
  call par_halo_cell(s%u)
  call par_halo_cell(s%v)
  call par_halo_cell(s%vv)

  ! --- 平衡二次流の横断流速比 r = N* h κ(自帯で評価 → ハロ交換。§84.3) ---
  if (gm%flv%f_sec) then
    call eval_secflow(gm, p, g, s)
    call par_halo_cell(gm%flv%rsec)
  end if

  ! --- ループ1: エッジの掃流砂フラックス(各成分の書き手は一意) ---
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) reduction(+: nclip, nfix) &
  !$omp   private(i, j, k, in, jn, okc, okbank, gq, ue, vve, hhe, rne, taus, qbs, qb, &
  !$omp           sdup, dze, winvd, dirp, ubar, vbar, dxv, dyv, re, gam, afx, tsce)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        ! 乾湿・流向は動的なので、条件を満たさない場合も必ず 0 を代入する
        gq = 0.0
        ! 堤防(仮想壁面)エッジ = 河道—非河道の境界では掃流砂を運ばない
        ! (掃流砂は河道内に閉じる。越流時の土砂輸送は浮遊砂(移流が
        ! 壁を含む実フラックス mn1 を使う)が担う。§17 の壁は水理側で
        ! 動的(越流)だが、河床材料の掃流は堤防を越えないとする)
        if (okc .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            ! 堤防エッジ判定は近傍が有効セルと確定してから行う
            ! (rw の確保範囲は x と違い番兵なし。x 番兵ガードより先に
            ! rw(in,jn) を読むと i=0/nx+1 で範囲外 — -fcheck np=2 で実検出)
            okbank = .true.
            if (g%bank_active) then
              okbank = ((g%rw(i,j) > 0) .eqv. (g%rw(in,jn) > 0))
            end if
            ! エッジ水理量(両セル平均)と法線流速
            vve = (s%vv(i,j) + s%vv(in,jn)) / 2
            hhe = (s%h(i,j) + s%h(in,jn)) / 2
            if (okbank .and. vve > 0.0 .and. hhe > p%dd) then
              ue = (s%u(i,j) + s%u(in,jn)) / 2 * gm%flv%ex(k) &
                 + (s%v(i,j) + s%v(in,jn)) / 2 * gm%flv%ey(k)
              hhe = max(hhe, p%dv)           ! 極浅水深での τ* 発散を防ぐ
              rne = (g%rn(i,j) + g%rn(in,jn)) / 2
              ! 無次元掃流力(マニング閉じ。g は分子分母で相殺)。taufac は
              ! 有効掃流力の比(1 = 分離なし。1.0 の乗算は厳密に不変)
              taus = gm%flv%taufac * rne**2 * vve**2 / (gm%sgrav * gm%d50 * hhe**(1.0/3.0))
              if (taus > gm%tausc) then
                ! 流砂方向の射影 dirp = (q⃗_b/q_b)·ê_k。補正なしは水深平均流向
                ! ue/vve(|dirp| <= 1)。補正ありは q⃗_b/q_b = t̂ + r n̂ − γ∇z
                ! (§84.3。t̂ = (ū, v̄)/vve、n̂ = (−v̄, ū)/vve = 左法線、
                ! r = 両セル平均の rsec、γ = √(τ*c/(μs μk τ*))、∇z は両セルの
                ! 中央差分勾配の平均)。水の法線流速がゼロのエッジでも横断
                ! 流砂が通るため、入口条件は補正後の dirp で判定する
                if (gm%flv%f_dir) then
                  ubar = (s%u(i,j) + s%u(in,jn)) / 2
                  vbar = (s%v(i,j) + s%v(in,jn)) / 2
                  dxv = ubar / vve
                  dyv = vbar / vve
                  if (gm%flv%f_sec) then
                    re = (gm%flv%rsec(i,j) + gm%flv%rsec(in,jn)) / 2
                    dxv = dxv - re * vbar / vve
                    dyv = dyv + re * ubar / vve
                  end if
                  dirp = dxv * gm%flv%ex(k) + dyv * gm%flv%ey(k)
                  if (gm%flv%f_slope) then
                    ! 射影に効くのは ∇z のリンク方向成分だけなので、エッジをまたぐ
                    ! 直接差分 (z_n − z_c)/d_k で評価する(§84.3 の改訂: 中央差分は
                    ! 2 セル周期の市松モードを見ない = 減衰せず、長時間計算で河床に
                    ! 市松が育った実検出。直接差分は市松を拡散で抑える)
                    gam = gm%flv%gcoef * sqrt(gm%tausc / taus)
                    dirp = dirp - gam * (s%z(in,jn) - s%z(i,j)) * gm%flv%rdist(k)
                  end if
                else
                  dirp = ue / vve
                end if
                if (dirp /= 0.0) then
                  ! 平衡流砂量(無次元)
                  if (gm%f_qbform == 1) then       ! 芦田・道上
                    qbs = 17.0 * taus**1.5 * (1.0 - gm%tausc / taus) &
                                           * (1.0 - sqrt(gm%tausc / taus))
                  else                             ! MPM
                    qbs = 8.0 * (taus - gm%tausc)**1.5
                  end if
                  qb = qbs * gm%flv%qbcoef            ! 固体体積の単位幅流砂量 (m2/s)
                  ! 方向射影 × 通過幅でエッジ流量に
                  gq = qb * dirp * gm%flv%wl(k)
                  ! 河岸面の遮断(§84.2): 掃流砂は河床面を転がる。
                  !   (R1) 風上(供給)セルは湿潤でなければ供給しない(乾いた
                  !        セルの τ* は両セル平均の見かけで、実体がない)
                  !   (R2) 受け手の地盤が供給セルの水面以上なら運ばない(土砂は
                  !        水面より上へ登れない = そのエッジは河岸面であり、
                  !        河岸面の交換は側岸侵食 f_berode の担当)
                  if (gq > 0.0) then
                    if (s%h(i,j) <= p%dd .or. s%z(in,jn) >= s%z(i,j) + s%h(i,j)) gq = 0.0
                  else
                    if (s%h(in,jn) <= p%dd .or. s%z(i,j) >= s%z(in,jn) + s%h(in,jn)) gq = 0.0
                  end if
                  ! 定着(§84.6): 供給(風上)側セルの定着度 a で限界掃流力を
                  ! τ*c (1 + c_τ a) に上げ、閾値判定と流砂量式の両方に効かせる
                  ! (受け手側の a は見ない = 定着面への堆積は妨げない。a = 0 の
                  ! セルは分岐に入らず厳密に不変)
                  if (gm%f_fixation > 0 .and. gq /= 0.0) then
                    if (gq > 0.0) then
                      afx = s%fx(i,j)
                    else
                      afx = s%fx(in,jn)
                    end if
                    if (afx > 0.0) then
                      tsce = gm%tausc * (1.0 + gm%fix%ctau * afx)
                      if (taus <= tsce) then
                        gq = 0.0
                      else
                        gq = gq * (qbs_form(gm%f_qbform, taus, tsce) / qbs)
                      end if
                      nfix = nfix + 1
                    end if
                  end if
                  ! 通過幅係数(水と同じ開口・幅キャップ。無効時は乗算なし)。
                  ! 動的振り替えの表 fwd(§68.14)も水と同じく乗じる: geomorph は
                  ! swflow の後に走り、fwd はこのステップの頭で作られて連続式が
                  ! 使った表のまま(次ステップ頭で作り直される)
                  if (chn%have_frw) gq = gq * chn%frw(k, i+die(k), j+dje(k))
                  if (chn%have_fwd) gq = gq * chn%fwd(k, i+die(k), j+dje(k))
                  ! 可動層クランプ: 供給側(風上)セルの土層厚を超える
                  ! 浸食をこのエッジ単独で起こさない(複数エッジの同時
                  ! 流出による僅かな超過はループ2の床クリップが受ける)。
                  ! 河道幅有効時は供給側の河道底面積あたりに換算(winvd)
                  if (gq > 0.0) then
                    sdup = s%sd(i,j)
                  else
                    sdup = s%sd(in,jn)
                  end if
                  winvd = 1.0
                  if (chn%have_width) then
                    if (gq > 0.0) then
                      winvd = 1.0 / chn%wfrac(i,j)
                    else
                      winvd = 1.0 / chn%wfrac(in,jn)
                    end if
                  end if
                  dze = abs(gq) * dts * gm%wrk%ainv * winvd * gm%poroi
                  if (sdup <= 0.0) then
                    gq = 0.0                       ! 岩盤露出(sd <= 0。丸めの負値も)= 供給なし
                    dze = 0.0
                  else if (dze > sdup) then
                    gq = gq * (sdup / dze)
                    dze = sdup
                  end if
                  ! 変動上限ガード(地形波の CFL 相当。morfac を上げた
                  ! ときの暴走防止。クリップは流量段階=保存則は保たれる)
                  if (dze > gm%dzmax) then
                    gq = gq * (gm%dzmax / dze)
                    nclip = nclip + 1
                  end if
                end if
              end if
            end if
          end if
        end if
        gm%wrk%q(k, i+die(k), j+dje(k)) = gq
      end do

      ! --- 開境界面の掃流フラックス(境界土砂供給・流出の第1段) ---
      ! 面に接する唯一の有効セルが全8方位を検査して書く(k>=5 の面
      ! スロットの所有者は域外に居ないため、内側セルが代わりに書く。
      ! 単一書き手は保たれる)。水理量は内側セルの一方側値、流向は
      ! セル流速の面法線射影。ue > 0(流出)は常に容量輸送(河床低下波が
      ! 域外へ抜ける)、ue < 0(流入)は f_bcfeed=1 のとき容量供給
      ! (平衡給砂。上流端の河床が維持される)。境界面の通過幅補正 frw は
      ! 未適用(§18 制約(5) の辺開口と同じ扱い)
      if (bcs%have_open_bc .and. okc) then
        do k = 1, 8
          in = i + din(k)
          jn = j + djn(k)
          if (g%x(in,jn) > 0) cycle
          if (.not. bc_open_face(in, jn)) cycle
          ! 開面は毎ステップ必ず代入する(乾湿・流向は動的)
          gq = 0.0
          vve = s%vv(i,j)
          hhe = s%h(i,j)
          if (vve > 0.0 .and. hhe > p%dd) then
            ue = s%u(i,j) * gm%flv%ex(k) + s%v(i,j) * gm%flv%ey(k)   ! 正 = 域外へ
            if (ue > 0.0 .or. gm%f_bcfeed > 0) then
              hhe = max(hhe, p%dv)
              rne = g%rn(i,j)
              taus = gm%flv%taufac * rne**2 * vve**2 / (gm%sgrav * gm%d50 * hhe**(1.0/3.0))
              if (taus > gm%tausc) then
                if (gm%f_qbform == 1) then       ! 芦田・道上
                  qbs = 17.0 * taus**1.5 * (1.0 - gm%tausc / taus) &
                                         * (1.0 - sqrt(gm%tausc / taus))
                else                             ! MPM
                  qbs = 8.0 * (taus - gm%tausc)**1.5
                end if
                qb = qbs * gm%flv%qbcoef
                gq = qb * (ue / vve) * gm%flv%wl(k)
                ! 定着(§84.6): 域外への流出は自セルが供給側(流入の給砂は不変)
                if (gm%f_fixation > 0 .and. gq > 0.0) then
                  afx = s%fx(i,j)
                  if (afx > 0.0) then
                    tsce = gm%tausc * (1.0 + gm%fix%ctau * afx)
                    if (taus <= tsce) then
                      gq = 0.0
                    else
                      gq = gq * (qbs_form(gm%f_qbform, taus, tsce) / qbs)
                    end if
                    nfix = nfix + 1
                  end if
                end if
                winvd = 1.0
                if (chn%have_width) winvd = 1.0 / chn%wfrac(i,j)
                dze = abs(gq) * dts * gm%wrk%ainv * winvd * gm%poroi
                if (gq > 0.0) then
                  ! 流出: 供給側 = 自セルの可動層クランプ
                  if (dze > s%sd(i,j)) then
                    gq = gq * (s%sd(i,j) / dze)
                    dze = s%sd(i,j)
                  end if
                end if
                ! 変動上限ガード(流出・流入とも)
                if (dze > gm%dzmax) then
                  gq = gq * (gm%dzmax / dze)
                  nclip = nclip + 1
                end if
              end if
            end if
          end if
          ! 格納は所有者正準の向き(sign_e を乗じて格納すると、ループ2の
          ! sign_e(k) 倍の読み出しで gq = 域外向き正 が復元される)
          gm%wrk%q(ke(k), i+die(k), j+dje(k)) = sign_e(k) * gq
        end do
      end if
    end do
  end do
  !$omp end parallel do

  ! --- 側岸侵食(§84.4): 河岸面エッジに河岸→脚部の流砂を加算する ---
  if (gm%f_berode > 0) call bank_edge_pass(gm, p, g, s, dts)

  ! --- 供給量制限 → 発散 → z と sd の共動更新(共有の適用経路) ---
  call apply_edge_flux(gm, g, s, dts)

  ! ガード発動の累計(dispose で報告。nlim・vleak は apply_edge_flux が加算)
  gm%flv%nclip = gm%flv%nclip + nclip
  gm%fix%nfix = gm%fix%nfix + nfix

end subroutine


!----------------------------------------------------------------------
! 共有エッジ流量 wrk%q(固体体積の流量。k=1..4 の所有成分+開境界面の
! k>=5 スロット)を河床に適用する: 供給量制限(ループ 1.5)→ 発散(ループ 2)
! → z と sd の共動更新+地下水容量の整合。fluvial と bank(崩落)が共用
! (§84.1)。書き手の契約: 呼び出し側は対象セルの 4 成分と、x<=0 の近傍に
! 向く面スロットを 0 を含めて必ず上書きしてから呼ぶ
!----------------------------------------------------------------------
module subroutine apply_edge_flux(gm, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn
  real :: dv8, dz, cap, fx, winv, qk, fd, vout, vcap
  integer :: nlim
  real :: vleak

  nlim = 0
  vleak = 0.0

  ! --- ループ1.5: 供給量制限(セルの総流出要求 > 可動層 sd なら縮小) ---
  ! エッジ別の可動層クランプは「このエッジ単独」の上限なので、複数エッジが
  ! 同時に流出すると合計が sd を超え、ループ2の岩盤床クリップ(保存則の
  ! 破れ = vleak)に落ちていた。ここで風上セルごとに総流出要求を集計し、
  ! 超過分を縮小率 fdon(0〜1)にして「そのセルを風上とする全エッジ」に
  ! 乗じる(bedslide のドナー律速と同型)。評価は自帯のみ、ハロ交換で
  ! 隣接ランクの帯界面セルの値を受け取り、ループ2の両側が同じ fdon を
  ! 読む = 反対称性(土砂体積保存)は保たれる。制限が発動しないセルは
  ! fdon = 1.0 の乗算で結果は厳密に不変(発動なしの既存ケースはビット一致)
  !$omp parallel do schedule(static) reduction(+: nlim) private(i, j, k, qk, vout, vcap, winv)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      gm%flv%fdon(i,j) = 1.0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      vout = 0.0
      do k = 1, 8
        qk = sign_e(k) * gm%wrk%q(ke(k), i+die(k), j+dje(k))   ! 正 = 流出
        if (qk > 0.0) vout = vout + qk
      end do
      if (vout > 0.0) then
        winv = 1.0
        if (chn%have_width) winv = 1.0 / chn%wfrac(i,j)
        ! 供給可能量を流量に換算: sd = vcap * dts * ainv * winv * poroi
        ! (sd の丸めの負値は 0 と見なす = 供給なし)
        vcap = max(s%sd(i,j), 0.0) / (dts * gm%wrk%ainv * winv * gm%poroi)
        if (vout > vcap) then
          gm%flv%fdon(i,j) = vcap / vout         ! sd = 0(岩盤)なら 0
          nlim = nlim + 1
        end if
      end if
    end do
  end do
  !$omp end parallel do
  call par_halo_cell(gm%flv%fdon)

  ! --- ループ2: 発散 → z と sd の共動更新 + 地下水容量の整合 ---
  !   各エッジ流量に風上セルの fdon を乗じて集計する(風上が域外 = 開境界
  !   からの流入は縮小なし。近傍の fdon 読みは x 番兵ガードの内側で — §12)
  !   (集計式は従来の dv8 + sign_e(k)*(…) の形を保つ: fdon = 1 のとき
  !   q*1.0 = q が厳密なので、-Ofast の積和縮約も従来と同じになり
  !   ビット一致が保たれる — 縮小率を加算後に掛ける形に書き換えると
  !   縮約の形が変わり最終桁が動く(実検出))
  !$omp parallel do schedule(static) reduction(+: vleak) &
  !$omp   private(i, j, k, in, jn, dv8, dz, cap, fx, winv, qk, fd)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      dv8 = 0.0
      do k = 1, 8
        qk = gm%wrk%q(ke(k), i+die(k), j+dje(k))
        fd = 1.0
        if (sign_e(k) * qk > 0.0) then
          fd = gm%flv%fdon(i,j)
        else if (sign_e(k) * qk < 0.0) then
          in = i + din(k)
          jn = j + djn(k)
          if (g%x(in,jn) > 0) fd = gm%flv%fdon(in,jn)
        end if
        dv8 = dv8 + sign_e(k) * (qk * fd)
      end do
      ! 河道幅有効時は体積発散を河道底面積 wfrac*dx*dy で厚さに換算
      ! (Δz の河道底集中。無効時は 1.0 の乗算で厳密に不変)
      winv = 1.0
      if (chn%have_width) winv = 1.0 / chn%wfrac(i,j)
      dz = -dv8 * dts * gm%wrk%ainv * winv * gm%poroi
      ! 岩盤床クリップ(供給量制限の後は丸め誤差分しか残らないはずの
      ! 最終防衛。失った体積は vleak に計上して黙らない)
      if (dz < -s%sd(i,j)) then
        vleak = vleak + (-dz - s%sd(i,j)) / gm%poroi / gm%wrk%ainv / winv
        dz = -s%sd(i,j)
      end if
      ! 共動更新(z と sd が同じ Δz で動く → 帯水層底 (z - sd) は不変)
      s%z(i,j) = s%z(i,j) + dz
      s%sd(i,j) = s%sd(i,j) + dz
      ! 浸食で地下水容量が現在の貯留を下回ったら、超過分を地表水へ渡す
      ! (飽和表土が削られ、含まれていた水が地表に出る。反対称適用)
      if (s%gw_active) then
        cap = s%sd(i,j) * g%sy0
        if (s%hg(i,j) > cap) then
          fx = s%hg(i,j) - cap
          s%hg(i,j) = cap
          s%h(i,j) = s%h(i,j) + fx
        end if
      end if
    end do
  end do
  !$omp end parallel do

  gm%flv%nlim = gm%flv%nlim + nlim
  gm%flv%vleak = gm%flv%vleak + vleak

end subroutine


!----------------------------------------------------------------------
! 平衡流砂量(無次元)。ループ 1 の式と同じ形(定着の τ*c,eff で再評価する用)
!----------------------------------------------------------------------
pure function qbs_form(form, taus, tsc) result(qbs)
  integer, intent(in) :: form
  real, intent(in) :: taus, tsc
  real :: qbs
  if (form == 1) then                ! 芦田・道上
    qbs = 17.0 * taus**1.5 * (1.0 - tsc / taus) * (1.0 - sqrt(tsc / taus))
  else                               ! MPM
    qbs = 8.0 * (taus - tsc)**1.5
  end if
end function

!----------------------------------------------------------------------
! 平衡二次流の河床近傍横断流速比 r = N* h κ(§84.3)
!   κ = n̂·[(t̂·∇)t̂] = (u² v_x − v² u_y + u v (v_y − u_x)) / |V|³ は水深平均
!   流速場の幾何学的な流線曲率(左曲がり正。κ n̂ は曲率中心向きなので
!   r n̂ は常に湾曲内側 = 座標系の向きによらない)。
!   流速の勾配は 4 近傍がすべて有効な湿潤セル(x>0, sw<=0, h>dd)のときだけ
!   中央差分で評価し、それ以外(河岸沿い・開境界列・水際)は r = 0 とする。
!   片側差分や乾いた近傍(u=0)を使うと河岸沿い・境界列に偽の曲率が立ち、
!   横断流砂の発散で穴が育つ(実検出: 直線水路の自由流出列で 4.8 m)。
!   評価は湿潤(h > dd)かつ |V| > vmin のセルのみ、|r| <= rmax で打ち切る。
!   書き: 自帯 js..je の rsec(全セル。不活性は 0)。ハロ交換は呼び出し側
!----------------------------------------------------------------------
subroutine eval_secflow(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: i, j
  real :: ux, uy, vx, vy, kap, r

  !$omp parallel do schedule(static) private(i, j, ux, uy, vx, vy, kap, r)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      r = 0.0
      if (g%x(i,j) > 0) then
        if (g%sw(i,j) <= 0 .and. s%h(i,j) > p%dd .and. s%vv(i,j) > gm%flv%vmin) then
          if (wet4(p, g, s, i, j)) then
            ux = (s%u(i+1,j) - s%u(i-1,j)) / (2 * g%dx)
            vx = (s%v(i+1,j) - s%v(i-1,j)) / (2 * g%dx)
            uy = (s%u(i,j+1) - s%u(i,j-1)) / (2 * g%dy)
            vy = (s%v(i,j+1) - s%v(i,j-1)) / (2 * g%dy)
            kap = (s%u(i,j)**2 * vx - s%v(i,j)**2 * uy &
                   + s%u(i,j) * s%v(i,j) * (vy - ux)) / s%vv(i,j)**3
            r = gm%flv%nstar * s%h(i,j) * kap
            r = max(-gm%flv%rmax, min(gm%flv%rmax, r))
          end if
        end if
      end if
      gm%flv%rsec(i,j) = r
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 4 近傍がすべて有効な湿潤セルか(近傍マスクの読みは x 番兵ガードの内側で)
!----------------------------------------------------------------------
pure function wet4(p, g, s, i, j) result(ok)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  logical :: ok
  integer :: k, in, jn
  ok = .true.
  do k = 2, 7, 5               ! k = 2 (j-1), 7 (j+1)
    in = i + din(k); jn = j + djn(k)
    if (g%x(in,jn) <= 0) then
      ok = .false.; return
    end if
    if (g%sw(in,jn) > 0 .or. s%h(in,jn) <= p%dd) then
      ok = .false.; return
    end if
  end do
  do k = 4, 5                  ! k = 4 (i-1), 5 (i+1)
    in = i + din(k); jn = j + djn(k)
    if (g%x(in,jn) <= 0) then
      ok = .false.; return
    end if
    if (g%sw(in,jn) > 0 .or. s%h(in,jn) <= p%dd) then
      ok = .false.; return
    end if
  end do
end function

end submodule
