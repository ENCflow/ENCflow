submodule(m_swflow_enc) m_swflow_enc_bc
  ! 境界条件の適用層(m_swflow_enc_adv と同じ「親の私有状態への
  ! ホスト結合を活かしたコード分割」の submodule)。
  !   - bc_init      : 辺型・セル別面型 bt_cell・放射基準水位・流入区間の
  !                    開口幅を t_boundary から構築(init_weights の後に呼ぶ)
  !   - boundary_h   : 水深側の境界処理(ため池・降雨・湧き出し・水位規定)
  !   - boundary_uvmn: エッジ uv/mn1 への強制条件(辺境界・区間流入)
  !   - bc_open_face : continuous / restore_uvmn の枠外面の取り込み判定
  ! 設計の正本は developer.md §15。親の have_open_bc は bc_init が設定する。
  ! 親の重み(l8, mn2dh, n8x/y)・方位定数(din/dje 等)・t_enc_status は
  ! ホスト結合で参照する。dcp 等の use 経由の名前は nvfortran バグ回避の
  ! ため submodule 側で直接 use する(§13)
  use, intrinsic :: iso_fortran_env, only : r64 => real64
  use m_boundary, only : t_boundary, e_bc_wall, e_bc_outflow, e_bc_radiation, &
                         e_bc_inflow, e_side_w, e_side_e, e_side_n, e_side_s, &
                         dam_operate, dam_sink, dam_draw, e_struct_dam
  use m_parallel, only : dcp, par_stop, par_allreduce_sumr
  implicit none

  ! 境界条件の私有状態(bc_init が構築)
  integer :: f_bc_side(1:4) = e_bc_wall     ! 外縁4辺の境界条件型(W,E,N,S)
  integer, allocatable :: bt_cell(:,:)      ! 外縁面の型(セル別。(j,W/E)・(i,N/S)。
                                            !   辺の型を初期値とし流入区間が上書き)
  real, allocatable :: bc_eta_cell(:,:)     ! 放射境界の基準水位(セル別)
  real, allocatable :: infl_wseg(:)         ! 各流入区間の開口幅の合計 (m)
  real, allocatable :: infl_hseg(:)         ! 区間の面エントリ別水深(重み按分の
                                            !   作業配列。全ランクが同値を共有)
  ! 辺の法線方向の方位(W, E, N, S)
  integer, parameter :: kn_side(1:4) = [4, 5, 2, 7]
  ! エッジ格納スロットの k 成分と符号(親の continuous と同じ写像)
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]

contains

