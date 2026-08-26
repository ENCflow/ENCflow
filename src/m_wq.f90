module m_wq
  ! ============== 水質(負荷流出)プロセスモジュール(§30) ==============
  ! 単一物質の柱状量 s%cq を対象とする簡易環境水理シミュレーション。
  !   輸送:   浮遊砂と同じ保存輸送カーネル(advect_scalar)を swflow_enc が
  !           ステップ内で実行(s%wq_active)。本モジュールは発生源・
  !           鉛直交換・診断を担う加算的プロセス
  !   有効化: fn_wq の指定(&list_wq。f_wq=0 で一時無効化)。ENC 格子のみ
  !   単位系: cq = 柱状量 (g/m2。貯留の意味論は h と同一 = セル内質量 =
  !           cq×gv×wfrac×A)。濃度 cqc = cq/vh (mg/L。vh は σ の矩形換算
  !           水深 = swflow_vh。σ・幅セルでも体積平均濃度が正しく出る)
  !   発生源: 点源(セル群、g/s)・面源(セル群、kg/ha/day)は一定または
  !           時系列(t=0 からの経過日、線形補間・端値保持)。分布面源
  !           (fn_wq_map: 原単位 kg/ha/day のセル別分布×倍率。一定)は
  !           全有効セルへ投入し、点源・面源と排他でなく重ね合わせ。
  !           降雨中濃度(湿性沈着 wq_rain_conc/wq_rain_series、mg/L)は
  !           地表到達雨量 s%pre×濃度を全域投入(これも重ね合わせ)。
  !           境界流入濃度(区間流入ごと、mg/L)は b%cqin テーブル経由で
  !           輸送カーネルに渡す
  !   浸透:   f_wq_infil=1(既定)で浸透水に濃度同伴し、地下質量プール
  !           s%cg へ移す。gwflow の鉛直交換が s%fxg に浸透量を記録し、
  !           本モジュールが読んでゼロ戻しする契約。0 で地表に残留
  !           (粒子態向け)。cg は幾何面積基底(セル内質量 = cg×A)で
  !           保持し、cq 基底(gv×wfrac)との換算(gwfac_of)は浸透同伴・
  !           湧出還元の両端で行う — 地下横輸送(柱状量の対称交換)の
  !           質量収支が gv・wfrac の分布によらず厳密に閉じる条件(W3)
  !   地下輸送: 側方流動(f_gwlateral=1)有効時、m_gwflow_lateral が水と
  !           同じエッジ流量で cg を風上輸送し、飽和湧出には同率移動
  !           ×1/R を同伴して s%fxs に記録する(W3。§30)。本モジュールは
  !           fxs を読んで地表 cq へ還元(湧出還元)しゼロ戻しする。
  !           遅延化係数 wq_rg(R >= 1。平衡吸着の遅延)は側方移流と
  !           湧出の実効濃度を 1/R に落とす(s%cg_rginv 経由で lateral に
  !           渡す。R→∞ で不動化)。層2(cg2)・gwflow_bucket 系は将来拡張
  !   管路:   wq_gwc_conc(mg/L)指定で管路連続体層(f_gwconduit)と連携
  !           (下水噴出の衛生リスク評価。供給側固定濃度近似 = 管内の
  !           質量は解かず、噴出・陸側開放吐口の水量 s%fxco に固定濃度を
  !           乗じた質量を地表 cq へ投入する。晴天時汚水の定数濃度近似)。
  !           枡流入は f_wq_gwc_in=1(既定)で s%fxci の水量に濃度同伴し
  !           管路台帳へ除去(0 で地表残留)。fxci/fxco は fxg と同じ
  !           「conduit が記録し本モジュールが読んでゼロ戻し」の契約。
  !           管内の質量プール・管内移流は将来拡張(§46.5 の議論)
  !   ダム:   捕捉帯セルは毎ステップ全量吸収されるため、質量も同伴して
  !           ダム別台帳へ移す(放流濃度 0 = 既知の妥協。貯水池内混合は
  !           将来拡張)。ため池(rscap)の吸収分は W1 では地表に残留
  !           (既知の妥協)
  !   蒸発:   純水のみが抜けるため質量は残留(濃縮)= 物理的に正しい。
  !           コード上の連携は不要
  !   save:   s%cq と cg をモジュール私有ファイル wq.dat で保存(§7 の
  !           契約C と同型。state.dat の形式は不変。cg の基底変更
  !           (2026-08-26)で save_version を更新済み)
  !   診断:   result/wq.csv(投入・境界流入・浸透・ダム捕捉・系外流出は
  !           収支残差として台帳化。rank0、dt_recrd 間隔)。
  !           濃度場 C(m_output)とプローブ・測線負荷列(m_record)は
  !           s%cqc / s%cq を読む
  !   MPI:    発生源はセル局所、台帳集計は par_sum_rows(決定的)
  ! ======================================================================
  use iso_fortran_env, only : real64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_boundary, only : t_boundary, e_struct_dam, interp_series, read_cell_file2
  use m_swflow_enc, only : swflow_vh, have_width, wfrac
  use m_gwflow_conduit, only : gwflow_conduit_ready
  use list_wq, only : t_list_wq, list_wq_read, nwqgmax, nwqcmax, nwqvmax, nwqfmax
  use m_fileio, only : fileio_write_rle, fileio_read_rle, fileio_read_matrix
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : dcp, is_root, par_info, par_stop, par_abort, par_sum_rows, &
                         par_gather_to, par_scatter_cell
  use m_util, only : itoa
  implicit none
  private
  public :: t_wq
  public :: m_wq_init
  public :: m_wq_calc
  public :: m_wq_derive
  public :: m_wq_record
  public :: m_wq_dispose

  real, parameter :: secday = 86400.0
  ! 原単位 kg/ha/day -> g/s/m2(1 kg/ha/day = 1000 g / 10000 m2 / 86400 s)
  real, parameter :: unit2gsm2 = 1000.0 / 10000.0 / 86400.0
  real, parameter :: kgha2gm2 = 0.1          ! kg/ha -> g/m2
  real, parameter :: rhow = 1000.0           ! 水の密度 (kg/m3。せん断応力の次元化)

  ! 発生源グループ(点源・面源共通の骨格)
  type t_wqsrc
    integer :: nc = 0                    ! 自帯内のセル数
    integer, allocatable :: cells(:,:)   ! 自帯内のセル (1:2, 1:nc)
    integer :: ncall = 0                 ! グループ全体のセル数(負荷の等分配用)
    real :: q0 = 0.0                     ! 一定値(点源 g/s、面源 kg/ha/day)
    integer :: nser = 0                  ! 時系列の点数(0 = 一定値)
    real, allocatable :: ser(:,:)        ! 時系列 (1:2, 1:nser) = (s, 値)
  end type

  ! ダム捕捉台帳
  type t_wqdam
    integer :: ist = 0                   ! b%struct のインデックス
    integer :: nc = 0                    ! 自帯内の捕捉帯セル数
    integer, allocatable :: cells(:,:)
  end type

  type t_wq
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.
    logical :: initialized = .false.
    integer :: f_infil = 1
    real :: gwc_conc = -1.0                         ! 管路連携: 噴出・吐口水の固定濃度
                                                    !   (g/m3。負 = 連携無効)
    integer :: f_gwc_in = 1                         ! 管路連携: 枡流入の同伴 (0:残留, 1:台帳へ)
    logical :: gwc_checked = .false.                ! f_gwconduit 有効性の遅延検査済み
    real :: fdec = 1.0                              ! 1ステップの減衰係数 exp(-k·dt)(1=減衰なし)
    real :: vs = 0.0                                ! 沈降速度 (m/s。0=なし)
    integer :: npt = 0, nar = 0
    type(t_wqsrc), allocatable :: pt(:), ar(:)
    integer :: nin = 0                              ! 境界流入濃度の指定数
    integer, allocatable :: inifl(:)                ! 対象の区間流入番号
    real, allocatable :: incval(:)                  ! 一定濃度 (g/m3)
    type(t_wqsrc), allocatable :: inser(:)          ! 時系列(ser のみ使用)
    real, allocatable :: rmap(:,:)                  ! 分布面源の投入率 (g/s/m2。地理的
                                                    !   面積あたり。帯。未指定なら未確保)
    logical :: have_rain = .false.                  ! 降雨中濃度(湿性沈着)の有効
    type(t_wqsrc) :: rain                           ! 降雨中濃度 (mg/L。q0 か ser)
    ! 表面蓄積プール+洗い出し(buildup-washoff。プール本体は s%bp。§30)
    logical :: have_pool = .false.                  ! プールの有効(確保・保存・出力)
    logical :: have_bd = .false.                    ! 蓄積レートあり
    logical :: map_to_pool = .false.                ! rmap を蓄積レートとして使う
    real :: bdrate = 0.0                            ! 一様蓄積レート (g/s/m2)
    real :: bmax = 0.0                              ! 蓄積上限 (g/m2。0=線形無限)
    logical :: have_wash = .false.                  ! 洗い出しの有効
    real :: wkr = 0.0                               ! 雨滴洗い出し係数 (1/m)
    real :: wkf = 0.0                               ! せん断洗い出し係数 (1/s)
    real :: wtauc = 1.0                             ! 限界せん断応力 (N/m2)
    integer :: f_settle = 0                         ! 沈降の行き先 (0:消失, 1:プール)
    integer :: ndam = 0
    type(t_wqdam), allocatable :: dam(:)
    ! 診断(行部分和 real64。累積 m3 でなく質量 g)
    real(real64), allocatable :: vrow(:,:)  ! (js:je, 1:13) 1=点源 2=面源 3=浸透(→cg)
                                            !   4=ダム捕捉 5=減衰消失 6=沈降
                                            !   7=分布面源 8=降雨沈着 9=蓄積(→bp)
                                            !   10=洗い出し(bp→cq) 13=湧出還元(cg→cq)
                                            !   11=管路噴出・吐口の投入 12=枡流入(→管路台帳)
    integer :: un = 0                       ! CSV 装置番号(rank0。open(newunit=) は負値。§22)
  end type

