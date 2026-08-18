module m_gwflow_pump
  ! ========= 地下水シンク: 井戸揚水・地下水取水 =========
  ! セル集合+流量時系列(または一定値)で指定した揚水量を地下貯留から
  ! 汲み上げ、系外へ除去する(内部ソース &list_bound_source の地下版。
  ! 2026-08-18。developer.md §16.4)。
  !   - 有効化は &list_gwflow の f_gwpump=1(加算的プロセス。無効時は
  !     資源を一切確保しない)。設定は同じ fn_gwflow 内の
  !     &list_gwflow_pump(自分で読む。m_gwflow_bucket 契約)
  !   - 井戸は最大 npmax 個。各井戸はセル集合(井戸群・集水域取水)+
  !     流量 (m3/s。正=取水のみ) を持ち、需要はセル集合へ等分配する
  !     (あるセルが涸れても他セルへは再配分しない = 局所性の維持)
  !   - 取水層 gwp_layer: 1=土層 s%hg(既定)、2=風化基岩層 s%hg2
  !     (f_gwlayer2=1 が必要)
  !   - 取水はそのセルの貯留でキャップする(涸れ井戸 = 供給律速。
  !     無条件安定で dt 制約なし)。需要と実取水の累積を井戸別に集計し、
  !     dispose で総括を表示する(涸れの診断)
  !   - 淡塩2層(f_salt_gw=1)併用時は淡水優先で汲む(浅い井戸
  !     スクリーン近似: 界面より上から取水)。淡水厚で足りない分だけ
  !     塩水層 s%hgs を減らす(= 塩水の混入)。揚水誘引の海水浸入・
  !     アップコーニングは側方流動と塩水層ダイナミクスが自動で表す
  !   - 注入(負の流量)は非対応(容量超過分の行き先の定義が要るため。
  !     地表への還元・灌漑は &list_bound_source で別途与える)
  !   - 汲み上げは瞬時フラックスで内部状態を持たない → save/restore
  !     不要(契約5)。時系列は絶対時刻 s%t で引くためリスタスト整合
  !   - owner-compute: 自帯 js..je のセルのみ更新。セル局所の鉛直操作
  !     なのでハロ交換は不要(契約3。ハロの hg は次の側方 calc 冒頭・
  !     saltwater calc 冒頭で交換される)
  ! ======================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_boundary, only : interp_series, read_cell_file2, read_val_file2
  use m_gwflow_layer2, only : gwflow_layer2_active
  use m_parallel, only : par_info, par_stop, par_allreduce_sumr, dcp, is_root
  use m_util, only : itoa
  implicit none
  private
  public :: gwflow_pump_init
  public :: gwflow_pump_calc
  public :: gwflow_pump_dispose

  integer, parameter :: npmax = 50     ! 井戸の最大数
  integer, parameter :: npcmax = 99    ! 1井戸あたりの最大セル数(インライン。
                                       !   それ以上は fn_gwp_cell のファイルで)
  integer, parameter :: npvmax = 999   ! 時系列の最大データ数(インライン)

  type t_well                          ! 井戸1個
    integer :: ncell = 0               ! セル数
    integer, allocatable :: cell(:,:)  ! セル座標 (1:2, 1:ncell)
    integer :: nval = 0                ! 時系列データ数
    real, allocatable :: val(:,:)      ! 時系列 (1:2, 1:nval) (s, m3/s)
    integer :: layer = 1               ! 取水層(1:土層 hg, 2:風化基岩層 hg2)
    real :: dem = 0.0                  ! 累積需要(自帯セル分の柱状水深和 m)
    real :: act = 0.0                  ! 累積取水(同上)
  end type

  ! モデル私有の設定(単一インスタンス前提。developer.md §12)
  type t_gwpump
    integer :: nwell = 0
    type(t_well), allocatable :: well(:)
    logical :: initialized = .false.
  end type
  type(t_gwpump) :: gp

  ! namelist 読み込み用の静的作業配列(スタックに置かないための措置。
  ! list_boundary と同じ実バグ対策。init のみ使用)
  integer :: gwp_cell(1:2,1:npcmax,1:npmax)
  real :: gwp_val(1:2,1:npvmax,1:npmax)

contains


