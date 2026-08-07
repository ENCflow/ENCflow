!======================================================================
! m_geomorph の submodule: 掃流砂 Exner(f_fluvial)
!   親モジュールの型・定数・共有作業領域(flv/wrk)・require_work には
!   ホスト結合でアクセスする(単段参照。§13)。サブグリッド河道幅の
!   係数と開境界の面判定は m_swflow_enc から直接 use する
!   (protected 読み取り専用。STG では geomorph 自体が par_stop する
!   ため ENC 私有への依存で問題ない)
!======================================================================
submodule(m_geomorph) m_geomorph_fluvial
  use m_parallel, only : par_stop, dcp, par_halo_cell
  use m_swflow_enc, only : have_width, have_frw, frw, wfrac, &
                           have_open_bc, bc_open_face
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_fluvial(gm, p, g, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_geomorph), intent(in) :: list
  real :: lpx, lpy, ldx, ldy, dr

  ! --- パラメータ検証 ---
  if (list%fluv_d50 <= 0.0) call par_stop("list_geomorph: f_fluvial requires fluv_d50 > 0")
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
  gm%d50 = list%fluv_d50
  gm%tausc = list%fluv_tausc
  gm%dzmax = list%fluv_dzmax
  gm%f_bcfeed = list%fluv_bcfeed

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
  flv%wl(1) = sqrt((ldy * g%dy)**2 + (ldx * g%dx)**2)
  flv%wl(2) = lpx * g%dx
  flv%wl(3) = flv%wl(1)
  flv%wl(4) = lpy * g%dy
  flv%wl(5) = flv%wl(4)
  flv%wl(6) = flv%wl(3)
  flv%wl(7) = flv%wl(2)
  flv%wl(8) = flv%wl(1)
  ! k軸方向(中心→近傍)の単位ベクトル
  flv%ex(1) = -g%dx / dr;  flv%ey(1) = -g%dy / dr
  flv%ex(2) = 0.0;         flv%ey(2) = -1.0
  flv%ex(3) = g%dx / dr;   flv%ey(3) = -g%dy / dr
  flv%ex(4) = -1.0;        flv%ey(4) = 0.0
  flv%ex(5) = 1.0;         flv%ey(5) = 0.0
  flv%ex(6) = -g%dx / dr;  flv%ey(6) = g%dy / dr
  flv%ex(7) = 0.0;         flv%ey(7) = 1.0
  flv%ex(8) = g%dx / dr;   flv%ey(8) = g%dy / dr

  ! 流砂量の次元化係数(無次元流砂量 → m2/s)
  flv%qbcoef = sqrt(gm%sgrav * p%gg * gm%d50**3)

  call require_work(g)
end subroutine


