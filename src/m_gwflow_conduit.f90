module m_gwflow_conduit
  ! ============ 管路連続体層(等価被圧連続体)モジュール ============
  ! 下水道網・岩盤亀裂網・カルスト洞窟網・農地暗渠などのサブグリッド
  ! 管路網を、セル別容量 cap と 8 方向異方コンダクタンスを持つ
  ! 「人工被圧帯水層」として表す加算的プロセス(第一用途は都市下水道。
  ! 設計の正本は docs/gwconduit_plan.md §10、決定は developer.md §46)。
  ! &list_gwflow の f_gwconduit=1 で有効化(無効時は s%hgc もエッジ係数も
  ! 確保せず、呼び出しもハロ交換も行わない = メモリ・CPU ゼロ追加)。
  !
  ! 用途はコード分岐ではなく設定の直交スイッチで表す:
  !   - 流束則     f_gwc_fluxlaw(1:線形, 2:sqrt 乱流)
  !   - 地表交換   枡・吸込穴密度(fn_gwc_inlet / gwc_inlet)の指定有無
  !   - 層間交換   gwc_leak_layer(0:なし, 1:層1=土層, 2:層2=風化基岩)
  !   下水道 = {sqrt, 枡あり, 層間なし}、岩盤 = {sqrt/線形, 枡なし, 層2}
  !   のようにプリセットする(gwconduit_plan.md §10.3 の表)
  !
  ! 【毎 gwflow ステップの処理(この順で固定)】
  !  (1) 地表交換(密度 > 0 のセル。反対称適用):
  !      流入(地表→管路。地表水位 > 管路水頭):
  !        不圧時は堰式 q1 = cw·h^1.5、満管時はオリフィス式
  !        q1 = co·sqrt(2g·ΔH)(m3/s/個)。流入量は「水頭が等化する量」
  !        (折れ線水頭の枝ごとの閉形式 eq_inflow)で制限し振動を防ぐ
  !      噴出(管路→地表。被圧時 = hgc > cap のみ):
  !        オリフィス式。噴出量は被圧分 (hgc − cap) と等化量で制限
  !  (2) 側方通水(コンダクタンス指定時): m_gwflow_lateral の conduit_core。
  !      水頭は折れ線(不圧 sy_c / 被圧 sy_slot の疑似スロット)。
  !      容量超過は排出せず層内保持(サーチャージ = Preissmann スロット
  !      連続体版)。呼び出し前に s%hgc のハロを交換する。
  !      **サブサイクリング(§46.5 (4)。静的 N)**: dts が陽解法の
  !      dt 上界を超える設定は par_stop せず、init で決めた
  !      N = ceiling(dts/dt_lim) 回に細分して dts/N ずつ進める
  !      (ハロ交換はサイクルごと。dt_lim は allreduce_max 由来で
  !      全ランク同一 → N も同一 = collective が同期)。N = 1 なら
  !      演算列は従来と厳密同一 = 既存ケースはビット一致。上限
  !      gwc_nsubmax を超える設定は par_stop。細分は側方通水のみ
  !      (交換項 (1)(3)(4) は等化上限・容量制限で無条件安定のため
  !      dts のまま)
  !  (3) 層間交換(gwc_leak_layer > 0): 相手層(s%hg / s%hg2)との
  !      水頭比較で向きを決め、定数交換能 kleak・容量制限の単純形で
  !      双方向に移す(下水道の浸入水・漏水と岩盤の涵養・漏出は同一の項)。
  !      交換能はセル別マップ fn_gwc_leak(mm/h)でも与えられる
  !      (0 のセルは交換なし = ライニング区間・健全管。§46.5 (2)。
  !       一様指定はスカラー値充填 = スカラー指定とビット一致)
  !  (4) 吐口(fn_gwc_outfall 指定時。§46.5 (8b)(3)): オリフィス式
  !      q = ca·sqrt(2g·ΔH)(ca = セル別 Cd·A マップ)の開放管端。
  !      フラップ内蔵 = 管路水頭 > 受け水頭のときのみ放流(逆流なし)。
  !      不圧・被圧を問わない。受け先はセルの隣接状況で決まる:
  !      - 海域セルに隣接(8近傍): 受け水頭 = 隣接海域セルの最低水位
  !        (潮位)。放流水は系外へ除去(海は水位固定の受け皿。
  !        S_total は放流分だけ減少)。等化上限 = 管路水頭が受け水頭
  !        まで下がる量(折れ線水頭の逆関数)で無条件安定。累積放流は
  !        行部分和で集計し dispose で総括(par_sum_rows = 決定的)
  !      - 海隣接なし(陸側開放吐口 = 坑口・暗渠の daylight): 受け
  !        水頭 = 自セルの地表水位。放流は s%h へ(域内 = 質量保存。
  !        同一ループで s%e を回復 = 契約2)。等化上限は流出で地表
  !        水位が 1:1 で上がる逆向き閉形式(eq_outflow)で無条件安定
  !
  ! 【制約・意味論】
  !  - 水頭底 zbot は静的(init 時に z − gwc_depth または fn_gwc_bot)。
  !    geomorph による z の時間変化には追随しない(管路は掘り直さない)
  !  - cap = 0 のセルは「管路なし」: 貯留・通水・交換のすべてが恒久無効
  !  - 蒸発散は hgc に触れない(閉管路の意味論)
  !  - 水質連携(§30): wq の管路連携(wq_gwc_conc)が有効なときだけ、
  !    地表交換量を s%fxci(流入)/ s%fxco(噴出・陸側吐口)へ記録する
  !    (allocated 判定 = 本モジュールは wq を知らない。fxg と同じ契約)
  !  - gwc_leak_layer=1 は土層系(sd, sy0)の有効化、=2 は f_gwlayer2=1 が
  !    前提(init で検証して par_stop)
  !
  ! 【初期値】gwc_sat0(充満率 0〜1。既定 0 = 空)。hgc = sat0·cap。
  !  平衡が要る長期計算はスピンアップ→save→restore(層2と同じ流儀)
  !
  ! 【リスタート】s%hgc はモデル私有ファイル gwflow_conduit.dat(RLE)で
  !  保存(m_gwflow_bucket ヘッダの契約5。state.dat の形式は不変)。
  !  restore 時に自ファイルが無ければ par_stop。吐口の累積放流体積は
  !  純診断のため save 対象外(hmax・qcum と同じ扱い。§7)= 再開後は
  !  再開時点からの累積になる
  ! ==================================================================
  use, intrinsic :: iso_fortran_env, only : real64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_gwflow_lateral, only : t_conduitlayer, conduit_head, conduit_core, &
                               conduit_build_cnd, gwflow_conduit_dtcheck, &
                               gwflow_lateral_geom_init
  use m_gwflow_layer2, only : gwflow_layer2_active, gwflow_layer2_leakinfo
  use m_fileio, only : fileio_read_matrix, fileio_write_rle, fileio_read_rle
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : par_info, par_stop, dcp, is_root, par_halo_cell, &
                         par_gather_to, par_scatter_cell, par_sum_rows
  implicit none
  private
  public :: gwflow_conduit_init
  public :: gwflow_conduit_calc
  public :: gwflow_conduit_dispose
  ! 機場(struct_pump の管路取水 f_pump_src=1)向けの公開口(§46.5 (8a)。
  ! 依存方向: m_boundary_structure → 本モジュール。boundary の init は
  ! gwflow より先に走るため、有効性検査は makebdc 側の遅延検査で行う)
  public :: gwflow_conduit_ready
  public :: gwflow_conduit_head_of
  public :: gwflow_conduit_cap_of

  ! モデル私有の設定(単一インスタンス前提。developer.md §12。
  ! 多重インスタンス(下水道×岩盤の併用)が要る時はこの型を配列化する
  ! 昇格を等価リファクタとして行う。gwconduit_plan.md §10.3)
  type t_gwcond
    type(t_conduitlayer) :: cl       ! カーネルの層パラメータ・静的場
    logical :: lat = .false.         ! 側方通水の有効(コンダクタンス指定)
    logical :: surf = .false.        ! 地表交換の有効(枡・穴密度指定)
    real, allocatable :: dinlet(:,:) ! 枡・人孔・吸込穴密度 (個/m2)
    real :: cw = 0.0                 ! 堰係数(q1 = cw·h^1.5 m3/s/個)
    real :: co = 0.0                 ! オリフィス係数 Cd·A (m2)
    integer :: leak_layer = 0        ! 層間交換の相手(0:なし, 1:層1, 2:層2)
    real, allocatable :: kleakc(:,:) ! 層間交換能 (m/s。セル別。0 = 交換なし)
    integer :: nsub = 1              ! 側方通水のサブサイクル数(§46.5 (4)。静的)
    logical :: outf = .false.        ! 吐口(海域セル放流)の有効
    real, allocatable :: caout(:,:)  ! 吐口のオリフィス係数 Cd·A (m2)。0 = なし
    real(real64), allocatable :: vout_row(:)  ! 累積放流体積の行部分和 (m3)
    real :: syinv1 = 0.0             ! 層1水頭用 1/sy0(leak_layer=1)
    real :: d2 = 0.0                 ! 層2の層厚・比湧水量・容量(leak_layer=2)
    real :: syinv2 = 0.0
    real :: cap2 = 0.0
    logical :: initialized = .false.
  end type
  type(t_gwcond) :: gwc

