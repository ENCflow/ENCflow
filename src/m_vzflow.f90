module m_vzflow
  ! ============ 鉛直不飽和浸透(VZ)流出モデル(fn_vz。§87) ============
  ! 谷(2023)の VZ 流出モデル(十分深い参照土壌柱の鉛直不飽和浸透を解き、
  ! 各地点の土層厚の深さの下向き流束を読み出して面積で積分する)を、
  ! **共有参照柱**・**VZ 区画**・**明示的な出口**として格子に載せる管理側
  ! (設計の正本 docs/vz_plan.md、決定の記録 developer.md §87)。
  !
  ! 【構成】
  !   柱 c   : m_vzflow_column の 1 次元 Richards 計算核(単位面積当たりの解)。
  !   区画 g : 区画番号ラスタ(fn_vz_zone。0 = 適用外)で同じ番号を持つセル群。
  !            1 つの柱を参照する(複数区画が同じ柱を共有してよい)。
  !   出口   : 区画の排水を地表セルへ移す(vz_out_kind = 1。配分率つき)か
  !            系外へ出す(= 2)。側方の遅れは解かない(瞬間的な直接排水。
  !            側方系の応答を省略した近似 — 水粒子の瞬間移動の主張ではない)。
  !
  ! 【保存的な読み出し】(vz_plan.md §4.4)
  !   セル i の土層厚 d_i が界面 ζ_j と ζ_{j+1} の間にあれば α = (d − ζ_j)/Δζ。
  !   排水 D_i = (1−α)F_j + αF_{j+1}、貯留 S_i = (1−α)B_j + αB_{j+1}
  !   (B_j = Σ_{k≤j} θ_k Δζ_k)を同じ係数で読むので ΔS_i = F_0 − D_i
  !   (+ 非線形残差)が構造的に成立する。区画では初期化時に界面重み
  !   W_{g,j} = Σ A_i b_{i,j}(m²)と層重み M_{g,k}(m³)を作り、時間ループは
  !   ΔV_g = Σ_j W F、V_g = Σ_k M θ の O(柱の層数) で集約する(セル走査なし)。
  !   共有柱の d_i より深い部分の水は数えない(数値的な参照領域)。
  !
  ! 【雨の受け渡し】(§87 の合意: swflow の後に s%h から回収)
  !   VZ セルにも浅水流ソルバーが通常どおり雨を入れる(boundary_h の
  !   h1 += pre·dt/gv)。本モジュールは swflow の直後に同じ式の量を s%h から
  !   回収して柱の上端流束にする(浅水流ソルバーと s%pre は無改修。s%pre を
  !   読む土壌雨量指数も影響を受けない)。回収後の h は「その雨がなかった
  !   場合」の値になる(乾いた VZ セルでは 0 に戻る)。上流から流れ込んだ水
  !   (run-on)は回収しない = 地表流のまま(一方向の近似。VZ セルへの
  !   再浸透は解かない)。回収で h を 0 で切らない: 連続式が残した微小な負の
  !   水深を 0 にすると、台帳に数えた雨より取り除いた水が少なくなる。
  !   柱の上端流束: f_vz_rain = 0 は柱内のセルで雨量が一致することを検査して
  !   その値、= 1 は柱内の面積平均(「平均入力への置換」という独自の近似)。
  !
  ! 【同期】dt_vz(idt ステップ)ごとに、区間の各ステップの上端流束を区分一定で
  !   与えて全柱を進め、区画へ集約し、出口へ渡す。区間の排水は区間末に
  !   まとめて渡す(dt_gwflow の間引きと同じ意味論。未来の雨は使わない)。
  !   回収済み未同期の雨は s%vzp(セル)として台帳に数える。
  !
  ! 【並列】全ランクが全柱を同じ入力で冗長に解く(§11「冗長計算=配布機構」。
  !   柱の解は全ランクでビット同一)。通信は同期ごとに柱の入力を揃える 1 回
  !   (厳密一致: max の allreduce / 平均: 行部分和の par_sum_rows)だけ。
  !   出口セルへの加算は所有ランクだけ(区画総量を再総和しない)。
  !
  ! 【所有と台帳】VZ 貯留は hg と別物(hg に代入しない)。calcstat が
  !   s%vzstore(区画の V_g の総和)と s%vzp を S_grnd に算入する。
  !   保存・復元は私有ファイル vzflow.dat(契約5。柱の ψ・試行刻み・累積
  !   診断・出口の繰越)。区間の途中で保存する場合は dispose で残りを
  !   同期してから保存する(連続計算と一致するのは同期時刻で保存したとき)。
  !
  ! 【初版の併用制限】fn_gwflow・fn_snow・fn_glacier・fn_geomorph・fn_wq・
  !   fn_salt・ネスト・STG は init で停止(vz_plan.md §4.10)。VZ セルは河道・
  !   海・境界・ソース・構造物のセルに置けず、出口は VZ セル・海セル・
  !   水位規定セルに置けない。
  ! ====================================================================
  use, intrinsic :: iso_fortran_env, only : real64, int64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo, m_geoinfo_require_sd
  use m_state, only : t_state
  use m_boundary, only : t_boundary
  use m_swflow_enc, only : chn
  use list_vz, only : t_list_vz, list_vz_read, vz_ncolmax, vz_nzonemax, vz_noutmax, vz_ndepmax
  use m_vzflow_column, only : t_vzcol, t_vzctl, t_vzgeo, vzcol_init, vzcol_advance, vzcol_props, &
                              vzcol_dispose, vzcol_steady_psi, vz_ok, vz_fail_time, vz_fail_ponding
  use m_fileio, only : fileio_read_matrix
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : param_default, itoa
  use m_parallel, only : par_info, par_stop, dcp, is_root, par_gather_to, par_bcast_cell, &
                         par_bcast_cell_i, par_allreduce_max, par_allreduce_sumi, par_sum_rows
  implicit none
  private
  public :: t_vzflow
  public :: m_vzflow_init
  public :: m_vzflow_calc
  public :: m_vzflow_record
  public :: m_vzflow_outprof
  public :: m_vzflow_dispose

  integer, parameter :: save_version = 20261026   ! vzflow.dat の形式の版(形式変更日。§7)

  !-------------------------------------------
  ! VZ 区画
  !-------------------------------------------
  type t_vzzone
    integer :: col = 0                         ! 参照する柱
    integer :: ncell = 0                       ! セル数(全域)
    real(real64) :: area = 0.0_real64          ! 面積 A_g (m2)
    real(real64), allocatable :: w(:)          ! 界面重み W_{g,j} (0:nz。m2)
    real(real64), allocatable :: m(:)          ! 層重み M_{g,k} (1:nz。m3)
    real(real64) :: sdmin = 0.0_real64, sdmax = 0.0_real64, sdmean = 0.0_real64  ! 土層厚の統計 (m)
    integer :: kind = 0                        ! 出口 1: 地表セル / 2: 系外
    integer :: nout = 0                        ! 出口セル数(kind = 1)
    integer, allocatable :: oidx(:)            ! 出口セルの通し番号(t_vzflow の ocell の添字)
    real(real64), allocatable :: ow(:)         ! 配分率(和 = 1 に正規化済み)
    ! 診断(累積 m3。全ランク同値)
    real(real64) :: vin = 0.0_real64           ! 上端入力 A_g·F_0
    real(real64) :: vdrain = 0.0_real64        ! 底面排水 Σ W F
    real(real64) :: vint = 0.0_real64          ! 地表セルへの移送
    real(real64) :: vext = 0.0_real64          ! 系外流出
    real(real64) :: vcorr = 0.0_real64         ! 負の排水(丸め規模)を 0 に切った補正量
    real(real64) :: vstore0 = 0.0_real64       ! 計算開始時の貯留 (m3)
    real(real64) :: vstore = 0.0_real64        ! 現在の貯留 Σ M θ (m3)
    real(real64) :: dvlast = 0.0_real64        ! 直近の同期区間の排水 (m3)
  end type

  !-------------------------------------------
  ! VZ 流出モデルの状態の容器(t_encflow の成分。init に早期 return 経路が
  ! あるため全成分デフォルト初期化。§13)
  !-------------------------------------------
  type t_vzflow
    logical :: enabled = .false.
    integer :: ncol = 0, nzone = 0
    type(t_vzctl) :: ctl                       ! 数値制御(全柱共通)
    type(t_vzcol), allocatable :: cols(:)      ! 共有参照柱
    type(t_vzzone), allocatable :: zones(:)    ! VZ 区画
    integer, allocatable :: zid(:,:)           ! 区画番号(帯 ish:ieh, jsh:jeh。0 = 適用外)
    integer, allocatable :: colncell(:)        ! 柱を参照するセル数(全域)
    integer :: rainmode = 0                    ! 0: 柱内で一致を要求 / 1: 柱内面積平均
    integer :: idt = 1                         ! 同期間隔(ステップ数)
    real(real64) :: dxdy = 0.0_real64          ! セル面積 (m2)
    integer :: kstep = 0                       ! 現在の同期区間に積算済みのステップ数
    ! 厳密一致モードの区間内履歴(ステップ × 柱。局所の max と −min。PREC = s%pre と同じ)
    real, allocatable :: rmx(:,:), rmn(:,:)
    ! 面積平均モード: 局所の行部分和の変化点スナップショット
    integer, allocatable :: chg(:)             ! (1:idt) 局所で入力が変わったステップ
    real(real64), allocatable :: rsnow(:,:)    ! (js:je, 1:ncol) このステップの行部分和
    real(real64), allocatable :: rsprev(:,:)   ! 直前のスナップショット
    integer :: nsnap = 0
    integer, allocatable :: snapk(:)           ! スナップショットのステップ
    real(real64), allocatable :: snap(:,:,:)   ! (js:je, 1:ncol, 1:nsnap)
    ! 区間の区分一定入力(柱ごと)
    real(real64), allocatable :: rstep(:,:)    ! (1:idt, 1:ncol) 各ステップの上端流束 (m/s)
    integer, allocatable :: nseg(:)
    real(real64), allocatable :: segl(:,:), segr(:,:)   ! (1:idt, 1:ncol)
    ! 柱の積算流束(直近の同期区間・累積)
    integer :: nzmax = 0
    real(real64), allocatable :: fsum(:,:)     ! (0:nzmax, 1:ncol) 直近の同期区間 (m)
    real(real64), allocatable :: fcum(:,:)     ! (0:nzmax, 1:ncol) 計算開始からの累積 (m)
    real(real64), allocatable :: rlast(:)      ! 直近ステップの上端流束 (m/s)
    integer, allocatable :: stat(:)            ! 前進の結果(柱ごと)
    ! 出口セル(全区画で重複を除いた一覧)
    integer :: nocell = 0
    integer, allocatable :: ocell(:,:)         ! (1:2, 1:nocell)
    real(real64), allocatable :: ovol(:)       ! 同期区間の移送量 (m3。作業)
    real(real64), allocatable :: ocarry(:)     ! 繰越(要求と実際に加わった体積の差 m3。所有ランクのみ意味を持つ)
    real(real64), allocatable :: ovcum(:)      ! 累積の移送量 (m3。全ランク同値)
    ! 診断出力
    integer :: ndep = 0
    real(real64) :: odep(1:vz_ndepmax) = 0.0_real64
    logical :: outprof = .false.
    integer :: un_zone = 0, un_col = 0         ! CSV 装置番号(rank0)
    logical :: initialized = .false.
  end type