!----------------------------------------------------------------------
module subroutine calc_fluvial(gm, p, g, s, dts)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt
  real :: gq, ue, vve, hhe, rne, taus, qbs, qb, sdup, dze, winvd
  real :: dv8, dz, cap, fx, winv
  integer :: nclip
  real :: vleak
  logical :: okc, okbank

  nclip = 0
  vleak = 0.0

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

  ! --- ループ1: エッジの掃流砂フラックス(各成分の書き手は一意) ---
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) reduction(+: nclip) &
  !$omp   private(i, j, k, in, jn, okc, okbank, gq, ue, vve, hhe, rne, taus, qbs, qb, &
  !$omp           sdup, dze, winvd)
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
              ue = (s%u(i,j) + s%u(in,jn)) / 2 * flv%ex(k) &
                 + (s%v(i,j) + s%v(in,jn)) / 2 * flv%ey(k)
              if (ue /= 0.0) then
                hhe = max(hhe, p%dv)         ! 極浅水深での τ* 発散を防ぐ
                rne = (g%rn(i,j) + g%rn(in,jn)) / 2
                ! 無次元掃流力(マニング閉じ。g は分子分母で相殺)
                taus = rne**2 * vve**2 / (gm%sgrav * gm%d50 * hhe**(1.0/3.0))
                if (taus > gm%tausc) then
                  ! 平衡流砂量(無次元)
                  if (gm%f_qbform == 1) then       ! 芦田・道上
                    qbs = 17.0 * taus**1.5 * (1.0 - gm%tausc / taus) &
                                           * (1.0 - sqrt(gm%tausc / taus))
                  else                             ! MPM
                    qbs = 8.0 * (taus - gm%tausc)**1.5
                  end if
                  qb = qbs * flv%qbcoef            ! 固体体積の単位幅流砂量 (m2/s)
                  ! 流向射影(|ue|/vve <= 1)× 通過幅でエッジ流量に
                  gq = qb * (ue / vve) * flv%wl(k)
                  ! 通過幅係数(水と同じ開口・幅キャップ。無効時は乗算なし)
                  if (have_frw) gq = gq * frw(k, i+die(k), j+dje(k))
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
                  if (have_width) then
                    if (gq > 0.0) then
                      winvd = 1.0 / wfrac(i,j)
                    else
                      winvd = 1.0 / wfrac(in,jn)
                    end if
                  end if
                  dze = abs(gq) * dts * wrk%ainv * winvd * gm%poroi
                  if (dze > sdup) then
                    gq = gq * (sdup / dze)         ! sdup=0(岩盤)なら 0
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
        wrk%q(k, i+die(k), j+dje(k)) = gq
      end do

      ! --- 開境界面の掃流フラックス(境界土砂供給・流出の第1段) ---
      ! 面に接する唯一の有効セルが全8方位を検査して書く(k>=5 の面
      ! スロットの所有者は域外に居ないため、内側セルが代わりに書く。
      ! 単一書き手は保たれる)。水理量は内側セルの一方側値、流向は
      ! セル流速の面法線射影。ue > 0(流出)は常に容量輸送(河床低下波が
      ! 域外へ抜ける)、ue < 0(流入)は f_bcfeed=1 のとき容量供給
      ! (平衡給砂。上流端の河床が維持される)。境界面の通過幅補正 frw は
      ! 未適用(§18 制約(5) の辺開口と同じ扱い)
      if (have_open_bc .and. okc) then
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
            ue = s%u(i,j) * flv%ex(k) + s%v(i,j) * flv%ey(k)   ! 正 = 域外へ
            if (ue > 0.0 .or. gm%f_bcfeed > 0) then
              hhe = max(hhe, p%dv)
              rne = g%rn(i,j)
              taus = rne**2 * vve**2 / (gm%sgrav * gm%d50 * hhe**(1.0/3.0))
              if (taus > gm%tausc) then
                if (gm%f_qbform == 1) then       ! 芦田・道上
                  qbs = 17.0 * taus**1.5 * (1.0 - gm%tausc / taus) &
                                         * (1.0 - sqrt(gm%tausc / taus))
                else                             ! MPM
                  qbs = 8.0 * (taus - gm%tausc)**1.5
                end if
                qb = qbs * flv%qbcoef
                gq = qb * (ue / vve) * flv%wl(k)
                winvd = 1.0
                if (have_width) winvd = 1.0 / wfrac(i,j)
                dze = abs(gq) * dts * wrk%ainv * winvd * gm%poroi
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
          wrk%q(ke(k), i+die(k), j+dje(k)) = sign_e(k) * gq
        end do
      end if
    end do
  end do
  !$omp end parallel do

  ! --- ループ2: 発散 → z と sd の共動更新 + 地下水容量の整合 ---
  !$omp parallel do schedule(static) reduction(+: vleak) &
  !$omp   private(i, j, k, dv8, dz, cap, fx, winv)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      dv8 = 0.0
      do k = 1, 8
        dv8 = dv8 + sign_e(k) * wrk%q(ke(k), i+die(k), j+dje(k))
      end do
      ! 河道幅有効時は体積発散を河道底面積 wfrac*dx*dy で厚さに換算
      ! (Δz の河道底集中。無効時は 1.0 の乗算で厳密に不変)
      winv = 1.0
      if (have_width) winv = 1.0 / wfrac(i,j)
      dz = -dv8 * dts * wrk%ainv * winv * gm%poroi
      ! 岩盤床クリップ(複数エッジの同時流出でエッジ別クランプを僅かに
      ! 超えた場合の最終防衛。失った体積は vleak に計上して黙らない)
      if (dz < -s%sd(i,j)) then
        vleak = vleak + (-dz - s%sd(i,j)) / gm%poroi / wrk%ainv / winv
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

  ! ガード発動の累計(dispose で報告)
  flv%nclip = flv%nclip + nclip
  flv%vleak = flv%vleak + vleak

end subroutine


end submodule
