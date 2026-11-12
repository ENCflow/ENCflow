module m_driftwood
  ! ================= 流木プロセスモジュール(§50) =================
  ! 流木をセルごとの柱状材積 (m3/m2 = m) のオイラー的なラスタ場として
  ! 概算する加算的プロセス。個別流木のラグランジュ追跡・幾何的閉塞・
  ! 衝突力は対象外(§0 方針2。docs/driftwood_plan.md §1)。
  !   台帳:   立木ストック wst(私有。幾何面積基底 m3/m2)→ 流木化 →
  !           流動流木 s%hd(柱状量。貯留の意味論は h・hs と同一)→
  !           接地・乾燥 → 堆積流木 s%wd(柱状量。再流動あり)
  !   輸送:   浮遊砂と同じ保存輸送カーネル(advect_scalar)を swflow_enc が
  !           ステップ内で実行(s%dw_active)。本モジュールは発生・停止・
  !           再流動・台帳・診断を担う(セル局所のみ = エッジ・ハロ・
  !           collective 不要)
  !   有効化: fn_driftwood の指定(&list_driftwood。f_dw=0 で一時無効化)。
  !           ENC 格子のみ。無効時はメモリ・CPU ゼロ追加
  !   発生:   (a) 水理的流失 — wst>0 かつ h+hs>dw_hrec かつ vv>dw_vrec で
  !           wst→hd をレート dw_wrec(数値的閉包【独自】・閾値は
  !           校正パラメータ。§50.5)。(b) 侵食連行 — 累積侵食深 zref−z が根系深
  !           dw_droot を超えたセルの wst 全量→hd(zref は init 時 z の
  !           私有写し。z 低下の事実だけを見るため f_fluvial/f_debris/
  !           f_slide/f_release のどの侵食・崩壊とも自動連動)
  !   停止:   喫水 hf = 円柱の浮力平衡の厳密解(Braudrick & Grant 2000
  !           式(23)(6)。sg・D の線形近似でなく円形セグメント面積で解く)。
  !           h+hs < hf または vv < dw_vstop で hd→wd をレート dw_wstop
  !           (f_dbstop=1 と同型の数値的閉包)。乾燥セル(h≤dd)は全量。
  !           再流動は h+hs > dw_rfloat・hf かつ vv > dw_vfloat で wd→hd
  !           レート dw_wfloat(既定 0 = なし)。wd は z に足さない
  !   既定:   物性・校正値は未指定なら既定を採用し、採用値を必ず 1 行表示する
  !           (§62 の gm_param と同じ流儀。dw_param)。立木ストックは両方未指定
  !           なら陸のセル一様に 0.001 m3/m2(針葉樹渓流の発生流木量の包絡
  !           §50.5)。発生は両方未指定なら水理的流失・侵食連行とも既定で有効、
  !           片方だけ指定なら他方は無効(明示の尊重)。最小入力は fn_driftwood
  !           (空の &list_driftwood)だけ(§50.6)
  !   運動量: 流動流木 hd・堆積流木 wd は、運動量・抵抗に算入しない(§50)
  !   集積:   捕捉率 E の分布 fn_dwtrap を与えると、捕捉セルを通る流動流木を
  !           集積流木 s%wj(柱状量。hd と同じ基底。動かない)へ移す。よく混ざった
  !           セルの滞留時間 Δx/|V| に対して、1 ステップの捕捉量は
  !           hd·r/(1+r)、r = E/(1−E)·|V|Δt/Δx(E >= 1 は全量。捕捉の規則は【独自】)。
  !           集積量が dw_jamgrow を超えたセルは E = 1(任意)。f_dwjam = 1(既定)
  !           では、集積を多孔質の障害物として、辺の半陰の抗力項
  !           −κ0·min(w_e/h_f, φ)·|V|、κ0 = 2 C_D/(π d (1−φ)³) を swflow_enc が足す
  !           (係数の構造は Follett ら 2020 の C_A = L C_D a/(1−φ)³。離散化は【独自】。
  !           C_D・φ は校正値。本モジュールは係数と有効フラグを s%dw_jamk・
  !           s%dw_jamphi・s%dw_jam に書く。§50.7・docs/woodjam_plan.md)。
  !           fn_dwtrap を与えなければ、確保も分岐の中の計算もしない。
  !           カルバートの流入口(&list_struct_culvert の culv_jam = 1。§50.8): その
  !           カルバートが取水している側のセル群の流動流木を、全量、集積流木へ移す
  !           (カルバートは流木を通さないので、届いた流木は流入口に溜まる)。集積の損失は
  !           m_boundary の structure_makebdc が s%wj を読んで流量則に入れる
  !   ダム:   捕捉帯セルは毎ステップ全量吸収されるため、流動流木 hd も
  !           同伴してダム別台帳へ移す(m_wq と同じ契約。放流流木 0 =
  !           既知の妥協。堆積 wd は接地済みのため残す)
  !   save:   s%hd, s%wd, wst, zref をモジュール私有ファイル driftwood.dat
  !           で保存(§7 の契約C。state.dat の形式は不変)。fn_dwtrap を与えた
  !           ときだけ、末尾に集積の印(整数 1)と s%wj を追記する
  !   診断:   result/driftwood.csv(発生・堆積・再流動・ダム捕捉の累積と
  !           現在貯留。系外流出は収支残差。rank0、dt_recrd 間隔。
  !           総和は par_sum_rows = 決定的)。fn_dwtrap を与えたときだけ、捕捉の
  !           累積 trap_m3 と現在の集積 vol_jam_m3 の 2 列が末尾に増える
  !   出力:   f_out_hd(流動 Hd0001…)、f_out_wd(堆積 Wd0001… +
  !           期間最大到達量 Wd9999 = max(hd+wd)。統計は save 対象外)、
  !           f_out_wj(集積 Wj0001…。fn_dwtrap 必須)
  ! ================================================================
  use iso_fortran_env, only : real64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_boundary, only : t_boundary, e_struct_dam, e_struct_culvert
  use list_driftwood, only : t_list_driftwood, list_driftwood_read
  use m_swflow_enc, only : chn
  use m_fileio, only : fileio_read_matrix
  use m_restart, only : restart_write_cell, restart_read_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : dcp, is_root, par_info, par_stop, par_abort, par_sum_rows, &
                         par_gather_to, par_scatter_cell, par_allreduce_sumi
  use m_util, only : itoa, rtoa, param_default, es_out
  implicit none
  private
  public :: t_driftwood
  public :: m_driftwood_init
  public :: m_driftwood_calc
  public :: m_driftwood_record
  public :: m_driftwood_dispose
  public :: m_driftwood_draft

  ! ダム捕捉台帳(m_wq の t_wqdam と同型)
  type t_dwdam
    integer :: ist = 0                   ! b%struct のインデックス
    integer :: nc = 0                    ! 自帯内の捕捉帯セル数
    integer, allocatable :: cells(:,:)
  end type

  type t_driftwood
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.
    logical :: initialized = .false.
    real :: hf = 0.0                     ! 喫水 (m)。円柱の浮力平衡の厳密解
                                         !   (B&G2000 式(23)(6)。init で二分法)
    logical :: have_hyd = .false.        ! 水理的流失の有効
    real :: wrec = 0.0                   ! 水理的流失レート (m/s)
    real :: hrec = 0.0                   ! 水理的流失の水深閾値 (m。h+hs)
    real :: vrec = 0.0                   ! 水理的流失の流速閾値 (m/s)
    logical :: have_ero = .false.        ! 侵食連行の有効
    real :: droot = 0.0                  ! 根系深 (m)
    real :: wstop = 0.0                  ! 接地堆積レート (m/s)
    real :: vstop = 0.0                  ! 低速堆積の流速閾値 (m/s。0=水深のみ)
    logical :: have_flt = .false.        ! 再流動の有効
    real :: wfloat = 0.0                 ! 再流動レート (m/s)
    real :: hfloat = 0.0                 ! 再流動の水深閾値 (m) = dw_rfloat・hf(導出)
    real :: vfloat = 0.0                 ! 再流動の流速閾値 (m/s)
    real, allocatable :: wst(:,:)        ! 立木ストック (m3/m2。幾何面積基底 =
                                         !   セル内材積 wst×A。帯 jsh:jeh で確保
                                         !   するが更新・参照は js:je のみ)
    real, allocatable :: zref(:,:)       ! 侵食連行の基準地形 (m。init 時 z の写し)
    logical :: have_jam = .false.        ! 集積流木 s%wj あり(fn_dwtrap の指定、または
                                         !   culv_jam = 1 のカルバート。台帳の列・保存の対象)
    logical :: have_trap = .false.       ! 捕捉セルあり(fn_dwtrap の指定)
    real, allocatable :: trap(:,:)       ! 捕捉率 E(0〜1。have_trap のときだけ確保)
    integer :: nculv = 0                 ! 流入口で流木を捕捉するカルバートの数
    type(t_dwdam), allocatable :: culv(:)   ! そのセル(自帯内。cells(3,k) = 1: 取水セル群 cin、
                                         !   2: 吐口セル群 cout。ist は b%struct の番号)
    real :: jamgrow = -1.0               ! 集積量 (m3/m2) がこれを超えたセルは E = 1
                                         !   (<= 0 は無効 = 捕捉率は一定)
    integer :: ndam = 0
    type(t_dwdam), allocatable :: dam(:)
    ! 診断(行部分和 real64。材積 m3)
    real(real64), allocatable :: vrow(:,:)  ! (js:je, 1:6) 1=水理的流失 2=侵食連行
                                            !   3=堆積(hd→wd) 4=再流動(wd→hd)
                                            !   5=ダム捕捉 6=構造物での捕捉(hd→wj。
                                            !   have_jam のときだけ集計・出力する)
    integer :: un = 0                    ! CSV 装置番号(rank0)
  end type