contains


!----------------------------------------------------------------------
! 初期化(fn_vz 未指定・f_vz = 0 なら何もしない)
!   multi: 複数インスタンス(ネスト等)で実行中か(初版は非対応)
!----------------------------------------------------------------------
subroutine m_vzflow_init(vz, p, g, b, s, multi)
  type(t_vzflow), intent(out) :: vz
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g      ! 土層厚の遅延確保口(require_sd)のため inout
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s
  logical, intent(in) :: multi
  type(t_list_vz) :: list
  integer :: c, z

  if (len_trim(p%fn_vz) == 0) then
    if (p%f_state_restore > 0) call stop_if_orphan(p)
    return
  end if
  call list_vz_read(p, list)
  select case (list%f_vz)
    case (0)
      call par_info("list_vz: f_vz=0, VZ runoff is not enabled")
      if (p%f_state_restore > 0) call stop_if_orphan(p)
      return
    case (1)
    case default
      call par_stop("list_vz: f_vz must be 0 or 1: " // itoa(list%f_vz))
  end select

  call check_combinations(p, multi)
  call setup_control(vz, p, list)
  call setup_columns(vz, list)
  call setup_zones(vz, p, g, b, list)

  allocate(s%vzp(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  s%vz_active = .true.

  ! 区間の作業配列
  allocate(vz%rstep(1:vz%idt, 1:vz%ncol), source = 0.0_real64)
  allocate(vz%nseg(1:vz%ncol), source = 0)
  allocate(vz%segl(1:vz%idt, 1:vz%ncol), vz%segr(1:vz%idt, 1:vz%ncol), source = 0.0_real64)
  if (vz%rainmode == 0) then
    allocate(vz%rmx(1:vz%idt, 1:vz%ncol), vz%rmn(1:vz%idt, 1:vz%ncol), source = 0.0)
  else
    allocate(vz%chg(1:vz%idt), source = 0)
    allocate(vz%rsnow(dcp%js:dcp%je, 1:vz%ncol), vz%rsprev(dcp%js:dcp%je, 1:vz%ncol), &
             source = 0.0_real64)
    allocate(vz%snapk(1:2), source = 0)
    allocate(vz%snap(dcp%js:dcp%je, 1:vz%ncol, 1:2), source = 0.0_real64)
  end if
  vz%nzmax = 0
  do c = 1, vz%ncol
    vz%nzmax = max(vz%nzmax, vz%cols(c)%geo%nz)
  end do
  allocate(vz%fsum(0:vz%nzmax, 1:vz%ncol), vz%fcum(0:vz%nzmax, 1:vz%ncol), source = 0.0_real64)
  allocate(vz%rlast(1:vz%ncol), source = 0.0_real64)
  allocate(vz%stat(1:vz%ncol), source = vz_ok)

  if (p%f_state_restore > 0) call restore_state(vz, p)

  ! 貯留の初期値(restore 時は復元した柱の状態から)
  do z = 1, vz%nzone
    vz%zones(z)%vstore = zone_storage(vz, z)
    if (p%f_state_restore <= 0) vz%zones(z)%vstore0 = vz%zones(z)%vstore
  end do
  s%vzstore = total_storage(vz)

  call report_zones(vz)
  call open_csv(vz, p)
  vz%enabled = .true.
  vz%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 毎ステップ(swflow の直後): 雨の回収と、同期時刻なら柱の前進・集約・出口
!   判定(vz%enabled・mod(it, idt))は全ランク同一(collective 安全)
!----------------------------------------------------------------------
subroutine m_vzflow_calc(vz, p, g, s, it)
  type(t_vzflow), intent(inout) :: vz
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it

  if (.not. vz%enabled) return
  call recover_rain(vz, p, g, s)
  if (mod(it, vz%idt) == 0) call sync_interval(vz, p, s)
end subroutine


!----------------------------------------------------------------------
! 区画・柱の時系列 CSV(dt_record 間隔。値は全ランク同値で rank0 が書く)
!   vz_zone.csv  : 区画の累積水量(m3)と収支残差
!   vz_column.csv: 柱の上端入力・積算流束・指定深さの累積排水と貯留(m)・
!                  内部刻みの診断
!----------------------------------------------------------------------
subroutine m_vzflow_record(vz, s)
  type(t_vzflow), intent(in) :: vz
  type(t_state), intent(in) :: s
  integer :: z, c, k, jf
  real(real64) :: res, alpha, dcum, sto
  real(real64), allocatable :: bsum(:)

  if (.not. vz%enabled) return
  if (.not. is_root) return
  do z = 1, vz%nzone
    associate (zz => vz%zones(z))
      ! 区画の収支残差 = 貯留変化 − (入力 − 排水) − 補正(非線形残差の集積と丸め)
      res = zz%vstore - zz%vstore0 - zz%vin + zz%vdrain - zz%vcorr
      write(vz%un_zone, '(f0.2,",",i0,",",i0,8(",",es23.15))') s%t, z, zz%col, zz%area, &
            zz%vin, zz%vstore, zz%vdrain, zz%vint, zz%vext, zz%vcorr, res
    end associate
  end do
  flush(vz%un_zone)
  do c = 1, vz%ncol
    associate (col => vz%cols(c), geo => vz%cols(c)%geo)
      allocate(bsum(0:geo%nz))
      bsum(0) = 0.0_real64
      do k = 1, geo%nz
        bsum(k) = bsum(k-1) + col%th(k) * geo%dzl(k)
      end do
      write(vz%un_col, '(f0.2,",",i0,3(",",es23.15))', advance='no') s%t, c, vz%rlast(c), &
            vz%fcum(0, c), vz%fcum(geo%nz, c)
      do k = 1, vz%ndep
        call depth_index(geo, vz%odep(k), jf, alpha)
        if (jf < geo%nz) then
          dcum = (1.0_real64 - alpha) * vz%fcum(jf, c) + alpha * vz%fcum(jf+1, c)
          sto = (1.0_real64 - alpha) * bsum(jf) + alpha * bsum(jf+1)
        else
          dcum = vz%fcum(geo%nz, c)
          sto = bsum(geo%nz)
        end if
        write(vz%un_col, '(2(",",es23.15))', advance='no') dcum, sto
      end do
      write(vz%un_col, '(3(",",i0),",",es12.4)') col%nacc, col%nrej, col%nit, col%dtlast
      deallocate(bsum)
    end associate
  end do
  flush(vz%un_col)
end subroutine


!----------------------------------------------------------------------
! 柱の鉛直分布の CSV(f_vz_outprof = 1 のとき、分布出力の時刻に。rank0)
!   vzprof_<柱>_<出力番号>.csv: 層中心の深さ・ψ・θ・K と、層の下面の深さ・
!   計算開始からの累積流束(上面 = 深さ 0 の累積は vz_column.csv の F0)
!----------------------------------------------------------------------
subroutine m_vzflow_outprof(vz, p, ifn)
  type(t_vzflow), intent(in) :: vz
  type(t_sysparam), intent(in) :: p
  integer, intent(in) :: ifn
  integer :: c, k, un
  real(real64) :: th, cap, kk
  character(len=32) :: fn

  if (.not. vz%enabled) return
  if (.not. vz%outprof) return
  if (.not. is_root) return
  do c = 1, vz%ncol
    write(fn, '("vzprof_",i0,"_",i4.4,".csv")') c, ifn
    open(newunit=un, file=trim(p%dir_result)//"/"//trim(fn), status='replace')
    write(un, '(a)') "z(m),psi(m),theta,K(m/s),zbottom(m),Fbottom(m)"
    do k = 1, vz%cols(c)%geo%nz
      call vzcol_props(vz%cols(c)%geo, vz%cols(c)%psi(k), th, cap, kk)
      write(un, '(es23.15,5(",",es23.15))') vz%cols(c)%geo%zc(k), vz%cols(c)%psi(k), th, kk, &
            vz%cols(c)%geo%zf(k), vz%fcum(k, c)
    end do
    close(un)
  end do
end subroutine


!----------------------------------------------------------------------
! 破棄(save は dispose で。契約5)。区間の途中で保存する場合は残りを
! 同期してから保存する(回収済みの雨を捨てない。s%h への移送は m_state の
! save より先なので保存状態に入る)
!----------------------------------------------------------------------
subroutine m_vzflow_dispose(vz, p, s)
  type(t_vzflow), intent(inout) :: vz
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  integer :: c
  if (.not. vz%enabled) return
  if (p%f_state_save > 0) then
    if (vz%kstep > 0) then
      call par_info("vz: syncing the partial interval of "//itoa(vz%kstep)//" steps before saving")
      call sync_interval(vz, p, s)
    end if
    call save_state(vz, p)
  end if
  if (is_root .and. vz%un_zone /= 0) close(vz%un_zone)
  if (is_root .and. vz%un_col /= 0) close(vz%un_col)
  vz%un_zone = 0
  vz%un_col = 0
  do c = 1, vz%ncol
    call vzcol_dispose(vz%cols(c))
  end do
  if (allocated(vz%cols)) deallocate(vz%cols)
  if (allocated(vz%zones)) deallocate(vz%zones)
  vz%enabled = .false.
  vz%initialized = .false.
end subroutine


!======================================================================
!========================= PRIVATE ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 初版で併用できない機能・実行形態を停止する(vz_plan.md §4.10)
!----------------------------------------------------------------------
subroutine check_combinations(p, multi)
  type(t_sysparam), intent(in) :: p
  logical, intent(in) :: multi
  call no_combo(p%fn_gwflow, "fn_gwflow", "both would own the same soil layer")
  call no_combo(p%fn_snow, "fn_snow", "snowmelt would bypass the VZ columns")
  call no_combo(p%fn_glacier, "fn_glacier", "ice melt would bypass the VZ columns")
  call no_combo(p%fn_geomorph, "fn_geomorph", "the soil depth read by the VZ zones must stay fixed")
  call no_combo(p%fn_wq, "fn_wq", "the VZ columns do not carry solutes")
  call no_combo(p%fn_salt, "fn_salt", "the VZ columns do not interact with the saltwater layers")
  call no_combo(p%fn_nest, "fn_nest", "nesting is not supported by vz yet")
  if (multi) call par_stop("list_vz: multiple instances (nesting) are not supported by vz yet")
  if (p%f_gridsystem /= 0) call par_stop("list_vz: vz requires f_gridsystem=0 (ENC)")
contains
  subroutine no_combo(fn, name, why)
    character(len=*), intent(in) :: fn, name, why
    if (len_trim(fn) > 0) call par_stop("list_vz: vz cannot be combined with "//name//" ("//why//")")
  end subroutine
end subroutine


!----------------------------------------------------------------------
! 共通設定と数値制御(既定は採用値を "(default)" 付きで表示。§62・§64)
!   数値制御の既定は計算核の試験(developer.md §87)で決めた出発値であり、
!   普遍的な検証済み値ではない
!----------------------------------------------------------------------
subroutine setup_control(vz, p, list)
  type(t_vzflow), intent(inout) :: vz
  type(t_sysparam), intent(in) :: p
  type(t_list_vz), intent(in) :: list
  real :: dtv, v
  integer :: k

  dtv = param_default("vz", "dt_vz", list%dt_vz, 60.0, " s", unset = -9999.0)
  if (dtv < 0.0) call par_stop("list_vz: dt_vz must be >= 0 (0 = every step)")
  if (dtv == 0.0) then
    vz%idt = 1
  else
    vz%idt = max(1, nint(dtv / p%dt))
  end if
  if (vz%idt > 1) call par_info("vz: columns are synchronised every "//itoa(vz%idt)//" steps")

  select case (list%f_vz_rain)
    case (0, 1)
      vz%rainmode = list%f_vz_rain
    case default
      call par_stop("list_vz: f_vz_rain must be 0(identical within a column) or 1(area average): " &
                    // itoa(list%f_vz_rain))
  end select
  select case (list%f_vz_kface)
    case (1, 2)
      vz%ctl%kface = list%f_vz_kface
    case default
      call par_stop("list_vz: f_vz_kface must be 1(arithmetic) or 2(harmonic): " // itoa(list%f_vz_kface))
  end select

  v = param_default("vz", "vz_dt_init", list%vz_dt_init, 1.0, " s", unset = -9999.0)
  vz%ctl%dt_init = real(v, real64)
  v = param_default("vz", "vz_dt_min", list%vz_dt_min, 1.0e-3, " s", unset = -9999.0)
  vz%ctl%dt_min = real(v, real64)
  v = param_default("vz", "vz_dt_max", list%vz_dt_max, 3600.0, " s", unset = -9999.0)
  vz%ctl%dt_max = real(v, real64)
  if (.not. (vz%ctl%dt_min > 0.0_real64 .and. vz%ctl%dt_min <= vz%ctl%dt_init &
             .and. vz%ctl%dt_init <= vz%ctl%dt_max)) then
    call par_stop("list_vz: require 0 < vz_dt_min <= vz_dt_init <= vz_dt_max")
  end if
  v = param_default("vz", "vz_tol_theta", list%vz_tol_theta, 1.0e-3, "", unset = -9999.0)
  vz%ctl%tol_th = real(v, real64)
  v = param_default("vz", "vz_tol_psi", list%vz_tol_psi, 1.0e-3, "", unset = -9999.0)
  vz%ctl%tol_psi_a = real(v, real64)
  vz%ctl%tol_psi_r = real(v, real64)
  v = param_default("vz", "vz_tol_q", list%vz_tol_q, 1.0e-2, "", unset = -9999.0)
  vz%ctl%tol_q_r = real(v, real64)
  v = param_default("vz", "vz_mb_rate", list%vz_mb_rate, 1.0e-11, " m/s", unset = -9999.0)
  vz%ctl%mb_rate = real(v, real64)
  if (.not. (vz%ctl%tol_th > 0.0_real64 .and. vz%ctl%tol_psi_a > 0.0_real64 .and. &
             vz%ctl%tol_q_r > 0.0_real64 .and. vz%ctl%mb_rate > 0.0_real64)) then
    call par_stop("list_vz: vz_tol_theta, vz_tol_psi, vz_tol_q and vz_mb_rate must be > 0")
  end if
  if (list%vz_maxit <= -9998) then
    vz%ctl%maxit = 25
    call par_info("vz: vz_maxit = 25 (default)")
  else
    vz%ctl%maxit = list%vz_maxit
    call par_info("vz: vz_maxit = "//itoa(vz%ctl%maxit))
  end if
  if (vz%ctl%maxit < 2) call par_stop("list_vz: vz_maxit must be >= 2")

  vz%ndep = 0
  do k = 1, vz_ndepmax
    if (list%vz_out_depth(k) <= -9998.0) exit
    if (list%vz_out_depth(k) < 0.0) call par_stop("list_vz: vz_out_depth must be >= 0")
    vz%ndep = k
    vz%odep(k) = real(list%vz_out_depth(k), real64)
  end do
  vz%outprof = (list%f_vz_outprof == 1)
end subroutine


!----------------------------------------------------------------------
! 共有参照柱(物性・格子・初期条件・下端)。小杉パラメータには既定を置かない
! (原論文の使用値と照合できるまで必須入力。vz_plan.md §8 の 7)
!----------------------------------------------------------------------
subroutine setup_columns(vz, list)
  type(t_vzflow), intent(inout) :: vz
  type(t_list_vz), intent(in) :: list
  integer :: c, nc, nz, ninit
  real :: depth, dz
  real(real64) :: ks, psi0, psibot
  logical :: ok
  character(len=8) :: tag

  nc = 0
  do c = 1, vz_ncolmax
    if (list%vz_ks_mmh(c) <= -9998.0) exit
    nc = c
  end do
  do c = nc + 1, vz_ncolmax
    if (list%vz_ks_mmh(c) > -9998.0) then
      call par_stop("list_vz_column: columns must be numbered 1, 2, ... without gaps (vz_ks_mmh(" &
                    // itoa(c) // ") is set after a gap)")
    end if
  end do
  if (nc == 0) call par_stop("list_vz_column: no column is defined (set vz_ks_mmh(1) etc.)")
  vz%ncol = nc
  allocate(vz%cols(1:nc))

  do c = 1, nc
    write(tag, '("(",i0,")")') c
    if (list%vz_ks_mmh(c) <= 0.0) call par_stop("list_vz_column: vz_ks_mmh"//trim(tag)//" must be > 0")
    if (.not. (list%vz_thetar(c) >= 0.0 .and. list%vz_thetar(c) < list%vz_thetas(c) &
               .and. list%vz_thetas(c) <= 1.0)) then
      call par_stop("list_vz_column: require 0 <= vz_thetar"//trim(tag)//" < vz_thetas"//trim(tag)//" <= 1")
    end if
    if (.not. (list%vz_psim(c) < 0.0 .and. list%vz_psim(c) > -9998.0)) then
      call par_stop("list_vz_column: vz_psim"//trim(tag)//" must be given and < 0 (m)")
    end if
    if (.not. (list%vz_sigma(c) > 0.0)) call par_stop("list_vz_column: vz_sigma"//trim(tag)//" must be > 0")
    depth = param_default("vz", "vz_depth"//trim(tag), list%vz_depth(c), 10.0, " m", unset = -9999.0)
    dz = param_default("vz", "vz_dz"//trim(tag), list%vz_dz(c), 0.025, " m", unset = -9999.0)
    if (.not. (depth > 0.0 .and. dz > 0.0)) call par_stop("list_vz_column: vz_depth and vz_dz must be > 0")
    ! 層数は入力の精度(既定 real)で判定し、層厚は depth/nz を real64 で作る
    ! (単精度ビルドでは 0.025 等が real64 に広げると端数を持ち、整数倍の
    ! 判定と層の積み上げが入力の丸めに左右されるため)
    nz = nint(depth / dz)
    if (nz < 2 .or. abs(real(nz) * dz - depth) > 8.0 * epsilon(depth) * depth) then
      call par_stop("list_vz_column: vz_depth"//trim(tag)//" must be an integer multiple (>= 2) of vz_dz" &
                    //trim(tag))
    end if
    select case (list%f_vz_bottom(c))
      case (1)
        psibot = 0.0_real64
      case (2)
        if (list%vz_psibot(c) <= -9998.0) then
          call par_stop("list_vz_column: f_vz_bottom"//trim(tag)//"=2 requires vz_psibot"//trim(tag))
        end if
        psibot = real(list%vz_psibot(c), real64)
      case default
        call par_stop("list_vz_column: f_vz_bottom"//trim(tag)//" must be 1(free drainage) or 2(fixed pressure)")
    end select
    ks = real(list%vz_ks_mmh(c), real64) / 3.6e6_real64
    ! 格子と物性を先に設定(初期 ψ は仮。定常流束指定ならこのあと解く)
    call vzcol_init(vz%cols(c), vz%ctl, ks, real(list%vz_thetas(c), real64), &
                    real(list%vz_thetar(c), real64), real(list%vz_psim(c), real64), &
                    real(list%vz_sigma(c), real64), real(depth, real64), &
                    real(depth, real64) / real(nz, real64), list%f_vz_bottom(c), psibot, -1.0_real64, ok)
    if (.not. ok) call par_stop("list_vz_column: invalid column geometry"//trim(tag))
    ! 初期条件: 定常重力排水の流束 q0、一様な ψ0、静水圧の地下水面の深さ d_wt の
    ! いずれか 1 つ
    ninit = count([list%vz_q0_mmh(c) > -9998.0, list%vz_psi0(c) > -9998.0, list%vz_wt0(c) > -9998.0])
    if (ninit > 1) then
      call par_stop("list_vz_column: give only one of vz_q0_mmh"//trim(tag)//", vz_psi0"//trim(tag) &
                    //" and vz_wt0"//trim(tag))
    else if (list%vz_wt0(c) > -9998.0) then
      if (.not. (list%vz_wt0(c) >= 0.0)) call par_stop("list_vz_column: vz_wt0"//trim(tag)//" must be >= 0 (m)")
      call set_hydrostatic_psi(vz%cols(c), real(list%vz_wt0(c), real64))
      cycle
    else if (list%vz_q0_mmh(c) > -9998.0) then
      call vzcol_steady_psi(vz%cols(c)%geo, real(list%vz_q0_mmh(c), real64) / 3.6e6_real64, psi0, ok)
      if (.not. ok) then
        call par_stop("list_vz_column: vz_q0_mmh"//trim(tag)//" must satisfy 0 < q0 < Ks (and be resolvable)")
      end if
    else if (list%vz_psi0(c) > -9998.0) then
      if (.not. (list%vz_psi0(c) < 0.0)) call par_stop("list_vz_column: vz_psi0"//trim(tag)//" must be < 0 (m)")
      psi0 = real(list%vz_psi0(c), real64)
    else
      call par_stop("list_vz_column: give the initial condition vz_q0_mmh"//trim(tag)//" (steady drainage" &
                    //" flux), vz_psi0"//trim(tag)//" (uniform pressure head) or vz_wt0"//trim(tag) &
                    //" (depth of a hydrostatic water table)")
    end if
    call set_uniform_psi(vz%cols(c), psi0)
  end do
end subroutine


!----------------------------------------------------------------------
! 柱の状態を一様な ψ にする(θ も同じ物性式で導く)
!----------------------------------------------------------------------
subroutine set_uniform_psi(col, psi0)
  type(t_vzcol), intent(inout) :: col
  real(real64), intent(in) :: psi0
  integer :: k
  real(real64) :: cap, kk
  do k = 1, col%geo%nz
    col%psi(k) = psi0
    call vzcol_props(col%geo, col%psi(k), col%th(k), cap, kk)
  end do
end subroutine


!----------------------------------------------------------------------
! 柱の状態を静水圧にする: 深さ d_wt の地下水面(ψ = 0)から ψ(ζ) = ζ − d_wt
! (層中心の深さ ζ_k で評価。地下水面より下は正 = 飽和。柱の下端より深い
! 地下水面なら全層が負)。下端を固定圧 ψ_b にした柱で d_wt = L − ψ_b とすれば
! 流束 0 の静止解(谷 2023 の小斜面の人工降雨実験 KIEX の初期条件:
! 下端 ψ = 0、地表 ψ = −L の線形分布)
!----------------------------------------------------------------------
subroutine set_hydrostatic_psi(col, dwt)
  type(t_vzcol), intent(inout) :: col
  real(real64), intent(in) :: dwt
  integer :: k
  real(real64) :: cap, kk
  do k = 1, col%geo%nz
    col%psi(k) = col%geo%zc(k) - dwt
    call vzcol_props(col%geo, col%psi(k), col%th(k), cap, kk)
  end do
end subroutine


!----------------------------------------------------------------------
! 区画: 区画番号マップ・土層厚・重み W/M・出口・帯の区画番号・検査
!   マップと土層厚は全ランクが全域で持ち(rank0 読み+配布)、重みを同じ順序
!   (j 昇順・i 昇順)で冗長に計算する(全ランクでビット同一)
!----------------------------------------------------------------------
subroutine setup_zones(vz, p, g, b, list)
  type(t_vzflow), intent(inout) :: vz
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  type(t_boundary), intent(in) :: b
  type(t_list_vz), intent(in) :: list
  integer, allocatable :: zmap(:,:), hist(:,:)
  real, allocatable :: sdf(:,:)
  real(real64), allocatable :: part(:,:)
  integer :: i, j, z, c, nz, jf, k, nzn, nzmx
  real(real64) :: d, alpha, a, wsum, msum, adsum
  logical :: used
  character(:), allocatable :: fname

  if (len_trim(list%fn_vz_zone) == 0) call par_stop("list_vz: fn_vz_zone (zone number raster) is required")
  vz%dxdy = real(g%dx, real64) * real(g%dy, real64)
  a = vz%dxdy

  ! --- 区画番号マップ(整数。rank0 読み → 全ランクへ) ---
  allocate(zmap(1:g%nx, 1:g%ny), source = 0)
  fname = trim(p%dir_data) // "/" // trim(list%fn_vz_zone)
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
      if (zmap(i,j) < 0) call stop_at("vz: negative zone number", i, j)
      if (zmap(i,j) == 0) cycle
      if (g%sw(i,j) > 0) call stop_at("vz: a VZ cell is on a sea cell", i, j)
      if (g%rw(i,j) > 0) call stop_at("vz: a VZ cell is on a channel cell (rw)", i, j)
      nzn = max(nzn, zmap(i,j))
    end do
  end do
  if (nzn == 0) call par_stop("vz: fn_vz_zone has no VZ cell (all zone numbers are 0 in the domain)")
  if (nzn > vz_nzonemax) call par_stop("vz: zone numbers must be <= "//itoa(vz_nzonemax))
  vz%nzone = nzn
  allocate(vz%zones(1:nzn))
  do z = nzn + 1, vz_nzonemax
    if (list%vz_out_kind(z) > -9998 .or. list%vz_zone_col(z) > -9998) then
      call par_stop("list_vz_zone: zone "//itoa(z)//" is set but absent from fn_vz_zone")
    end if
  end do
  call check_vz_cells(b, zmap)

  ! --- 区画の参照柱 ---
  do z = 1, nzn
    c = list%vz_zone_col(z)
    if (c <= -9998) c = z            ! 未指定 = 区画番号と同じ柱
    if (c < 1 .or. c > vz%ncol) then
      call par_stop("list_vz_zone: vz_zone_col("//itoa(z)//") refers to an undefined column "//itoa(c))
    end if
    vz%zones(z)%col = c
  end do
  do c = 1, vz%ncol
    used = .false.
    do z = 1, nzn
      if (vz%zones(z)%col == c) used = .true.
    end do
    if (.not. used) call par_stop("list_vz_column: column "//itoa(c)//" is not referenced by any zone")
  end do

  ! --- 土層厚(geoinfo の sd。既定なし: VZ の読み出し深さは与件) ---
  call m_geoinfo_require_sd(g)
  allocate(sdf(1:g%nx, 1:g%ny), source = 0.0)
  call par_gather_to(sdf, g%sd)
  call par_bcast_cell(sdf)

  ! --- 重み W/M(整数ヒストグラム+部分層。O(セル数 + 層数)) ---
  nzmx = 0
  do c = 1, vz%ncol
    nzmx = max(nzmx, vz%cols(c)%geo%nz)
  end do
  allocate(hist(0:nzmx, 1:nzn), source = 0)
  allocate(part(1:nzmx + 1, 1:nzn), source = 0.0_real64)
  do z = 1, nzn
    nz = vz%cols(vz%zones(z)%col)%geo%nz
    allocate(vz%zones(z)%w(0:nz), source = 0.0_real64)
    allocate(vz%zones(z)%m(1:nz), source = 0.0_real64)
    vz%zones(z)%sdmin = huge(1.0_real64)
    vz%zones(z)%sdmax = 0.0_real64
  end do
  do j = 1, g%ny
    do i = 1, g%nx
      z = zmap(i,j)
      if (z == 0) cycle
      associate (zz => vz%zones(z), geo => vz%cols(vz%zones(z)%col)%geo)
        d = real(sdf(i,j), real64)
        ! 土層厚 0 は「雨がそのまま排水される区分」: 界面 0 で読み出すので
        ! D = F_0、S = 0(W(0) に入り、層重み M には入らない。谷 2023 の線形分布の
        ! 0 cm 区分)。負と非数は停止
        if (.not. (d >= 0.0_real64)) call stop_at("vz: soil depth must be >= 0 on VZ cells", i, j)
        if (d > geo%depth) then
          call stop_at("vz: soil depth exceeds the column depth vz_depth (deepen the column)", i, j)
        end if
        call depth_index(geo, d, jf, alpha)
        zz%ncell = zz%ncell + 1
        zz%w(jf) = zz%w(jf) + a * (1.0_real64 - alpha)
        if (alpha > 0.0_real64) zz%w(jf+1) = zz%w(jf+1) + a * alpha
        hist(jf, z) = hist(jf, z) + 1
        if (jf < geo%nz) part(jf+1, z) = part(jf+1, z) + a * (d - geo%zf(jf))
        zz%sdmin = min(zz%sdmin, d)
        zz%sdmax = max(zz%sdmax, d)
        zz%sdmean = zz%sdmean + d
      end associate
    end do
  end do
  do z = 1, nzn
    associate (zz => vz%zones(z), geo => vz%cols(vz%zones(z)%col)%geo)
      if (zz%ncell == 0) call par_stop("vz: zone "//itoa(z)//" has no cell in fn_vz_zone")
      zz%area = a * real(zz%ncell, real64)
      zz%sdmean = zz%sdmean / real(zz%ncell, real64)
      ! M_k = A·Δζ_k·(d が ζ_k 以上のセル数) + 部分層
      jf = 0
      do k = geo%nz, 1, -1
        jf = jf + hist(k, z)           ! d が ζ_k 以上(界面 k 以深)のセル数の累積
        zz%m(k) = a * geo%dzl(k) * real(jf, real64) + part(k, z)
      end do
      ! 整合の検査: Σ W = A_g、Σ M = Σ A d
      wsum = sum(zz%w)
      msum = sum(zz%m)
      adsum = a * zz%sdmean * real(zz%ncell, real64)
      if (abs(wsum - zz%area) > 1.0e-10_real64 * zz%area .or. &
          abs(msum - adsum) > 1.0e-10_real64 * adsum) then
        call par_stop("vz: inconsistent depth weights in zone "//itoa(z)//" (internal check)")
      end if
    end associate
  end do
  allocate(vz%colncell(1:vz%ncol), source = 0)
  do z = 1, nzn
    vz%colncell(vz%zones(z)%col) = vz%colncell(vz%zones(z)%col) + vz%zones(z)%ncell
  end do

  ! --- 出口 ---
  call setup_outlets(vz, g, b, list, zmap)

  ! --- 帯の区画番号(時間ループ用) ---
  allocate(vz%zid(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0)
  do j = max(dcp%jsh, 1), min(dcp%jeh, g%ny)
    do i = max(dcp%ish, 1), min(dcp%ieh, g%nx)
      vz%zid(i,j) = zmap(i,j)
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! VZ セルが境界・ソース・構造物のセルと重ならないこと(雨の回収量が
! boundary_h の式と一致する前提。vz_plan.md §4.10)
!----------------------------------------------------------------------
subroutine check_vz_cells(b, zmap)
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
    if (zmap(i,j) > 0) call stop_at("vz: a VZ cell overlaps "//what//" cell", i, j)
  end subroutine
end subroutine


!----------------------------------------------------------------------
! 出口(区画ごとの種別・セル・配分率)と、全区画で重複を除いたセル一覧
!----------------------------------------------------------------------
subroutine setup_outlets(vz, g, b, list, zmap)
  type(t_vzflow), intent(inout) :: vz
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_list_vz), intent(in) :: list
  integer, intent(in) :: zmap(:,:)
  integer :: z, k, kk, n, i, j, q, st, ns
  integer :: tmpcell(1:2, 1:vz_noutmax * vz_nzonemax)
  real(real64) :: wsum
  character(len=16) :: tag

  vz%nocell = 0
  do z = 1, vz%nzone
    write(tag, '("(",i0,")")') z
    associate (zz => vz%zones(z))
      n = 0
      do k = 1, vz_noutmax
        if (list%vz_out_cell(1,k,z) <= -9998) exit
        n = k
      end do
      select case (list%vz_out_kind(z))
        case (1)
          if (n == 0) call par_stop("list_vz_zone: vz_out_kind"//trim(tag)//"=1 requires vz_out_cell(:,:,"// &
                                    itoa(z)//")")
        case (2)
          if (n > 0) call par_stop("list_vz_zone: vz_out_kind"//trim(tag)//"=2 (outflow from the system)" &
                                   //" takes no vz_out_cell")
        case default
          call par_stop("list_vz_zone: vz_out_kind"//trim(tag)//" must be given: 1(surface cells) or" &
                        //" 2(outflow from the system)")
      end select
      zz%kind = list%vz_out_kind(z)
      zz%nout = n
      if (n == 0) cycle
      allocate(zz%oidx(1:n), zz%ow(1:n))
      do k = 1, n
        i = list%vz_out_cell(1,k,z)
        j = list%vz_out_cell(2,k,z)
        if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
          call par_stop("list_vz_zone: outlet cell out of the grid in zone "//itoa(z)//": ("// &
                        itoa(i)//","//itoa(j)//")")
        end if
        if (g%x(i,j) <= 0) call stop_at("list_vz_zone: an outlet cell is outside the domain", i, j)
        if (g%sw(i,j) > 0) call stop_at("list_vz_zone: an outlet cell is a sea cell (use vz_out_kind=2" &
                                        //" for outflow from the system)", i, j)
        if (zmap(i,j) > 0) call stop_at("list_vz_zone: an outlet cell is a VZ cell", i, j)
        do kk = 1, k - 1
          if (list%vz_out_cell(1,kk,z) == i .and. list%vz_out_cell(2,kk,z) == j) then
            call stop_at("list_vz_zone: duplicate outlet cell in zone "//itoa(z), i, j)
          end if
        end do
        do st = 1, b%nstage
          do ns = 1, b%stage(st)%ncell
            if (b%stage(st)%cell(1,ns) == i .and. b%stage(st)%cell(2,ns) == j) then
              call stop_at("list_vz_zone: an outlet cell is a water level boundary cell", i, j)
            end if
          end do
        end do
        ! 重複を除いた一覧へ登録
        q = 0
        do kk = 1, vz%nocell
          if (tmpcell(1,kk) == i .and. tmpcell(2,kk) == j) q = kk
        end do
        if (q == 0) then
          vz%nocell = vz%nocell + 1
          q = vz%nocell
          tmpcell(1,q) = i
          tmpcell(2,q) = j
        end if
        zz%oidx(k) = q
        ! 配分率: 1 セルなら省略可(= 1)。複数なら全て必須(暗黙の等分配はしない)
        if (list%vz_out_w(k,z) <= -9998.0) then
          if (n == 1) then
            zz%ow(k) = 1.0_real64
          else
            call par_stop("list_vz_zone: vz_out_w(:,"//itoa(z)//") is required for every outlet cell" &
                          //" when a zone has more than one")
          end if
        else
          if (.not. (list%vz_out_w(k,z) >= 0.0)) then
            call par_stop("list_vz_zone: vz_out_w(:,"//itoa(z)//") must be >= 0")
          end if
          zz%ow(k) = real(list%vz_out_w(k,z), real64)
        end if
      end do
      wsum = sum(zz%ow)
      if (abs(wsum - 1.0_real64) > 1.0e-6_real64) then
        call par_stop("list_vz_zone: vz_out_w(:,"//itoa(z)//") must sum to 1")
      end if
      zz%ow(:) = zz%ow(:) / wsum       ! 丸め規模の差だけ正規化(採用値は区画確認表に出す)
    end associate
  end do
  allocate(vz%ocell(1:2, 1:max(vz%nocell,1)), source = 0)
  if (vz%nocell > 0) vz%ocell(:, 1:vz%nocell) = tmpcell(:, 1:vz%nocell)
  allocate(vz%ovol(1:max(vz%nocell,1)), vz%ocarry(1:max(vz%nocell,1)), vz%ovcum(1:max(vz%nocell,1)), &
           source = 0.0_real64)
end subroutine


!----------------------------------------------------------------------
! 毎ステップ: VZ セルに入った雨を s%h から回収し、柱の入力として記録する
!   回収量は boundary_h の加算と同じ式 pre·dt/gv(VZ セルは河道セルでない
!   ので wfrac は掛からない)。上流から流れ込んだ水は回収しない。
!   h を 0 で切らない(浅水流の連続式は前ステップの水深で流出を決め、
!   run-on のある VZ セルでは雨を加える前の水深が微小な負になりうる。
!   0 で切ると回収した雨 pre·dt より取り除いた水が少なく、水を作る)
!----------------------------------------------------------------------
subroutine recover_rain(vz, p, g, s)
  type(t_vzflow), intent(inout) :: vz
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, z, c, k
  real :: pr, dh
  real :: lmx(1:vz%ncol), lmn(1:vz%ncol)
  logical :: changed

  vz%kstep = vz%kstep + 1
  k = vz%kstep
  lmx(:) = -huge(1.0)
  lmn(:) = -huge(1.0)
  if (vz%rainmode == 1) vz%rsnow(:,:) = 0.0_real64
  !$omp parallel do schedule(static) private(i, j, z, c, pr, dh) reduction(max: lmx, lmn)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      z = vz%zid(i,j)
      if (z == 0) cycle
      c = vz%zones(z)%col
      pr = s%pre(i,j)
      dh = s%pre(i,j) * p%dt / s%gv(i,j)
      s%h(i,j) = s%h(i,j) - dh
      s%e(i,j) = s%z(i,j) + s%h(i,j)
      s%vzp(i,j) = s%vzp(i,j) + pr * p%dt
      lmx(c) = max(lmx(c), pr)
      lmn(c) = max(lmn(c), -pr)
      if (vz%rainmode == 1) vz%rsnow(j,c) = vz%rsnow(j,c) + real(pr, real64)
    end do
  end do
  !$omp end parallel do

  if (vz%rainmode == 0) then
    vz%rmx(k,:) = lmx(:)
    vz%rmn(k,:) = lmn(:)
  else
    ! 局所の入力が直前のスナップショットから変わったステップを記録する
    changed = (k == 1)
    if (.not. changed) changed = any(vz%rsnow /= vz%rsprev)
    if (changed) then
      vz%chg(k) = 1
      vz%rsprev(:,:) = vz%rsnow(:,:)
      call push_snapshot(vz, k)
    else
      vz%chg(k) = 0
    end if
  end if
end subroutine


!----------------------------------------------------------------------
! 面積平均モードの行部分和のスナップショットを積む(容量は倍々に伸ばす)
!----------------------------------------------------------------------
subroutine push_snapshot(vz, k)
  type(t_vzflow), intent(inout) :: vz
  integer, intent(in) :: k
  real(real64), allocatable :: tmp(:,:,:)
  integer, allocatable :: tk(:)
  integer :: ncap
  ncap = size(vz%snapk)
  if (vz%nsnap == ncap) then
    allocate(tmp(dcp%js:dcp%je, 1:vz%ncol, 1:2*ncap), source = 0.0_real64)
    allocate(tk(1:2*ncap), source = 0)
    tmp(:, :, 1:ncap) = vz%snap(:, :, 1:ncap)
    tk(1:ncap) = vz%snapk(1:ncap)
    call move_alloc(tmp, vz%snap)
    call move_alloc(tk, vz%snapk)
  end if
  vz%nsnap = vz%nsnap + 1
  vz%snapk(vz%nsnap) = k
  vz%snap(:, :, vz%nsnap) = vz%rsnow(:, :)
end subroutine


!----------------------------------------------------------------------
! 同期: 区間の上端流束を確定し、全柱を進め、区画へ集約し、出口へ渡す
!   (collective。全ランクが同じ順で呼ぶ)
!----------------------------------------------------------------------
subroutine sync_interval(vz, p, s)
  type(t_vzflow), intent(inout) :: vz
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  integer :: nk, c, k, z, q, j, jf, isn, kk
  real, allocatable :: buf(:)
  integer, allocatable :: gchg(:)
  real(real64) :: tot, dv, h, thr
  real(real64), allocatable :: rows(:)
  character(len=512) :: msg

  nk = vz%kstep
  if (nk == 0) return

  ! --- 区間の各ステップの上端流束(柱ごと) ---
  if (vz%rainmode == 0) then
    ! 局所の max と −min を全ランクの max に揃え、柱内の一致を検査する
    allocate(buf(1:2*nk*vz%ncol))
    buf(1:nk*vz%ncol) = reshape(vz%rmx(1:nk, :), [nk*vz%ncol])
    buf(nk*vz%ncol+1:) = reshape(vz%rmn(1:nk, :), [nk*vz%ncol])
    call par_allreduce_max(buf)
    vz%rmx(1:nk, :) = reshape(buf(1:nk*vz%ncol), [nk, vz%ncol])
    vz%rmn(1:nk, :) = reshape(buf(nk*vz%ncol+1:), [nk, vz%ncol])
    do c = 1, vz%ncol
      do k = 1, nk
        if (vz%rmx(k,c) /= -vz%rmn(k,c)) then
          write(msg, '(a,i0,a,es12.4,a,es12.4,a)') "vz: ground rainfall differs within column ", c, &
                " (min ", -vz%rmn(k,c), ", max ", vz%rmx(k,c), " m/s); set f_vz_rain=1 (area average)" &
                // " or split the zone so that each column receives identical rainfall"
          call par_stop(trim(msg))
        end if
        vz%rstep(k,c) = real(vz%rmx(k,c), real64)
      end do
    end do
    deallocate(buf)
  else
    ! 全ランクの変化点を揃え、変化したステップだけ行部分和を決定的に総和する
    allocate(gchg(1:nk))
    gchg(:) = vz%chg(1:nk)
    call par_allreduce_sumi(gchg)
    allocate(rows(dcp%js:dcp%je))
    do k = 1, nk
      if (k > 1 .and. gchg(k) == 0) then
        vz%rstep(k,:) = vz%rstep(k-1,:)
        cycle
      end if
      isn = 0
      do kk = 1, vz%nsnap
        if (vz%snapk(kk) <= k) isn = kk     ! 局所で k 以前の最新のスナップショット
      end do
      do c = 1, vz%ncol
        rows(:) = vz%snap(:, c, isn)
        call par_sum_rows(rows, tot)
        vz%rstep(k,c) = tot / real(vz%colncell(c), real64)
      end do
    end do
    deallocate(rows, gchg)
  end if

  ! --- 区分一定の区間に圧縮して全柱を進める(柱ごとに独立 = OpenMP) ---
  h = real(p%dt, real64)
  do c = 1, vz%ncol
    vz%nseg(c) = 0
    do k = 1, nk
      if (vz%nseg(c) > 0) then
        if (vz%segr(vz%nseg(c), c) == vz%rstep(k,c)) then
          vz%segl(vz%nseg(c), c) = vz%segl(vz%nseg(c), c) + h
          cycle
        end if
      end if
      vz%nseg(c) = vz%nseg(c) + 1
      vz%segl(vz%nseg(c), c) = h
      vz%segr(vz%nseg(c), c) = vz%rstep(k,c)
    end do
    vz%rlast(c) = vz%rstep(nk,c)
  end do
  vz%fsum(:,:) = 0.0_real64
  !$omp parallel do schedule(dynamic)
  do c = 1, vz%ncol
    call vzcol_advance(vz%cols(c), vz%ctl, vz%nseg(c), vz%segl(:,c), vz%segr(:,c), &
                       vz%fsum(0:vz%cols(c)%geo%nz, c), vz%stat(c))
  end do
  !$omp end parallel do
  do c = 1, vz%ncol
    select case (vz%stat(c))
      case (vz_ok)
      case (vz_fail_ponding)
        write(msg, '(a,i0,a,f0.1,a)') "vz: column ", c, " needs ponding at t=", s%t, &
              " s (rainfall exceeds what the soil surface accepts without positive pressure; out of scope)"
        call par_stop(trim(msg))
      case default
        write(msg, '(a,i0,a,f0.1,a,es10.3,a,i0,a)') "vz: column ", c, " cannot advance at t=", s%t, &
              " s (time step fell below vz_dt_min=", vz%ctl%dt_min, " s; last rejection kind ", &
              vz%cols(c)%lastfail, ": 1 nonlinear, 2 range, 3 linear, 4 time error)"
        call par_stop(trim(msg))
    end select
    vz%fcum(:,c) = vz%fcum(:,c) + vz%fsum(:,c)
  end do

  ! --- 区画へ集約(上向きの有意な排水は適用外) ---
  vz%ovol(:) = 0.0_real64
  do z = 1, vz%nzone
    associate (zz => vz%zones(z), geo => vz%cols(vz%zones(z)%col)%geo)
      c = zz%col
      thr = vz%ctl%tol_q_a * real(nk, real64) * h
      do jf = 0, geo%nz
        if (zz%w(jf) > 0.0_real64 .and. vz%fsum(jf, c) < -thr) then
          write(msg, '(a,i0,a,f0.4,a,f0.1,a)') "vz: upward flux at depth ", jf, " (", geo%zf(jf), &
                " m) read by zone at t=", s%t, " s; direct drainage cannot take upward flux"
          call par_stop(trim(msg)//" (zone "//itoa(z)//")")
        end if
      end do
      dv = 0.0_real64
      do jf = 0, geo%nz
        dv = dv + zz%w(jf) * vz%fsum(jf, c)
      end do
      zz%vin = zz%vin + zz%area * vz%fsum(0, c)
      if (dv < 0.0_real64) then
        zz%vcorr = zz%vcorr - dv       ! 丸め規模の負の排水は 0 に切り、補正量として記録
        dv = 0.0_real64
      end if
      zz%vdrain = zz%vdrain + dv
      zz%dvlast = dv
      if (zz%kind == 2) then
        zz%vext = zz%vext + dv
      else
        zz%vint = zz%vint + dv
        do k = 1, zz%nout
          vz%ovol(zz%oidx(k)) = vz%ovol(zz%oidx(k)) + zz%ow(k) * dv
        end do
      end if
      zz%vstore = zone_storage(vz, z)
    end associate
  end do

  ! --- 出口セルへの移送(所有ランクのみ。同じセルへの複数区画の量は合計済み) ---
  do q = 1, vz%nocell
    vz%ovcum(q) = vz%ovcum(q) + vz%ovol(q)
    j = vz%ocell(2,q)
    if (j < dcp%js .or. j > dcp%je) cycle
    call add_to_surface(vz, s, q)
  end do

  ! --- 台帳と区間のリセット ---
  s%vzstore = total_storage(vz)
  s%vzp(:,:) = 0.0
  vz%kstep = 0
  vz%nsnap = 0
end subroutine


!----------------------------------------------------------------------
! 出口セル q へ体積を加える(雨・境界ソースと同じ換算 V/(dx·dy)/gv/wfrac)。
! 実際に加わった体積との差は繰越(単精度ビルドで微小な量が丸めで消えない)
!----------------------------------------------------------------------
subroutine add_to_surface(vz, s, q)
  type(t_vzflow), intent(inout) :: vz
  type(t_state), intent(inout) :: s
  integer, intent(in) :: q
  integer :: i, j
  real :: hold, wf
  real(real64) :: vreq, fac
  i = vz%ocell(1,q)
  j = vz%ocell(2,q)
  wf = 1.0
  if (chn%have_width) wf = chn%wfrac(i,j)
  vreq = vz%ovol(q) + vz%ocarry(q)
  fac = vz%dxdy * real(s%gv(i,j), real64) * real(wf, real64)
  hold = s%h(i,j)
  s%h(i,j) = s%h(i,j) + real(vreq / fac)
  s%e(i,j) = s%z(i,j) + s%h(i,j)
  vz%ocarry(q) = vreq - real(s%h(i,j) - hold, real64) * fac
end subroutine


!----------------------------------------------------------------------
! 区画の VZ 貯留 V_g = Σ_k M_{g,k} θ_k (m3)
!----------------------------------------------------------------------
real(real64) function zone_storage(vz, z)
  type(t_vzflow), intent(in) :: vz
  integer, intent(in) :: z
  integer :: k
  zone_storage = 0.0_real64
  associate (zz => vz%zones(z), col => vz%cols(vz%zones(z)%col))
    do k = 1, col%geo%nz
      zone_storage = zone_storage + zz%m(k) * col%th(k)
    end do
  end associate
end function


!----------------------------------------------------------------------
! 全区画の VZ 貯留を柱状換算の総和で返す(Σ V_g/(dx·dy)。calcstat 用)
!----------------------------------------------------------------------
real(real64) function total_storage(vz)
  type(t_vzflow), intent(in) :: vz
  integer :: z
  total_storage = 0.0_real64
  do z = 1, vz%nzone
    total_storage = total_storage + vz%zones(z)%vstore
  end do
  total_storage = total_storage / vz%dxdy
end function


!----------------------------------------------------------------------
! 深さ d の界面区間: ζ_jf ≤ d ≤ ζ_{jf+1}、α = (d − ζ_jf)/Δζ(d = L なら jf = nz, α = 0)
!----------------------------------------------------------------------
subroutine depth_index(geo, d, jf, alpha)
  type(t_vzgeo), intent(in) :: geo
  real(real64), intent(in) :: d
  integer, intent(out) :: jf
  real(real64), intent(out) :: alpha
  jf = int(d / (geo%depth / real(geo%nz, real64)))
  jf = max(0, min(geo%nz, jf))
  do while (jf < geo%nz)
    if (geo%zf(jf+1) > d) exit
    jf = jf + 1
  end do
  do while (jf > 0)
    if (geo%zf(jf) <= d) exit
    jf = jf - 1
  end do
  if (jf >= geo%nz) then
    jf = geo%nz
    alpha = 0.0_real64
  else
    alpha = (d - geo%zf(jf)) / (geo%zf(jf+1) - geo%zf(jf))
  end if
end subroutine


!----------------------------------------------------------------------
! 区画確認表(初期化時に画面へ。Log.txt には書かない)
!----------------------------------------------------------------------
subroutine report_zones(vz)
  type(t_vzflow), intent(in) :: vz
  integer :: z, k
  character(len=512) :: line
  call par_info("vz: "//itoa(vz%ncol)//" column(s), "//itoa(vz%nzone)//" zone(s)")
  do z = 1, vz%nzone
    associate (zz => vz%zones(z))
      write(line, '(a,i0,a,i0,a,i0,a,es11.4,a,3f9.4)') "  zone ", z, ": column ", zz%col, ", cells ", &
            zz%ncell, ", area ", zz%area, " m2, soil depth min/mean/max", zz%sdmin, zz%sdmean, zz%sdmax
      call par_info(trim(line))
      if (zz%kind == 2) then
        call par_info("    outlet: outflow from the system")
      else
        do k = 1, zz%nout
          write(line, '(a,i0,a,i0,a,f8.5)') "    outlet cell (", vz%ocell(1,zz%oidx(k)), ",", &
                vz%ocell(2,zz%oidx(k)), ") weight ", zz%ow(k)
          call par_info(trim(line))
        end do
      end if
    end associate
  end do
end subroutine


!----------------------------------------------------------------------
! CSV を開く(rank0)
!----------------------------------------------------------------------
subroutine open_csv(vz, p)
  type(t_vzflow), intent(inout) :: vz
  type(t_sysparam), intent(in) :: p
  integer :: k
  character(len=32) :: buf
  if (.not. is_root) return
  open(newunit=vz%un_zone, file=trim(p%dir_result)//"/vz_zone.csv", status='replace')
  write(vz%un_zone, '(a)') "time(s),zone,column,area(m2),vin(m3),vstore(m3),vdrain(m3)," // &
                           "vsurface(m3),vexternal(m3),vcorr(m3),residual(m3)"
  open(newunit=vz%un_col, file=trim(p%dir_result)//"/vz_column.csv", status='replace')
  write(vz%un_col, '(a)', advance='no') "time(s),column,rate(m/s),F0(m),Fbottom(m)"
  do k = 1, vz%ndep
    write(buf, '(f0.4)') vz%odep(k)
    if (buf(1:1) == '.') buf = '0'//trim(buf)
    write(vz%un_col, '(a)', advance='no') ",D@"//trim(buf)//"(m),S@"//trim(buf)//"(m)"
  end do
  write(vz%un_col, '(a)') ",nacc,nrej,nit,dtlast(s)"
end subroutine


!----------------------------------------------------------------------
! 保存(私有ファイル vzflow.dat。rank0 が書く。読み並びは restore_state と対)
!   出口の繰越は所有ランクだけが持つので、その行だけが非 0 の行部分和を
!   par_sum_rows で集める(寄与が 1 つなので総和は厳密。real64 のまま
!   集めるので単精度ビルドでも繰越が丸められない)
!----------------------------------------------------------------------
subroutine save_state(vz, p)
  type(t_vzflow), intent(in) :: vz
  type(t_sysparam), intent(in) :: p
  integer :: un, c, z, q, j
  real(real64), allocatable :: carry(:), rowv(:)
  allocate(carry(1:max(vz%nocell,1)), source = 0.0_real64)
  allocate(rowv(dcp%js:dcp%je))
  do q = 1, vz%nocell
    rowv(:) = 0.0_real64
    j = vz%ocell(2,q)
    if (j >= dcp%js .and. j <= dcp%je) rowv(j) = vz%ocarry(q)
    call par_sum_rows(rowv, carry(q))
  end do
  if (.not. is_root) return
  call sysdep_mkdir(p%dir_save)
  open(newunit=un, file=trim(p%dir_save)//'/vzflow.dat', form='unformatted', status='replace')
  write(un) save_version, vz%ncol, vz%nzone, vz%nocell
  do c = 1, vz%ncol
    write(un) vz%cols(c)%geo%nz, vz%cols(c)%geo%depth, vz%cols(c)%geo%ks, vz%cols(c)%geo%ths
  end do
  do z = 1, vz%nzone
    write(un) vz%zones(z)%col, vz%zones(z)%ncell, vz%zones(z)%sdmean
  end do
  do c = 1, vz%ncol
    write(un) vz%cols(c)%psi, vz%cols(c)%dtnext, vz%cols(c)%nacc, vz%cols(c)%nrej, vz%cols(c)%nit, &
              vz%cols(c)%dtlast, vz%rlast(c)
    write(un) vz%fcum(0:vz%cols(c)%geo%nz, c)
  end do
  do z = 1, vz%nzone
    write(un) vz%zones(z)%vin, vz%zones(z)%vdrain, vz%zones(z)%vint, vz%zones(z)%vext, &
              vz%zones(z)%vcorr, vz%zones(z)%vstore0, vz%zones(z)%dvlast
  end do
  if (vz%nocell > 0) then
    write(un) vz%ocell(:, 1:vz%nocell)
    write(un) carry(1:vz%nocell), vz%ovcum(1:vz%nocell)
  end if
  close(un)
end subroutine


!----------------------------------------------------------------------
! 復元(全ランクが同じファイルを読む。小さいベクトルだけなので配布はしない)。
! 構成の識別(柱・区画・出口の数と主要な値)が保存時と違えば停止する
!----------------------------------------------------------------------
subroutine restore_state(vz, p)
  type(t_vzflow), intent(inout) :: vz
  type(t_sysparam), intent(in) :: p
  character(:), allocatable :: fname
  logical :: found
  integer :: un, ver, nc, nzn, noc, c, z, nz, col, ncell, ios
  real(real64) :: depth, ks, ths, sdmean
  real(real64), allocatable :: tmp(:)
  integer, allocatable :: oc(:,:)
  logical :: mismatch

  fname = trim(p%dir_save)//'/vzflow.dat'
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("vz: state file not found (was fn_vz enabled when saving): "//fname)
  mismatch = .false.
  open(newunit=un, file=fname, form='unformatted', status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("vz: cannot open "//fname)
  read(un) ver, nc, nzn, noc
  if (ver /= save_version .or. nc /= vz%ncol .or. nzn /= vz%nzone .or. noc /= vz%nocell) then
    mismatch = .true.
  else
    do c = 1, nc
      read(un) nz, depth, ks, ths
      if (nz /= vz%cols(c)%geo%nz .or. depth /= vz%cols(c)%geo%depth .or. ks /= vz%cols(c)%geo%ks &
          .or. ths /= vz%cols(c)%geo%ths) mismatch = .true.
    end do
    do z = 1, nzn
      read(un) col, ncell, sdmean
      if (col /= vz%zones(z)%col .or. ncell /= vz%zones(z)%ncell .or. sdmean /= vz%zones(z)%sdmean) &
        mismatch = .true.
    end do
  end if
  if (mismatch) then
    close(un)
    call par_stop("vz: the configuration (columns, zones, soil depth or outlets) differs from the saved state "&
                  //fname)
  end if
  do c = 1, nc
    associate (col_ => vz%cols(c))
      read(un) col_%psi, col_%dtnext, col_%nacc, col_%nrej, col_%nit, col_%dtlast, vz%rlast(c)
      call refresh_theta(col_)
      read(un) vz%fcum(0:col_%geo%nz, c)
    end associate
  end do
  do z = 1, nzn
    read(un) vz%zones(z)%vin, vz%zones(z)%vdrain, vz%zones(z)%vint, vz%zones(z)%vext, &
             vz%zones(z)%vcorr, vz%zones(z)%vstore0, vz%zones(z)%dvlast
  end do
  if (noc > 0) then
    allocate(oc(1:2, 1:noc), tmp(1:noc))
    read(un) oc
    if (any(oc /= vz%ocell(:, 1:noc))) then
      close(un)
      call par_stop("vz: the outlet cells differ from the saved state "//fname)
    end if
    read(un) tmp, vz%ovcum(1:noc)
    vz%ocarry(1:noc) = tmp
  end if
  close(un)
end subroutine


!----------------------------------------------------------------------
! 復元した ψ から θ を同じ物性式で導く(θ を別に保存して食い違わせない)
!----------------------------------------------------------------------
subroutine refresh_theta(col)
  type(t_vzcol), intent(inout) :: col
  integer :: k
  real(real64) :: cap, kk
  do k = 1, col%geo%nz
    call vzcol_props(col%geo, col%psi(k), col%th(k), cap, kk)
  end do
end subroutine


!----------------------------------------------------------------------
! 無効なのに私有ファイルが dir_save にあれば停止する(保存時の VZ 貯留を
! 黙って捨てない。§16.2 の stop_if_orphan_state と同じ門番)
!----------------------------------------------------------------------
subroutine stop_if_orphan(p)
  type(t_sysparam), intent(in) :: p
  logical :: found
  inquire(file=trim(p%dir_save)//'/vzflow.dat', exist=found)
  if (found) then
    call par_stop("vz: vzflow.dat exists in "//trim(p%dir_save)//" but VZ is not enabled at restart" &
                  //" (its stored state would be dropped); enable fn_vz or remove the file if the drop is intended")
  end if
end subroutine


!----------------------------------------------------------------------
! セル位置つきの停止(全ランクが同じ全域データで同じ判定をする場所でのみ使う)
!----------------------------------------------------------------------
subroutine stop_at(msg, i, j)
  character(len=*), intent(in) :: msg
  integer, intent(in) :: i, j
  call par_stop(msg//" at ("//itoa(i)//","//itoa(j)//")")
end subroutine

end module
