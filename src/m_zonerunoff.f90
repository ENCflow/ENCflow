module m_zonerunoff
  ! ============ 区画流出の共通基盤(VZ 流出 §87 と貯留関数法 §106 が共有) ============
  ! 区画番号ラスタで指定した区画について、モデル(VZ の共有参照柱、貯留関数の
  ! タンク)の外側の受け渡しを受け持つ(developer.md §106.2。§16.1 の「第 2 モデルが
  ! 実在した時点で昇格」により m_vzflow から移した部分)。
  !
  ! 【受け持つもの】
  !   区画番号ラスタ : 読み込み(rank0 → 全ランク)・セルの検査(海・河道・境界・
  !                    ソース・構造物のセルに置けない)・区画のセル数と面積・
  !                    帯の区画番号 zid
  !   入力群         : 区画をまとめて同じ上端流束で駆動する単位(VZ = 共有参照柱、
  !                    貯留関数 = 区画そのもの)。区画 → 入力群の対応はモデルが渡す
  !   雨の回収       : swflow の直後に区画セルの雨 pre·dt/gv を s%h から回収し、
  !                    モデルの未同期の雨の台帳(VZ の s%vzp 等)に積む(h を 0 で
  !                    切らない。§87.2)。入力群の上端流束は、厳密一致モード
  !                    (rainmode = 0。群内で地上雨量が一致しなければ停止)か
  !                    面積平均モード(= 1。行部分和の決定的総和。独自の近似)で
  !                    同期時刻に確定し、区分一定の区間に圧縮する
  !   出口           : 区画の流出を地表セルへ配分率つきで移す(kind 1)か系外へ
  !                    出す(kind 2)。地表セルへの加算は所有ランクだけ、同じセルへの
  !                    複数区画の量は合計して一度だけ、要求と実際に加わった体積の
  !                    差は real64 の繰越
  !   基底流         : 区画ごとの時系列(時刻(分), mm/h。区画面積基底)を同期区間で
  !                    厳密に積分し、流出と同じ出口へ渡す(外部供給。§87.9)
  ! 【受け持たないもの】区画の流出量の計算(柱・タンクの前進)・区画の貯留・
  !   モデル固有の検査・保存ファイルの形式(繰越の集約 zr_gather_carry だけを
  !   提供し、書き出しと読み込みはモデルの save/restore が行う)
  !
  ! 【並列】帯の区画番号だけを時間ループで使う。全ランク同値の量(区画の累積・
  !   出口の累積)と所有ランクだけが意味を持つ量(繰越)を区別する。判定は全ランクで
  !   同一(collective 安全)。
  ! ==========================================================================
  use, intrinsic :: iso_fortran_env, only : real64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state, sect_cell, sect_vh, sect_add_vh
  use m_boundary, only : t_boundary, read_val_file2
  use m_swflow_enc, only : chn
  use m_fileio, only : fileio_read_matrix
  use m_util, only : itoa
  use m_parallel, only : par_info, par_stop, dcp, is_root, par_bcast_cell_i, par_allreduce_max, &
                         par_allreduce_sumi, par_allreduce_maxi, par_sum_rows
  implicit none
  private
  public :: t_zonerunoff, t_zrzone
  public :: zr_read_map, zr_set_groups, zr_setup_outlets, zr_setup_baseflow, zr_alloc_interval
  public :: zr_recover_rain, zr_collect_input, zr_deliver, zr_gather_carry
  public :: zr_report_outlets, zr_check_disjoint, zr_dispose, zr_stop_at

  !-------------------------------------------
  ! 区画の出口・基底流・移送の累積(全ランク同値)
  !-------------------------------------------
  type t_zrzone
    integer :: grp = 0                         ! 入力群(VZ = 柱、貯留関数 = 区画)
    integer :: ncell = 0                       ! セル数(全域)
    real(real64) :: area = 0.0_real64          ! 面積 A_g (m2)
    integer :: kind = 0                        ! 出口 1: 地表セル / 2: 系外
    integer :: nout = 0                        ! 出口セル数(kind = 1)
    integer, allocatable :: oidx(:)            ! 出口セルの通し番号(t_zonerunoff の ocell の添字)
    real(real64), allocatable :: ow(:)         ! 配分率(和 = 1 に正規化済み)
    integer :: nbase = 0                       ! 基底流の時系列の点数(0 = 基底流なし)
    real(real64), allocatable :: bt(:), bq(:)  ! 基底流の時系列(時刻 s、強度 m/s。区画面積基底)
    real(real64) :: vint = 0.0_real64          ! 地表セルへの移送の累積(流出 + 基底流。m3)
    real(real64) :: vext = 0.0_real64          ! 系外流出の累積(流出 + 基底流。m3)
    real(real64) :: vbase = 0.0_real64         ! 基底流の累積(外部供給。m3)
  end type

  !-------------------------------------------
  ! 区画流出の共通部の状態(モデルの容器の成分。init に早期 return 経路が
  ! あるため全成分デフォルト初期化。§13)
  !-------------------------------------------
  type t_zonerunoff
    character(len=8) :: tag = ""               ! メッセージ・変数名の接頭辞("vz" / "sfm")
    character(len=8) :: label = ""             ! 区画セルの呼び名("VZ" / "SFM")
    character(len=24) :: nml = ""              ! 区画の namelist グループ名(メッセージ用)
    character(len=8) :: grpword = ""           ! 入力群の呼び名("column" / "zone")
    integer :: nzone = 0, ngrp = 0
    type(t_zrzone), allocatable :: zones(:)
    integer, allocatable :: zid(:,:)           ! 区画番号(帯 ish:ieh, jsh:jeh。0 = 適用外)
    integer, allocatable :: grpncell(:)        ! 入力群のセル数(全域)
    logical :: have_base = .false.             ! 基底流を与えた区画があるか
    integer :: rainmode = 0                    ! 0: 群内で一致を要求 / 1: 群内面積平均
    integer :: idt = 1                         ! 同期間隔(ステップ数)
    real(real64) :: dxdy = 0.0_real64          ! セル面積 (m2)
    integer :: kstep = 0                       ! 現在の同期区間に積算済みのステップ数
    ! 厳密一致モードの区間内履歴(ステップ × 群。局所の max と −min。PREC = s%pre と同じ)
    real, allocatable :: rmx(:,:), rmn(:,:)
    ! 面積平均モード: 局所の行部分和の変化点スナップショット
    integer, allocatable :: chg(:)             ! (1:idt) 局所で入力が変わったステップ
    real(real64), allocatable :: rsnow(:,:)    ! (js:je, 1:ngrp) このステップの行部分和
    real(real64), allocatable :: rsprev(:,:)   ! 直前のスナップショット
    integer :: nsnap = 0
    integer, allocatable :: snapk(:)           ! スナップショットのステップ
    real(real64), allocatable :: snap(:,:,:)   ! (js:je, 1:ngrp, 1:nsnap)
    ! 区間の区分一定入力(群ごと)
    real(real64), allocatable :: rstep(:,:)    ! (1:idt, 1:ngrp) 各ステップの上端流束 (m/s)
    integer, allocatable :: nseg(:)
    real(real64), allocatable :: segl(:,:), segr(:,:)   ! (1:idt, 1:ngrp) 区間の長さ (s)・流束 (m/s)
    real(real64), allocatable :: rlast(:)      ! 直近ステップの上端流束 (m/s)
    ! 出口セル(全区画で重複を除いた一覧)
    integer :: nocell = 0
    integer, allocatable :: ocell(:,:)         ! (1:2, 1:nocell)
    real(real64), allocatable :: ovol(:)       ! 同期区間の移送量 (m3。作業)
    real(real64), allocatable :: ocarry(:)     ! 繰越(要求と実際に加わった体積の差 m3。所有ランクのみ意味を持つ)
    real(real64), allocatable :: ovcum(:)      ! 累積の移送量 (m3。全ランク同値)
  end type