contains


!----------------------------------------------------------------------
! 流木モジュールを初期化する
!   fn_driftwood 未指定 or f_dw=0 なら何もしない(enabled = .false.)。
!   s%dw_active を立てるため swflow init より前・m_geomorph_init より後
!   (morfac の検査に s%geo_morfac を使う)に呼ぶこと。
!   セル検証はゾーン2(全域 x/sw が使える帯縮小前)で行う
!----------------------------------------------------------------------
subroutine m_driftwood_init(dw, p, g, b, s)
  type(t_driftwood), intent(out) :: dw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b      ! ダム捕捉台帳の構築
  type(t_state), intent(inout) :: s      ! hd/wd の確保と dw_active
  type(t_list_driftwood) :: list
  integer :: j, nb
  integer :: nbv(1)
  real :: dlog, sg

  if (len_trim(p%fn_driftwood) == 0) then
    ! 流木出力は本モジュールが前提(§28.9 の f_out_hs と同じ様式)
    if (p%f_out_hd > 0 .or. p%f_out_wd > 0 .or. p%f_out_wj > 0) then
      call par_stop("list_sysparam: f_out_hd/f_out_wd/f_out_wj require the driftwood module " &
                    //"(fn_driftwood)")
    end if
    if (njam_culverts(b) > 0) then
      call par_stop("list_struct_culvert: culv_jam = 1 requires the driftwood module " &
                    //"(fn_driftwood)")
    end if
    return
  end if
  if (p%f_gridsystem /= 0) then
    call par_stop("list_driftwood: the driftwood module supports the ENC grid only " &
                  //"(same restriction as suspended sediment)")
  end if

  call list_driftwood_read(p, list)
  if (list%f_dw == 0) then      ! fn を書いたまま一時無効化する経路
    if (p%f_out_hd > 0 .or. p%f_out_wd > 0 .or. p%f_out_wj > 0) then
      call par_stop("list_sysparam: f_out_hd/f_out_wd/f_out_wj require the driftwood module " &
                    //"(f_dw=0 disables it)")
    end if
    if (njam_culverts(b) > 0) then
      call par_stop("list_struct_culvert: culv_jam = 1 requires the driftwood module " &
                    //"(f_dw=0 disables it)")
    end if
    return
  end if

  ! --- 代表諸元(喫水の実体。既定あり。§50.6) ---
  dlog = dw_param("dw_dlog", list%dw_dlog, 0.3, " m")
  if (dlog <= 0.0) call par_stop("list_driftwood: dw_dlog must be > 0")
  sg = dw_param("dw_sglog", list%dw_sglog, 0.5, "")
  if (sg <= 0.0 .or. sg >= 1.0) then
    call par_stop("list_driftwood: dw_sglog must be in (0,1) — the module assumes " &
                  //"floatable wood (sinking logs are out of scope)")
  end if
  ! 喫水(浮遊限界水深)は円柱の浮力平衡の厳密解(m_driftwood_draft。§50.4)
  dw%hf = m_driftwood_draft(sg, dlog)

  ! --- 発生: 両方未指定なら水理的流失・侵食連行とも既定で有効(侵食連行は
  !     地形が動かなければ発火しない = 無害)。片方だけ指定なら他方は無効 ---
  if (list%dw_wrec <= -9998.0 .and. list%dw_droot <= -9998.0) then
    dw%wrec = dw_param("dw_wrec", list%dw_wrec, 1.0e-5, " m/s")
    dw%hrec = dw_param("dw_hrec", list%dw_hrec, 0.5, " m")
    dw%vrec = dw_param("dw_vrec", list%dw_vrec, 1.0, " m/s")
    dw%have_hyd = .true.
    dw%droot = dw_param("dw_droot", list%dw_droot, 0.5, " m")
    dw%have_ero = .true.
  else
    if (list%dw_wrec > -9998.0) then
      if (list%dw_wrec <= 0.0) call par_stop("list_driftwood: dw_wrec must be > 0")
      dw%wrec = list%dw_wrec
      dw%hrec = dw_param("dw_hrec", list%dw_hrec, 0.5, " m")
      dw%vrec = dw_param("dw_vrec", list%dw_vrec, 1.0, " m/s")
      if (dw%hrec < 0.0) call par_stop("list_driftwood: dw_hrec must be >= 0")
      if (dw%vrec < 0.0) call par_stop("list_driftwood: dw_vrec must be >= 0")
      dw%have_hyd = .true.
    end if
    if (list%dw_droot > -9998.0) then
      if (list%dw_droot <= 0.0) call par_stop("list_driftwood: dw_droot must be > 0")
      dw%droot = list%dw_droot
      dw%have_ero = .true.
    end if
  end if

  ! --- 停止・堆積(既定あり)---
  dw%wstop = dw_param("dw_wstop", list%dw_wstop, 0.01, " m/s")
  if (dw%wstop <= 0.0) call par_stop("list_driftwood: dw_wstop must be > 0")
  if (list%dw_vstop < 0.0) call par_stop("list_driftwood: dw_vstop must be >= 0")
  dw%vstop = list%dw_vstop

  ! --- 再流動(既定 dw_wfloat=0 = なし。ヒステリシスの検証つき)---
  if (list%dw_wfloat < 0.0) call par_stop("list_driftwood: dw_wfloat must be >= 0")
  if (list%dw_wfloat > 0.0) then
    if (list%dw_rfloat <= 1.0) then
      call par_stop("list_driftwood: dw_rfloat must be > 1 (hysteresis against " &
                    //"per-step deposit/refloat oscillation)")
    end if
    if (list%dw_vfloat <= -9998.0) then
      call par_stop("list_driftwood: dw_wfloat requires dw_vfloat (m/s)")
    end if
    if (list%dw_vfloat < dw%vstop) then
      call par_stop("list_driftwood: dw_vfloat must be >= dw_vstop (hysteresis)")
    end if
    dw%wfloat = list%dw_wfloat
    dw%hfloat = list%dw_rfloat * dw%hf
    dw%vfloat = list%dw_vfloat
    dw%have_flt = .true.
  end if

  ! --- 流木はイベント量であり地形時間の加速と整合しない(f_debris と同じ) ---
  if (s%geo_morfac /= 0.0 .and. s%geo_morfac /= 1.0) then
    call par_stop("list_driftwood: the driftwood module requires morfac=1 " &
                  //"(event-scale computation)")
  end if

  ! --- 立木ストック(一様 dw_stock0 か分布 fn_dwstock の排他。両方未指定なら
  !     陸のセル一様に既定 0.001 m3/m2 = 「とりあえず動かす」の最小入力(§50.6)。
  !     分布は rank0 読み+帯 scatter。方式2) ---
  if (len_trim(list%fn_dwstock) > 0 .and. list%dw_stock0 > -9998.0) then
    call par_stop("list_driftwood: specify the standing stock by either dw_stock0 " &
                  //"(uniform) or fn_dwstock (map), not both")
  end if
  allocate(dw%wst(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (len_trim(list%fn_dwstock) > 0) then
    call read_stock_scatter(p, g, list%fn_dwstock, dw%wst)
  else
    if (list%dw_stock0 > -9998.0) then
      if (list%dw_stock0 < 0.0) call par_stop("list_driftwood: dw_stock0 must be >= 0")
      dw%wst(:,:) = list%dw_stock0
    else
      ! 既定: 陸(海でない)の使用セル一様。針葉樹渓流の発生流木量の実績
      ! 包絡 1,000 m3/km2(§50.5)。採用セル数を表示する
      dw%wst(:,:) = 0.001
      nb = 0
      do j = dcp%js, dcp%je
        nb = nb + count(g%x(1:g%nx,j) > 0 .and. g%sw(1:g%nx,j) == 0)
      end do
      nbv(1) = nb
      call par_allreduce_sumi(nbv)
      call par_info("driftwood: dw_stock0 = 0.001 m3/m2 on land cells (default; " &
                    //itoa(nbv(1))//" cells)")
    end if
    ! 域外セルにはストックを置かない(台帳集計・出力と整合)
    block
      integer :: i3, j3
      do j3 = dcp%jsh, dcp%jeh
        do i3 = 1, g%nx
          if (g%x(i3,j3) <= 0) dw%wst(i3,j3) = 0.0
        end do
      end do
    end block
  end if
  ! 海セルには立木を置かない(発生の sw 除外と整合。ゾーン2 = sw は全域)
  block
    integer :: i2, j2
    do j2 = dcp%jsh, dcp%jeh
      do i2 = 1, g%nx
        if (g%sw(i2,j2) > 0) dw%wst(i2,j2) = 0.0
      end do
    end do
  end block

  ! --- 状態の確保 ---
  allocate(s%hd(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%wd(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (p%f_out_wd > 0) then
    allocate(s%wdmax(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  end if
  ! 侵食連行の基準地形(init 時 z の写し。海セルの潮位追随 z は
  ! 対象外セルのため影響しない)
  allocate(dw%zref(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  do j = dcp%jsh, dcp%jeh
    dw%zref(:,j) = s%z(:,j)
  end do

  ! --- 構造物での捕捉と集積(fn_dwtrap の指定、または culv_jam = 1 のカルバートで有効。
  !     §50.7・§50.8)---
  call setup_culv(dw, b)
  if (len_trim(list%fn_dwtrap) > 0 .or. dw%nculv > 0) then
    call setup_jam(dw, p, g, s, list, dlog)
  else if (p%f_out_wj > 0) then
    call par_stop("list_sysparam: f_out_wj requires capture cells of the driftwood module " &
                  //"(fn_dwtrap in list_driftwood, or a culvert with culv_jam = 1)")
  end if

  ! --- ダム捕捉台帳(全ダム・湖沼が対象。m_wq と同型) ---
  call setup_dams(dw, b)

  ! --- リスタート ---
  if (p%f_state_restore > 0) call restore_state(dw, p, g, s)

  allocate(dw%vrow(dcp%js:dcp%je, 1:6), source = 0.0_real64)

  ! --- 診断 CSV(rank0。累積はラン先頭からの積算 = restore でリセット)。捕捉セルを
  !     与えたときだけ、捕捉の累積と現在の集積の 2 列を末尾に足す(§50.7) ---
  if (is_root) then
    open(newunit=dw%un, file=trim(p%dir_result)//"/driftwood.csv", status='replace')
    if (dw%have_jam) then
      write(dw%un, '(a)') "time_s,rec_hyd_m3,rec_ero_m3,deposit_m3,refloat_m3,to_dam_m3," &
                          //"vol_stock_m3,vol_float_m3,vol_deposit_m3,trap_m3,vol_jam_m3"
    else
      write(dw%un, '(a)') "time_s,rec_hyd_m3,rec_ero_m3,deposit_m3,refloat_m3,to_dam_m3," &
                          //"vol_stock_m3,vol_float_m3,vol_deposit_m3"
    end if
  end if

  s%dw_active = .true.
  s%dw_sg = list%dw_sglog              ! 荷重評価用に公開(m_bldgdebris が読む。§63.3)
  dw%enabled = .true.
  dw%initialized = .true.
  call par_info("driftwood module enabled")
end subroutine


!----------------------------------------------------------------------
! 喫水(浮遊限界水深)d_b を返す(m)。円柱の浮力平衡 ρlog・πD²/4 =
! ρw・A_sub(d_b)(Braudrick & Grant 2000, WRR 36(2), 式(23)(6))。A_sub は
! 円形断面の水没セグメント面積で、面積率 f(x) = (θ − sinθ)/(2π)、
! θ = 2acos(1−2x)、x = d/D。f(x) = sg を二分法で解く(単調増加。全ランク
! 同一演算 = 決定的。sg=0.5 は x=0.5 の厳密対称解)。瓦礫モジュール(§63)も
! 同じ関数で喫水を導く
!----------------------------------------------------------------------
function m_driftwood_draft(sg, d) result(hf)
  real, intent(in) :: sg    ! 材(瓦礫)の見かけ比重 (0<sg<1)
  real, intent(in) :: d     ! 代表直径(寸法)(m)
  real :: hf
  real :: xlo, xhi, xm, th
  integer :: k2
  xlo = 0.0
  xhi = 1.0
  do k2 = 1, 60
    xm = 0.5 * (xlo + xhi)
    th = 2.0 * acos(1.0 - 2.0 * xm)
    if ((th - sin(th)) / (2.0 * acos(-1.0)) < sg) then
      xlo = xm
    else
      xhi = xm
    end if
  end do
  hf = 0.5 * (xlo + xhi) * d
end function


!----------------------------------------------------------------------
! 未指定(番兵 −9999)なら既定値を採用し、採用値を必ず 1 行表示する
! (m_geomorph の gm_param と同じ流儀。§62.1。既定なら "(default)" 付き。
!  実体は m_util の param_default(§64)— 接頭辞 "driftwood" の薄い包み)
!----------------------------------------------------------------------
function dw_param(name, val, def, unit) result(eff)
  character(len=*), intent(in) :: name     ! namelist 名(表示用)
  real, intent(in) :: val                  ! namelist の値(番兵 -9999 = 未指定)
  real, intent(in) :: def                  ! 未指定時の既定値
  character(len=*), intent(in) :: unit     ! 単位(先頭に空白。無次元は "")
  real :: eff
  eff = param_default("driftwood", name, val, def, unit, unset=-9999.0)
end function


!----------------------------------------------------------------------
! 構造物での捕捉と集積の初期化(fn_dwtrap の指定、または culv_jam = 1 のカルバートが
! あるとき。§50.7・§50.8。docs/woodjam_plan.md)
!   fn_dwtrap があれば捕捉率 E の分布を読み(使用セルで 0〜1 を検査)、集積流木 s%wj を確保する。
!   f_dwjam = 1 では、集積の抵抗の係数 κ0 = 2 C_D/(π d (1−φ)³) と充填率 φ を
!   s%dw_jamk・s%dw_jamphi に書き、s%dw_jam を立てる(swflow_enc が読む)。
!   係数の構造は Follett ら(2020)の多孔質の障害物の係数 C_A = L C_D a/(1−φ)³
!   (円柱で a = 4φ/(π d))で、C_D・φ は校正値(既定 1.0・0.3 は仮の値)
!----------------------------------------------------------------------
subroutine setup_jam(dw, p, g, s, list, dlog)
  type(t_driftwood), intent(inout) :: dw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_driftwood), intent(in) :: list
  real, intent(in) :: dlog               ! 流木の代表直径 (m。採用値)
  real :: cd, phi

  if (list%f_dwjam /= 0 .and. list%f_dwjam /= 1) then
    call par_stop("list_driftwood: f_dwjam must be 0 (ledger only) or 1 (drag of the jam)")
  end if
  if (len_trim(list%fn_dwtrap) > 0) then
    allocate(dw%trap(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    call read_stock_scatter(p, g, list%fn_dwtrap, dw%trap, name = "fn_dwtrap", vmax = 1.0)
    dw%have_trap = .true.
  end if
  allocate(s%wj(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  dw%have_jam = .true.
  if (dw%nculv > 0) then
    call par_info("driftwood: "//itoa(dw%nculv)//" culvert(s) capture driftwood at the inlet " &
                  //"(culv_jam = 1)")
  end if

  ! 集積が進むと捕捉率が 1 になる集積量(任意。与えたときだけ採用値を表示する)
  if (list%dw_jamgrow > -9998.0) then
    dw%jamgrow = dw_param("dw_jamgrow", list%dw_jamgrow, 0.0, " m3/m2")
    if (dw%jamgrow <= 0.0) call par_stop("list_driftwood: dw_jamgrow must be > 0")
  end if

  if (list%f_dwjam == 1) then
    cd = dw_param("dw_jamcd", list%dw_jamcd, 1.0, "")
    if (cd <= 0.0) call par_stop("list_driftwood: dw_jamcd must be > 0")
    phi = dw_param("dw_jamphi", list%dw_jamphi, 0.3, "")
    if (phi <= 0.0 .or. phi >= 1.0) call par_stop("list_driftwood: dw_jamphi must be in (0,1)")
    s%dw_jamk = 2.0 * cd / (acos(-1.0) * dlog * (1.0 - phi)**3)
    s%dw_jamphi = phi
    s%dw_jam = .true.
    call par_info("driftwood: jam drag coefficient 2 C_D/(pi d (1-phi)^3) = " &
                  //rtoa(s%dw_jamk)//" 1/m")
  else
    call par_info("driftwood: f_dwjam = 0 (jammed wood is a ledger only; no drag on the flow)")
  end if
end subroutine


!----------------------------------------------------------------------
! 立木ストック分布・捕捉率の分布の読み込み(rank0 読み+帯 scatter。使用セルの
! 負値と、vmax を与えたときはそれを超える値はエラー。m_wq の read_map_scatter と
! 同型。name は表示用の namelist 名で、省略時は fn_dwstock)
!----------------------------------------------------------------------
subroutine read_stock_scatter(p, g, fn, a, name, vmax)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn
  real, intent(inout) :: a(dcp%ish:, dcp%jsh:)
  character(len=*), intent(in), optional :: name
  real, intent(in), optional :: vmax
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname, nm
  character(len=1024) :: msg
  logical :: found
  integer :: i, j

  nm = "fn_dwstock"
  if (present(name)) nm = name
  fname = trim(p%dir_data)//"/"//trim(fn)
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("list_driftwood: "//nm//" not found: "//fname)

  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny))
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, wk, p%f_input_mode)
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) <= 0) cycle
        if (wk(i,j) < 0.0) then
          write(msg,'(a,2i7,es12.4)') "list_driftwood: "//nm//" has a negative " &
                                      //"value at cell", i, j, wk(i,j)
          call par_abort(trim(msg))
        end if
        if (present(vmax)) then
          if (wk(i,j) > vmax) then
            write(msg,'(a,es12.4,a,2i7,es12.4)') "list_driftwood: "//nm//" exceeds ", vmax, &
                                                 " at cell", i, j, wk(i,j)
            call par_abort(trim(msg))
          end if
        end if
      end do
    end do
    call par_scatter_cell(wk, a)
  else
    call par_scatter_cell(dum, a)
  end if
end subroutine


!----------------------------------------------------------------------
! 流入口で流木を捕捉するカルバート(culv_jam = 1。§50.8)の数。b%struct は namelist 由来で
! 全ランク同一
!----------------------------------------------------------------------
function njam_culverts(b) result(n)
  type(t_boundary), intent(in) :: b
  integer :: n, ist
  n = 0
  if (.not. allocated(b%struct)) return
  do ist = 1, size(b%struct)
    if (b%struct(ist)%kind == e_struct_culvert .and. b%struct(ist)%jam == 1) n = n + 1
  end do
end function


!----------------------------------------------------------------------
! 流入口で流木を捕捉するカルバートのセルの一覧(自帯分のみ。setup_dams と同型)
!   cells(1:2,k) = セル、cells(3,k) = 1: 取水セル群 cin、2: 吐口セル群 cout。
!   捕捉するのは、そのステップに取水している側だけ(m_driftwood_calc)
!----------------------------------------------------------------------
subroutine setup_culv(dw, b)
  type(t_driftwood), intent(inout) :: dw
  type(t_boundary), intent(in) :: b
  integer :: ist, nc, n, k, kk, i, j, pass

  dw%nculv = njam_culverts(b)
  if (dw%nculv == 0) return

  allocate(dw%culv(1:dw%nculv))
  nc = 0
  do ist = 1, size(b%struct)
    if (b%struct(ist)%kind /= e_struct_culvert .or. b%struct(ist)%jam /= 1) cycle
    nc = nc + 1
    dw%culv(nc)%ist = ist
    do pass = 1, 2                       ! 1: 数える、2: 格納する
      n = 0
      do k = 1, b%struct(ist)%ncin + b%struct(ist)%ncout
        if (k <= b%struct(ist)%ncin) then
          i = b%struct(ist)%cin(1,k)
          j = b%struct(ist)%cin(2,k)
          kk = 1
        else
          i = b%struct(ist)%cout(1,k-b%struct(ist)%ncin)
          j = b%struct(ist)%cout(2,k-b%struct(ist)%ncin)
          kk = 2
        end if
        if (j < dcp%js .or. j > dcp%je) cycle
        n = n + 1
        if (pass == 2) dw%culv(nc)%cells(1:3,n) = [i, j, kk]
      end do
      if (pass == 1) then
        dw%culv(nc)%nc = n
        allocate(dw%culv(nc)%cells(1:3, 1:max(n,1)), source = 0)
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! ダム捕捉台帳の構築(全ダムの捕捉帯セル。自帯分のみ。m_wq と同型)
!----------------------------------------------------------------------
subroutine setup_dams(dw, b)
  type(t_driftwood), intent(inout) :: dw
  type(t_boundary), intent(in) :: b
  integer :: ist, nd, n, k, j

  nd = 0
  if (allocated(b%struct)) then
    do ist = 1, size(b%struct)
      if (b%struct(ist)%kind == e_struct_dam) nd = nd + 1
    end do
  end if
  dw%ndam = nd
  if (nd == 0) return

  allocate(dw%dam(1:nd))
  nd = 0
  do ist = 1, size(b%struct)
    if (b%struct(ist)%kind /= e_struct_dam) cycle
    nd = nd + 1
    dw%dam(nd)%ist = ist
    n = 0
    do k = 1, b%struct(ist)%ncin
      j = b%struct(ist)%cin(2,k)
      if (j >= dcp%js .and. j <= dcp%je) n = n + 1
    end do
    dw%dam(nd)%nc = n
    allocate(dw%dam(nd)%cells(1:2, 1:max(n,1)), source = 0)
    n = 0
    do k = 1, b%struct(ist)%ncin
      j = b%struct(ist)%cin(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle
      n = n + 1
      dw%dam(nd)%cells(1,n) = b%struct(ist)%cin(1,k)
      dw%dam(nd)%cells(2,n) = j
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 流木過程を適用する(毎ステップ。run_main が geomorph calc の後に呼ぶ =
! 同一ステップの z 更新を見た侵食連行)。
!   順序: (0) カルバートの流入口での捕捉(culv_jam) (1) 侵食連行 (2) 水理的流失
!         (2b) 構造物での捕捉(fn_dwtrap) (3) 接地・乾燥堆積 (4) 再流動
!         (5) ダム捕捉 (6) 到達量統計
!   更新は自帯 js..je のセル内交換のみ(owner-compute。近傍を読まない
!   ため 2 パス不要 = §28.2 の適用外)。
!   無効時は no-op。冒頭の return 判定は全ランクで同一 = collective 安全
!----------------------------------------------------------------------
subroutine m_driftwood_calc(dw, p, g, s, b, it)
  type(t_driftwood), intent(inout) :: dw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_boundary), intent(in) :: b      ! カルバートの目標流量 q(取水している側の判定)
  integer, intent(in) :: it
  integer :: i, j, k, nd, side
  real :: hh, w, ee

  if (it < 0) continue  ! 引数未使用の警告を抑制
  if (.not. dw%enabled) return

  ! (0) カルバートの流入口での捕捉(culv_jam = 1。§50.8): カルバートは流木を通さないので、
  !     取水している側のセル群に届いた流動流木を、全量、集積流木へ移す。取水している側は、
  !     このステップの目標流量 q(makebdc の値。全ランク同値)の符号で決める(q > 0: 取水セル群、
  !     q < 0: 吐口セル群。q = 0 は捕捉しない = 水を引いていない流入口には掛からない)
  do nd = 1, dw%nculv
    if (b%struct(dw%culv(nd)%ist)%q == 0.0) cycle
    side = 2
    if (b%struct(dw%culv(nd)%ist)%q > 0.0) side = 1
    do k = 1, dw%culv(nd)%nc
      if (dw%culv(nd)%cells(3,k) /= side) cycle
      i = dw%culv(nd)%cells(1,k)
      j = dw%culv(nd)%cells(2,k)
      if (s%hd(i,j) <= 0.0) cycle
      w = s%hd(i,j)
      s%hd(i,j) = 0.0
      s%wj(i,j) = s%wj(i,j) + w
      dw%vrow(j,6) = dw%vrow(j,6) + vol_col(g, s, i, j, w)
    end do
  end do

  !$omp parallel do schedule(dynamic) private(i, j, hh, w, ee)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      hh = s%h(i,j) + max(s%hs(i,j), 0.0)     ! 混合流動深(判定は h+hs。§50)

      ! (1) 侵食連行: 累積侵食深が根系深を超えたら立木は根系ごと全量流失
      !     (どの侵食・崩壊プロセスの z 低下でも効く。発生後は wst=0 =
      !     再判定は自然に停止)
      if (dw%have_ero .and. dw%wst(i,j) > 0.0) then
        if (dw%zref(i,j) - s%z(i,j) > dw%droot) then
          w = dw%wst(i,j)
          dw%wst(i,j) = 0.0
          s%hd(i,j) = s%hd(i,j) + w / colfac(s, i, j)
          dw%vrow(j,2) = dw%vrow(j,2) + vol_geo(g, w)
        end if
      end if

      ! (2) 水理的流失: 浸水深・流速の閾値超過でレート流失
      !     (レート式は数値的閉包【独自】、閾値は校正パラメータ。§50.5)
      if (dw%have_hyd .and. dw%wst(i,j) > 0.0) then
        if (hh > dw%hrec .and. s%vv(i,j) > dw%vrec) then
          w = min(dw%wst(i,j), dw%wrec * p%dt)
          dw%wst(i,j) = dw%wst(i,j) - w
          s%hd(i,j) = s%hd(i,j) + w / colfac(s, i, j)
          dw%vrow(j,1) = dw%vrow(j,1) + vol_geo(g, w)
        end if
      end if

      ! (2b) 構造物での捕捉(§50.7): 捕捉セルの流動流木を、セルを 1 回通過するうちの割合 E で
      !      集積流木へ移す。よく混ざったセルの滞留時間 Δx/|V| に対して r = E/(1−E)·|V|Δt/Δx、
      !      1 ステップの捕捉量は hd·r/(1+r)(規則は【独自】)。E >= 1 と、集積量が dw_jamgrow を
      !      超えたセルは全量(移流の後に呼ばれるので「入った流木をすべて止める」になる)。
      !      集積は動かない。残った hd は下の接地・乾燥堆積の対象になる
      if (dw%have_trap) then
        if (dw%trap(i,j) > 0.0 .and. s%hd(i,j) > 0.0) then
          ee = dw%trap(i,j)
          if (dw%jamgrow > 0.0) then
            if (s%wj(i,j) > dw%jamgrow) ee = 1.0
          end if
          if (ee >= 1.0) then
            w = s%hd(i,j)
          else
            w = ee / (1.0 - ee) * s%vv(i,j) * p%dt / min(g%dx, g%dy)
            w = s%hd(i,j) * w / (1.0 + w)
          end if
          s%hd(i,j) = s%hd(i,j) - w
          s%wj(i,j) = s%wj(i,j) + w
          dw%vrow(j,6) = dw%vrow(j,6) + vol_col(g, s, i, j, w)
        end if
      end if

      ! (3) 接地・乾燥堆積: 喫水未満・低速でレート堆積、乾燥セルは全量
      !     (suspend の乾燥繰り入れと同型)
      if (s%hd(i,j) > 0.0) then
        if (s%h(i,j) <= p%dd) then
          w = s%hd(i,j)
        else if (hh < dw%hf .or. s%vv(i,j) < dw%vstop) then
          w = min(s%hd(i,j), dw%wstop * p%dt)
        else
          w = 0.0
        end if
        if (w > 0.0) then
          s%hd(i,j) = s%hd(i,j) - w
          s%wd(i,j) = s%wd(i,j) + w
          dw%vrow(j,3) = dw%vrow(j,3) + vol_col(g, s, i, j, w)
        end if
      end if

      ! (4) 再流動: 浮遊余裕率つきの閾値超過でレート再流動(既定なし。
      !     ヒステリシス rfloat>1・vfloat>=vstop は init が検証済み)
      if (dw%have_flt .and. s%wd(i,j) > 0.0) then
        if (hh > dw%hfloat .and. s%vv(i,j) > dw%vfloat) then
          w = min(s%wd(i,j), dw%wfloat * p%dt)
          s%wd(i,j) = s%wd(i,j) - w
          s%hd(i,j) = s%hd(i,j) + w
          dw%vrow(j,4) = dw%vrow(j,4) + vol_col(g, s, i, j, w)
        end if
      end if
    end do
  end do
  !$omp end parallel do

  ! (5) ダム捕捉帯の吸収(水は毎ステップ全量吸収されるため流動流木も
  !     同伴してダム台帳へ。堆積 wd は接地済みのため残す。§50)
  do nd = 1, dw%ndam
    do k = 1, dw%dam(nd)%nc
      i = dw%dam(nd)%cells(1,k)
      j = dw%dam(nd)%cells(2,k)
      if (s%hd(i,j) <= 0.0) cycle
      dw%vrow(j,5) = dw%vrow(j,5) + vol_col(g, s, i, j, s%hd(i,j))
      s%hd(i,j) = 0.0
    end do
  end do

  ! (6) 期間最大到達量 Wd9999 = max(hd+wd)(f_out_wd 指定時のみ確保。
  !     save 対象外 = hmax 系と同じ意図的仕様。§7)
  if (allocated(s%wdmax)) then
    !$omp parallel do schedule(static) private(i, j, w)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        w = s%hd(i,j) + s%wd(i,j)
        if (w > s%wdmax(i,j)) s%wdmax(i,j) = w
      end do
    end do
    !$omp end parallel do
  end if
end subroutine


!----------------------------------------------------------------------
! セル (i,j) の柱状量→実材積の換算係数と換算(m3。real64)
!   柱状量の材積 = w × gv × wfrac × A(h・hs と同じ実効面積基底)、
!   幾何面積基底(wst)の材積 = w × A
!----------------------------------------------------------------------
function colfac(s, i, j) result(f)
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  real :: f, wf
  wf = 1.0
  if (chn%have_width) wf = chn%wfrac(i,j)
  f = s%gv(i,j) * wf
end function

function vol_col(g, s, i, j, w) result(vol)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  real, intent(in) :: w
  real(real64) :: vol
  vol = real(w, real64) * real(colfac(s, i, j), real64) &
        * real(g%dx, real64) * real(g%dy, real64)
end function

function vol_geo(g, w) result(vol)
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: w
  real(real64) :: vol
  vol = real(w, real64) * real(g%dx, real64) * real(g%dy, real64)
end function


!----------------------------------------------------------------------
! 診断 CSV の出力(record 間隔。collective: 全ランクで呼ぶ)
!   現在貯留(ストック・流動・堆積)も台帳化(par_sum_rows = 決定的)。
!   系外流出は収支残差として利用者が導出する(初期ストック総量 −
!   全項目の和)
!----------------------------------------------------------------------
subroutine m_driftwood_record(dw, p, g, s)
  type(t_driftwood), intent(inout) :: dw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64) :: v(1:5), vstk, vflt, vdep, vtrap, vjam
  real(real64) :: rows(dcp%js:dcp%je), rows2(dcp%js:dcp%je), rows3(dcp%js:dcp%je)
  real(real64) :: rows4(dcp%js:dcp%je)
  integer :: i, j, k
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (.not. dw%enabled) return

  do k = 1, 5
    call par_sum_rows(dw%vrow(:,k), v(k))
  end do
  rows(:) = 0.0_real64
  rows2(:) = 0.0_real64
  rows3(:) = 0.0_real64
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      rows(j) = rows(j) + vol_geo(g, dw%wst(i,j))
      rows2(j) = rows2(j) + vol_col(g, s, i, j, s%hd(i,j))
      rows3(j) = rows3(j) + vol_col(g, s, i, j, s%wd(i,j))
    end do
  end do
  call par_sum_rows(rows, vstk)
  call par_sum_rows(rows2, vflt)
  call par_sum_rows(rows3, vdep)

  ! 構造物での捕捉の累積と現在の集積(集積流木を持つときだけ。判定は全ランクで同一)
  if (dw%have_jam) then
    call par_sum_rows(dw%vrow(:,6), vtrap)
    rows4(:) = 0.0_real64
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        rows4(j) = rows4(j) + vol_col(g, s, i, j, s%wj(i,j))
      end do
    end do
    call par_sum_rows(rows4, vjam)
  end if

  if (is_root .and. dw%un /= 0) then
    if (dw%have_jam) then
      write(dw%un, '(f0.2,10(",",es15.7))') s%t, es_out([v(1:5), vstk, vflt, vdep, vtrap, vjam])
    else
      write(dw%un, '(f0.2,8(",",es15.7))') s%t, es_out([v(1:5), vstk, vflt, vdep])
    end if
    flush(dw%un)
  end if
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モジュール私有ファイル driftwood.dat。契約C。§7)
!   保存対象: s%hd, s%wd, wst, zref(4成分固定)。wdmax は統計 = 対象外。
!   捕捉セルを与えたとき(fn_dwtrap)だけ、末尾に集積の印(整数 1)と s%wj を
!   追記する(§50.7)。与えないときのファイルは従来とバイト同一で、save_version は
!   変えない(印のないファイルは「集積なし」として読める)
!----------------------------------------------------------------------
subroutine save_state(dw, p, g, s)
  type(t_driftwood), intent(in) :: dw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, allocatable :: wk(:,:)
  integer :: un
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/driftwood.dat', form='unformatted', &
         status='replace')
  end if
  ! 帯配列を窓形に集約しながら rank0 が RLE で書く(§83。読み並びは restore と対)
  call restart_write_cell(un, s%hd)
  call restart_write_cell(un, s%wd)
  call restart_write_cell(un, dw%wst)
  call restart_write_cell(un, dw%zref)
  if (dw%have_jam) then
    if (is_root) write(un) 1
    call restart_write_cell(un, s%wj)
  end if
  if (is_root) close(un)
end subroutine


subroutine restore_state(dw, p, g, s)
  type(t_driftwood), intent(inout) :: dw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  character(:), allocatable :: fname
  logical :: found
  integer :: un, ios
  integer :: njam(1)
  if (g%initialized) continue  ! 引数未使用の警告を抑制

  ! 版・格子・精度の検証は m_state(check_save_info)が済ませている。
  ! 自ファイルの有無のみ確認(無ければ停止 — 意図しない材積消失を防ぐ)
  fname = trim(p%dir_save)//'/driftwood.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("driftwood: state file not found (was fn_driftwood enabled " &
                  //"when saving): "//fname)
  end if

  if (is_root) open(newunit=un, file=fname, form='unformatted', status='old')
  call restart_read_cell(un, s%hd)
  call restart_read_cell(un, s%wd)
  call restart_read_cell(un, dw%wst)
  call restart_read_cell(un, dw%zref)
  ! 集積流木(§50.7): 保存した側が捕捉セルを与えていれば、末尾に印 1 と表がある。
  ! 印は rank0 が読み、和で全ランクに共有する(rank0 以外は 0 を持ち寄る。
  ! swflow_enc の動的振り替えの表と同じ手順)。印のないファイルは読めずに 0 になる
  njam(1) = 0
  if (is_root) then
    read(un, iostat=ios) njam(1)
    if (ios /= 0) njam(1) = 0
  end if
  call par_allreduce_sumi(njam)
  if (dw%have_jam) then
    if (njam(1) == 1) then
      call restart_read_cell(un, s%wj)
    else
      call par_info("driftwood: the save holds no jammed wood (no capture cells when " &
                    //"saving); the jam starts from zero")
    end if
  else if (njam(1) == 1) then
    call par_info("driftwood: the jammed wood in the save is not restored because this run " &
                  //"has no capture cells (its volume leaves the ledger)")
  end if
  if (is_root) close(un)
end subroutine


!----------------------------------------------------------------------
! 流木モジュールを破棄する(save は dispose で行う。契約C)
!----------------------------------------------------------------------
subroutine m_driftwood_dispose(dw, p, g, s)
  type(t_driftwood), intent(inout) :: dw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (.not. dw%enabled) return
  if (p%f_state_save > 0) call save_state(dw, p, g, s)
  if (is_root .and. dw%un /= 0) close(dw%un)
  dw%un = 0
  if (allocated(dw%wst)) deallocate(dw%wst)
  if (allocated(dw%zref)) deallocate(dw%zref)
  if (allocated(dw%trap)) deallocate(dw%trap)
  if (allocated(dw%culv)) deallocate(dw%culv)
  if (allocated(dw%dam)) deallocate(dw%dam)
  if (allocated(dw%vrow)) deallocate(dw%vrow)
  dw%enabled = .false.
  dw%initialized = .false.
end subroutine

end module
