module m_gwflow_lateral
  ! ========= 側方流動モデル: 非線形 Boussinesq(2次元・8近傍 FV) =========
  ! 飽和帯の側方 Darcy 流(handoff_gwflow_tani.md §3.2b)。
  ! m_swflow_enc と同じ8近傍・エッジ流量4成分の構造(die/dje/ke/sign_e の
  ! 規約、p_diagratio 系の通過幅配分)を踏襲し、
  !   ループ1: 各セルが所有するエッジ成分 k=1..4 のフラックスを計算
  !   ループ2: 計算済みエッジ流量で連続式(発散)+飽和超過の引き渡し
  ! の2段で解く(2026-08-05 決定。4近傍・セル中心の旧実装から変更)。
  !
  ! 【エッジ配列は一時作業領域(永続エッジ状態レスの原則は不変。§4a)】
  !   フラックスは無履歴なので、エッジ配列 q は calc 内で書いて読み切る
  !   スクラッチである: 二重バッファなし・save/restore 対象外・
  !   par_halo_edge / par_edge_merge 不要。時刻 n の hg 退避(旧 wk)は
  !   2ループ分離により不要になった。
  !   動的に変わるエッジ(乾湿)は毎回書き手が 0 を含めて必ず代入する。
  !   マスク起因で書かれないエッジは確保時 0 のまま=恒久無フラックス。
  !
  ! 【定式化】
  !   h_gw = s%hg / sy0(飽和帯厚。s%hg は柱状換算水量)
  !   H    = (s%z - sd) + h_gw [+ s%h]   … 全水頭(同 §3.2.3)。
  !          地表湛水 s%h の寄与は飽和セル(s%hg >= sd*sy0)のみ。
  !          ENCflow は不飽和セルにも湛水が存在しうる(浸透途中の
  !          表面水)が、不飽和帯を介した湛水は地下水面と水圧的に
  !          連続でないため駆動力に含めない(§3.2.3 の実装細目)
  !   q_k  = K_sh * h_e * (H_c - H_n)/dr_k * l_k
  !          (書き手セル c から k 近傍 n へ向かい正の体積流量。
  !           h_e は算術平均を上流側(H の高い側)の h_gw でキャップ)
  !   dr_k は近傍中心間距離(w8dr 相当)、l_k は通過幅(l8 相当。
  !   gw_diagratio による対角/軸配分。既定は m_swflow_enc の
  !   p_diagratio と同値 2/(2+sqrt(2)))
  !
  ! 【数値安定化(§5)】
  !   - 両セル h_gw <= eps で流量ゼロ(乾燥判定)
  !   - 上流側 h_gw <= eps で流量ゼロ
  !   - 過大流出の抑制: 1エッジの流出で上流側が eps を割る場合は縮小
  !     (exflux_reduction 相当。複数エッジ同時流出での微小な行き過ぎは
  !      浅水側と同じく許容し、次ステップの乾燥判定で自己回復する)
  !   - 陽解法の安定条件は h_gw <= sd の構造的上界から静的に評価できる:
  !     dt <= 0.5 * sy0 * dx*dy / (K_sh * max(sd) * Σ_k l_k/dr_k)。
  !     init で検査し、実効時間刻み dts が超えるときは par_stop
  !
  ! 【MPI(§4a)】
  !   calc 冒頭で par_halo_cell(s%hg) と par_halo_cell(s%h) を交換する
  !   (鉛直モデルと引き渡しが帯のみ更新するため、末尾交換では古くなる)。
  !   s%z のハロは m_swflow_enc がステップ頭で毎ステップ交換済みのものに
  !   依存する(呼び出し順 swflow→gwflow が前提。順序を変えるなら再検討)。
  !   帯界面のエッジ(行 je の成分 k=1..3)は、書き手ループをハロ行 je+1
  !   まで延長して自ランクでも冗長計算する(エッジは無履歴なので、南北の
  !   両ランクが同一のセルハロ入力・同一の式・同一の格納向きからビット
  !   厳密に同じ値を得る。swflow の par_edge_merge に相当する通信は不要。
  !   §11「冗長計算=配布機構」)
  !
  ! 【地表流との結合】
  !   側方流入で飽和容量 sd*sy0 を超えたセルは、超過分を s%h へ渡し
  !   s%e を回復する(反対称適用。m_gwflow_bucket 契約(1)(2)と同型。
  !   ループ2に畳み込む: ループ1が時刻 n の s%h を読み終えているため)。
  !   海域セルとは無フラックス(海への地下水流出は当面扱わない)
  !
  ! 【リスタート】
  !   無履歴のためモデル私有状態なし(s%hg は m_state が保存)。契約5の
  !   私有ファイルは不要
  ! =====================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_parallel, only : par_info, par_stop, dcp, par_halo_cell, par_allreduce_max
  implicit none
  private
  public :: gwflow_lateral_init
  public :: gwflow_lateral_calc
  public :: gwflow_lateral_dispose

  ! 8近傍の規約(m_swflow_enc と同一。din/djn=近傍、die/dje/ke/sign_e=
  ! エッジ成分の格納位置と向き。k=1..4 が所有成分、k=5..8 は近傍の所有)
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]
  integer, parameter :: die(1:8) = [ -1,  0,  0, -1,  0, -1,  0,  0]
  integer, parameter :: dje(1:8) = [ -1, -1, -1,  0,  0,  0,  0,  0]
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]

  ! モデル私有の設定・作業領域(単一インスタンス前提。developer.md §12)
  type t_gwlat
    real :: ksh = 0.0                ! 側方飽和透水係数 (m/s)
    real :: eps = 0.0                ! 乾燥判定・過大流出抑制の正則化厚 (m)
    real :: sy0 = 0.0                ! 比湧水量(= g%sy0。init で転記)
    real :: syinv = 0.0              ! 1 / sy0
    real :: ainv = 0.0               ! 1 / (dx*dy)
    real :: rdr(1:8) = 0.0           ! 1 / 近傍セル中心間距離
    real :: wl(1:8) = 0.0            ! k軸方向フラックスの通過幅 (m)
    real, allocatable :: q(:,:,:)    ! エッジ流量4成分 (m3/s)。一時作業領域
    logical :: initialized = .false.
  end type
  type(t_gwlat) :: glt