contains


!----------------------------------------------------------------------
! 区画番号ラスタを読み、検査し、区画のセル数・面積と帯の区画番号を作る。
! zmap(全域)を返す(モデルが区画ごとの重み等の初期化に使う一時配列)。
!   tag・label・nml・grpword はメッセージ用の名前(呼び出し前に設定済み)
!   nzmax: 区画番号の上限(namelist の配列寸法)
!----------------------------------------------------------------------
subroutine zr_read_map(zr, p, g, b, fn, fnname, nzmax, zmap)
  type(t_zonerunoff), intent(inout) :: zr
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  character(len=*), intent(in) :: fn       ! 区画番号ラスタのファイル名(dir_data 起点)
  character(len=*), intent(in) :: fnname   ! その変数名(メッセージ用)
  integer, intent(in) :: nzmax
  integer, allocatable, intent(out) :: zmap(:,:)
  integer :: i, j, z, nzn
  character(:), allocatable :: fname

  if (len_trim(fn) == 0) call par_stop("list_"//trim(zr%tag)//": "//fnname//" (zone number raster) is required")
  zr%dxdy = real(g%dx, real64) * real(g%dy, real64)

  ! --- 区画番号マップ(整数。rank0 読み → 全ランクへ) ---
  allocate(zmap(1:g%nx, 1:g%ny), source = 0)
  fname = trim(p%dir_data) // "/" // trim(fn)
  call par_info(" reading " // fname)
  if (is_root) call fileio_read_matrix(fname, g%nx, g%ny, zmap, p%f_input_mode)
  call par_bcast_cell_i(zmap)
  nzn = 0
  do j = 1, g%ny
    do i = 1, g%nx
      if (g%x(i,j) <= 0) then
        zmap(i,j) = 0                  ! 領域外の値は使わない
        cycle
      end if
      if (zmap(i,j) < 0) call zr_stop_at(trim(zr%tag)//": negative zone number", i, j)
      if (zmap(i,j) == 0) cycle
      if (g%sw(i,j) > 0) call zr_stop_at(trim(zr%tag)//": a "//trim(zr%label)//" cell is on a sea cell", i, j)
      if (g%rw(i,j) > 0) call zr_stop_at(trim(zr%tag)//": a "//trim(zr%label)//" cell is on a channel cell (rw)", i, j)
      nzn = max(nzn, zmap(i,j))
    end do
  end do
  if (nzn == 0) call par_stop(trim(zr%tag)//": "//fnname//" has no "//trim(zr%label) &
                              //" cell (all zone numbers are 0 in the domain)")
  if (nzn > nzmax) call par_stop(trim(zr%tag)//": zone numbers must be <= "//itoa(nzmax))
  zr%nzone = nzn
  allocate(zr%zones(1:nzn))
  call check_cells(zr, b, zmap)

  ! --- 区画のセル数と面積 ---
  do j = 1, g%ny
    do i = 1, g%nx
      z = zmap(i,j)
      if (z == 0) cycle
      zr%zones(z)%ncell = zr%zones(z)%ncell + 1
    end do
  end do
  do z = 1, nzn
    if (zr%zones(z)%ncell == 0) call par_stop(trim(zr%tag)//": zone "//itoa(z)//" has no cell in "//fnname)
    zr%zones(z)%area = zr%dxdy * real(zr%zones(z)%ncell, real64)
  end do

  ! --- 帯の区画番号(時間ループ用) ---
  allocate(zr%zid(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0)
  do j = max(dcp%jsh, 1), min(dcp%jeh, g%ny)
    do i = max(dcp%ish, 1), min(dcp%ieh, g%nx)
      zr%zid(i,j) = zmap(i,j)
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 区画セルが境界・ソース・構造物のセルと重ならないこと(雨の回収量が
! boundary_h の式と一致する前提。vz_plan.md §4.10)
!----------------------------------------------------------------------
subroutine check_cells(zr, b, zmap)
  type(t_zonerunoff), intent(in) :: zr
  type(t_boundary), intent(in) :: b
  integer, intent(in) :: zmap(:,:)
  integer :: k, n
  do k = 1, b%nsrc
    do n = 1, b%src(k)%ncell
      call chk(b%src(k)%cell(1,n), b%src(k)%cell(2,n), "an injection/extraction source")
    end do
  end do
  do k = 1, b%nstage
    do n = 1, b%stage(k)%ncell
      call chk(b%stage(k)%cell(1,n), b%stage(k)%cell(2,n), "a water level boundary")
    end do
  end do
  do k = 1, b%ninflow
    do n = 1, b%inflow(k)%ncell
      call chk(b%inflow(k)%cell(1,n), b%inflow(k)%cell(2,n), "an inflow boundary")
    end do
  end do
  do k = 1, b%nstruct
    do n = 1, b%struct(k)%ncin
      call chk(b%struct(k)%cin(1,n), b%struct(k)%cin(2,n), "a structure")
    end do
    do n = 1, b%struct(k)%ncout
      call chk(b%struct(k)%cout(1,n), b%struct(k)%cout(2,n), "a structure")
    end do
  end do
contains
  subroutine chk(i, j, what)
    integer, intent(in) :: i, j
    character(len=*), intent(in) :: what
    if (i < 1 .or. i > size(zmap,1) .or. j < 1 .or. j > size(zmap,2)) return
    if (zmap(i,j) > 0) call zr_stop_at(trim(zr%tag)//": a "//trim(zr%label)//" cell overlaps "//what//" cell", i, j)
  end subroutine
end subroutine


!----------------------------------------------------------------------
! 区画 → 入力群の対応(grp(z) は 1..ngrp。全群が参照されていることはモデルが
! 検査する)と群のセル数
!----------------------------------------------------------------------
subroutine zr_set_groups(zr, grp, ngrp)
  type(t_zonerunoff), intent(inout) :: zr
  integer, intent(in) :: grp(:)
  integer, intent(in) :: ngrp
  integer :: z
  zr%ngrp = ngrp
  do z = 1, zr%nzone
    zr%zones(z)%grp = grp(z)
  end do
  allocate(zr%grpncell(1:ngrp), source = 0)
  do z = 1, zr%nzone
    zr%grpncell(zr%zones(z)%grp) = zr%grpncell(zr%zones(z)%grp) + zr%zones(z)%ncell
  end do
end subroutine


!----------------------------------------------------------------------
! 出口(区画ごとの種別・セル・配分率)と、全区画で重複を除いたセル一覧
!   out_kind(z)・out_cell(1:2, k, z)・out_w(k, z) は namelist の生の値
!   (未指定は −9999)。変数名はメッセージで tag を接頭辞にして示す
!----------------------------------------------------------------------
subroutine zr_setup_outlets(zr, g, b, out_kind, out_cell, out_w, zmap)
  type(t_zonerunoff), intent(inout) :: zr
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  integer, intent(in) :: out_kind(:)
  integer, intent(in) :: out_cell(:,:,:)
  real, intent(in) :: out_w(:,:)
  integer, intent(in) :: zmap(:,:)
  integer :: z, k, kk, n, i, j, q, st, ns, noutmax
  integer, allocatable :: tmpcell(:,:)
  real(real64) :: wsum
  character(len=16) :: tag
  character(:), allocatable :: nml, pf

  nml = trim(zr%nml)
  pf = trim(zr%tag)
  noutmax = size(out_cell, 2)
  allocate(tmpcell(1:2, 1:noutmax * zr%nzone), source = 0)
  zr%nocell = 0
  do z = 1, zr%nzone
    write(tag, '("(",i0,")")') z
    associate (zz => zr%zones(z))
      n = 0
      do k = 1, noutmax
        if (out_cell(1,k,z) <= -9998) exit
        n = k
      end do
      select case (out_kind(z))
        case (1)
          if (n == 0) call par_stop(nml//": "//pf//"_out_kind"//trim(tag)//"=1 requires "//pf//"_out_cell(:,:,"// &
                                    itoa(z)//")")
        case (2)
          if (n > 0) call par_stop(nml//": "//pf//"_out_kind"//trim(tag)//"=2 (outflow from the system)" &
                                   //" takes no "//pf//"_out_cell")
        case default
          call par_stop(nml//": "//pf//"_out_kind"//trim(tag)//" must be given: 1(surface cells) or" &
                        //" 2(outflow from the system)")
      end select
      zz%kind = out_kind(z)
      zz%nout = n
      if (n == 0) cycle
      allocate(zz%oidx(1:n), zz%ow(1:n))
      do k = 1, n
        i = out_cell(1,k,z)
        j = out_cell(2,k,z)
        if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
          call par_stop(nml//": outlet cell out of the grid in zone "//itoa(z)//": ("// &
                        itoa(i)//","//itoa(j)//")")
        end if
        if (g%x(i,j) <= 0) call zr_stop_at(nml//": an outlet cell is outside the domain", i, j)
        if (g%sw(i,j) > 0) call zr_stop_at(nml//": an outlet cell is a sea cell (use "//pf//"_out_kind=2" &
                                           //" for outflow from the system)", i, j)
        if (zmap(i,j) > 0) call zr_stop_at(nml//": an outlet cell is a "//trim(zr%label)//" cell", i, j)
        do kk = 1, k - 1
          if (out_cell(1,kk,z) == i .and. out_cell(2,kk,z) == j) then
            call zr_stop_at(nml//": duplicate outlet cell in zone "//itoa(z), i, j)
          end if
        end do
        do st = 1, b%nstage
          do ns = 1, b%stage(st)%ncell
            if (b%stage(st)%cell(1,ns) == i .and. b%stage(st)%cell(2,ns) == j) then
              call zr_stop_at(nml//": an outlet cell is a water level boundary cell", i, j)
            end if
          end do
        end do
        ! 重複を除いた一覧へ登録
        q = 0
        do kk = 1, zr%nocell
          if (tmpcell(1,kk) == i .and. tmpcell(2,kk) == j) q = kk
        end do
        if (q == 0) then
          zr%nocell = zr%nocell + 1
          q = zr%nocell
          tmpcell(1,q) = i
          tmpcell(2,q) = j
        end if
        zz%oidx(k) = q
        ! 配分率: 1 セルなら省略可(= 1)。複数なら全て必須(暗黙の等分配はしない)
        if (out_w(k,z) <= -9998.0) then
          if (n == 1) then
            zz%ow(k) = 1.0_real64
          else
            call par_stop(nml//": "//pf//"_out_w(:,"//itoa(z)//") is required for every outlet cell" &
                          //" when a zone has more than one")
          end if
        else
          if (.not. (out_w(k,z) >= 0.0)) then
            call par_stop(nml//": "//pf//"_out_w(:,"//itoa(z)//") must be >= 0")
          end if
          zz%ow(k) = real(out_w(k,z), real64)
        end if
      end do
      wsum = sum(zz%ow)
      if (abs(wsum - 1.0_real64) > 1.0e-6_real64) then
        call par_stop(nml//": "//pf//"_out_w(:,"//itoa(z)//") must sum to 1")
      end if
      zz%ow(:) = zz%ow(:) / wsum       ! 丸め規模の差だけ正規化(採用値は区画確認表に出す)
    end associate
  end do
  allocate(zr%ocell(1:2, 1:max(zr%nocell,1)), source = 0)
  if (zr%nocell > 0) zr%ocell(:, 1:zr%nocell) = tmpcell(:, 1:zr%nocell)
  allocate(zr%ovol(1:max(zr%nocell,1)), zr%ocarry(1:max(zr%nocell,1)), zr%ovcum(1:max(zr%nocell,1)), &
           source = 0.0_real64)
end subroutine


!----------------------------------------------------------------------
! 基底流の時系列(区画ごと。ファイル指定が namelist より優先 = 境界の時系列と
! 同じ規約)。時刻は分 → 秒、強度は mm/h → m/s。時刻は減らないこと
! (同じ時刻の 2 点で段差を表せる)、強度は 0 以上
!   base(1:2, k, z) = (時刻(分), mm/h)(未指定は −9999)、fn_base(z) はファイル名
!----------------------------------------------------------------------
subroutine zr_setup_baseflow(zr, p, base, fn_base)
  type(t_zonerunoff), intent(inout) :: zr
  type(t_sysparam), intent(in) :: p
  real, intent(in) :: base(:,:,:)
  character(len=*), intent(in) :: fn_base(:)
  integer :: z, k, n
  real, allocatable :: val(:,:)
  character(len=16) :: tag

  do z = 1, zr%nzone
    write(tag, '("(",i0,")")') z
    if (len_trim(fn_base(z)) > 0) then
      call par_info(" reading "//trim(p%dir_data)//"/"//trim(fn_base(z)))
      call read_val_file2(trim(p%dir_data)//"/"//trim(fn_base(z)), n, val)
      if (n == 0) call par_stop(trim(zr%nml)//": fn_"//trim(zr%tag)//"_base"//trim(tag)//" has no data")
    else
      n = 0
      do k = 1, size(base, 2)
        if (base(1,k,z) <= -9998.0) exit    ! 番兵で終端
        n = k
      end do
      if (n == 0) cycle
      allocate(val(1:2, 1:n))
      val(1,1:n) = base(1,1:n,z) * 60     ! 分を秒に(ファイルの読み込みと同じ演算)
      val(2,1:n) = base(2,1:n,z)
    end if
    associate (zz => zr%zones(z))
      zz%nbase = n
      allocate(zz%bt(1:n), zz%bq(1:n))
      do k = 1, n
        if (.not. (val(2,k) >= 0.0)) then
          call par_stop(trim(zr%nml)//": the baseflow of zone "//itoa(z)//" must be >= 0 (mm/h)")
        end if
        if (k > 1) then
          if (val(1,k) < val(1,k-1)) then
            call par_stop(trim(zr%nml)//": the baseflow times of zone "//itoa(z)//" must not decrease")
          end if
        end if
        zz%bt(k) = real(val(1,k), real64)
        zz%bq(k) = real(val(2,k), real64) / 3.6e6_real64
      end do
    end associate
    deallocate(val)
    zr%have_base = .true.
  end do
end subroutine


!----------------------------------------------------------------------
! 同期区間の作業配列を確保する(rainmode・idt・ngrp が確定してから)
!----------------------------------------------------------------------
subroutine zr_alloc_interval(zr)
  type(t_zonerunoff), intent(inout) :: zr
  allocate(zr%rstep(1:zr%idt, 1:zr%ngrp), source = 0.0_real64)
  allocate(zr%nseg(1:zr%ngrp), source = 0)
  allocate(zr%segl(1:zr%idt, 1:zr%ngrp), zr%segr(1:zr%idt, 1:zr%ngrp), source = 0.0_real64)
  if (zr%rainmode == 0) then
    allocate(zr%rmx(1:zr%idt, 1:zr%ngrp), zr%rmn(1:zr%idt, 1:zr%ngrp), source = 0.0)
  else
    allocate(zr%chg(1:zr%idt), source = 0)
    allocate(zr%rsnow(dcp%js:dcp%je, 1:zr%ngrp), zr%rsprev(dcp%js:dcp%je, 1:zr%ngrp), &
             source = 0.0_real64)
    allocate(zr%snapk(1:2), source = 0)
    allocate(zr%snap(dcp%js:dcp%je, 1:zr%ngrp, 1:2), source = 0.0_real64)
  end if
  allocate(zr%rlast(1:zr%ngrp), source = 0.0_real64)
end subroutine


!----------------------------------------------------------------------
! 毎ステップ: 区画セルに入った雨を s%h から回収し、入力群の入力として記録する
!   回収量は boundary_h の加算と同じ式 pre·dt/gv(区画セルは河道セルでない
!   ので wfrac は掛からない)。上流から流れ込んだ水は回収しない。
!   h を 0 で切らない(浅水流の連続式は前ステップの水深で流出を決め、
!   run-on のある区画セルでは雨を加える前の水深が微小な負になりうる。
!   0 で切ると回収した雨 pre·dt より取り除いた水が少なく、水を作る)
!   acc: モデルの未同期の雨の台帳(セル面積基底 pre·dt の積算 m。同期で 0 に戻す)
!----------------------------------------------------------------------
subroutine zr_recover_rain(zr, p, g, s, acc)
  type(t_zonerunoff), intent(inout) :: zr
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(inout) :: acc(dcp%ish:, dcp%jsh:)
  integer :: i, j, z, c, k
  real :: pr, dh
  real :: lmx(1:zr%ngrp), lmn(1:zr%ngrp)
  logical :: changed

  zr%kstep = zr%kstep + 1
  k = zr%kstep
  lmx(:) = -huge(1.0)
  lmn(:) = -huge(1.0)
  if (zr%rainmode == 1) zr%rsnow(:,:) = 0.0_real64
  !$omp parallel do schedule(static) private(i, j, z, c, pr, dh) reduction(max: lmx, lmn)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      z = zr%zid(i,j)
      if (z == 0) cycle
      c = zr%zones(z)%grp
      pr = s%pre(i,j)
      dh = s%pre(i,j) * p%dt / s%gv(i,j)
      s%h(i,j) = s%h(i,j) - dh
      s%e(i,j) = s%z(i,j) + s%h(i,j)
      acc(i,j) = acc(i,j) + pr * p%dt
      lmx(c) = max(lmx(c), pr)
      lmn(c) = max(lmn(c), -pr)
      if (zr%rainmode == 1) zr%rsnow(j,c) = zr%rsnow(j,c) + real(pr, real64)
    end do
  end do
  !$omp end parallel do

  if (zr%rainmode == 0) then
    zr%rmx(k,:) = lmx(:)
    zr%rmn(k,:) = lmn(:)
  else
    ! 局所の入力が直前のスナップショットから変わったステップを記録する
    changed = (k == 1)
    if (.not. changed) changed = any(zr%rsnow /= zr%rsprev)
    if (changed) then
      zr%chg(k) = 1
      zr%rsprev(:,:) = zr%rsnow(:,:)
      call push_snapshot(zr, k)
    else
      zr%chg(k) = 0
    end if
  end if
end subroutine


!----------------------------------------------------------------------
! 面積平均モードの行部分和のスナップショットを積む(容量は倍々に伸ばす)
!----------------------------------------------------------------------
subroutine push_snapshot(zr, k)
  type(t_zonerunoff), intent(inout) :: zr
  integer, intent(in) :: k
  real(real64), allocatable :: tmp(:,:,:)
  integer, allocatable :: tk(:)
  integer :: ncap
  ncap = size(zr%snapk)
  if (zr%nsnap == ncap) then
    allocate(tmp(dcp%js:dcp%je, 1:zr%ngrp, 1:2*ncap), source = 0.0_real64)
    allocate(tk(1:2*ncap), source = 0)
    tmp(:, :, 1:ncap) = zr%snap(:, :, 1:ncap)
    tk(1:ncap) = zr%snapk(1:ncap)
    call move_alloc(tmp, zr%snap)
    call move_alloc(tk, zr%snapk)
  end if
  zr%nsnap = zr%nsnap + 1
  zr%snapk(zr%nsnap) = k
  zr%snap(:, :, zr%nsnap) = zr%rsnow(:, :)
end subroutine


!----------------------------------------------------------------------
! 同期の前半: 区間の各ステップの上端流束を入力群ごとに確定し(collective)、
! 区分一定の区間(nseg・segl・segr)に圧縮する。kstep > 0 で呼ぶこと
!----------------------------------------------------------------------
subroutine zr_collect_input(zr, p)
  type(t_zonerunoff), intent(inout) :: zr
  type(t_sysparam), intent(in) :: p
  integer :: nk, c, k, isn, kk
  real, allocatable :: buf(:)
  integer, allocatable :: gchg(:)
  real(real64) :: tot, h
  real(real64), allocatable :: rows(:)
  character(len=512) :: msg

  nk = zr%kstep
  if (zr%rainmode == 0) then
    ! 局所の max と −min を全ランクの max に揃え、群内の一致を検査する
    allocate(buf(1:2*nk*zr%ngrp))
    buf(1:nk*zr%ngrp) = reshape(zr%rmx(1:nk, :), [nk*zr%ngrp])
    buf(nk*zr%ngrp+1:) = reshape(zr%rmn(1:nk, :), [nk*zr%ngrp])
    call par_allreduce_max(buf)
    zr%rmx(1:nk, :) = reshape(buf(1:nk*zr%ngrp), [nk, zr%ngrp])
    zr%rmn(1:nk, :) = reshape(buf(nk*zr%ngrp+1:), [nk, zr%ngrp])
    do c = 1, zr%ngrp
      do k = 1, nk
        if (zr%rmx(k,c) /= -zr%rmn(k,c)) then
          write(msg, '(a,a,i0,a,es12.4,a,es12.4,a)') trim(zr%tag)//": ground rainfall differs within ", &
                trim(zr%grpword)//" ", c, " (min ", -zr%rmn(k,c), ", max ", zr%rmx(k,c), " m/s); set f_" &
                // trim(zr%tag)//"_rain=1 (area average) or split the zone so that each "//trim(zr%grpword) &
                // " receives identical rainfall"
          call par_stop(trim(msg))
        end if
        zr%rstep(k,c) = real(zr%rmx(k,c), real64)
      end do
    end do
    deallocate(buf)
  else
    ! 全ランクの変化点を揃え、変化したステップだけ行部分和を決定的に総和する
    allocate(gchg(1:nk))
    gchg(:) = zr%chg(1:nk)
    call par_allreduce_sumi(gchg)
    allocate(rows(dcp%js:dcp%je))
    do k = 1, nk
      if (k > 1 .and. gchg(k) == 0) then
        zr%rstep(k,:) = zr%rstep(k-1,:)
        cycle
      end if
      isn = 0
      do kk = 1, zr%nsnap
        if (zr%snapk(kk) <= k) isn = kk     ! 局所で k 以前の最新のスナップショット
      end do
      do c = 1, zr%ngrp
        rows(:) = zr%snap(:, c, isn)
        call par_sum_rows(rows, tot)
        zr%rstep(k,c) = tot / real(zr%grpncell(c), real64)
      end do
    end do
    deallocate(rows, gchg)
  end if

  ! --- 区分一定の区間に圧縮する ---
  h = real(p%dt, real64)
  do c = 1, zr%ngrp
    zr%nseg(c) = 0
    do k = 1, nk
      if (zr%nseg(c) > 0) then
        if (zr%segr(zr%nseg(c), c) == zr%rstep(k,c)) then
          zr%segl(zr%nseg(c), c) = zr%segl(zr%nseg(c), c) + h
          cycle
        end if
      end if
      zr%nseg(c) = zr%nseg(c) + 1
      zr%segl(zr%nseg(c), c) = h
      zr%segr(zr%nseg(c), c) = zr%rstep(k,c)
    end do
    zr%rlast(c) = zr%rstep(nk,c)
  end do
end subroutine


!----------------------------------------------------------------------
! 同期の後半: 区画の流出 dv(z)(m3。モデルが計算した 0 以上の量)に基底流を
! 加えて出口へ渡し、区間を閉じる(acc を 0 に戻す。collective ではないが
! 全ランクが同じ順で呼ぶ)。基底流は区間 [ta, tb] の積分(区間端は s%t と同じ
! t0 + dt·it の式で、隣の区間と継ぎ目が一致する)
!----------------------------------------------------------------------
subroutine zr_deliver(zr, p, s, dv, acc)
  type(t_zonerunoff), intent(inout) :: zr
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  real(real64), intent(in) :: dv(:)
  real, intent(inout) :: acc(dcp%ish:, dcp%jsh:)
  integer :: z, k, q, j, nk
  real(real64) :: dvb, ta, tb

  nk = zr%kstep
  tb = real(p%t0, real64) + real(p%dt, real64) * real(s%it, real64)
  ta = real(p%t0, real64) + real(p%dt, real64) * real(s%it - nk, real64)
  zr%ovol(:) = 0.0_real64
  do z = 1, zr%nzone
    associate (zz => zr%zones(z))
      dvb = 0.0_real64
      if (zz%nbase > 0) then
        dvb = zz%area * base_integral(zz, ta, tb)
        zz%vbase = zz%vbase + dvb
      end if
      if (zz%kind == 2) then
        zz%vext = zz%vext + (dv(z) + dvb)
      else
        zz%vint = zz%vint + (dv(z) + dvb)
        do k = 1, zz%nout
          zr%ovol(zz%oidx(k)) = zr%ovol(zz%oidx(k)) + zz%ow(k) * (dv(z) + dvb)
        end do
      end if
    end associate
  end do

  ! --- 出口セルへの移送(所有ランクのみ。同じセルへの複数区画の量は合計済み) ---
  do q = 1, zr%nocell
    zr%ovcum(q) = zr%ovcum(q) + zr%ovol(q)
    j = zr%ocell(2,q)
    if (j < dcp%js .or. j > dcp%je) cycle
    call add_to_surface(zr, s, q)
  end do

  ! --- 区間のリセット ---
  acc(:,:) = 0.0
  zr%kstep = 0
  zr%nsnap = 0
end subroutine


!----------------------------------------------------------------------
! 基底流の区分線形の時系列(範囲外は端の値を保持)の [ta, tb] の積分 (m)
!----------------------------------------------------------------------
pure real(real64) function base_integral(zz, ta, tb) result(v)
  type(t_zrzone), intent(in) :: zz
  real(real64), intent(in) :: ta, tb
  integer :: k, n
  real(real64) :: a, b, fa, fb
  n = zz%nbase
  v = 0.0_real64
  if (ta < zz%bt(1)) v = v + (min(tb, zz%bt(1)) - ta) * zz%bq(1)
  do k = 1, n - 1
    a = max(ta, zz%bt(k))
    b = min(tb, zz%bt(k+1))
    if (b <= a) cycle                  ! 区間外(同じ時刻の 2 点の段差も含む)
    fa = zz%bq(k) + (zz%bq(k+1) - zz%bq(k)) * (a - zz%bt(k)) / (zz%bt(k+1) - zz%bt(k))
    fb = zz%bq(k) + (zz%bq(k+1) - zz%bq(k)) * (b - zz%bt(k)) / (zz%bt(k+1) - zz%bt(k))
    v = v + (b - a) * 0.5_real64 * (fa + fb)
  end do
  if (tb > zz%bt(n)) v = v + (tb - max(ta, zz%bt(n))) * zz%bq(n)
end function


!----------------------------------------------------------------------
! 出口セル q へ体積を加える(雨・境界ソースと同じ換算 V/(dx·dy)/gv/wfrac)。
! 実際に加わった体積との差は繰越(単精度ビルドで微小な量が丸めで消えない)
!----------------------------------------------------------------------
subroutine add_to_surface(zr, s, q)
  type(t_zonerunoff), intent(inout) :: zr
  type(t_state), intent(inout) :: s
  integer, intent(in) :: q
  integer :: i, j
  real :: hold, wf
  real(real64) :: vreq, fac
  i = zr%ocell(1,q)
  j = zr%ocell(2,q)
  wf = 1.0
  if (chn%have_width) wf = chn%wfrac(i,j)
  vreq = zr%ovol(q) + zr%ocarry(q)
  fac = zr%dxdy * real(s%gv(i,j), real64) * real(wf, real64)
  if (sect_cell(s, i, j)) then
    ! 断面形 σ のセルは体積(矩形換算水深)で足し、繰越も体積の差で数える(§26.2)
    hold = sect_vh(s, i, j, s%h(i,j))
    call sect_add_vh(s, i, j, real(vreq / fac))
    s%e(i,j) = s%z(i,j) + s%h(i,j)
    zr%ocarry(q) = vreq - real(sect_vh(s, i, j, s%h(i,j)) - hold, real64) * fac
    return
  end if
  hold = s%h(i,j)
  s%h(i,j) = s%h(i,j) + real(vreq / fac)
  s%e(i,j) = s%z(i,j) + s%h(i,j)
  zr%ocarry(q) = vreq - real(s%h(i,j) - hold, real64) * fac
end subroutine


!----------------------------------------------------------------------
! 出口の繰越を全ランク同値に集める(collective。保存の前に全ランクで呼ぶ)。
!   繰越は所有ランクだけが持つので、その行だけが非 0 の行部分和を par_sum_rows で
!   集める(寄与が 1 つなので総和は厳密。real64 のまま集めるので単精度ビルドでも
!   繰越が丸められない)
!----------------------------------------------------------------------
subroutine zr_gather_carry(zr, carry)
  type(t_zonerunoff), intent(in) :: zr
  real(real64), allocatable, intent(out) :: carry(:)
  real(real64), allocatable :: rowv(:)
  integer :: q, j
  allocate(carry(1:max(zr%nocell,1)), source = 0.0_real64)
  allocate(rowv(dcp%js:dcp%je))
  do q = 1, zr%nocell
    rowv(:) = 0.0_real64
    j = zr%ocell(2,q)
    if (j >= dcp%js .and. j <= dcp%je) rowv(j) = zr%ocarry(q)
    call par_sum_rows(rowv, carry(q))
  end do
end subroutine


!----------------------------------------------------------------------
! 区画確認表の出口と基底流の行(初期化時に画面へ。Log.txt には書かない)
!----------------------------------------------------------------------
subroutine zr_report_outlets(zr, z)
  type(t_zonerunoff), intent(in) :: zr
  integer, intent(in) :: z
  integer :: k
  character(len=512) :: line
  associate (zz => zr%zones(z))
    if (zz%kind == 2) then
      call par_info("    outlet: outflow from the system")
    else
      do k = 1, zz%nout
        write(line, '(a,i0,a,i0,a,f8.5)') "    outlet cell (", zr%ocell(1,zz%oidx(k)), ",", &
              zr%ocell(2,zz%oidx(k)), ") weight ", zz%ow(k)
        call par_info(trim(line))
      end do
    end if
    if (zz%nbase > 0) then
      write(line, '(a,i0,a,2(f0.1,a,g0.6,a))') "    baseflow: ", zz%nbase, " point(s), from (", &
            zz%bt(1) / 60.0_real64, " min, ", zz%bq(1) * 3.6e6_real64, " mm/h) to (", &
            zz%bt(zz%nbase) / 60.0_real64, " min, ", zz%bq(zz%nbase) * 3.6e6_real64, &
            " mm/h), added at the outlet"
      call par_info(trim(line))
    end if
  end associate
end subroutine


!----------------------------------------------------------------------
! 2 つのモデルの区画が重ならないこと、出口が相手の区画セルにないことを検査する
! (VZ と貯留関数の併用。collective: 全ランクが呼び、同じ判定で停止する)。
! 帯の区画番号と、所有ランクでの出口セルの判定を最大値で集める
!----------------------------------------------------------------------
subroutine zr_check_disjoint(za, zb, g)
  type(t_zonerunoff), intent(in) :: za, zb
  type(t_geoinfo), intent(in) :: g
  integer :: i, j, q, iover, ioutab, ioutba
  ! 位置は「全域の通し番号 + 1」の最大で集める(0 = なし)。同じ判定を全ランクで
  iover = 0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (za%zid(i,j) > 0 .and. zb%zid(i,j) > 0) iover = max(iover, cellno(i, j))
    end do
  end do
  ioutab = 0
  do q = 1, za%nocell
    i = za%ocell(1,q)
    j = za%ocell(2,q)
    if (j < dcp%js .or. j > dcp%je) cycle
    if (zb%zid(i,j) > 0) ioutab = max(ioutab, cellno(i, j))
  end do
  ioutba = 0
  do q = 1, zb%nocell
    i = zb%ocell(1,q)
    j = zb%ocell(2,q)
    if (j < dcp%js .or. j > dcp%je) cycle
    if (za%zid(i,j) > 0) ioutba = max(ioutba, cellno(i, j))
  end do
  call par_allreduce_maxi(iover)
  call par_allreduce_maxi(ioutab)
  call par_allreduce_maxi(ioutba)
  if (iover > 0) call stop_no(trim(za%tag)//" and "//trim(zb%tag)//": a cell belongs to both a " &
                              //trim(za%label)//" zone and a "//trim(zb%label)//" zone", iover)
  if (ioutab > 0) call stop_no(trim(za%nml)//": an outlet cell is a "//trim(zb%label)//" cell", ioutab)
  if (ioutba > 0) call stop_no(trim(zb%nml)//": an outlet cell is a "//trim(za%label)//" cell", ioutba)
contains
  integer function cellno(i, j)
    integer, intent(in) :: i, j
    cellno = (j - 1) * g%nx + i
  end function
  subroutine stop_no(msg, n)
    character(len=*), intent(in) :: msg
    integer, intent(in) :: n
    call zr_stop_at(msg, mod(n - 1, g%nx) + 1, (n - 1) / g%nx + 1)
  end subroutine
end subroutine


!----------------------------------------------------------------------
! 破棄(区画の一覧だけ。ほかの配列は容器の intent(out) で解放される)
!----------------------------------------------------------------------
subroutine zr_dispose(zr)
  type(t_zonerunoff), intent(inout) :: zr
  if (allocated(zr%zones)) deallocate(zr%zones)
end subroutine


!----------------------------------------------------------------------
! セル位置つきの停止(全ランクが同じ全域データで同じ判定をする場所でのみ使う)
!----------------------------------------------------------------------
subroutine zr_stop_at(msg, i, j)
  character(len=*), intent(in) :: msg
  integer, intent(in) :: i, j
  call par_stop(msg//" at ("//itoa(i)//","//itoa(j)//")")
end subroutine

end module