!----------------------------------------------------------------------
! 境界条件の適用層の初期化(t_boundary からモジュール状態を構築)
!   開口幅の計算が親の l8 を使うため init_weights より後に呼ぶこと
!----------------------------------------------------------------------
module subroutine bc_init(p, g, b)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  integer :: ifl, ifl2, m
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  ! 辺境界条件を写す(ホットループでの間接参照回避)
  f_bc_side = b%edge%btype
  have_open_bc = any(f_bc_side /= e_bc_wall) .or. (b%ninflow > 0)
  if (any(f_bc_side == e_bc_radiation)) then
    ! 基準水位は m_boundary_set_etaref(m_state_init 直後)が確定済み
    if (.not. allocated(b%edge%eta_cell)) then
      call par_stop("swflow: reference water level for the radiation boundary is not set" &
                    //" (check the m_boundary_set_etaref wiring)")
    end if
    bc_eta_cell = b%edge%eta_cell
  end if

  ! 外縁面の型をセル別に構築する(辺の型を初期値とし、流入区間の
  ! 法線面を e_bc_inflow で上書き。bc_open_face が参照する)
  allocate(bt_cell(1:max(g%nx, g%ny), 1:4))
  bt_cell(:,e_side_w) = f_bc_side(e_side_w)
  bt_cell(:,e_side_e) = f_bc_side(e_side_e)
  bt_cell(:,e_side_n) = f_bc_side(e_side_n)
  bt_cell(:,e_side_s) = f_bc_side(e_side_s)
  do ifl = 1, b%ninflow
    do m = 1, b%inflow(ifl)%ncell
      select case (b%inflow(ifl)%side(m))
        case (e_side_w, e_side_e)
          bt_cell(b%inflow(ifl)%cell(2,m), b%inflow(ifl)%side(m)) = e_bc_inflow
        case default
          bt_cell(b%inflow(ifl)%cell(1,m), b%inflow(ifl)%side(m)) = e_bc_inflow
      end select
    end do
  end do

  ! 各流入区間の開口幅(法線面の l8 の合計)を計算する
  ! (規定流量はこの幅で按分するため、総流入量は開口率によらず厳密)
  if (b%ninflow > 0) then
    allocate(infl_wseg(1:b%ninflow), source = 0.0)
    m = 0
    do ifl = 1, b%ninflow
      m = max(m, b%inflow(ifl)%ncell)
      do ifl2 = 1, b%inflow(ifl)%ncell
        infl_wseg(ifl) = infl_wseg(ifl) + l8(kn_side(b%inflow(ifl)%side(ifl2)))
      end do
    end do
    allocate(infl_hseg(1:m), source = 0.0)
  end if

end subroutine


!----------------------------------------------------------------------
! 境界条件の適用層の破棄
!----------------------------------------------------------------------
module subroutine bc_dispose()
  if (allocated(bc_eta_cell)) deallocate(bc_eta_cell)
  if (allocated(bt_cell)) deallocate(bt_cell)
  if (allocated(infl_wseg)) deallocate(infl_wseg)
  if (allocated(infl_hseg)) deallocate(infl_hseg)
end subroutine


!----------------------------------------------------------------------
! 水深の境界条件をセットする
!   このルーチンより前に実行されるcontinuous/init_enc_statusにおいて
!   水深はs%hからsx%h1に更新されているので、ここではsx%h1を更新する　
!     s%h：前ステップの水深
!     sx%h1：現ステップの連続式適用後の水深
!----------------------------------------------------------------------
module subroutine boundary_h(p, g, b, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(inout) :: sx
  integer :: i, j, k, isrc, istage, ip, ncs, ncd
  logical :: fwd
  real :: qcell, dht, dh
  real, allocatable :: vst(:)

  !$omp parallel do schedule(dynamic) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%sw(i,j) > 0) cycle
      if (g%x(i,j) <= 0) cycle

      ! ため池の処理(吸収量は s%fxr へ記録 — m_wq が読んで質量を
      ! 同伴しゼロ戻しする契約。fxg と同型。未確保なら記録しない。§30.7)
      if (g%rscap(i,j) > 0.0 .and. g%rscap(i,j) > s%hrs(i,j)) then ! ため池に余力がある
        if (sx%h1(i,j) > (g%rscap(i,j) - s%hrs(i,j))) then         !   ため池があふれる
          if (allocated(s%fxr)) s%fxr(i,j) = s%fxr(i,j) + (g%rscap(i,j) - s%hrs(i,j))
          sx%h1(i,j) = sx%h1(i,j) - (g%rscap(i,j) - s%hrs(i,j))    !     場の水深がため池の余力分だけ減る
          s%hrs(i,j) = g%rscap(i,j)                                !     ため池が満水になる
        else                                                       !   ため池があふれない
          if (allocated(s%fxr)) s%fxr(i,j) = s%fxr(i,j) + sx%h1(i,j)
          s%hrs(i,j) = s%hrs(i,j) + sx%h1(i,j)                     !     ため池の水深が増加する
          sx%h1(i,j) = 0.0                                         !     場の水深がゼロになる
        end if
      end if

      ! 降雨を加えて次ステップの水深を初期化
      !   河道幅有効時は平面積率 wfrac でも除す(セル全面の雨が河道断面へ
      !   集中する。gv の建物集中と同じ意味論。§18)
      if (have_width) then
        sx%h1(i,j) = sx%h1(i,j) + s%pre(i,j) * p%dt / g%gv(i,j) / wfrac(i,j)
      else
        sx%h1(i,j) = sx%h1(i,j) + s%pre(i,j) * p%dt / g%gv(i,j)
      end if

    end do
  end do
  !$omp end parallel do

  ! 湧き出し・吸い込みを加える
  !   所有ランクのみ適用する(リストは全ランクが保持。developer.md §11)。
  !   空隙率 gv で割って水深に換算する(降雨と同じ扱い。これで各セルの
  !   受け取る体積が q·dx·dy で等しくなり、総量が厳密に Q になる)
  do isrc = 1, b%nsrc
    do k = 1, b%src(isrc)%ncell
      i = b%src(isrc)%cell(1,k)
      j = b%src(isrc)%cell(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle
      ! 河道幅有効時は平面積率 wfrac でも除す(体積→水深換算の統一。§18)
      if (have_width) then
        sx%h1(i,j) = sx%h1(i,j) + b%src(isrc)%q / g%gv(i,j) / wfrac(i,j)
      else
        sx%h1(i,j) = sx%h1(i,j) + b%src(isrc)%q / g%gv(i,j)
      end if
      ! 吸い込み(負の流量)でセルを負水深にしない(不足分は汲めない)
      if (sx%h1(i,j) < 0) sx%h1(i,j) = 0
    end do
  end do

  ! 内部水理構造物(ポンプ・カルバート等。§22): 取水セル群から吐口
  ! セル群への質量保存的な強制転送。目標流量 q は makebdc がステップ
  ! 開始時状態の水理則から決定済み。q < 0 は逆向きの転送(cout→cin。
  ! カルバートの双方向)で、源側・先側のセル群が入れ替わるだけで
  ! 処理は同形。ここでは源側で「実在する水量まで」の吸い上げ制限を
  ! 適用し、実際に汲めた体積だけを先側へ与える(授受の体積が厳密に
  ! 一致)。源と先が別ランクでも、実体積の共有は「所有ランクのみ
  ! 非ゼロ+総和 allreduce」で決定的(§11)。
  ! 順方向で吐口なし(ncout=0)は域外排水(系から除去。ポンプのみ)。
  ! collective は全ランクが同数実行する(nstruct は namelist 由来で全ランク同一)
  if (b%nstruct > 0) then
    allocate(vst(1:b%nstruct), source = 0.0)
    do ip = 1, b%nstruct
      if (b%struct(ip)%q == 0.0) cycle
      fwd = b%struct(ip)%q > 0.0
      if (fwd) then
        ncs = b%struct(ip)%ncin
      else
        ncs = b%struct(ip)%ncout
      end if
      ! セルあたり目標水深(体積の等分配。gv・wfrac で水深に換算)
      qcell = abs(b%struct(ip)%q) * p%dt / (ncs * g%dx * g%dy)
      do k = 1, ncs
        if (fwd) then
          i = b%struct(ip)%cin(1,k)
          j = b%struct(ip)%cin(2,k)
        else
          i = b%struct(ip)%cout(1,k)
          j = b%struct(ip)%cout(2,k)
        end if
        if (j < dcp%js .or. j > dcp%je) cycle
        ! 管路取水ポンプ(src=1。機場。§46.5 (8a))は管路連続体層の
        ! 貯留 s%hgc から汲む。hgc は柱状換算水量(セル全面積基準)の
        ! ため gv・wfrac の換算はしない。src=1 はポンプのみ(init で
        ! 検証)= 常に順方向
        if (b%struct(ip)%src == 1) then
          dh = min(max(s%hgc(i,j), 0.0), qcell)
          s%hgc(i,j) = s%hgc(i,j) - dh
          vst(ip) = vst(ip) + dh * g%dx * g%dy
          cycle
        end if
        if (have_width) then
          dht = qcell / g%gv(i,j) / wfrac(i,j)
        else
          dht = qcell / g%gv(i,j)
        end if
        ! ため池セル(rscap>0)は場の水面でなく貯留 s%hrs から汲む
        ! (前池排水。§22)。汲んで空いた容量への地表水の再吸収は
        ! 次ステップのため池処理が行う(1ステップ遅れ)。
        ! カルバートはため池セル不許可(init で検証)のため、この分岐は
        ! 順方向(ポンプ)でのみ生きる
        if (g%rscap(i,j) > 0.0) then
          dh = min(max(s%hrs(i,j), 0.0), dht)
          s%hrs(i,j) = s%hrs(i,j) - dh
        else
          dh = min(max(sx%h1(i,j), 0.0), dht)
          sx%h1(i,j) = sx%h1(i,j) - dh
        end if
        if (have_width) then
          vst(ip) = vst(ip) + dh * g%gv(i,j) * wfrac(i,j) * g%dx * g%dy
        else
          vst(ip) = vst(ip) + dh * g%gv(i,j) * g%dx * g%dy
        end if
      end do
    end do
    call par_allreduce_sumr(vst)
    do ip = 1, b%nstruct
      if (vst(ip) <= 0.0) cycle
      fwd = b%struct(ip)%q > 0.0
      if (fwd) then
        ncd = b%struct(ip)%ncout
        if (ncd <= 0) cycle                      ! 域外排水は除去のみ
      else
        ncd = b%struct(ip)%ncin
      end if
      qcell = vst(ip) / (ncd * g%dx * g%dy)
      do k = 1, ncd
        if (fwd) then
          i = b%struct(ip)%cout(1,k)
          j = b%struct(ip)%cout(2,k)
        else
          i = b%struct(ip)%cin(1,k)
          j = b%struct(ip)%cin(2,k)
        end if
        if (j < dcp%js .or. j > dcp%je) cycle
        if (have_width) then
          sx%h1(i,j) = sx%h1(i,j) + qcell / g%gv(i,j) / wfrac(i,j)
        else
          sx%h1(i,j) = sx%h1(i,j) + qcell / g%gv(i,j)
        end if
      end do
    end do
    deallocate(vst)
  end if

  ! 水位規定セル群(流域出口の流出境界、背水・感潮域等)
  !   指定水位 η に強制する(最後に適用=同一セルでは最優先)。
  !   周囲との面フラックスは momentum が通常計算するため、規定水位が
  !   作る勾配が流出入を駆動し、u,v,m,n・record にも自然に乗る。
  !   η が河床より低ければセルは常に空=完全排水口になる
  do istage = 1, b%nstage
    do k = 1, b%stage(istage)%ncell
      i = b%stage(istage)%cell(1,k)
      j = b%stage(istage)%cell(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle
      ! σ 有効時は規定水位の水深を矩形換算水深へ変換して格納する
      ! (h1 は vh 運用。非適用セルは sect_v が恒等。§26)
      if (have_sect) then
        sx%h1(i,j) = sect_v(max(b%stage(istage)%eta - s%z(i,j), 0.0), sdep(i,j))
      else
        sx%h1(i,j) = max(b%stage(istage)%eta - s%z(i,j), 0.0)
      end if
    end do
  end do

end subroutine


!----------------------------------------------------------------------
! ダム・湖沼の適用(§22): 捕捉集合セルの到達水を全量吸収して s%hrs に
! 貯留し(=バケツ。到達水は段落ち的に消える)、運転ルール(dam_operate)
! で引き落とし体積を決めて放流セルへ分配する。水位固定湖沼(dmode=0。
! 放流セルなし)は到達水を貯留せず全量消失させる(dam_sink。
! lake_plan.md §3.4)。
!   呼び出しは時間ループの boundary_h の直前のみ(init の boundary_h
!   適用には含めない: 含めると restore 時に最終ステップのダム操作が
!   二重適用され、往復ビット一致が破れる)。
!   位置は連続式適用後・boundary_h(降雨・湧き出し)より前
!   (この歩に流入した水を捕捉する。捕捉帯セルへの直接降雨・湧き出しは
!   次の歩に吸収される=1歩遅れ)。
!   collective(par_sum_rows×2/基)は全ランクがダムごとに同数実行する
!   (nstruct・kind は namelist 由来で全ランク同一)。
!   捕捉帯・放流セルは ため池・河道幅指定と併用不可(init で検証済み)
!   のため換算は /gv のみ
!----------------------------------------------------------------------
module subroutine dam_apply(p, g, b, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(inout) :: b    ! dam_operate が診断量を更新する
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(inout) :: sx
  integer :: i, j, k, ip
  real :: qcell, vola, vdraw
  real(r64) :: vabs_row(dcp%js:dcp%je), vrow(dcp%js:dcp%je)

  do ip = 1, b%nstruct
    if (b%struct(ip)%kind /= e_struct_dam) cycle
    vabs_row = 0.0_r64
    vrow = 0.0_r64
    !--- 湖沼参照構造物(lref>0): 参照先湖沼の貯留から自分の運転則で引き、
    !    自分の放流セルへ分配する(§22 第2弾)。参照先(小さい番号)の
    !    dam_operate はこのループで処理済み。collective なし ---
    if (b%struct(ip)%lref > 0) then
      call dam_draw(b, ip, p, g, s, vdraw)
      if (vdraw > 0.0) then
        qcell = vdraw / (b%struct(ip)%ncout * g%dx * g%dy)
        do k = 1, b%struct(ip)%ncout
          i = b%struct(ip)%cout(1,k)
          j = b%struct(ip)%cout(2,k)
          if (j < dcp%js .or. j > dcp%je) cycle
          sx%h1(i,j) = sx%h1(i,j) + qcell / g%gv(i,j)
        end do
      end if
      cycle
    end if
    !--- 水位固定湖沼(dmode=0): 到達水は全量消失(貯留しない)。
    !    hrs は常に 0 のまま。分岐は namelist 由来で全ランク同一 ---
    if (b%struct(ip)%dmode == 0) then
      do k = 1, b%struct(ip)%ncin
        i = b%struct(ip)%cin(1,k)
        j = b%struct(ip)%cin(2,k)
        if (j < dcp%js .or. j > dcp%je) cycle
        if (sx%h1(i,j) > 0.0) then
          vabs_row(j) = vabs_row(j) + real(sx%h1(i,j) * g%gv(i,j) * g%dx * g%dy, r64)
          sx%h1(i,j) = 0.0
        end if
      end do
      call dam_sink(b, ip, p, vabs_row)
      cycle
    end if
    do k = 1, b%struct(ip)%ncin
      i = b%struct(ip)%cin(1,k)
      j = b%struct(ip)%cin(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle
      if (sx%h1(i,j) > 0.0) then
        vola = sx%h1(i,j) * g%gv(i,j) * g%dx * g%dy
        s%hrs(i,j) = s%hrs(i,j) + sx%h1(i,j)
        sx%h1(i,j) = 0.0
        vabs_row(j) = vabs_row(j) + real(vola, r64)
      end if
      vrow(j) = vrow(j) + real(s%hrs(i,j) * g%gv(i,j) * g%dx * g%dy, r64)
    end do
    call dam_operate(b, ip, p, g, s, vabs_row, vrow, vdraw)
    if (vdraw > 0.0) then
      qcell = vdraw / (b%struct(ip)%ncout * g%dx * g%dy)
      do k = 1, b%struct(ip)%ncout
        i = b%struct(ip)%cout(1,k)
        j = b%struct(ip)%cout(2,k)
        if (j < dcp%js .or. j > dcp%je) cycle
        sx%h1(i,j) = sx%h1(i,j) + qcell / g%gv(i,j)
      end do
    end if
  end do

end subroutine


!----------------------------------------------------------------------
! エッジの流速・流量(uv/mn1)への強制条件の適用点
!   momentum(内部面の計算)と continuous(h1 更新)の間、
!   par_edge_merge の後に毎ステップ無条件に呼ばれる。強制条件の族を
!   追加する場合はこのルーチンに節を足し、有効判定は節の内側で行う
!   (将来の候補: カルバート出入り口等)。
!   現在の節: 節1=外縁4辺の辺境界(自由流出/長波放射)、
!   節2=区間流入(外縁法線面の流量規定)。
!
! 辺境界の節: 開いた辺の境界面に段落ち式の流速・流量をセットする。
!   continuous / restore_uvmn 側は bc_open_face が真の面を
!   取り込むことで、流出が h1 と u,v,m,n に乗る。
!   - 境界面の書き手はこのルーチンだけ(momentum は x 番兵で触れない)。
!     開いた辺の面は乾燥時も 0 を毎ステップ書く(前ステップ値の残留防止)
!   - 面集合は辺を横切る法線+斜めの3方位(開口の合計=辺全長。
!     boundary_plan.md 案D)。角セルの斜め面は bc_open_face が
!     「両辺 open」を要求するため壁の水密性が保たれる
!   - 符号: スロットの正準向きは k=1..4 所有者基準なので、sign_e(k) を
!     乗じて格納する(continuous が読むと外向き正になる)
!   - MPI: 東西辺はスロット行 js-1..je を書く(mn コミット範囲と同一)。
!     共有行 js-1 / je のスロットは隣接する両ランクが同じ h(ハロ)から
!     冗長に計算して同値になる。界面補完(par_edge_merge)は境界面
!     スロットを運ばないため、この冗長書きが RK の他セル面参照の
!     ランク数不変性の条件になる。南北辺の面はスロット行 0 / ny で
!     端ランクの単独所有(冗長書き不要)
!----------------------------------------------------------------------
module subroutine boundary_uvmn(p, g, b, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(inout) :: sx

  integer :: i, j
  integer :: ifl, m, k, sd, ie, je
  integer :: ncseg
  real :: qw, qwm, wsum, hmx, frw, alpha, h, hc, he, uve1, mne1
  logical :: blend
  ! 各辺を横切る面の方位(1番目が法線、2・3番目が斜め)
  integer, parameter :: kfw(1:3) = [4, 1, 6]   ! 西辺(セル (1,j))
  integer, parameter :: kfe(1:3) = [5, 3, 8]   ! 東辺(セル (nx,j))
  integer, parameter :: kfn(1:3) = [2, 1, 3]   ! 北辺(セル (i,1))
  integer, parameter :: kfs(1:3) = [7, 6, 8]   ! 南辺(セル (i,ny))

  ! ==== 節1: 外縁4辺の辺境界(簡易流出) ====
  if (have_open_bc) then

    ! 西辺・東辺(全ランクが自帯+共有行のセル js-1..je+1 を走査。
    ! ハロ行のセルは共有行スロットの冗長計算のため。put 側のスロット行
    ! フィルタが書き込み範囲を js-1..je に制限する)
    if (f_bc_side(e_side_w) /= e_bc_wall) then
      do j = max(dcp%js - 1, 1), min(dcp%je + 1, dcp%ny_g)
        call put_bc_faces(p, g, s, sx, 1, j, kfw, e_side_w)
      end do
    end if
    if (f_bc_side(e_side_e) /= e_bc_wall) then
      do j = max(dcp%js - 1, 1), min(dcp%je + 1, dcp%ny_g)
        call put_bc_faces(p, g, s, sx, dcp%nx_g, j, kfe, e_side_e)
      end do
    end if

    ! 北辺・南辺(行の所有ランクのみ。判定は全ランクが同一コードで実行)
    ! 角の斜め面は複数辺のループが書く(idempotent: 辺の条件が同型なら
    ! 同値。異なる場合は後に処理される N/S 辺の式が有効になる)
    if (f_bc_side(e_side_n) /= e_bc_wall .and. dcp%js <= 1 .and. 1 <= dcp%je) then
      do i = g%wx(1,1), g%wx(2,1)
        call put_bc_faces(p, g, s, sx, i, 1, kfn, e_side_n)
      end do
    end if
    if (f_bc_side(e_side_s) /= e_bc_wall .and. dcp%js <= dcp%ny_g .and. dcp%ny_g <= dcp%je) then
      do i = g%wx(1,dcp%ny_g), g%wx(2,dcp%ny_g)
        call put_bc_faces(p, g, s, sx, i, dcp%ny_g, kfs, e_side_s)
      end do
    end if

  end if

  ! ==== 節2: 区間流入(外縁の法線面に流量を規定) ====
  !   規定流量は区間内で按分して与える。按分は重みの正規化(Σ=Q)で
  !   行うため、どのモードでも総流入量は厳密。
  !     dist=0: 開口幅で均等按分(単位幅流量 qw = Q/W_seg が区間一様)
  !     dist=1: 水深按分(qw_m = Q·h_m/Σ(h·w)。wet セルで流入流速が一様)
  !     dist=2: 通水能按分(重み h^{5/3}。マニング則の等勾配断面と同じ
  !             配分で、深いセルほど流速も大きい)
  !   dist=1,2 は均等按分と連続ブレンドして適用する:
  !     fr = u_max/sqrt(g·h_max)(最深セルに全面按分したときの流速比)
  !     α  = clamp(2·(1 − fr), 0, 1)(fr<=0.5 で 1、fr>=1 で 0、間は線形)
  !     qw_m = α·(重み按分) + (1−α)·(均等按分)
  !   配分が現在の h の連続関数になるため、モード切替の不連続・振動が
  !   原理的に存在せず、記憶する状態もない(リスタート往復も厳密)。
  !   乾いた断面・薄膜だけの断面・退水時は fr が大きく自動的に均等側に
  !   寄る(薄膜断面で最深セルへの流量集中がダム崩壊流を起こして発散
  !   する実挙動への安定化を兼ねる。α·fr = 2fr(1−fr) <= 1/2 なので
  !   最深セルの配分流量は常に限界流量の半分以下)。wet 率による切替は
  !   行わない(低水時に澪筋だけが wet の状態が本モードの主用途のため)。
  !   重みの h は前ステップの s%h(スキームの他項と同じ時刻レベル)。
  !   h < dd のセルへの重み側の配分はゼロ。
  !   節1の後に適用し、開いた辺上の流入区間では辺の式を上書きする。
  !   面の取り込みは bt_cell(e_bc_inflow)経由で bc_open_face が開く。
  !   MPI: 東西辺のスロット行=セル行なので、共有行 js-1 はハロの h から
  !   冗長計算する(節1と同じ規則)。南北辺は行の所有ランクのみ。
  !   重みの水深は「所有ランクだけが埋めるゼロ初期化ベクトル+全ランク
  !   実数和」で全ランクに同値を配る(1要素1寄与なので加算順に依存せず
  !   ビット決定的。par_allreduce_sumr の頭書き参照)。collective なので
  !   実行判定(dist, q)は全ランク同値の量だけで行う(§5)
  do ifl = 1, b%ninflow
    ncseg = b%inflow(ifl)%ncell

    ! 重み按分の準備(重みベクトルの共有とブレンド係数 α の決定)
    blend = (b%inflow(ifl)%dist > 0 .and. b%inflow(ifl)%q > 0.0)
    alpha = 0.0
    wsum = 0.0
    if (blend) then
      infl_hseg(1:ncseg) = 0.0
      do m = 1, ncseg
        j = b%inflow(ifl)%cell(2,m)
        if (j < dcp%js .or. j > dcp%je) cycle       ! 所有ランクだけが埋める
        infl_hseg(m) = s%h(b%inflow(ifl)%cell(1,m), j)
      end do
      call par_allreduce_sumr(infl_hseg(1:ncseg))
      do m = 1, ncseg
        h = infl_hseg(m)
        if (h < p%dd) cycle
        wsum = wsum + wgt_dist(h, b%inflow(ifl)%dist) &
                      * l8(kn_side(b%inflow(ifl)%side(m)))
      end do
      if (wsum > 0.0) then
        ! 最深セルに全面按分したときの流速比(フルード数)から α を決める
        hmx = maxval(infl_hseg(1:ncseg))
        frw = b%inflow(ifl)%q * wgt_dist(hmx, b%inflow(ifl)%dist) / wsum &
              / (hmx * sqrt(p%gg * hmx))
        alpha = min(1.0, max(0.0, 2.0 * (1.0 - frw)))
      end if
    end if

    if (b%inflow(ifl)%q <= 0.0) then
      qw = 0.0
    else
      qw = b%inflow(ifl)%q / infl_wseg(ifl)     ! 均等按分の単位幅流量 (m2/s)
    end if
    do m = 1, ncseg
      i = b%inflow(ifl)%cell(1,m)
      j = b%inflow(ifl)%cell(2,m)
      sd = b%inflow(ifl)%side(m)
      select case (sd)
        case (e_side_w, e_side_e)
          if (j < dcp%js - 1 .or. j > dcp%je) cycle   ! スロット行=セル行
        case default
          if (j < dcp%js .or. j > dcp%je) cycle       ! 行の所有ランクのみ
      end select
      k = kn_side(sd)
      ie = i + die(k)
      je = j + dje(k)
      ! 面エントリの単位幅流量(重み側は dry 面ゼロ、均等側と α で
      ! ブレンド。α=0 なら qwm = qw に厳密に一致)と参照水深。
      ! ブレンド時の h は共有ベクトルから引く(共有行の冗長書きが両ランク
      ! でビット同値になる条件。dist=0 は従来どおりハロの s%h)
      if (blend) then
        h = infl_hseg(m)
        if (h < p%dd) then
          qwm = (1.0 - alpha) * qw
        else
          qwm = alpha * (b%inflow(ifl)%q * wgt_dist(h, b%inflow(ifl)%dist) / wsum) &
                + (1.0 - alpha) * qw
        end if
      else
        qwm = qw
        h = s%h(i,j)
      end if
      ! エッジ水深: 内側セルの水深に限界水深の床を敷く(乾床への流入で
      ! uv1 = q/he が発散しないように。ネスティングが水深も渡す事情の
      ! 簡易代替。boundary_plan.md)
      hc = (qwm**2 / p%gg)**(1.0 / 3.0)
      he = max(h, hc, p%dv)
      uve1 = -qwm / he           ! 外向き正の負値=流入
      mne1 = -qwm
      sx%uv(ke(k), ie, je) = sign_e(k) * uve1
      sx%mn1(ke(k), ie, je) = sign_e(k) * mne1
    end do
  end do

end subroutine


!----------------------------------------------------------------------
! 区間流入の配分モード別の重み(dist=1: 水深、dist=2: 通水能 h^{5/3})
!----------------------------------------------------------------------
function wgt_dist(h, dist) result(w)
  real, intent(in) :: h
  integer, intent(in) :: dist
  real :: w
  if (dist >= 2) then
    w = h**(5.0 / 3.0)
  else
    w = h
  end if
end function
!----------------------------------------------------------------------
! セル (i,j) の、辺 sd を横切る面 kf(1:3) に辺境界の値を書く。
! エッジ水深は外縁内側セルの水深 h をそのまま使う(質量は mn1 だけで
! 決まり厳密。uv は診断・移流参照用の同階層近似)。
! boundary_uvmn の contained にせず引数渡しの submodule 手続きとする:
! nvfortran は module 手続きの contained 内側への親 private の
! 二段ホスト結合を解決できない(TPR #27323 系。din 等が未宣言エラーに
! なる実発生)。単段のホスト結合(adv と同形)は解決できる
!----------------------------------------------------------------------
subroutine put_bc_faces(p, g, s, sx, i, j, kf, sd)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(inout) :: sx
  integer, intent(in) :: i, j
  integer, intent(in) :: kf(1:3)
  integer, intent(in) :: sd
  integer :: m, k, in, jn, ie, je
  real :: h, un, uc, eta_r, uve1, mne1, dh, cor

  if (g%x(i,j) <= 0) return
  if (g%sw(i,j) > 0) return    ! 海セルは continuous が更新しないため対象外
  h = s%h(i,j)
  do m = 1, 3
    k = kf(m)
    in = i + din(k)
    jn = j + djn(k)
    if (.not. bc_open_face(in, jn)) cycle  ! 角の斜め面は両辺 open が条件
    ie = i + die(k)
    je = j + dje(k)
    ! スロット行が自ランクの書き込み範囲(js-1..je)外ならスキップ
    if (je < dcp%js - 1 .or. je > dcp%je) cycle
    if (h < p%dd) then
      uve1 = 0
      mne1 = 0
    else
      select case (f_bc_side(sd))
      case (e_bc_outflow)
        ! 自由流出(洪水向け): 前進してきた流れは自速度のまま通過させ
        ! (段落ち式が射流を絞って堰き止めるのを防ぐ)、滞留水は
        ! 段落ち(自由越流。rivermouth_drop と同式)で抜く。
        ! max により流入は起きない(uc > 0)
        un = s%u(i,j) * n8x(k) + s%v(i,j) * n8y(k)   ! セル流速の面法線成分
        uc = ((2. / 3.)**(3. / 2)) * sqrt(p%gg * h)  ! 段落ち速度
        uve1 = max(un, uc)
        mne1 = uve1 * h
      case default   ! e_bc_radiation
        ! 長波放射(津波向け): 静水(η=η_ref)ではフラックスゼロ、
        ! 水位偏差に比例して透過。負値=流入(引き波)も許す。
        ! 乾いたセルは上の h<dd 分岐でゼロ(境界からの再湿潤はしない)。
        ! 基準水位は境界セルごと(W/E は j、N/S は i で引く)
        if (sd == e_side_w .or. sd == e_side_e) then
          eta_r = bc_eta_cell(j, sd)
        else
          eta_r = bc_eta_cell(i, sd)
        end if
        uve1 = sqrt(p%gg / max(h, p%dv)) * (s%z(i,j) + h - eta_r)
        mne1 = uve1 * h
      end select
      ! 過大な流出の抑制(流出方向のみ。momentum の抑制と同型で、
      ! 境界面ではフラグによらず適用)
      dh = mne1 * mn2dh(k) / g%gv(i,j)
      if (have_width) dh = dh / wfrac(i,j)
      if (dh > 0 .and. h - dh <= 0) then
        cor = max(h - p%dd, 0.0) / dh
        uve1 = uve1 * cor
        mne1 = mne1 * cor
      end if
    end if
    sx%uv(ke(k), ie, je) = sign_e(k) * uve1
    sx%mn1(ke(k), ie, je) = sign_e(k) * mne1
  end do
end subroutine


!----------------------------------------------------------------------
! 近傍 (in,jn) が格子枠外で、その面が横切る辺が全て開いているか。
! 型はセル別(bt_cell)で引く: 法線面のゴースト(枠外座標が1軸のみ)は
! 対応するセルの面型を参照し、流入区間の上書き(e_bc_inflow)が効く。
! 角の斜め面はゴースト座標が両軸とも枠外になり、添字が範囲外の辺は
! 辺の型(f_bc_side)に落ちる=従来どおり両辺 open が条件(壁の水密性)。
! 枠内の x=0(無効セル)への面は常に閉(偽を返す)
!----------------------------------------------------------------------
module function bc_open_face(in, jn) result(op)
  integer, intent(in) :: in, jn
  logical :: op
  op = (in < 1 .or. in > dcp%nx_g .or. jn < 1 .or. jn > dcp%ny_g)
  if (.not. op) return
  if (in < 1        .and. bc_face_type(e_side_w, jn) == e_bc_wall) op = .false.
  if (in > dcp%nx_g .and. bc_face_type(e_side_e, jn) == e_bc_wall) op = .false.
  if (jn < 1        .and. bc_face_type(e_side_n, in) == e_bc_wall) op = .false.
  if (jn > dcp%ny_g .and. bc_face_type(e_side_s, in) == e_bc_wall) op = .false.
end function


!----------------------------------------------------------------------
! 辺 sd の添字 idx における外縁面の型を返す
! (idx が範囲外=角のゴーストは辺の型に落とす)
!----------------------------------------------------------------------
function bc_face_type(sd, idx) result(t)
  integer, intent(in) :: sd, idx
  integer :: t
  if (allocated(bt_cell) .and. idx >= 1 .and. idx <= size(bt_cell, 1)) then
    t = bt_cell(idx, sd)
  else
    t = f_bc_side(sd)
  end if
end function

end submodule