!----------------------------------------------------------------------
! 井戸揚水の初期化(固有グループ &list_gwflow_pump を自分で読む)。
! gwp_layer=2 の検査があるため m_gwflow_init は層2 init より後に呼ぶこと
!----------------------------------------------------------------------
subroutine gwflow_pump_init(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: un, ios
  real :: gwp_q0(1:npmax)
  integer :: gwp_layer(1:npmax)
  character(len=1024) :: fn_gwp_cell(1:npmax), fn_gwp_val(1:npmax)
  logical :: active(1:npmax)
  integer :: iw, n, k, i, j
  namelist /list_gwflow_pump/ gwp_cell, gwp_q0, gwp_val, gwp_layer, &
                              fn_gwp_cell, fn_gwp_val

  if (s%initialized) continue  ! 引数未使用の警告を抑制

  gwp_cell = -9999
  gwp_q0 = -9999.0
  gwp_val = -9999.0
  gwp_layer = 1
  fn_gwp_cell = ""
  fn_gwp_val = ""

  call par_info("reading list_gwflow_pump in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_pump: cannot open " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow_pump, iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_pump: cannot read namelist " &
                              // "(f_gwpump=1 requires &list_gwflow_pump)")
  close(un)

  ! 井戸番号は 1 から連続(&list_bound_source と同じ規約)
  do iw = 1, npmax
    active(iw) = (gwp_cell(1,1,iw) > -9999) &
                 .or. (gwp_val(1,1,iw) > -9999.0) &
                 .or. (gwp_q0(iw) > -9999.0) &
                 .or. (len_trim(fn_gwp_cell(iw)) > 0) &
                 .or. (len_trim(fn_gwp_val(iw)) > 0)
  end do
  gp%nwell = count(active)
  if (gp%nwell <= 0) call par_stop("list_gwflow_pump: no wells defined (f_gwpump=1)")
  if (.not. all(active(1:gp%nwell))) then
    call par_stop("list_gwflow_pump: well numbers must be consecutive from 1")
  end if

  allocate(gp%well(1:gp%nwell))
  do iw = 1, gp%nwell

    !--- セル集合(ファイル指定が優先) ---
    if (len_trim(fn_gwp_cell(iw)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(fn_gwp_cell(iw)), &
                           gp%well(iw)%ncell, gp%well(iw)%cell)
    else
      n = 0
      do k = 1, npcmax
        if (gwp_cell(1,k,iw) <= -9999) exit   ! 番兵で終端
        n = n + 1
      end do
      allocate(gp%well(iw)%cell(1:2,1:max(n,1)))
      gp%well(iw)%cell(1:2,1:n) = gwp_cell(1:2,1:n,iw)
      gp%well(iw)%ncell = n
    end if

    !--- 流量(ファイル > インライン時系列 > 一定値。時刻は分→秒換算) ---
    if (len_trim(fn_gwp_val(iw)) > 0) then
      call read_val_file2(trim(p%dir_data)//"/"//trim(fn_gwp_val(iw)), &
                          gp%well(iw)%nval, gp%well(iw)%val)
    else if (gwp_val(1,1,iw) > -9999.0) then
      n = 0
      do k = 1, npvmax
        if (gwp_val(1,k,iw) <= -9999.0) exit  ! 番兵で終端
        n = n + 1
      end do
      allocate(gp%well(iw)%val(1:2,1:max(n,1)))
      gp%well(iw)%val(1,1:n) = gwp_val(1,1:n,iw) * 60   ! 分を秒に換算
      gp%well(iw)%val(2,1:n) = gwp_val(2,1:n,iw)
      gp%well(iw)%nval = n
    else if (gwp_q0(iw) > -9999.0) then
      allocate(gp%well(iw)%val(1:2,1:1))                ! 一定値は1点時系列に退化
      gp%well(iw)%val(1,1) = 0.0
      gp%well(iw)%val(2,1) = gwp_q0(iw)
      gp%well(iw)%nval = 1
    end if

    !--- 取水層 ---
    gp%well(iw)%layer = gwp_layer(iw)

    !--- 検証 ---
    if (gp%well(iw)%ncell <= 0) then
      call par_stop("list_gwflow_pump: well "//itoa(iw)//" has no cells")
    end if
    if (gp%well(iw)%nval <= 0) then
      call par_stop("list_gwflow_pump: well "//itoa(iw)//" has no pumping rate " &
                    // "(give gwp_q0, gwp_val or fn_gwp_val)")
    end if
    if (any(gp%well(iw)%val(2,1:gp%well(iw)%nval) < 0.0)) then
      call par_stop("list_gwflow_pump: well "//itoa(iw)//" has a negative rate " &
                    // "(injection is not supported; use &list_bound_source for recharge)")
    end if
    if (gp%well(iw)%layer < 1 .or. gp%well(iw)%layer > 2) then
      call par_stop("list_gwflow_pump: well "//itoa(iw)//" gwp_layer must be " &
                    // "1(soil) or 2(weathered bedrock)")
    end if
    if (gp%well(iw)%layer == 2 .and. .not. gwflow_layer2_active()) then
      call par_stop("list_gwflow_pump: well "//itoa(iw)//" gwp_layer=2 requires " &
                    // "f_gwlayer2=1")
    end if
    do k = 1, gp%well(iw)%ncell
      i = gp%well(iw)%cell(1,k)
      j = gp%well(iw)%cell(2,k)
      if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
        call par_stop("list_gwflow_pump: well "//itoa(iw)//" cell (" &
                      //itoa(i)//","//itoa(j)//") is outside the domain")
      end if
      if (g%x(i,j) <= 0) then
        call par_stop("list_gwflow_pump: well "//itoa(iw)//" cell (" &
                      //itoa(i)//","//itoa(j)//") is not a valid cell")
      end if
      if (g%sw(i,j) > 0) then
        call par_stop("list_gwflow_pump: well "//itoa(iw)//" cell (" &
                      //itoa(i)//","//itoa(j)//") is a sea cell")
      end if
    end do
  end do

  call par_info(" gwflow_pump: "//itoa(gp%nwell)//" well(s)")
  gp%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 井戸揚水の計算(1回の呼び出しで実効時間刻み dts ぶんの取水)。
! 実行判定(井戸数・時系列)は namelist 由来で全ランク同一(collective
! 安全。ただし本手続きに collective はない)
!----------------------------------------------------------------------
subroutine gwflow_pump_calc(p, g, s, it, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  real, intent(in) :: dts
  integer :: iw, k, i, j
  real :: q, dh, hgb, fx, sx

  if (it < 0) continue  ! 引数未使用の警告を抑制
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  do iw = 1, gp%nwell
    q = interp_series(gp%well(iw)%val, gp%well(iw)%nval, s%t)
    if (q <= 0.0) cycle
    ! セルあたりの需要(柱状換算水深 m。セル集合へ等分配)
    dh = q * dts / (gp%well(iw)%ncell * g%dx * g%dy)
    do k = 1, gp%well(iw)%ncell
      i = gp%well(iw)%cell(1,k)
      j = gp%well(iw)%cell(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle       ! owner-compute
      gp%well(iw)%dem = gp%well(iw)%dem + dh
      if (gp%well(iw)%layer == 1) then
        ! 土層から取水(貯留でキャップ = 涸れ井戸)
        hgb = s%hg(i,j)
        fx = min(dh, hgb)
        if (fx <= 0.0) cycle
        s%hg(i,j) = hgb - fx
        ! 淡塩2層: 淡水優先(浅井戸スクリーン近似)。淡水厚
        ! hgb - hgs で足りない分だけ塩水層を減らす(fx <= hgb より
        ! sx <= hgs が構造的に成立。max は丸め保護)
        if (allocated(s%hgs)) then
          sx = fx - (hgb - s%hgs(i,j))
          if (sx > 0.0) s%hgs(i,j) = max(s%hgs(i,j) - sx, 0.0)
        end if
      else
        ! 風化基岩層から取水
        fx = min(dh, s%hg2(i,j))
        if (fx <= 0.0) cycle
        s%hg2(i,j) = s%hg2(i,j) - fx
      end if
      gp%well(iw)%act = gp%well(iw)%act + fx
    end do
  end do

end subroutine


!----------------------------------------------------------------------
! 井戸揚水の破棄。需要・実取水の総括を表示する(涸れの診断)。
! par_allreduce_sumr は collective — 全ランクが dispose を呼ぶ前提
! (m_gwflow_dispose 経由で成立)。診断のみで状態には関与しない
!----------------------------------------------------------------------
subroutine gwflow_pump_dispose(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real, allocatable :: vsum(:)
  character(len=256) :: msg
  integer :: iw
  real :: pct

  if (p%initialized) continue  ! 引数未使用の警告を抑制

  if (gp%nwell > 0) then
    ! 井戸別の需要・実取水を全ランク総和し体積 (m3) で総括
    allocate(vsum(1:2*gp%nwell))
    do iw = 1, gp%nwell
      vsum(2*iw-1) = gp%well(iw)%dem * g%dx * g%dy
      vsum(2*iw)   = gp%well(iw)%act * g%dx * g%dy
    end do
    call par_allreduce_sumr(vsum)
    if (is_root) then
      do iw = 1, gp%nwell
        pct = 100.0
        if (vsum(2*iw-1) > 0.0) pct = vsum(2*iw) / vsum(2*iw-1) * 100.0
        write(msg,'(a,i0,a,es12.4,a,es12.4,a,f6.1,a)') &
          " gwflow_pump: well ", iw, ": demand ", vsum(2*iw-1), &
          " m3, pumped ", vsum(2*iw), " m3 (", pct, " %)"
        call par_info(trim(msg))
      end do
    end if
    deallocate(vsum)
  end if

  if (allocated(gp%well)) deallocate(gp%well)
  gp%nwell = 0
  gp%initialized = .false.
end subroutine

end module