contains


!----------------------------------------------------------------------
! Boussinesq 側方流の初期化(固有グループを自分で読む)。
! g%sd は m_gwflow_init が m_geoinfo_require_sd で確保済み。
! dts は実効時間刻み(安定条件の静的検査に使う)
!----------------------------------------------------------------------
subroutine gwflow_lateral_init(p, g, s, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: un, ios, i, j, k
  real :: gw_ksh_mmh, gw_eps, gw_diagratio
  real :: lpx, lpy, ldx, ldy, dr
  real :: l8x(1:8), l8y(1:8), w8dr(1:8)
  real :: sdmax(1), sum_ldr, dt_lim
  character(len=256) :: msg
  namelist /list_gwflow_lateral/ gw_ksh_mmh, gw_eps, gw_diagratio

  if (s%initialized) continue  ! 引数未使用の警告を抑制

  gw_ksh_mmh = 0.0
  gw_eps = 1.0e-3
  gw_diagratio = 2.0 / (2.0 + sqrt(2.0))   ! m_swflow_enc の p_diagratio と同値

  call par_info("reading list_gwflow_lateral in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow_lateral, iostat=ios)
  if (ios /= 0) call par_stop("error in reading list_gwflow_lateral")
  close(un)

  if (gw_ksh_mmh <= 0.0) call par_stop("list_gwflow_lateral: gw_ksh_mmh must be > 0")
  if (gw_eps <= 0.0) call par_stop("list_gwflow_lateral: gw_eps must be > 0")
  if (gw_diagratio < 0.0 .or. gw_diagratio > 1.0) then
    call par_stop("list_gwflow_lateral: gw_diagratio must be in [0,1]")
  end if
  if (g%sy0 <= 0.0 .or. g%sy0 > 1.0) then
    call par_stop("list_geoinfo: sy0 must be in (0,1] for gwflow lateral")
  end if
  ! 遅延確保口の呼び忘れ(m_gwflow_init の needs_sd)をここで検出する
  if (.not. allocated(g%sd)) call par_stop("gwflow_lateral: g%sd is not allocated")

  glt%ksh = gw_ksh_mmh / 1000.0 / 3600.0   ! mm/h -> m/s
  glt%eps = gw_eps
  glt%sy0 = g%sy0
  glt%syinv = 1.0 / g%sy0
  glt%ainv = 1.0 / (g%dx * g%dy)

  ! 8近傍の距離と通過幅(m_swflow_enc の init_weights と同一の配分則)
  dr = sqrt(g%dx**2 + g%dy**2)
  w8dr(1:8) = [ dr, g%dy, dr, g%dx, g%dx, dr, g%dy, dr ]
  forall(k=1:8) glt%rdr(k) = 1.0 / w8dr(k)
  if (g%dy > g%dx) then
    lpy = 1 - (g%dx / g%dy)**2 * gw_diagratio
    ldy = gw_diagratio / 2 * (g%dx / g%dy)**2
    lpx = 1 - gw_diagratio
    ldx = gw_diagratio / 2
  else
    lpy = 1 - gw_diagratio
    ldy = gw_diagratio / 2
    lpx = 1 - (g%dy / g%dx)**2 * gw_diagratio
    ldx = gw_diagratio / 2 * (g%dy / g%dx)**2
  end if
  l8y(1:8) = [ ldy, 0.0, ldy, lpy, lpy, ldy, 0.0, ldy ]
  l8x(1:8) = [ ldx, lpx, ldx, 0.0, 0.0, ldx, lpx, ldx ]
  forall(k=1:8) glt%wl(k) = sqrt((l8y(k) * g%dy)**2 + (l8x(k) * g%dx)**2)

  ! 陽解法の安定条件の静的検査(ヘッダ参照。h_gw <= sd の構造的上界)
  sdmax(1) = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      sdmax(1) = max(sdmax(1), g%sd(i,j))
    end do
  end do
  call par_allreduce_max(sdmax)
  sum_ldr = 0.0
  do k = 1, 8
    sum_ldr = sum_ldr + glt%wl(k) * glt%rdr(k)
  end do
  if (glt%ksh * sdmax(1) * sum_ldr > 0.0) then
    dt_lim = 0.5 * glt%sy0 * g%dx * g%dy / (glt%ksh * sdmax(1) * sum_ldr)
    write(msg,'(a,es10.3,a,es10.3,a)') "gwflow_lateral: dt limit = ", dt_lim, &
                                       " s (dts = ", dts, " s)"
    call par_info(trim(msg))
    if (dts > dt_lim) then
      call par_stop("gwflow_lateral: dts exceeds the explicit stability limit " &
                    // "(reduce dt/dt_gwflow or K_sh)")
    end if
  end if

  ! エッジ流量4成分(一時作業領域)。j 範囲はセル j を挟むエッジが
  ! j-1 と j にあるため下限 jsh-1(m_swflow_enc の uv/mn と同形)。
  ! 確保時 0: マスク起因で書かれないエッジは恒久 0(無フラックス)
  allocate(glt%q(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)
  glt%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! Boussinesq 側方流の計算(1回の呼び出しで実効時間刻み dts ぶんの更新)
!   ループ1: エッジ流量(時刻 n の状態から。書き手はハロ行 je+1 まで)
!   ループ2: 連続式+飽和超過の地表流への引き渡し
!----------------------------------------------------------------------
subroutine gwflow_lateral_calc(p, g, s, it, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt
  real :: hgwc, hgwn, hc0, hn0, hgw_up, hgw_e, gq, dh_up, dhg, capc, fx
  logical :: okc

  if (it < 0) continue  ! 引数未使用の警告を抑制(独自周期を持つモデル用に供給)
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  ! ステップ頭のハロ交換(ヘッダ【MPI】参照)
  call par_halo_cell(s%hg)
  call par_halo_cell(s%h)

  ! --- ループ1: エッジ流量(各成分の書き手は一意なので競合しない) ---
  !   帯界面のエッジ成分 k=1..3(行 je)はハロ行 je+1 の書き手が担う
  !   (冗長計算。全域端では行が存在せず対象外)
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) &
  !$omp   private(i, j, k, in, jn, okc, hgwc, hgwn, hc0, hn0, hgw_up, hgw_e, gq, dh_up)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      ! 書き手セルの飽和帯厚と全水頭(地表湛水は飽和セルのみ寄与)
      hgwc = s%hg(i,j) * glt%syinv
      hc0 = s%z(i,j) - g%sd(i,j) + hgwc
      if (s%hg(i,j) >= g%sd(i,j) * glt%sy0) hc0 = hc0 + s%h(i,j)
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        ! 乾湿は動的なので、条件を満たさない場合も必ず 0 を代入する
        gq = 0.0
        if (okc .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            hgwn = s%hg(in,jn) * glt%syinv
            if (hgwc > glt%eps .or. hgwn > glt%eps) then   ! 両側乾燥なら 0
              hn0 = s%z(in,jn) - g%sd(in,jn) + hgwn
              if (s%hg(in,jn) >= g%sd(in,jn) * glt%sy0) hn0 = hn0 + s%h(in,jn)
              if (hc0 /= hn0) then                          ! 勾配ゼロなら 0
                ! 上流側(全水頭の高い側)の飽和帯厚
                if (hc0 > hn0) then
                  hgw_up = hgwc
                else
                  hgw_up = hgwn
                end if
                if (hgw_up > glt%eps) then                  ! 上流側乾燥なら 0
                  ! 界面飽和帯厚: 算術平均を上流側でキャップ(correct_he 相当)
                  hgw_e = min(0.5 * (hgwc + hgwn), hgw_up)
                  ! エッジ流量(書き手 c から k 近傍 n に向かい正)
                  gq = glt%ksh * hgw_e * (hc0 - hn0) * glt%rdr(k) * glt%wl(k)
                  ! 過大流出の抑制: このエッジの流出で上流側が eps を
                  ! 割るなら縮小(exflux_reduction 相当。§5.1)
                  dh_up = abs(gq) * dts * glt%ainv * glt%syinv
                  if (hgw_up - dh_up <= glt%eps) then
                    gq = gq * (max(hgw_up - glt%eps, 0.0) / dh_up)
                  end if
                end if
              end if
            end if
          end if
        end if
        glt%q(k, i+die(k), j+dje(k)) = gq
      end do
    end do
  end do
  !$omp end parallel do

  ! --- ループ2: 連続式+飽和超過分の地表流への引き渡し ---
  !   マスク・乾燥エッジは 0 が入っているため無条件に8近傍を集計できる。
  !   引き渡しは反対称適用と水位の回復(契約(1)(2)相当)
  !$omp parallel do schedule(static) private(i, j, k, dhg, capc, fx)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      ! 8近傍の流出入を集計(中心から近傍に向かい正 → 流出の総和)
      dhg = 0.0
      do k = 1, 8
        dhg = dhg + sign_e(k) * glt%q(ke(k), i+die(k), j+dje(k))
      end do
      s%hg(i,j) = s%hg(i,j) - dhg * dts * glt%ainv
      ! 飽和超過分を s%h へ(§3.2.1/§8 決定)
      capc = g%sd(i,j) * glt%sy0
      if (s%hg(i,j) > capc) then
        fx = s%hg(i,j) - capc
        s%hg(i,j) = capc
        s%h(i,j) = s%h(i,j) + fx
        s%e(i,j) = s%z(i,j) + s%h(i,j)
      end if
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! Boussinesq 側方流の破棄(無履歴のため私有保存なし。ヘッダ【リスタート】)
!----------------------------------------------------------------------
subroutine gwflow_lateral_dispose(p)
  type(t_sysparam), intent(in) :: p
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (allocated(glt%q)) deallocate(glt%q)
  glt%initialized = .false.
end subroutine

end module