contains


!----------------------------------------------------------------------
! 水質モジュールを初期化する
!   fn_wq 未指定 or f_wq=0 なら何もしない(enabled = .false.)。
!   swflow init より前に呼ぶこと(s%wq_active を立てるため)。
!   セル検証はゾーン2(全域 x/rw が使える帯縮小前)で行う
!----------------------------------------------------------------------
subroutine m_wq_init(wq, p, g, b, s)
  type(t_wq), intent(out) :: wq
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(inout) :: b   ! cqin テーブルの確保
  type(t_state), intent(inout) :: s      ! cq/cqc/fxg の確保と wq_active
  type(t_list_wq) :: list
  integer :: k

  if (len_trim(p%fn_wq) == 0) return
  if (p%f_gridsystem /= 0) then
    call par_stop("list_wq: water quality transport supports the ENC grid only " &
                  //"(same restriction as suspended sediment)")
  end if

  call list_wq_read(p, list)
  if (list%f_wq == 0) return    ! fn を書いたまま一時無効化する経路

  if (list%wq_c0 < 0.0) call par_stop("list_wq: wq_c0 must be >= 0")
  if (list%f_wq_infil < 0 .or. list%f_wq_infil > 1) then
    call par_stop("list_wq: f_wq_infil must be 0(remain at surface) or 1(carry with infiltration)")
  end if
  wq%f_infil = list%f_wq_infil

  ! --- 地下輸送の遅延化係数(W3。平衡吸着の遅延 R = 1 + ρb·Kd/θ を
  !     物理量として直接与える — 導出は前処理。§0)---
  if (list%wq_rg > -9998.0) then
    if (list%wq_rg < 1.0) call par_stop("list_wq: wq_rg must be >= 1 (retardation factor)")
    if (wq%f_infil /= 1) then
      call par_stop("list_wq: wq_rg requires f_wq_infil=1 (groundwater mass pool)")
    end if
    s%cg_rginv = 1.0 / list%wq_rg
  end if

  ! --- 管路連続体層との連携(下水噴出の衛生リスク評価。§30 追記) ---
  !     f_gwconduit の有効性は gwflow init が後のため最初の calc で遅延検査
  if (list%wq_gwc_conc > -9998.0) then
    if (list%wq_gwc_conc < 0.0) call par_stop("list_wq: wq_gwc_conc must be >= 0")
    wq%gwc_conc = list%wq_gwc_conc                  ! mg/L = g/m3(換算不要)
  end if
  if (list%f_wq_gwc_in < 0 .or. list%f_wq_gwc_in > 1) then
    call par_stop("list_wq: f_wq_gwc_in must be 0(remain at surface) or 1(carry to conduit)")
  end if
  wq%f_gwc_in = list%f_wq_gwc_in

  ! --- 一次減衰(半減期か k20 の排他。W2)と沈降 ---
  if (list%wq_thalf > -9998.0 .and. list%wq_k20 > -9998.0) then
    call par_stop("list_wq: specify decay by either wq_thalf (half-life) or wq_k20, " &
                  //"not both")
  end if
  if (list%wq_thalf > -9998.0) then
    if (list%wq_thalf <= 0.0) call par_stop("list_wq: wq_thalf must be > 0")
    wq%fdec = exp(-log(2.0) / (list%wq_thalf * secday) * p%dt)
  else if (list%wq_k20 > -9998.0) then
    if (list%wq_k20 < 0.0) call par_stop("list_wq: wq_k20 must be >= 0")
    wq%fdec = exp(-list%wq_k20 / secday * p%dt)
  end if
  if (list%wq_vs > -9998.0) then
    if (list%wq_vs < 0.0) call par_stop("list_wq: wq_vs must be >= 0")
    wq%vs = list%wq_vs / secday
  end if

  ! --- 発生源グループの解釈(点源・面源) ---
  call setup_sources(wq, p, g, list)

  ! --- 分布面源(全有効セル・一定。点源・面源と重ね合わせ) ---
  if (len_trim(list%fn_wq_map) > 0) call setup_map_source(wq, p, g, list)

  ! --- 降雨中濃度(湿性沈着。点源・面源・分布と重ね合わせ) ---
  call setup_rain_conc(wq, list)

  ! --- 表面蓄積プール+洗い出し(buildup-washoff) ---
  call setup_pool(wq, p, g, s, list)

  ! --- 境界流入濃度 ---
  call setup_inflow_conc(wq, g, b, list)

  ! --- ダム捕捉台帳(全ダム・湖沼が対象) ---
  call setup_dams(wq, g, b)

  ! --- 状態の確保 ---
  allocate(s%cq(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%cqc(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (wq%f_infil == 1) then
    allocate(s%fxg(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(s%cg(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    ! 湧出同伴質量の記録場(W3。gwflow_lateral が書き、本モジュールが
    ! 読んで cq へ還元しゼロ戻し。側方無効時は恒久 0 のまま)
    allocate(s%fxs(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  end if
  if (wq%gwc_conc >= 0.0) then
    ! 管路連携の交換量記録場(fxg と同じ契約。conduit は allocated 判定で
    ! 記録するだけ = wq を知らない)
    allocate(s%fxco(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    if (wq%f_gwc_in == 1) allocate(s%fxci(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  end if
  ! 初期濃度(mg/L)から柱状量へ: cq = conc × vh。init 時点は swflow 未初期化
  ! (σ の sdep 未構築)だが、restore 前のフレッシュ初期 h に対する換算は
  ! vh=h の矩形でよい(σ 有効時の初期水深は通常 0。非 0 初期水面に σ を
  ! 併用する場合の初期質量は矩形換算=既知の妥協)
  if (list%wq_c0 > 0.0) then
    do k = dcp%jsh, dcp%jeh
      s%cq(:,k) = list%wq_c0 * max(s%h(:,k), 0.0)
    end do
  end if

  ! --- リスタート ---
  if (p%f_state_restore > 0) call restore_state(wq, p, g, s)

  allocate(wq%vrow(dcp%js:dcp%je, 1:13), source = 0.0_real64)

  ! --- 診断 CSV(rank0。累積はラン先頭からの積算 = restore でリセット) ---
  if (is_root) then
    open(newunit=wq%un, file=trim(p%dir_result)//"/wq.csv", status='replace')
    write(wq%un, '(a)') "time_s,in_point_g,in_area_g,in_map_g,in_rain_g,in_gwc_g," &
                        //"in_bldup_g,wash_g,to_gw_g,seep_g,to_gwc_g,to_dam_g,decay_g," &
                        //"settle_g,mass_surface_g,mass_gw_g,mass_pool_g"
  end if

  s%wq_active = .true.
  wq%enabled = .true.
  wq%initialized = .true.
  call par_info("water quality (load runoff) enabled")
end subroutine


!----------------------------------------------------------------------
! 発生源グループの解釈(点源=g/s、面源=kg/ha/day。セルは inline か
! ファイル。負荷は一定か時系列の排他)
!----------------------------------------------------------------------
subroutine setup_sources(wq, p, g, list)
  type(t_wq), intent(inout) :: wq
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_wq), intent(in) :: list
  integer :: igrp

  ! グループ数(セル指定があるものを先頭から数える。連続充填を要求)
  wq%npt = count_groups(list%wq_pt_cell, list%fn_wq_pt_cell)
  wq%nar = count_groups(list%wq_ar_cell, list%fn_wq_ar_cell)
  if (wq%npt > 0) allocate(wq%pt(1:wq%npt))
  if (wq%nar > 0) allocate(wq%ar(1:wq%nar))

  do igrp = 1, wq%npt
    call setup_one_source(wq%pt(igrp), p, g, "point source", igrp, &
                          list%wq_pt_cell(:,:,igrp), list%fn_wq_pt_cell(igrp), &
                          list%wq_pt_load(igrp), list%wq_pt_series(:,:,igrp))
  end do
  do igrp = 1, wq%nar
    call setup_one_source(wq%ar(igrp), p, g, "diffuse source", igrp, &
                          list%wq_ar_cell(:,:,igrp), list%fn_wq_ar_cell(igrp), &
                          list%wq_ar_load(igrp), list%wq_ar_series(:,:,igrp))
  end do
end subroutine


function count_groups(cells, fns) result(n)
  integer, intent(in) :: cells(:,:,:)
  character(len=*), intent(in) :: fns(:)
  integer :: n, igrp
  n = 0
  do igrp = 1, size(fns)
    if (cells(1,1,igrp) == -9999 .and. len_trim(fns(igrp)) == 0) exit
    n = n + 1
  end do
end function


subroutine setup_one_source(src, p, g, label, igrp, cells, fn, q0, series)
  type(t_wqsrc), intent(inout) :: src
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: label
  integer, intent(in) :: igrp
  integer, intent(in) :: cells(:,:)
  character(len=*), intent(in) :: fn
  real, intent(in) :: q0
  real, intent(in) :: series(:,:)
  integer, allocatable :: wkcell(:,:)
  integer :: n, k, i, j

  ! --- セル集合(inline かファイルの排他) ---
  if (len_trim(fn) > 0 .and. cells(1,1) /= -9999) then
    call par_stop("list_wq: specify the cells of "//label//" "//itoa(igrp) &
                  //" either inline or by file, not both")
  end if
  if (len_trim(fn) > 0) then
    call read_cell_file2(trim(p%dir_data)//"/"//trim(fn), n, wkcell)
  else
    n = 0
    do k = 1, size(cells, 2)
      if (cells(1,k) == -9999) exit
      n = n + 1
    end do
    allocate(wkcell(1:2, 1:max(n,1)))
    wkcell(1:2, 1:n) = cells(1:2, 1:n)
  end if
  if (n < 1) call par_stop("list_wq: "//label//" "//itoa(igrp)//" has no cells")
  src%ncall = n

  ! --- 検証(全域マスク。ゾーン2で全ランク冗長・同一判定) ---
  do k = 1, n
    i = wkcell(1,k)
    j = wkcell(2,k)
    if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
      call par_stop("list_wq: "//label//" "//itoa(igrp)//" has a cell outside the domain")
    end if
    if (g%x(i,j) <= 0) then
      call par_stop("list_wq: "//label//" "//itoa(igrp)//" has a cell outside the valid area")
    end if
  end do

  ! --- 自帯内のセルだけ保持 ---
  src%nc = 0
  do k = 1, n
    if (wkcell(2,k) >= dcp%js .and. wkcell(2,k) <= dcp%je) src%nc = src%nc + 1
  end do
  allocate(src%cells(1:2, 1:max(src%nc,1)), source = 0)
  src%nc = 0
  do k = 1, n
    if (wkcell(2,k) < dcp%js .or. wkcell(2,k) > dcp%je) cycle
    src%nc = src%nc + 1
    src%cells(1:2, src%nc) = wkcell(1:2, k)
  end do

  ! --- 負荷(一定か時系列の排他。時系列は 経過日 -> 秒) ---
  n = 0
  do k = 1, size(series, 2)
    if (series(1,k) <= -9998.0) exit
    n = n + 1
  end do
  if (n > 0 .and. q0 > -9998.0) then
    call par_stop("list_wq: specify the load of "//label//" "//itoa(igrp) &
                  //" by either a constant or a time series, not both")
  end if
  if (n == 0 .and. q0 <= -9998.0) then
    call par_stop("list_wq: no load specified for "//label//" "//itoa(igrp))
  end if
  if (n > 0) then
    do k = 2, n
      if (series(1,k) <= series(1,k-1)) then
        call par_stop("list_wq: time series of "//label//" "//itoa(igrp) &
                      //" must have monotonically increasing times (elapsed days)")
      end if
    end do
    allocate(src%ser(1:2, 1:n))
    src%ser(1,1:n) = series(1,1:n) * secday
    src%ser(2,1:n) = series(2,1:n)
    src%nser = n
  else
    if (q0 < 0.0) call par_stop("list_wq: load of "//label//" "//itoa(igrp)//" must be >= 0")
    src%q0 = q0
  end if
end subroutine


!----------------------------------------------------------------------
! 境界流入濃度の解釈(区間流入番号ごと。b%cqin テーブルを確保する)
!----------------------------------------------------------------------
subroutine setup_inflow_conc(wq, g, b, list)
  type(t_wq), intent(inout) :: wq
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(inout) :: b
  type(t_list_wq), intent(in) :: list
  integer :: ifl, n, k, m

  wq%nin = 0
  do ifl = 1, nwqfmax
    if (list%wq_in_conc(ifl) > -9998.0 .or. list%wq_in_series(1,1,ifl) > -9998.0) then
      wq%nin = wq%nin + 1
    end if
  end do
  if (wq%nin == 0) return

  if (b%ninflow <= 0) then
    call par_stop("list_wq: wq_in_conc/wq_in_series require inflow sections " &
                  //"in &list_bound_inflow")
  end if
  allocate(wq%inifl(1:wq%nin), source = 0)
  allocate(wq%incval(1:wq%nin), source = 0.0)
  allocate(wq%inser(1:wq%nin))
  m = 0
  do ifl = 1, nwqfmax
    if (list%wq_in_conc(ifl) <= -9998.0 .and. list%wq_in_series(1,1,ifl) <= -9998.0) cycle
    m = m + 1
    if (ifl > b%ninflow) then
      call par_stop("list_wq: wq_in_*("//itoa(ifl)//") has no matching inflow section")
    end if
    wq%inifl(m) = ifl
    n = 0
    do k = 1, nwqvmax
      if (list%wq_in_series(1,k,ifl) <= -9998.0) exit
      n = n + 1
    end do
    if (n > 0 .and. list%wq_in_conc(ifl) > -9998.0) then
      call par_stop("list_wq: specify wq_in_*("//itoa(ifl)//") by either a constant " &
                    //"or a time series, not both")
    end if
    if (n > 0) then
      do k = 2, n
        if (list%wq_in_series(1,k,ifl) <= list%wq_in_series(1,k-1,ifl)) then
          call par_stop("list_wq: wq_in_series("//itoa(ifl)//") must have monotonically " &
                        //"increasing times (elapsed days)")
        end if
      end do
      allocate(wq%inser(m)%ser(1:2, 1:n))
      wq%inser(m)%ser(1,1:n) = list%wq_in_series(1,1:n,ifl) * secday
      wq%inser(m)%ser(2,1:n) = list%wq_in_series(2,1:n,ifl)
      wq%inser(m)%nser = n
    else
      if (list%wq_in_conc(ifl) < 0.0) then
        call par_stop("list_wq: wq_in_conc("//itoa(ifl)//") must be >= 0")
      end if
      wq%incval(m) = list%wq_in_conc(ifl)
    end if
  end do

  ! 濃度テーブル(mg/L = g/m3。カーネルの風上濃度 cq/h と同じ単位系。
  ! 値の充填は m_wq_calc が毎ステップ行う)
  allocate(b%cqin(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
end subroutine


!----------------------------------------------------------------------
! 分布面源の読み込み(原単位 kg/ha/day のセル別分布 × 倍率。
! rank0 読み+帯 scatter。負値はエラー。全有効セルへ一定率で投入。§30。
! f_wq_map=1 のときは蓄積プールへのレートとして使われる(setup_pool))
!----------------------------------------------------------------------
subroutine setup_map_source(wq, p, g, list)
  type(t_wq), intent(inout) :: wq
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_wq), intent(in) :: list

  if (list%wq_map_factor < 0.0) call par_stop("list_wq: wq_map_factor must be >= 0")
  allocate(wq%rmap(1:g%nx, dcp%jsh:dcp%jeh))
  ! kg/ha/day -> g/s/m2 に倍率込みで換算(rank0 で乗じてから配布)
  call read_map_scatter(p, g, list%fn_wq_map, "fn_wq_map", &
                        unit2gsm2 * list%wq_map_factor, wq%rmap)
end subroutine


!----------------------------------------------------------------------
! 分布ファイルの rank0 読み+倍率+帯 scatter(共通ヘルパ)。
! 使用セルの負値はエラー(0 は「なし」として許す)
!----------------------------------------------------------------------
subroutine read_map_scatter(p, g, fn, label, factor, a)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn, label
  real, intent(in) :: factor
  real, intent(inout) :: a(1:, dcp%jsh:)
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  character(len=1024) :: msg
  logical :: found
  integer :: i, j

  fname = trim(p%dir_data)//"/"//trim(fn)
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("list_wq: "//label//" not found: "//fname)

  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny))
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, wk, p%f_input_mode)
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) <= 0) cycle
        if (wk(i,j) < 0.0) then
          write(msg,'(a,2i7,es12.4)') "list_wq: "//label//" has a negative value at cell", &
                                      i, j, wk(i,j)
          call par_abort(trim(msg))
        end if
      end do
    end do
    wk(:,:) = wk(:,:) * factor
    call par_scatter_cell(wk, a)
  else
    call par_scatter_cell(dum, a)
  end if
end subroutine


!----------------------------------------------------------------------
! 表面蓄積プール+洗い出し(buildup-washoff)の解釈(§30)
!   蓄積 dB/dt = r·(1 − B/Bmax)(Bmax 省略で線形 dB/dt = r)。
!   洗い出し率 λ = kr·P + kf·max(τ/τc − 1, 0)(m_geomorph_wash と同型。
!   kr は SWMM 指数型洗い出し c1[1/mm]×1000 と互換)。
!   プール本体 s%bp はここで確保する(restore より前に呼ぶこと)
!----------------------------------------------------------------------
subroutine setup_pool(wq, p, g, s, list)
  type(t_wq), intent(inout) :: wq
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_wq), intent(in) :: list
  logical :: have_bd0

  ! --- 蓄積レート(一様値か分布の排他) ---
  if (list%f_wq_map < 0 .or. list%f_wq_map > 1) then
    call par_stop("list_wq: f_wq_map must be 0(direct input) or 1(buildup rate)")
  end if
  if (list%f_wq_map == 1 .and. len_trim(list%fn_wq_map) == 0) then
    call par_stop("list_wq: f_wq_map=1 requires fn_wq_map")
  end if
  wq%map_to_pool = (list%f_wq_map == 1)
  if (list%wq_bd_rate > -9998.0) then
    if (wq%map_to_pool) then
      call par_stop("list_wq: specify the buildup rate by either wq_bd_rate (uniform) " &
                    //"or fn_wq_map (f_wq_map=1), not both")
    end if
    if (list%wq_bd_rate < 0.0) call par_stop("list_wq: wq_bd_rate must be >= 0")
    wq%bdrate = list%wq_bd_rate * unit2gsm2
  end if
  wq%have_bd = wq%map_to_pool .or. wq%bdrate > 0.0

  ! --- 蓄積上限(飽和指数形。レートと併用のみ意味を持つ) ---
  if (list%wq_bd_max > -9998.0) then
    if (list%wq_bd_max <= 0.0) call par_stop("list_wq: wq_bd_max must be > 0")
    if (.not. wq%have_bd) then
      call par_stop("list_wq: wq_bd_max requires a buildup rate (wq_bd_rate " &
                    //"or f_wq_map=1)")
    end if
    wq%bmax = list%wq_bd_max * kgha2gm2
  end if

  ! --- 洗い出し係数 ---
  if (list%wq_wash_kr > -9998.0) then
    if (list%wq_wash_kr < 0.0) call par_stop("list_wq: wq_wash_kr must be >= 0")
    wq%wkr = list%wq_wash_kr
  end if
  if (list%wq_wash_kf > -9998.0) then
    if (list%wq_wash_kf < 0.0) call par_stop("list_wq: wq_wash_kf must be >= 0")
    wq%wkf = list%wq_wash_kf
    if (wq%wkf > 0.0) then
      if (list%wq_wash_tauc <= -9998.0) then
        call par_stop("list_wq: wq_wash_kf requires wq_wash_tauc (N/m2)")
      end if
      if (list%wq_wash_tauc <= 0.0) call par_stop("list_wq: wq_wash_tauc must be > 0")
      wq%wtauc = list%wq_wash_tauc
    end if
  end if
  wq%have_wash = wq%wkr > 0.0 .or. wq%wkf > 0.0

  ! --- 沈降の行き先 ---
  if (list%f_wq_settle < 0 .or. list%f_wq_settle > 1) then
    call par_stop("list_wq: f_wq_settle must be 0(lost to the bed) or 1(to the pool)")
  end if
  wq%f_settle = list%f_wq_settle
  if (wq%f_settle == 1 .and. wq%vs <= 0.0) then
    call par_stop("list_wq: f_wq_settle=1 requires wq_vs (settling velocity)")
  end if

  ! --- 初期プール(一様か分布の排他) ---
  have_bd0 = list%wq_bd0 > -9998.0 .or. len_trim(list%fn_wq_bd0) > 0
  if (list%wq_bd0 > -9998.0 .and. len_trim(list%fn_wq_bd0) > 0) then
    call par_stop("list_wq: specify the initial pool by either wq_bd0 (uniform) " &
                  //"or fn_wq_bd0 (map), not both")
  end if
  if (list%wq_bd0 > -9998.0 .and. list%wq_bd0 < 0.0) then
    call par_stop("list_wq: wq_bd0 must be >= 0")
  end if

  ! --- プールの有効判定と確保 ---
  wq%have_pool = wq%have_bd .or. have_bd0 .or. wq%f_settle == 1
  if (wq%have_wash .and. .not. wq%have_pool) then
    call par_stop("list_wq: washoff (wq_wash_*) requires a pool supply, one of " &
                  //"a buildup rate, an initial pool or f_wq_settle=1")
  end if
  if (.not. wq%have_pool) return

  allocate(s%bp(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (list%wq_bd0 > 0.0) then
    s%bp(:,:) = list%wq_bd0 * kgha2gm2
  else if (len_trim(list%fn_wq_bd0) > 0) then
    call read_map_scatter(p, g, list%fn_wq_bd0, "fn_wq_bd0", kgha2gm2, s%bp)
  end if
  ! 海セルにはプールを置かない(蓄積・洗い出しとも sw 除外と整合。
  ! ゾーン2 = sw は全域が使える)
  block
    integer :: i2, j2
    do j2 = dcp%jsh, dcp%jeh
      do i2 = 1, g%nx
        if (g%sw(i2,j2) > 0) s%bp(i2,j2) = 0.0
      end do
    end do
  end block
end subroutine


!----------------------------------------------------------------------
! 降雨中濃度の解釈(一定 wq_rain_conc か時系列 wq_rain_series の排他。
! 未指定なら無効。時系列は 経過日 -> 秒)
!----------------------------------------------------------------------
subroutine setup_rain_conc(wq, list)
  type(t_wq), intent(inout) :: wq
  type(t_list_wq), intent(in) :: list
  integer :: n, k

  n = 0
  do k = 1, size(list%wq_rain_series, 2)
    if (list%wq_rain_series(1,k) <= -9998.0) exit
    n = n + 1
  end do
  if (n == 0 .and. list%wq_rain_conc <= -9998.0) return    ! 未指定 = 無効
  if (n > 0 .and. list%wq_rain_conc > -9998.0) then
    call par_stop("list_wq: specify the concentration in precipitation by either " &
                  //"wq_rain_conc (constant) or wq_rain_series, not both")
  end if
  if (n > 0) then
    do k = 2, n
      if (list%wq_rain_series(1,k) <= list%wq_rain_series(1,k-1)) then
        call par_stop("list_wq: wq_rain_series must have monotonically increasing " &
                      //"times (elapsed days)")
      end if
    end do
    allocate(wq%rain%ser(1:2, 1:n))
    wq%rain%ser(1,1:n) = list%wq_rain_series(1,1:n) * secday
    wq%rain%ser(2,1:n) = list%wq_rain_series(2,1:n)
    wq%rain%nser = n
  else
    if (list%wq_rain_conc < 0.0) call par_stop("list_wq: wq_rain_conc must be >= 0")
    wq%rain%q0 = list%wq_rain_conc
  end if
  wq%have_rain = .true.
end subroutine


!----------------------------------------------------------------------
! ダム捕捉台帳の構築(全ダムの捕捉帯セル。自帯分のみ)
!----------------------------------------------------------------------
subroutine setup_dams(wq, g, b)
  type(t_wq), intent(inout) :: wq
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  integer :: ist, nd, n, k, j
  if (g%nx < 0) continue  ! 引数未使用の警告を抑制

  nd = 0
  if (allocated(b%struct)) then
    do ist = 1, size(b%struct)
      if (b%struct(ist)%kind == e_struct_dam) nd = nd + 1
    end do
  end if
  wq%ndam = nd
  if (nd == 0) return

  allocate(wq%dam(1:nd))
  nd = 0
  do ist = 1, size(b%struct)
    if (b%struct(ist)%kind /= e_struct_dam) cycle
    nd = nd + 1
    wq%dam(nd)%ist = ist
    n = 0
    do k = 1, b%struct(ist)%ncin
      j = b%struct(ist)%cin(2,k)
      if (j >= dcp%js .and. j <= dcp%je) n = n + 1
    end do
    wq%dam(nd)%nc = n
    allocate(wq%dam(nd)%cells(1:2, 1:max(n,1)), source = 0)
    n = 0
    do k = 1, b%struct(ist)%ncin
      j = b%struct(ist)%cin(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle
      n = n + 1
      wq%dam(nd)%cells(1,n) = b%struct(ist)%cin(1,k)
      wq%dam(nd)%cells(2,n) = j
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 水質過程を適用する(毎ステップ。run_main が swflow・gwflow の後に呼ぶ)
!   順序: (1) 境界流入濃度テーブルの更新(次ステップの移流が読む)
!         (2) 浸透同伴 cq→cg(gwflow が記録した fxg を消費)
!         (2a) 湧出還元 cg→cq(gwflow_lateral が記録した fxs を消費。W3)
!         (3) 発生源の投入
!         (4) ダム捕捉帯の質量吸収
!         (5) 導出濃度 cqc の更新
!   無効時は no-op。冒頭の return 判定は全ランクで同一 = collective 安全
!----------------------------------------------------------------------
subroutine m_wq_calc(wq, p, g, b, s, it)
  type(t_wq), intent(inout) :: wq
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(inout) :: b
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  integer :: i, j, k, m, nd
  real :: w, rate, fx
  real(real64) :: acell

  if (it < 0) continue  ! 引数未使用の警告を抑制
  if (.not. wq%enabled) return

  acell = real(g%dx, real64) * real(g%dy, real64)

  ! (1) 境界流入濃度テーブル(次ステップの advect_scalar が読む)
  do m = 1, wq%nin
    if (wq%inser(m)%nser > 0) then
      rate = interp_series(wq%inser(m)%ser, wq%inser(m)%nser, s%t)
    else
      rate = wq%incval(m)
    end if
    call fill_inflow_conc(g, b, wq%inifl(m), rate)
  end do

  ! (2) 浸透同伴(fxg = このステップの浸透量。柱状量の同率移動なので
  !     面積基底によらず質量保存が厳密。消費後ゼロ戻し)
  if (wq%f_infil == 1 .and. allocated(s%fxg)) then
    !$omp parallel do schedule(static) private(i, j, fx, w)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        fx = s%fxg(i,j)
        if (fx <= 0.0) cycle
        s%fxg(i,j) = 0.0
        if (s%cq(i,j) <= 0.0) cycle
        ! 移動割合 = fx / 浸透前水深(浸透後の h に fx を足し戻して復元)
        w = s%cq(i,j) * (fx / max(s%h(i,j) + fx, tiny(fx)))
        s%cq(i,j) = s%cq(i,j) - w
        ! cg は幾何面積基底 = cq 基底(gv×wfrac)から換算して積む
        ! (台帳 to_gw = mass_of(w) = Δcg×A と厳密整合。W3)
        s%cg(i,j) = s%cg(i,j) + w * gwfac_of(g, i, j)
        wq%vrow(j,3) = wq%vrow(j,3) + mass_of(g, i, j, w)
      end do
    end do
    !$omp end parallel do
  end if

  ! (2a) 湧出還元(W3): gwflow_lateral の飽和湧出に同伴して地下プールを
  !      抜けた質量(s%fxs。幾何面積基底)を、水と同じセルの地表 cq へ
  !      還元する(cq 基底へ換算)。fxg と同型の「lateral が記録し
  !      本モジュールが消費してゼロ戻し」の契約。側方無効時は恒久 0
  if (allocated(s%fxs)) then
    !$omp parallel do schedule(static) private(i, j, fx)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        fx = s%fxs(i,j)
        if (fx <= 0.0) cycle
        s%fxs(i,j) = 0.0
        s%cq(i,j) = s%cq(i,j) + fx / gwfac_of(g, i, j)
        wq%vrow(j,13) = wq%vrow(j,13) + real(fx, real64) * acell
      end do
    end do
    !$omp end parallel do
  end if

  ! (2b) 管路連続体層との交換同伴(供給側固定濃度近似。fxci/fxco は
  !      conduit が記録 = fxg と同じ契約。消費後ゼロ戻し)
  if (wq%gwc_conc >= 0.0) then
    if (.not. wq%gwc_checked) then
      ! f_gwconduit の有効性の遅延検査(wq init は gwflow init より先の
      ! ため。状態フラグは全ランク同一 = par_stop も同時)
      if (.not. gwflow_conduit_ready()) then
        call par_stop("list_wq: wq_gwc_conc requires f_gwconduit=1 (conduit layer)")
      end if
      wq%gwc_checked = .true.
    end if
    ! 噴出・陸側吐口 = 下水固定濃度の源(fxco は h と同基底の柱状水量)
    if (allocated(s%fxco)) then
      !$omp parallel do schedule(static) private(i, j, fx, w)
      do j = dcp%js, dcp%je
        do i = g%wx(1,j), g%wx(2,j)
          if (g%x(i,j) <= 0) cycle
          fx = s%fxco(i,j)
          if (fx <= 0.0) cycle
          s%fxco(i,j) = 0.0
          w = fx * wq%gwc_conc                       ! (m)×(g/m3) = g/m2 柱状
          s%cq(i,j) = s%cq(i,j) + w
          wq%vrow(j,11) = wq%vrow(j,11) + mass_of(g, i, j, w)
        end do
      end do
      !$omp end parallel do
    end if
    ! 枡流入 = 濃度同伴で管路台帳へ(浸透同伴と同じ同率移動)
    if (wq%f_gwc_in == 1 .and. allocated(s%fxci)) then
      !$omp parallel do schedule(static) private(i, j, fx, w)
      do j = dcp%js, dcp%je
        do i = g%wx(1,j), g%wx(2,j)
          if (g%x(i,j) <= 0) cycle
          fx = s%fxci(i,j)
          if (fx <= 0.0) cycle
          s%fxci(i,j) = 0.0
          if (s%cq(i,j) <= 0.0) cycle
          w = s%cq(i,j) * (fx / max(s%h(i,j) + fx, tiny(fx)))
          s%cq(i,j) = s%cq(i,j) - w
          wq%vrow(j,12) = wq%vrow(j,12) + mass_of(g, i, j, w)
        end do
      end do
      !$omp end parallel do
    end if
  end if

  ! (3) 発生源の投入(グループ負荷をセルへ配分し柱状量に加算)
  do k = 1, wq%npt
    if (wq%pt(k)%nser > 0) then
      rate = interp_series(wq%pt(k)%ser, wq%pt(k)%nser, s%t)   ! g/s(グループ合計)
    else
      rate = wq%pt(k)%q0
    end if
    rate = rate / real(wq%pt(k)%ncall)                          ! g/s/セル(等分配)
    do m = 1, wq%pt(k)%nc
      i = wq%pt(k)%cells(1,m)
      j = wq%pt(k)%cells(2,m)
      w = rate * p%dt / real(mass_of(g, i, j, 1.0))             ! g -> 柱状量
      s%cq(i,j) = s%cq(i,j) + w
      wq%vrow(j,1) = wq%vrow(j,1) + real(rate, real64) * real(p%dt, real64)
    end do
  end do
  do k = 1, wq%nar
    if (wq%ar(k)%nser > 0) then
      rate = interp_series(wq%ar(k)%ser, wq%ar(k)%nser, s%t)    ! kg/ha/day
    else
      rate = wq%ar(k)%q0
    end if
    rate = rate * unit2gsm2                                     ! g/s/m2(地理的面積あたり)
    do m = 1, wq%ar(k)%nc
      i = wq%ar(k)%cells(1,m)
      j = wq%ar(k)%cells(2,m)
      ! セルの負荷 = 原単位×セル面積。柱状量へは実効面積で除す
      w = rate * real(acell) * p%dt / real(mass_of(g, i, j, 1.0))
      s%cq(i,j) = s%cq(i,j) + w
      wq%vrow(j,2) = wq%vrow(j,2) + real(rate, real64) * acell * real(p%dt, real64)
    end do
  end do

  ! (3b) 分布面源の投入(全有効セル。一定率の前計算配列。
  !      f_wq_map=1 のときは直接投入せず蓄積プールのレートとして使う)
  if (allocated(wq%rmap) .and. .not. wq%map_to_pool) then
    !$omp parallel do schedule(static) private(i, j, w)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (wq%rmap(i,j) <= 0.0) cycle
        w = wq%rmap(i,j) * real(acell) * p%dt / real(mass_of(g, i, j, 1.0))
        s%cq(i,j) = s%cq(i,j) + w
        wq%vrow(j,7) = wq%vrow(j,7) + real(wq%rmap(i,j), real64) * acell * real(p%dt, real64)
      end do
    end do
    !$omp end parallel do
  end if

  ! (3c) 降雨中濃度(湿性沈着)の投入: このステップに swflow が加えた
  !      有効雨量 s%pre·dt(遮断適用後 = 地表到達分)× 濃度。セル判定は
  !      swflow の降雨適用と同一(sw セル除外)= 水と質量が厳密整合。
  !      樹冠に遮断された雨の沈着分は水と同伴して系外(既知の妥協。§30)
  if (wq%have_rain) then
    if (wq%rain%nser > 0) then
      rate = interp_series(wq%rain%ser, wq%rain%nser, s%t)     ! mg/L = g/m3
    else
      rate = wq%rain%q0
    end if
    if (rate > 0.0) then
      !$omp parallel do schedule(static) private(i, j, w)
      do j = dcp%js, dcp%je
        do i = g%wx(1,j), g%wx(2,j)
          if (g%sw(i,j) > 0) cycle
          if (g%x(i,j) <= 0) cycle
          if (s%pre(i,j) <= 0.0) cycle
          ! セルの質量 = 濃度×雨量×面積。柱状量へは実効面積で除す
          w = rate * s%pre(i,j) * p%dt * real(acell) / real(mass_of(g, i, j, 1.0))
          s%cq(i,j) = s%cq(i,j) + w
          wq%vrow(j,8) = wq%vrow(j,8) &
                         + real(rate, real64) * real(s%pre(i,j), real64) &
                           * real(p%dt, real64) * acell
        end do
      end do
      !$omp end parallel do
    end if
  end if

  ! (3d) 蓄積(buildup): dB/dt = r·(1 − B/Bmax)。Bmax=0 は線形 dB/dt = r。
  !      指数厳密更新(無条件安定)。B が既に Bmax 以上のセルは蓄積しない
  !      (沈降還流などで上限超過したプールを蓄積式が削らない条件)
  if (wq%have_bd) then
    !$omp parallel do schedule(static) private(i, j, w, rate)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%sw(i,j) > 0) cycle
        if (g%x(i,j) <= 0) cycle
        if (wq%map_to_pool) then
          rate = wq%rmap(i,j)
        else
          rate = wq%bdrate
        end if
        if (rate <= 0.0) cycle
        if (wq%bmax > 0.0) then
          if (s%bp(i,j) >= wq%bmax) cycle
          w = (wq%bmax - s%bp(i,j)) * (1.0 - exp(-rate * p%dt / wq%bmax))
        else
          w = rate * p%dt
        end if
        s%bp(i,j) = s%bp(i,j) + w
        wq%vrow(j,9) = wq%vrow(j,9) + real(w, real64) * acell
      end do
    end do
    !$omp end parallel do
  end if

  ! (3e) 洗い出し(washoff): λ = kr·P + kf·max(τ/τc − 1, 0)。
  !      P = 地表到達降雨強度(m/s)、τ = ρg·n²·vv²/h^(1/3)(マニング閉じ。
  !      m_geomorph_wash の面状侵食と同型)。湿潤セルのみ。
  !      移送 ΔB = B·(1 − e^(−λΔt))(指数厳密・質量保存厳密)
  if (wq%have_wash) then
    !$omp parallel do schedule(static) private(i, j, w, fx, rate)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%sw(i,j) > 0) cycle
        if (g%x(i,j) <= 0) cycle
        if (s%bp(i,j) <= 0.0) cycle
        if (s%h(i,j) <= p%dd) cycle          ! 乾燥セルは輸送水がなく洗えない
        rate = wq%wkr * s%pre(i,j)           ! 雨滴項 (1/s)
        if (wq%wkf > 0.0) then
          fx = max(s%h(i,j), p%dv)
          fx = rhow * p%gg * g%rn(i,j)**2 * s%vv(i,j)**2 / fx**(1.0/3.0)  ! τ (N/m2)
          if (fx > wq%wtauc) rate = rate + wq%wkf * (fx / wq%wtauc - 1.0)
        end if
        if (rate <= 0.0) cycle
        w = s%bp(i,j) * (1.0 - exp(-rate * p%dt))          ! g/m2(幾何面積基底)
        s%bp(i,j) = s%bp(i,j) - w
        s%cq(i,j) = s%cq(i,j) + w * real(acell) / real(mass_of(g, i, j, 1.0))
        wq%vrow(j,10) = wq%vrow(j,10) + real(w, real64) * acell
      end do
    end do
    !$omp end parallel do
  end if

  ! (4) ダム捕捉帯の質量吸収(水は毎ステップ全量吸収されるため質量も
  !     同伴してダム台帳へ。放流濃度 0 = 既知の妥協。§30)
  do nd = 1, wq%ndam
    do k = 1, wq%dam(nd)%nc
      i = wq%dam(nd)%cells(1,k)
      j = wq%dam(nd)%cells(2,k)
      if (s%cq(i,j) <= 0.0) cycle
      wq%vrow(j,4) = wq%vrow(j,4) + mass_of(g, i, j, s%cq(i,j))
      s%cq(i,j) = 0.0
    end do
  end do

  ! (5) 一次減衰(地表 cq・地下 cg とも。指数厳密解 c·exp(-kΔt)。W2)
  !     と沈降(地表のみ。線形近似 c·(1 - vs·Δt/vh)、下限 0。W2)
  if (wq%fdec < 1.0 .or. wq%vs > 0.0) then
    !$omp parallel do schedule(static) private(i, j, w, fx)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (wq%fdec < 1.0) then
          if (s%cq(i,j) > 0.0) then
            w = s%cq(i,j) * (1.0 - wq%fdec)
            s%cq(i,j) = s%cq(i,j) - w
            wq%vrow(j,5) = wq%vrow(j,5) + mass_of(g, i, j, w)
          end if
          if (allocated(s%cg)) then
            if (s%cg(i,j) > 0.0) then
              w = s%cg(i,j) * (1.0 - wq%fdec)
              s%cg(i,j) = s%cg(i,j) - w
              ! cg は幾何面積基底(質量 = w×A。W3)
              wq%vrow(j,5) = wq%vrow(j,5) + real(w, real64) * acell
            end if
          end if
          if (wq%have_pool) then
            if (s%bp(i,j) > 0.0) then
              w = s%bp(i,j) * (1.0 - wq%fdec)
              s%bp(i,j) = s%bp(i,j) - w
              wq%vrow(j,5) = wq%vrow(j,5) + real(w, real64) * acell
            end if
          end if
        end if
        if (wq%vs > 0.0 .and. s%cq(i,j) > 0.0) then
          fx = swflow_vh(i, j, s%h(i,j))
          if (fx > p%dd) then
            w = s%cq(i,j) * min(wq%vs * p%dt / fx, 1.0)
            s%cq(i,j) = s%cq(i,j) - w
            ! 行き先: 消失(河床外)かプール(再懸濁サイクル。f_wq_settle=1)。
            ! 台帳 settle は行き先によらず沈降量を数える(閉合の解釈は §30)
            if (wq%f_settle == 1) then
              s%bp(i,j) = s%bp(i,j) + real(mass_of(g, i, j, w)) / real(acell)
            end if
            wq%vrow(j,6) = wq%vrow(j,6) + mass_of(g, i, j, w)
          end if
        end if
      end do
    end do
    !$omp end parallel do
  end if

end subroutine


!----------------------------------------------------------------------
! 導出濃度 cqc = cq / vh の更新 (mg/L。σ・幅の換算込み。乾燥セルは 0)
!   run_main がステップ末尾パス(post)の後・統計/出力の前に呼ぶ
!   (h が確定した後の濃度を出力・プローブ・測線負荷が読む条件)
!----------------------------------------------------------------------
subroutine m_wq_derive(wq, p, g, s)
  type(t_wq), intent(in) :: wq
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: vh
  if (.not. wq%enabled) return
  !$omp parallel do schedule(static) private(i, j, vh)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      vh = swflow_vh(i, j, s%h(i,j))
      if (vh > p%dd) then
        s%cqc(i,j) = s%cq(i,j) / vh
      else
        s%cqc(i,j) = 0.0
      end if
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! セル (i,j) の cq 基底(gv×wfrac)→ cg の幾何面積基底への換算係数(W3)。
! cg×A = 質量 となる基底に揃えることで、地下横輸送(柱状量の対称交換)の
! 質量収支が gv・wfrac の分布によらず厳密に閉じる(§30)
!----------------------------------------------------------------------
function gwfac_of(g, i, j) result(f)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i, j
  real :: f
  f = g%gv(i,j)
  if (have_width) f = f * wfrac(i,j)
end function


!----------------------------------------------------------------------
! セル (i,j) の柱状量 w に対応する質量 (g)(real64)。
! 質量 = w × gv × wfrac × A(幅無効時は wfrac=1 の乗算で厳密に不変)
!----------------------------------------------------------------------
function mass_of(g, i, j, w) result(mass)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i, j
  real, intent(in) :: w
  real(real64) :: mass
  real :: wf
  wf = 1.0
  if (have_width) wf = wfrac(i,j)
  mass = real(w, real64) * real(g%gv(i,j), real64) * real(wf, real64) &
         * real(g%dx, real64) * real(g%dy, real64)
end function


!----------------------------------------------------------------------
! 区間流入 ifl の流入セルへ濃度 conc を充填する(帯内のみ)
!----------------------------------------------------------------------
subroutine fill_inflow_conc(g, b, ifl, conc)
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(inout) :: b
  integer, intent(in) :: ifl
  real, intent(in) :: conc
  integer :: k, i2, j2
  if (g%nx < 0) continue  ! 引数未使用の警告を抑制
  do k = 1, b%inflow(ifl)%ncell
    i2 = b%inflow(ifl)%cell(1,k)
    j2 = b%inflow(ifl)%cell(2,k)
    if (j2 >= dcp%js .and. j2 <= dcp%je) b%cqin(i2,j2) = conc
  end do
end subroutine


!----------------------------------------------------------------------
! 診断 CSV の出力(record 間隔。collective: 全ランクで呼ぶ)
!   地表・地下の現在貯留質量も台帳化(par_sum_rows = 決定的)
!----------------------------------------------------------------------
subroutine m_wq_record(wq, p, g, s)
  type(t_wq), intent(inout) :: wq
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64) :: v(1:13), msur, mgw, mpool, acell
  real(real64) :: rows(dcp%js:dcp%je), rows2(dcp%js:dcp%je), rows3(dcp%js:dcp%je)
  integer :: i, j, k
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (.not. wq%enabled) return

  acell = real(g%dx, real64) * real(g%dy, real64)
  do k = 1, 13
    call par_sum_rows(wq%vrow(:,k), v(k))
  end do
  rows(:) = 0.0_real64
  rows2(:) = 0.0_real64
  rows3(:) = 0.0_real64
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      rows(j) = rows(j) + mass_of(g, i, j, s%cq(i,j))
      ! cg は幾何面積基底(質量 = cg×A。W3)
      if (allocated(s%cg)) rows2(j) = rows2(j) + real(s%cg(i,j), real64) * acell
      if (wq%have_pool) rows3(j) = rows3(j) + real(s%bp(i,j), real64) * acell
    end do
  end do
  call par_sum_rows(rows, msur)
  call par_sum_rows(rows2, mgw)
  call par_sum_rows(rows3, mpool)

  if (is_root .and. wq%un /= 0) then
    write(wq%un, '(f0.2,16(",",es15.7))') s%t, v(1), v(2), v(7), v(8), v(11), v(9), &
                                          v(10), v(3), v(13), v(12), v(4), v(5), v(6), &
                                          msur, mgw, mpool
    flush(wq%un)
  end if
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モジュール私有ファイル wq.dat。契約C。§7)
!   保存対象: s%cq と cg(cqc は導出量、fxg はスクラッチ = 対象外)
!----------------------------------------------------------------------
subroutine save_state(wq, p, g, s)
  type(t_wq), intent(in) :: wq
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  integer :: un
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
  else
    allocate(wk(1, 1), source = 0.0)
  end if
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/wq.dat', form='unformatted', status='replace')
  end if
  call par_gather_to(wk, s%cq)
  if (is_root) call fileio_write_rle(un, wk)
  ! cg(f_wq_infil=0 では不使用 = ゼロを書いて形式を固定)
  if (allocated(s%cg)) then
    call par_gather_to(wk, s%cg)
  else
    if (is_root) wk = 0.0
  end if
  if (is_root) call fileio_write_rle(un, wk)
  ! bp(プール無効時もゼロを書いて形式を固定 = 常に3成分)
  if (wq%have_pool) then
    call par_gather_to(wk, s%bp)
  else
    if (is_root) wk = 0.0
  end if
  if (is_root) then
    call fileio_write_rle(un, wk)
    close(un)
  end if
  if (dum(1,1) > huge(0.0)) continue  ! 引数未使用の警告を抑制
end subroutine


subroutine restore_state(wq, p, g, s)
  type(t_wq), intent(inout) :: wq
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  logical :: found
  integer :: un

  ! 版・格子・精度の検証は m_state(check_save_info)が済ませている。
  ! 自ファイルの有無のみ確認(無ければ「保存時は wq 無効だった」として
  ! ゼロ初期のまま続行を許すのではなく停止する — 意図しない質量消失を防ぐ)
  fname = trim(p%dir_save)//'/wq.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("wq: state file not found (was fn_wq enabled when saving): "//fname)
  end if

  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, s%cq)
  else
    call par_scatter_cell(dum, s%cq)
  end if
  if (allocated(s%cg)) then
    if (is_root) then
      call fileio_read_rle(un, wk)
      call par_scatter_cell(wk, s%cg)
    else
      call par_scatter_cell(dum, s%cg)
    end if
  else
    if (is_root) call fileio_read_rle(un, wk)   ! cg 不使用 = 読み飛ばし
  end if
  if (wq%have_pool) then
    if (is_root) then
      call fileio_read_rle(un, wk)
      call par_scatter_cell(wk, s%bp)
    else
      call par_scatter_cell(dum, s%bp)
    end if
  end if
  ! プール無効時は bp レコードを読み飛ばすだけ(形式は常に3成分)
  if (is_root) close(un)
end subroutine


!----------------------------------------------------------------------
! 水質モジュールを破棄する(save は dispose で行う。契約C)
!----------------------------------------------------------------------
subroutine m_wq_dispose(wq, p, g, s)
  type(t_wq), intent(inout) :: wq
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (.not. wq%enabled) return
  if (p%f_state_save > 0) call save_state(wq, p, g, s)
  if (is_root .and. wq%un /= 0) close(wq%un)
  wq%un = 0
  if (allocated(wq%pt)) deallocate(wq%pt)
  if (allocated(wq%ar)) deallocate(wq%ar)
  if (allocated(wq%inifl)) deallocate(wq%inifl)
  if (allocated(wq%incval)) deallocate(wq%incval)
  if (allocated(wq%inser)) deallocate(wq%inser)
  if (allocated(wq%rmap)) deallocate(wq%rmap)
  if (allocated(wq%dam)) deallocate(wq%dam)
  if (allocated(wq%vrow)) deallocate(wq%vrow)
  wq%enabled = .false.
  wq%initialized = .false.
end subroutine

end module