contains


!----------------------------------------------------------------------
! 管路連続体層の初期化(固有グループ &list_gwflow_conduit を自分で読む)
!----------------------------------------------------------------------
subroutine gwflow_conduit_init(p, g, s, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: un, ios, i, j
  real :: sy2
  real, allocatable :: dens(:,:), wksy(:,:), wkslot(:,:)
  character(len=256) :: msg
  integer :: f_gwc_fluxlaw, gwc_nsubmax
  real :: gwc_cnd_m2s, gwc_cap, gwc_depth, gwc_sy, gwc_slot_sy, gwc_sat0
  real :: gwc_inlet, gwc_cw, gwc_co, gwc_leak_mmh
  real :: gwc_eps, gwc_eps_h, gwc_diagratio
  integer :: gwc_leak_layer
  character(len=1024) :: fn_gwc_cnd, fn_gwc_cap, fn_gwc_bot, fn_gwc_inlet
  character(len=1024) :: fn_gwc_outfall, fn_gwc_leak, fn_gwc_sy, fn_gwc_slot_sy
  namelist /list_gwflow_conduit/ f_gwc_fluxlaw, gwc_cnd_m2s, fn_gwc_cnd, &
    gwc_cap, fn_gwc_cap, gwc_depth, fn_gwc_bot, gwc_sy, gwc_slot_sy, &
    fn_gwc_sy, fn_gwc_slot_sy, &
    gwc_sat0, gwc_inlet, fn_gwc_inlet, gwc_cw, gwc_co, &
    gwc_leak_layer, gwc_leak_mmh, gwc_eps, gwc_eps_h, gwc_diagratio, &
    fn_gwc_outfall, fn_gwc_leak, gwc_nsubmax

  f_gwc_fluxlaw = 2
  gwc_cnd_m2s = 0.0
  fn_gwc_cnd = ""
  gwc_cap = 0.0
  fn_gwc_cap = ""
  gwc_depth = 0.0
  fn_gwc_bot = ""
  gwc_sy = 0.0
  gwc_slot_sy = 0.0
  gwc_sat0 = 0.0
  gwc_inlet = 0.0
  fn_gwc_inlet = ""
  fn_gwc_outfall = ""
  fn_gwc_leak = ""
  fn_gwc_sy = ""
  fn_gwc_slot_sy = ""
  gwc_cw = 2.66                      ! 堰式の既定(越流幅 1 m・流量係数 0.6 相当)
  gwc_co = 0.15                      ! オリフィスの既定(Cd 0.6 × 開口 0.25 m2)
  gwc_leak_layer = 0
  gwc_leak_mmh = 0.0
  gwc_eps = 1.0e-3
  gwc_eps_h = 1.0e-2
  gwc_diagratio = 2.0 / (2.0 + sqrt(2.0))   ! m_swflow_enc の p_diagratio と同値
  gwc_nsubmax = 100                         ! サブサイクル数の上限(§46.5 (4))

  call par_info("reading list_gwflow_conduit in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_conduit: cannot open " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow_conduit, iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_conduit: cannot read namelist")
  close(un)

  ! --- 検証(範囲・整合。list_* は読むだけ、解釈と検証はここ。§12) ---
  if (f_gwc_fluxlaw /= 1 .and. f_gwc_fluxlaw /= 2) then
    call par_stop("list_gwflow_conduit: f_gwc_fluxlaw must be 1(linear) or 2(sqrt)")
  end if
  ! 貯留係数のスカラー検証はマップ指定がない側にのみ適用する
  ! (マップ指定時はセル別検証 = 下の sy 節で行う。§46.5 (5))
  if (len_trim(fn_gwc_sy) == 0) then
    if (gwc_sy <= 0.0 .or. gwc_sy > 1.0) then
      call par_stop("list_gwflow_conduit: gwc_sy must be in (0,1]")
    end if
    if (len_trim(fn_gwc_slot_sy) == 0 &
        .and. (gwc_slot_sy <= 0.0 .or. gwc_slot_sy > gwc_sy)) then
      call par_stop("list_gwflow_conduit: gwc_slot_sy must be in (0, gwc_sy]")
    end if
  end if
  if (gwc_cap <= 0.0 .and. len_trim(fn_gwc_cap) == 0) then
    call par_stop("list_gwflow_conduit: set gwc_cap > 0 or fn_gwc_cap")
  end if
  if (gwc_depth <= 0.0 .and. len_trim(fn_gwc_bot) == 0) then
    call par_stop("list_gwflow_conduit: set gwc_depth > 0 or fn_gwc_bot")
  end if
  if (gwc_cnd_m2s < 0.0) call par_stop("list_gwflow_conduit: gwc_cnd_m2s must be >= 0")
  if (gwc_sat0 < 0.0 .or. gwc_sat0 > 1.0) then
    call par_stop("list_gwflow_conduit: gwc_sat0 must be in [0,1]")
  end if
  if (gwc_eps <= 0.0) call par_stop("list_gwflow_conduit: gwc_eps must be > 0")
  if (gwc_eps_h <= 0.0) call par_stop("list_gwflow_conduit: gwc_eps_h must be > 0")
  if (gwc_diagratio < 0.0 .or. gwc_diagratio > 1.0) then
    call par_stop("list_gwflow_conduit: gwc_diagratio must be in [0,1]")
  end if
  gwc%surf = (gwc_inlet > 0.0 .or. len_trim(fn_gwc_inlet) > 0)
  if (gwc%surf) then
    if (gwc_inlet < 0.0) call par_stop("list_gwflow_conduit: gwc_inlet must be >= 0")
    if (gwc_cw <= 0.0) call par_stop("list_gwflow_conduit: gwc_cw must be > 0")
    if (gwc_co <= 0.0) call par_stop("list_gwflow_conduit: gwc_co must be > 0")
  end if
  select case (gwc_leak_layer)
    case (0)
      ! 層間交換なし
    case (1)
      ! 土層系(sd, sy0)が有効であること(側方 Darcy と同じ前提)
      if (.not. allocated(g%sd)) then
        call par_stop("gwflow_conduit: gwc_leak_layer=1 requires a soil model " &
                      // "(enable f_gwvertical=2 or f_gwlateral=1)")
      end if
      if (g%sy0 <= 0.0 .or. g%sy0 > 1.0) then
        call par_stop("list_geoinfo: sy0 must be in (0,1] for gwc_leak_layer=1")
      end if
      gwc%syinv1 = 1.0 / g%sy0
    case (2)
      if (.not. gwflow_layer2_active()) then
        call par_stop("gwflow_conduit: gwc_leak_layer=2 requires f_gwlayer2=1")
      end if
      call gwflow_layer2_leakinfo(gwc%d2, sy2, gwc%cap2)
      gwc%syinv2 = 1.0 / sy2
    case default
      call par_stop("list_gwflow_conduit: gwc_leak_layer must be 0(none), 1(soil) or 2(layer2)")
  end select
  if (gwc_leak_layer > 0 .and. gwc_leak_mmh <= 0.0 &
      .and. len_trim(fn_gwc_leak) == 0) then
    call par_stop("list_gwflow_conduit: set gwc_leak_mmh > 0 or fn_gwc_leak " &
                  // "when gwc_leak_layer > 0")
  end if
  gwc%leak_layer = gwc_leak_layer
  gwc%cw = gwc_cw
  gwc%co = gwc_co
  gwc%lat = (gwc_cnd_m2s > 0.0 .or. len_trim(fn_gwc_cnd) > 0)

  ! --- カーネルの層パラメータ ---
  gwc%cl%fluxlaw = f_gwc_fluxlaw
  gwc%cl%eps = gwc_eps
  gwc%cl%eps_h = gwc_eps_h

  ! --- 静的場: 貯留容量 cap と水頭底 zbot(帯+ハロ) ---
  allocate(gwc%cl%cap(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (len_trim(fn_gwc_cap) > 0) then
    call read_map_scatter(p, g, fn_gwc_cap, gwc%cl%cap, "gwc_cap")
  else
    ! ゾーン2 = x/sw は全域が使える(帯行 jsh:jeh は全域の有効行)
    do j = dcp%jsh, dcp%jeh
      do i = 1, g%nx
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        gwc%cl%cap(i,j) = gwc_cap
      end do
    end do
  end if
  allocate(gwc%cl%zbot(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (len_trim(fn_gwc_bot) > 0) then
    ! 標高マップは負値可(海抜下の管底。一様埋設深 z-depth も負になり得る
    ! のと整合。§46.5 (7))
    call read_map_scatter(p, g, fn_gwc_bot, gwc%cl%zbot, "gwc_bot", signed=.true.)
  else
    ! 初期地形 z − 一様埋設深(静的。geomorph の z 変化には追随しない)
    gwc%cl%zbot(:,:) = g%z(1:g%nx, dcp%jsh:dcp%jeh) - gwc_depth
  end if

  ! --- 貯留係数(セル別。§46.5 (5)。一様指定はスカラー値充填 =
  !     スカラー指定とビット一致。断面の異なる幹線・枝管の同居に必要。
  !     セル別検証: 管路セル(cap>0)は sy ∈ (0,1] かつ slot ∈ (0, sy]。
  !     非管路セルの値は使われない(逆数は値 > 0 のセルのみ計算し、
  !     0 のセルは 0 のまま = 参照されない)---
  allocate(gwc%cl%syinvc(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gwc%cl%syinv_slot(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (len_trim(fn_gwc_sy) > 0 .or. len_trim(fn_gwc_slot_sy) > 0) then
    allocate(wksy(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(wkslot(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    if (len_trim(fn_gwc_sy) > 0) then
      call read_map_scatter(p, g, fn_gwc_sy, wksy, "gwc_sy")
    else
      wksy(:,:) = gwc_sy
    end if
    if (len_trim(fn_gwc_slot_sy) > 0) then
      call read_map_scatter(p, g, fn_gwc_slot_sy, wkslot, "gwc_slot_sy")
    else
      wkslot(:,:) = gwc_slot_sy
    end if
    do j = dcp%js, dcp%je
      do i = 1, g%nx
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        if (gwc%cl%cap(i,j) <= 0.0) cycle
        if (wksy(i,j) <= 0.0 .or. wksy(i,j) > 1.0) then
          write(msg,'(a,2i7,es12.4)') "gwflow_conduit: gwc_sy must be in (0,1] at", &
                                      i, j, wksy(i,j)
          call par_stop(trim(msg))
        end if
        if (wkslot(i,j) <= 0.0 .or. wkslot(i,j) > wksy(i,j)) then
          write(msg,'(a,2i7,es12.4)') "gwflow_conduit: gwc_slot_sy must be in " &
                                      // "(0, gwc_sy] at", i, j, wkslot(i,j)
          call par_stop(trim(msg))
        end if
      end do
    end do
    ! 逆数化は帯+ハロ全行(conduit_core が隣接セルの水頭を計算するため)
    do j = dcp%jsh, dcp%jeh
      do i = 1, g%nx
        if (wksy(i,j) > 0.0) gwc%cl%syinvc(i,j) = 1.0 / wksy(i,j)
        if (wkslot(i,j) > 0.0) gwc%cl%syinv_slot(i,j) = 1.0 / wkslot(i,j)
      end do
    end do
    deallocate(wksy, wkslot)
  else
    gwc%cl%syinvc(:,:) = 1.0 / gwc_sy
    gwc%cl%syinv_slot(:,:) = 1.0 / gwc_slot_sy
  end if

  ! --- 状態の確保と初期値(海セル・無効セル・管路なしセルには置かない) ---
  allocate(s%hgc(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (gwc_sat0 > 0.0) then
    do j = dcp%jsh, dcp%jeh
      do i = 1, g%nx
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        s%hgc(i,j) = gwc_sat0 * gwc%cl%cap(i,j)
      end do
    end do
  end if

  ! --- 地表交換の密度場 ---
  if (gwc%surf) then
    allocate(gwc%dinlet(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    if (len_trim(fn_gwc_inlet) > 0) then
      call read_map_scatter(p, g, fn_gwc_inlet, gwc%dinlet, "gwc_inlet")
    else
      gwc%dinlet(:,:) = gwc_inlet
    end if
  end if

  ! --- 吐口(海域セル放流)のオリフィス係数マップ(§46.5 (8b)) ---
  !     吐口セルは管路あり(cap > 0)かつ 8 近傍に海域セルが必要
  !     (受け水頭 = 隣接海域セルの最低水位。判定は所有帯で検査 —
  !      init はゾーン2で g%sw の帯+ハロ行が有効)
  gwc%outf = (len_trim(fn_gwc_outfall) > 0)
  if (gwc%outf) then
    allocate(gwc%caout(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    call read_map_scatter(p, g, fn_gwc_outfall, gwc%caout, "gwc_outfall")
    call outfall_check(g)
    allocate(gwc%vout_row(dcp%js:dcp%je), source = 0.0_real64)
  end if

  ! --- 層間交換能(セル別。一様指定はスカラー値充填 = スカラーと
  !     ビット一致。マップの 0 セルは交換なし = ライニング。§46.5 (2)) ---
  if (gwc%leak_layer > 0) then
    allocate(gwc%kleakc(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    if (len_trim(fn_gwc_leak) > 0) then
      call read_map_scatter(p, g, fn_gwc_leak, gwc%kleakc, "gwc_leak")
      gwc%kleakc(:,:) = gwc%kleakc(:,:) / 1000.0 / 3600.0   ! mm/h -> m/s
    else
      gwc%kleakc(:,:) = gwc_leak_mmh / 1000.0 / 3600.0
    end if
  end if

  ! --- 側方通水: 幾何(層1/2 と共有・冪等)→ エッジ係数 → 安定条件 ---
  if (gwc%lat) then
    call gwflow_lateral_geom_init(g, gwc_diagratio, 1.0e-3)
    allocate(dens(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    if (len_trim(fn_gwc_cnd) > 0) then
      call read_map_scatter(p, g, fn_gwc_cnd, dens, "gwc_cnd")
    else
      dens(:,:) = gwc_cnd_m2s
    end if
    call conduit_build_cnd(g, dens, gwc%cl)
    deallocate(dens)
    ! 安定条件 → サブサイクル数 N の決定(§46.5 (4)。N = 1 なら従来と
    ! 演算列が厳密同一。上限超過は設定エラーとして停止)
    if (gwc_nsubmax < 1) call par_stop("list_gwflow_conduit: gwc_nsubmax must be >= 1")
    call gwflow_conduit_dtcheck(g, "gwflow_conduit", gwc%cl, dts, gwc%nsub)
    if (gwc%nsub > gwc_nsubmax) then
      write(msg,'(a,i0,a,i0,a)') "gwflow_conduit: subcycle count ", gwc%nsub, &
          " exceeds gwc_nsubmax = ", gwc_nsubmax, &
          " (reduce conductance/dt or increase slot_sy/eps_h/gwc_nsubmax)"
      call par_stop(trim(msg))
    end if
  end if

  ! --- リスタート ---
  if (p%f_state_restore > 0) call restore_state(p, g, s)

  gwc%initialized = .true.
  call par_info("gwflow conduit continuum layer enabled")
end subroutine


!----------------------------------------------------------------------
! rank0 が全域マップを読み par_scatter_cell で帯+ハロへ配布する(方式2)。
! 係数マップ(cap/cnd/inlet 等)の負値はデータ不良として停止(判定は
! 全ランク同一 = 配布後の帯で検査)。標高マップ(zbot)は負値が正当
! (海抜下の管底)のため signed=.true. で検査を外す(§46.5 (7))
!----------------------------------------------------------------------
subroutine read_map_scatter(p, g, fn, a, label, signed)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn
  real, intent(inout) :: a(1:, dcp%jsh:)
  character(len=*), intent(in) :: label
  logical, intent(in), optional :: signed
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  integer :: i, j
  logical :: nonneg
  character(len=1024) :: msg

  nonneg = .true.
  if (present(signed)) nonneg = .not. signed
  fname = trim(p%dir_data) // "/" // trim(fn)
  call par_info(" reading " // fname)
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    call fileio_read_matrix(fname, g%nx, g%ny, wk, p%f_input_mode)
    call par_scatter_cell(wk, a)
  else
    call par_scatter_cell(dum, a)
  end if
  if (.not. nonneg) return
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      if (g%x(i,j) <= 0) cycle
      if (a(i,j) < 0.0) then
        write(msg,'(a,2i7,es12.4)') "gwflow_conduit: negative " // label // " at", &
                                    i, j, a(i,j)
        call par_stop(trim(msg))
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 地表水位 hsv と管路水頭が等しくなる流入量の上界(m 柱状)。
! 折れ線水頭の枝ごとの閉形式(不圧枝で収まらなければ満管まで詰めて
! 被圧枝で等化)。流入の行き過ぎ(数値振動)の防止に使う
!----------------------------------------------------------------------
pure real function eq_inflow(capv, zbotv, hgcv, hsv, syic, syis)
  real, intent(in) :: capv, zbotv, hgcv, hsv
  real, intent(in) :: syic, syis     ! セル別の 1/sy_c, 1/sy_slot(§46.5 (5))
  real :: hc, fx1, du

  hc = conduit_head(hgcv, capv, zbotv, syic, syis)
  if (hsv <= hc) then
    eq_inflow = 0.0
  else if (hgcv < capv) then
    fx1 = (hsv - hc) / (1.0 + syic)
    if (hgcv + fx1 <= capv) then
      eq_inflow = fx1                          ! 等化点は不圧枝
    else
      du = capv - hgcv                         ! 満管まで詰めて被圧枝で等化
      eq_inflow = du + max(hsv - du - (zbotv + capv * syic), 0.0) &
                       / (1.0 + syis)
    end if
  else
    eq_inflow = (hsv - hc) / (1.0 + syis)
  end if
end function


!----------------------------------------------------------------------
! 地表水位 hsv と管路水頭が等しくなる流出量の上界(m 柱状)。
! eq_inflow の逆向き(流出で地表水位は 1:1 で上がる)。折れ線の枝ごとの
! 閉形式(被圧枝で収まらなければ満管まで下げて不圧枝で等化)。
! 陸側開放吐口の数値振動防止に使う(§46.5 (3))
!----------------------------------------------------------------------
pure real function eq_outflow(capv, zbotv, hgcv, hsv, syic, syis)
  real, intent(in) :: capv, zbotv, hgcv, hsv
  real, intent(in) :: syic, syis     ! セル別の 1/sy_c, 1/sy_slot(§46.5 (5))
  real :: hc, fx1, du

  hc = conduit_head(hgcv, capv, zbotv, syic, syis)
  if (hc <= hsv) then
    eq_outflow = 0.0
  else if (hgcv > capv) then
    fx1 = (hc - hsv) / (1.0 + syis)
    if (hgcv - fx1 >= capv) then
      eq_outflow = fx1                          ! 等化点は被圧枝
    else
      du = hgcv - capv                          ! 満管まで下げて不圧枝で等化
      eq_outflow = du + max((zbotv + capv * syic) - (hsv + du), 0.0) &
                        / (1.0 + syic)
    end if
  else
    eq_outflow = (hc - hsv) / (1.0 + syic)
  end if
end function


!----------------------------------------------------------------------
! 管路連続体層の計算(毎 gwflow ステップ。地表交換→側方→層間の順で固定)
!----------------------------------------------------------------------
subroutine gwflow_conduit_calc(p, g, s, it, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  real, intent(in) :: dts
  integer :: i, j, di2, dj2, isub
  real :: capc, hcnd, hs, q1, fx, hother, capo
  real :: esea, hgt, ca, syic, syis
  logical :: hassea

  if (it < 0) continue  ! 引数未使用の警告を抑制

  ! (1) 地表交換(枡・吸込穴。堰式流入/オリフィス式噴出。反対称適用。
  !     owner-compute。s%h を変更したら s%e を回復する = 契約(2))
  if (gwc%surf) then
    !$omp parallel do schedule(static) private(i, j, capc, hcnd, hs, q1, fx, syic, syis)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        capc = gwc%cl%cap(i,j)
        if (capc <= 0.0) cycle
        if (gwc%dinlet(i,j) <= 0.0) cycle
        syic = gwc%cl%syinvc(i,j)
        syis = gwc%cl%syinv_slot(i,j)
        hcnd = conduit_head(s%hgc(i,j), capc, gwc%cl%zbot(i,j), syic, syis)
        hs = s%z(i,j) + s%h(i,j)
        if (hs > hcnd .and. s%h(i,j) > 0.0) then
          ! 流入(不圧 = 堰式の自由流入、満管 = オリフィス式の圧力流入)
          if (s%hgc(i,j) >= capc) then
            q1 = gwc%co * sqrt(2.0 * p%gg * (hs - hcnd))
          else
            q1 = gwc%cw * s%h(i,j)**1.5
          end if
          fx = min(gwc%dinlet(i,j) * q1 * dts, s%h(i,j), &
                   eq_inflow(capc, gwc%cl%zbot(i,j), s%hgc(i,j), hs, syic, syis))
          if (fx > 0.0) then
            s%h(i,j) = s%h(i,j) - fx
            s%hgc(i,j) = s%hgc(i,j) + fx
            s%e(i,j) = s%z(i,j) + s%h(i,j)
            ! 水質連携: 流入量を記録(fxg と同じ契約。wq が消費・ゼロ戻し)
            if (allocated(s%fxci)) s%fxci(i,j) = s%fxci(i,j) + fx
          end if
        else if (hcnd > hs .and. s%hgc(i,j) > capc) then
          ! 噴出(被圧時のみ。オリフィス式。被圧分と等化量で制限)
          q1 = gwc%co * sqrt(2.0 * p%gg * (hcnd - hs))
          fx = min(gwc%dinlet(i,j) * q1 * dts, s%hgc(i,j) - capc, &
                   (hcnd - hs) / (1.0 + syis))
          if (fx > 0.0) then
            s%hgc(i,j) = s%hgc(i,j) - fx
            s%h(i,j) = s%h(i,j) + fx
            s%e(i,j) = s%z(i,j) + s%h(i,j)
            ! 水質連携: 噴出量を記録(wq が固定濃度の質量を同伴させる)
            if (allocated(s%fxco)) s%fxco(i,j) = s%fxco(i,j) + fx
          end if
        end if
      end do
    end do
    !$omp end parallel do
  end if

  ! (2) 側方通水(近傍結合のためサイクルごとにハロ交換してからカーネルへ。
  !     サブサイクリング = §46.5 (4)。nsub は init 決定の静的値で全ランク
  !     同一 → ループ回数・collective が同期。nsub=1 は従来と演算列同一)
  if (gwc%lat) then
    do isub = 1, gwc%nsub
      call par_halo_cell(s%hgc)
      call conduit_core(g, s%hgc, gwc%cl, dts / gwc%nsub)
    end do
  end if

  ! (3) 層間交換(浸入水・漏水/涵養・漏出。水頭比較で向きを決める
  !     定数交換能・容量制限の単純形。反対称適用。s%h に触れない)
  if (gwc%leak_layer > 0) then
    !$omp parallel do schedule(static) private(i, j, capc, capo, hcnd, hother, fx, syic, syis)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        capc = gwc%cl%cap(i,j)
        if (capc <= 0.0) cycle
        syic = gwc%cl%syinvc(i,j)
        syis = gwc%cl%syinv_slot(i,j)
        hcnd = conduit_head(s%hgc(i,j), capc, gwc%cl%zbot(i,j), syic, syis)
        if (gwc%leak_layer == 1) then
          hother = (s%z(i,j) - s%sd(i,j)) + s%hg(i,j) * gwc%syinv1
          if (hother > hcnd) then
            fx = min(gwc%kleakc(i,j) * dts, s%hg(i,j))            ! 浸入水(層1→管路)
            if (fx > 0.0) then
              s%hg(i,j) = s%hg(i,j) - fx
              s%hgc(i,j) = s%hgc(i,j) + fx
            end if
          else if (hcnd > hother) then
            capo = s%sd(i,j) * g%sy0
            fx = min(gwc%kleakc(i,j) * dts, s%hgc(i,j), max(capo - s%hg(i,j), 0.0))
            if (fx > 0.0) then                              ! 漏水(管路→層1)
              s%hgc(i,j) = s%hgc(i,j) - fx
              s%hg(i,j) = s%hg(i,j) + fx
            end if
          end if
        else
          hother = (s%z(i,j) - s%sd(i,j) - gwc%d2) + s%hg2(i,j) * gwc%syinv2
          if (hother > hcnd) then
            fx = min(gwc%kleakc(i,j) * dts, s%hg2(i,j))           ! 涵養(層2→管路)
            if (fx > 0.0) then
              s%hg2(i,j) = s%hg2(i,j) - fx
              s%hgc(i,j) = s%hgc(i,j) + fx
            end if
          else if (hcnd > hother) then
            fx = min(gwc%kleakc(i,j) * dts, s%hgc(i,j), max(gwc%cap2 - s%hg2(i,j), 0.0))
            if (fx > 0.0) then                              ! 漏出(管路→層2)
              s%hgc(i,j) = s%hgc(i,j) - fx
              s%hg2(i,j) = s%hg2(i,j) + fx
            end if
          end if
        end if
      end do
    end do
    !$omp end parallel do
  end if

  ! (4) 吐口(隣接海域セルへの放流。§46.5 (8b)。フラップ内蔵・等化上限で
  !     無条件安定。放流水は系外へ除去 = S_total 減少。受け水頭の海域
  !     セル水位はハロ行を読み得るため s%e のハロを先に交換する
  !     (collective は outf が namelist 由来で全ランク同一)
  if (gwc%outf) then
    call par_halo_cell(s%e)
    !$omp parallel do schedule(static) &
    !$omp   private(i, j, di2, dj2, capc, ca, hcnd, esea, hs, hgt, q1, fx, hassea, syic, syis)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        capc = gwc%cl%cap(i,j)
        if (capc <= 0.0) cycle
        ca = gwc%caout(i,j)
        if (ca <= 0.0) cycle
        if (s%hgc(i,j) <= gwc%cl%eps) cycle
        ! 受け水頭 = 隣接海域セルの最低水位(min は順序不変で決定的)
        esea = 0.0
        hassea = .false.
        do dj2 = -1, 1
          do di2 = -1, 1
            if (di2 == 0 .and. dj2 == 0) cycle
            if (g%x(i+di2,j+dj2) <= 0) cycle
            if (g%sw(i+di2,j+dj2) <= 0) cycle
            if (hassea) then
              esea = min(esea, s%e(i+di2,j+dj2))
            else
              esea = s%e(i+di2,j+dj2)
              hassea = .true.
            end if
          end do
        end do
        syic = gwc%cl%syinvc(i,j)
        syis = gwc%cl%syinv_slot(i,j)
        hcnd = conduit_head(s%hgc(i,j), capc, gwc%cl%zbot(i,j), syic, syis)
        if (hassea) then
          ! 海側吐口(§46.5 (8b)): 受け水頭 = 潮位(固定)。系外へ除去
          if (hcnd <= esea) cycle              ! フラップ: 逆流なし
          q1 = ca * sqrt(2.0 * p%gg * (hcnd - esea))
          ! 等化上限: 管路水頭が受け水頭まで下がる貯留量(折れ線の逆関数)
          if (esea <= gwc%cl%zbot(i,j)) then
            hgt = 0.0
          else if (esea <= gwc%cl%zbot(i,j) + capc * syic) then
            hgt = (esea - gwc%cl%zbot(i,j)) / syic
          else
            hgt = capc + (esea - gwc%cl%zbot(i,j) - capc * syic) / syis
          end if
          fx = min(q1 * dts / (g%dx * g%dy), s%hgc(i,j) - hgt)
          if (fx > 0.0) then
            s%hgc(i,j) = s%hgc(i,j) - fx
            ! 行部分和(行の書き手スレッドは一意 = 競合なし・加算順は
            ! i 昇順で固定 = スレッド数・ランク数によらず決定的)
            gwc%vout_row(j) = gwc%vout_row(j) + real(fx, real64) * g%dx * g%dy
          end if
        else
          ! 陸側開放吐口(§46.5 (3)。坑口・暗渠の daylight): 受け水頭 =
          ! 自セルの地表水位。域内転送(s%h へ。s%e 回復 = 契約2)
          hs = s%z(i,j) + s%h(i,j)
          if (hcnd <= hs) cycle                ! フラップ: 逆流なし
          q1 = ca * sqrt(2.0 * p%gg * (hcnd - hs))
          fx = min(q1 * dts / (g%dx * g%dy), s%hgc(i,j), &
                   eq_outflow(capc, gwc%cl%zbot(i,j), s%hgc(i,j), hs, syic, syis))
          if (fx > 0.0) then
            s%hgc(i,j) = s%hgc(i,j) - fx
            s%h(i,j) = s%h(i,j) + fx
            s%e(i,j) = s%z(i,j) + s%h(i,j)
            ! 水質連携: 吐口放流量を記録(wq が固定濃度の質量を同伴させる)
            if (allocated(s%fxco)) s%fxco(i,j) = s%fxco(i,j) + fx
          end if
        end if
      end do
    end do
    !$omp end parallel do
  end if
end subroutine


!----------------------------------------------------------------------
! 機場向け公開口(§46.5 (8a)): 有効状態・管路水頭・容量。
! head/cap は帯内セル (i, 帯行 j) 前提(呼び手が所有ガードを掛ける)
!----------------------------------------------------------------------
pure logical function gwflow_conduit_ready()
  gwflow_conduit_ready = gwc%initialized
end function


pure real function gwflow_conduit_head_of(s, i, j)
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  gwflow_conduit_head_of = conduit_head(s%hgc(i,j), gwc%cl%cap(i,j), &
                                        gwc%cl%zbot(i,j), gwc%cl%syinvc(i,j), &
                                        gwc%cl%syinv_slot(i,j))
end function


pure real function gwflow_conduit_cap_of(i, j)
  integer, intent(in) :: i, j
  gwflow_conduit_cap_of = gwc%cl%cap(i,j)
end function


!----------------------------------------------------------------------
! 吐口セルの整合検査(管路ありが必須。所有帯で検査 = データ不良の停止は
! read_map_scatter の負値検査と同じ owner 側 par_stop)。
! 海域セル隣接の有無は吐口の受け先(海/自セル地表)を決めるだけで、
! どちらも正当(§46.5 (3) で陸側開放吐口を追加)
!----------------------------------------------------------------------
subroutine outfall_check(g)
  type(t_geoinfo), intent(in) :: g
  integer :: i, j
  character(len=256) :: msg

  do j = dcp%js, dcp%je
    do i = 1, g%nx
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (gwc%caout(i,j) <= 0.0) cycle
      if (gwc%cl%cap(i,j) <= 0.0) then
        write(msg,'(a,2i7)') "gwflow_conduit: outfall on a no-conduit cell (cap=0) at", i, j
        call par_stop(trim(msg))
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル gwflow_conduit.dat。契約5。§7)
!----------------------------------------------------------------------
subroutine save_state(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, allocatable :: wk(:,:)
  integer :: un
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
  else
    allocate(wk(1, 1), source = 0.0)
  end if
  call par_gather_to(wk, s%hgc)
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/gwflow_conduit.dat', form='unformatted', &
         status='replace')
    call fileio_write_rle(un, wk)
    close(un)
  end if
end subroutine


subroutine restore_state(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  logical :: found
  integer :: un

  ! 版・格子・精度の検証は m_state(check_save_info)が済ませている。
  ! 自ファイルの有無のみ確認(無ければ「保存時は管路層無効だった」として
  ! ゼロ継続を許さず停止 — 意図しない水収支の断絶を防ぐ)
  fname = trim(p%dir_save)//'/gwflow_conduit.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("gwflow_conduit: state file not found " &
                  // "(was f_gwconduit enabled when saving): "//fname)
  end if

  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    close(un)
    call par_scatter_cell(wk, s%hgc)
  else
    call par_scatter_cell(dum, s%hgc)
  end if
end subroutine


!----------------------------------------------------------------------
! 管路連続体層の破棄(save は dispose で行う。契約5)
!----------------------------------------------------------------------
subroutine gwflow_conduit_dispose(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64) :: vtot
  character(len=256) :: msg
  if (.not. gwc%initialized) return
  if (p%f_state_save > 0) call save_state(p, g, s)
  ! 吐口の累積放流体積の総括(par_sum_rows = 決定的。collective は
  ! outf が namelist 由来で全ランク同一のため安全)
  if (gwc%outf) then
    call par_sum_rows(gwc%vout_row, vtot)
    if (is_root) then
      write(msg,'(a,es12.4,a)') " gwflow_conduit: outfall discharge total = ", &
                                vtot, " m3 (removed to sea)"
      call par_info(trim(msg))
    end if
  end if
  if (allocated(gwc%cl%zbot)) deallocate(gwc%cl%zbot)
  if (allocated(gwc%cl%syinvc)) deallocate(gwc%cl%syinvc)
  if (allocated(gwc%cl%syinv_slot)) deallocate(gwc%cl%syinv_slot)
  if (allocated(gwc%cl%cap)) deallocate(gwc%cl%cap)
  if (allocated(gwc%cl%cnd)) deallocate(gwc%cl%cnd)
  if (allocated(gwc%dinlet)) deallocate(gwc%dinlet)
  if (allocated(gwc%caout)) deallocate(gwc%caout)
  if (allocated(gwc%vout_row)) deallocate(gwc%vout_row)
  if (allocated(gwc%kleakc)) deallocate(gwc%kleakc)
  gwc%initialized = .false.
end subroutine

end module
