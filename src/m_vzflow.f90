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
  !   基底流 : 区画ごとに与えた時系列(vz_base / fn_vz_base。mm/h、区画面積基底)を
  !            同期区間ごとに厳密に積分し、排水と同じ出口へ渡す(谷 2023 が観測から
  !            分離した基底流を VZ の計算値に加えた扱い。分離は利用者の前処理)。
  !            柱・区画の貯留には入らない外部供給(vz_zone.csv の vbase。出口の
  !            vsurface・vexternal は排水 + 基底流)。
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
  !   水位規定セルに置けない。貯留関数(fn_sfm。§106)とは区画が重ならなければ
  !   併用できる(検査は m_sfm_init)。
  !
  ! 【共通基盤】区画番号ラスタ・雨の回収と柱の入力の集約・出口・基底流は
  !   m_zonerunoff(t_zonerunoff を成分 zr に持つ。入力群 = 柱)。本モジュールは
  !   柱の前進・区画の重み W/M による集約・貯留・保存ファイルを受け持つ
  !   (§106.2 で移した。等価リファクタ)。
  ! ====================================================================
  use, intrinsic :: iso_fortran_env, only : real64, int64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo, m_geoinfo_require_sd
  use m_state, only : t_state
  use m_boundary, only : t_boundary
  use list_vz, only : t_list_vz, list_vz_read, vz_ncolmax, vz_nzonemax, vz_ndepmax
  use m_vzflow_column, only : t_vzcol, t_vzctl, t_vzgeo, vzcol_init, vzcol_advance, vzcol_props, &
                              vzcol_dispose, vzcol_steady_psi, vz_ok, vz_fail_time, vz_fail_ponding
  use m_zonerunoff, only : t_zonerunoff, zr_read_map, zr_set_groups, zr_setup_outlets, zr_setup_baseflow, &
                           zr_alloc_interval, zr_recover_rain, zr_collect_input, zr_deliver, &
                           zr_gather_carry, zr_report_outlets, zr_dispose
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : param_default, itoa, es_out
  use m_parallel, only : par_info, par_stop, dcp, is_root, par_gather_to, par_bcast_cell
  implicit none
  private
  public :: t_vzflow
  public :: m_vzflow_init
  public :: m_vzflow_calc
  public :: m_vzflow_record
  public :: m_vzflow_outprof
  public :: m_vzflow_dispose

  integer, parameter :: save_version = 20261027   ! vzflow.dat の形式の版(形式変更日。§7)

  !-------------------------------------------
  ! VZ 区画の柱に固有の量(セル数・面積・出口・基底流・移送の累積は
  ! 共通基盤 zr%zones(z))
  !-------------------------------------------
  type t_vzzone
    integer :: col = 0                         ! 参照する柱(= zr%zones(z)%grp)
    real(real64), allocatable :: w(:)          ! 界面重み W_{g,j} (0:nz。m2)
    real(real64), allocatable :: m(:)          ! 層重み M_{g,k} (1:nz。m3)
    real(real64) :: sdmin = 0.0_real64, sdmax = 0.0_real64, sdmean = 0.0_real64  ! 土層厚の統計 (m)
    ! 診断(累積 m3。全ランク同値)
    real(real64) :: vin = 0.0_real64           ! 上端入力 A_g·F_0
    real(real64) :: vdrain = 0.0_real64        ! 底面排水 Σ W F
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
    integer :: ncol = 0
    type(t_zonerunoff) :: zr                   ! 区画・雨の回収と柱の入力・出口・基底流(入力群 = 柱)
    type(t_vzctl) :: ctl                       ! 数値制御(全柱共通)
    type(t_vzcol), allocatable :: cols(:)      ! 共有参照柱
    type(t_vzzone), allocatable :: zones(:)    ! VZ 区画の柱に固有の量
    ! 柱の積算流束(直近の同期区間・累積)
    integer :: nzmax = 0
    real(real64), allocatable :: fsum(:,:)     ! (0:nzmax, 1:ncol) 直近の同期区間 (m)
    real(real64), allocatable :: fcum(:,:)     ! (0:nzmax, 1:ncol) 計算開始からの累積 (m)
    integer, allocatable :: stat(:)            ! 前進の結果(柱ごと)
    real(real64), allocatable :: dvz(:)        ! (1:nzone) 直近の同期区間の区画の排水 (m3。作業)
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

  vz%zr%tag = "vz"
  vz%zr%label = "VZ"
  vz%zr%nml = "list_vz_zone"
  vz%zr%grpword = "column"
  call check_combinations(p, multi)
  call setup_control(vz, p, list)
  call setup_columns(vz, list)
  call setup_zones(vz, p, g, b, list)

  allocate(s%vzp(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  s%vz_active = .true.

  ! 区間の作業配列
  call zr_alloc_interval(vz%zr)
  vz%nzmax = 0
  do c = 1, vz%ncol
    vz%nzmax = max(vz%nzmax, vz%cols(c)%geo%nz)
  end do
  allocate(vz%fsum(0:vz%nzmax, 1:vz%ncol), vz%fcum(0:vz%nzmax, 1:vz%ncol), source = 0.0_real64)
  allocate(vz%stat(1:vz%ncol), source = vz_ok)
  allocate(vz%dvz(1:vz%zr%nzone), source = 0.0_real64)

  if (p%f_state_restore > 0) call restore_state(vz, p)

  ! 貯留の初期値(restore 時は復元した柱の状態から)
  do z = 1, vz%zr%nzone
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
  call zr_recover_rain(vz%zr, p, g, s, s%vzp)
  if (mod(it, vz%zr%idt) == 0) call sync_interval(vz, p, s)
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
  do z = 1, vz%zr%nzone
    associate (zz => vz%zones(z), zc => vz%zr%zones(z))
      ! 区画の収支残差 = 貯留変化 − (入力 − 排水) − 補正(非線形残差の集積と丸め)
      res = zz%vstore - zz%vstore0 - zz%vin + zz%vdrain - zz%vcorr
      write(vz%un_zone, '(f0.2,",",i0,",",i0,8(",",es23.15))', advance='no') s%t, z, zz%col, &
            es_out([zc%area, zz%vin, zz%vstore, zz%vdrain, zc%vint, zc%vext, zz%vcorr, res])
      if (vz%zr%have_base) write(vz%un_zone, '(",",es23.15)', advance='no') es_out(zc%vbase)
      write(vz%un_zone, '(a)') ""
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
      write(vz%un_col, '(f0.2,",",i0,3(",",es23.15))', advance='no') s%t, c, &
            es_out([vz%zr%rlast(c), vz%fcum(0, c), vz%fcum(geo%nz, c)])
      do k = 1, vz%ndep
        call depth_index(geo, vz%odep(k), jf, alpha)
        if (jf < geo%nz) then
          dcum = (1.0_real64 - alpha) * vz%fcum(jf, c) + alpha * vz%fcum(jf+1, c)
          sto = (1.0_real64 - alpha) * bsum(jf) + alpha * bsum(jf+1)
        else
          dcum = vz%fcum(geo%nz, c)
          sto = bsum(geo%nz)
        end if
        write(vz%un_col, '(2(",",es23.15))', advance='no') es_out([dcum, sto])
      end do
      write(vz%un_col, '(3(",",i0),",",es12.4)') col%nacc, col%nrej, col%nit, es_out(col%dtlast)
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
      write(un, '(es23.15,5(",",es23.15))') es_out([vz%cols(c)%geo%zc(k), vz%cols(c)%psi(k), th, kk, &
            vz%cols(c)%geo%zf(k), vz%fcum(k, c)])
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
    if (vz%zr%kstep > 0) then
      call par_info("vz: syncing the partial interval of "//itoa(vz%zr%kstep)//" steps before saving")
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
  call zr_dispose(vz%zr)
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
    vz%zr%idt = 1
  else
    vz%zr%idt = max(1, nint(dtv / p%dt))
  end if
  if (vz%zr%idt > 1) call par_info("vz: columns are synchronised every "//itoa(vz%zr%idt)//" steps")

  select case (list%f_vz_rain)
    case (0, 1)
      vz%zr%rainmode = list%f_vz_rain
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
! 共有参照柱(物性・格子・初期条件・下端)
!   柱の数 = 設定のある最大の柱番号と、区画の設定が参照する最大の柱番号
!   (vz_zone_col。未指定なら区画番号)の大きい方(1 以上)。設定のない柱も
!   区画が参照していれば既定の柱になる(参照されない柱は setup_zones で停止)。
!   試算用の既定(developer.md §87.7。§62 と同じく採用値を必ず表示する):
!   小杉パラメータは 5 つとも未指定なら谷(2023)表−2 の竜ノ口山(TY)の組、
!   一部だけの指定は停止(別の土壌の値の混在を防ぐ)。初期条件が未指定なら
!   定常重力排水 q0 = 0.1 mm/h
!----------------------------------------------------------------------
subroutine setup_columns(vz, list)
  type(t_vzflow), intent(inout) :: vz
  type(t_list_vz), intent(in) :: list
  ! 試算用の小杉パラメータ(谷 2023 表−2 の竜ノ口山 TY: Ks = 5.0e-3 cm/s = 180 mm/h)と
  ! 初期条件の既定(降雨前の流出率の目安。経験値)
  real, parameter :: ty_ks_mmh = 180.0, ty_thetas = 0.370, ty_thetar = 0.230
  real, parameter :: ty_psim = -0.200, ty_sigma = 1.60
  real, parameter :: q0_default_mmh = 0.1
  integer :: c, nc, nz, ninit, nset, z
  real :: depth, dz, ksmmh, ths, thr, psim, sigma, q0mmh
  real(real64) :: ks, psi0, psibot
  logical :: ok
  character(len=8) :: tag
  character(len=32) :: buf

  nc = 0
  do c = 1, vz_ncolmax
    if (any([list%vz_ks_mmh(c), list%vz_thetas(c), list%vz_thetar(c), list%vz_psim(c), &
             list%vz_sigma(c), list%vz_depth(c), list%vz_dz(c), list%vz_q0_mmh(c), &
             list%vz_psi0(c), list%vz_wt0(c), list%vz_psibot(c)] > -9998.0) &
        .or. list%f_vz_bottom(c) /= 1) nc = c
  end do
  do z = 1, vz_nzonemax
    c = list%vz_zone_col(z)
    if (c <= -9998 .and. list%vz_out_kind(z) > -9998) c = z
    if (c > vz_ncolmax) then
      call par_stop("list_vz_zone: vz_zone_col("//itoa(z)//") must be <= "//itoa(vz_ncolmax))
    end if
    nc = max(nc, c)                   ! 不正な番号(0 以下)は setup_zones が停止
  end do
  nc = max(nc, 1)
  vz%ncol = nc
  allocate(vz%cols(1:nc))

  do c = 1, nc
    write(tag, '("(",i0,")")') c
    nset = count([list%vz_ks_mmh(c), list%vz_thetas(c), list%vz_thetar(c), list%vz_psim(c), &
                  list%vz_sigma(c)] > -9998.0)
    if (nset /= 0 .and. nset /= 5) then
      call par_stop("list_vz_column: give all five Kosugi parameters of column "//itoa(c) &
                    //" (vz_ks_mmh, vz_thetas, vz_thetar, vz_psim, vz_sigma) or none of them" &
                    //" (none = the trial set of Tani 2023, Tatsunokuchi-yama)")
    end if
    if (nset == 0) call par_info("vz: column "//itoa(c)//" uses the trial Kosugi set (Tani 2023 Table 2," &
                                 //" Tatsunokuchi-yama TY); give the values of the site for real use")
    ksmmh = param_default("vz", "vz_ks_mmh"//trim(tag), list%vz_ks_mmh(c), ty_ks_mmh, " mm/h", unset = -9999.0)
    ths = param_default("vz", "vz_thetas"//trim(tag), list%vz_thetas(c), ty_thetas, "", unset = -9999.0)
    thr = param_default("vz", "vz_thetar"//trim(tag), list%vz_thetar(c), ty_thetar, "", unset = -9999.0)
    psim = param_default("vz", "vz_psim"//trim(tag), list%vz_psim(c), ty_psim, " m", unset = -9999.0)
    sigma = param_default("vz", "vz_sigma"//trim(tag), list%vz_sigma(c), ty_sigma, "", unset = -9999.0)
    if (ksmmh <= 0.0) call par_stop("list_vz_column: vz_ks_mmh"//trim(tag)//" must be > 0")
    if (.not. (thr >= 0.0 .and. thr < ths .and. ths <= 1.0)) then
      call par_stop("list_vz_column: require 0 <= vz_thetar"//trim(tag)//" < vz_thetas"//trim(tag)//" <= 1")
    end if
    if (.not. (psim < 0.0)) call par_stop("list_vz_column: vz_psim"//trim(tag)//" must be < 0 (m)")
    if (.not. (sigma > 0.0)) call par_stop("list_vz_column: vz_sigma"//trim(tag)//" must be > 0")
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
    ks = real(ksmmh, real64) / 3.6e6_real64
    ! 格子と物性を先に設定(初期 ψ は仮。定常流束指定ならこのあと解く)
    call vzcol_init(vz%cols(c), vz%ctl, ks, real(ths, real64), &
                    real(thr, real64), real(psim, real64), &
                    real(sigma, real64), real(depth, real64), &
                    real(depth, real64) / real(nz, real64), list%f_vz_bottom(c), psibot, -1.0_real64, ok)
    if (.not. ok) call par_stop("list_vz_column: invalid column geometry"//trim(tag))
    ! 初期条件: 定常重力排水の流束 q0、一様な ψ0、静水圧の地下水面の深さ d_wt の
    ! いずれか 1 つ。どれもなければ q0 の既定
    ninit = count([list%vz_q0_mmh(c) > -9998.0, list%vz_psi0(c) > -9998.0, list%vz_wt0(c) > -9998.0])
    if (ninit > 1) then
      call par_stop("list_vz_column: give only one of vz_q0_mmh"//trim(tag)//", vz_psi0"//trim(tag) &
                    //" and vz_wt0"//trim(tag))
    else if (list%vz_wt0(c) > -9998.0) then
      if (.not. (list%vz_wt0(c) >= 0.0)) call par_stop("list_vz_column: vz_wt0"//trim(tag)//" must be >= 0 (m)")
      call set_hydrostatic_psi(vz%cols(c), real(list%vz_wt0(c), real64))
      cycle
    else if (list%vz_psi0(c) > -9998.0) then
      if (.not. (list%vz_psi0(c) < 0.0)) call par_stop("list_vz_column: vz_psi0"//trim(tag)//" must be < 0 (m)")
      psi0 = real(list%vz_psi0(c), real64)
    else
      q0mmh = param_default("vz", "vz_q0_mmh"//trim(tag), list%vz_q0_mmh(c), q0_default_mmh, " mm/h", &
                            unset = -9999.0)
      call vzcol_steady_psi(vz%cols(c)%geo, real(q0mmh, real64) / 3.6e6_real64, psi0, ok)
      if (.not. ok) then
        call par_stop("list_vz_column: vz_q0_mmh"//trim(tag)//" must satisfy 0 < q0 < Ks (and be resolvable)")
      end if
      write(buf, '(es12.4)') psi0
      call par_info("vz: column "//itoa(c)//" initial psi = "//trim(adjustl(buf))//" m (uniform; steady" &
                    //" drainage at vz_q0_mmh)")
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
! 区画: 区画番号マップ(共通基盤)・参照柱・土層厚・重み W/M・出口と基底流
! (共通基盤)・検査
!   マップと土層厚は全ランクが全域で持ち(rank0 読み+配布)、重みを同じ順序
!   (j 昇順・i 昇順)で冗長に計算する(全ランクでビット同一)
!----------------------------------------------------------------------
subroutine setup_zones(vz, p, g, b, list)
  type(t_vzflow), intent(inout) :: vz
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  type(t_boundary), intent(in) :: b
  type(t_list_vz), intent(in) :: list
  integer, allocatable :: zmap(:,:), hist(:,:), grp(:)
  real, allocatable :: sdf(:,:)
  real(real64), allocatable :: part(:,:)
  integer :: i, j, z, c, nz, jf, k, nzn, nzmx, ncell
  real(real64) :: d, alpha, a, wsum, msum, adsum
  logical :: used

  ! --- 区画番号マップ(共通基盤: 読み込み・セルの検査・セル数と面積・帯の区画番号) ---
  call zr_read_map(vz%zr, p, g, b, list%fn_vz_zone, "fn_vz_zone", vz_nzonemax, zmap)
  nzn = vz%zr%nzone
  a = vz%zr%dxdy
  allocate(vz%zones(1:nzn))
  do z = nzn + 1, vz_nzonemax
    if (list%vz_out_kind(z) > -9998 .or. list%vz_zone_col(z) > -9998 .or. &
        list%vz_base(1,1,z) > -9998.0 .or. len_trim(list%fn_vz_base(z)) > 0) then
      call par_stop("list_vz_zone: zone "//itoa(z)//" is set but absent from fn_vz_zone")
    end if
  end do

  ! --- 区画の参照柱 ---
  do z = 1, nzn
    c = list%vz_zone_col(z)
    if (c <= -9998) c = z            ! 未指定 = 区画番号と同じ柱
    if (c > vz%ncol .and. list%vz_out_kind(z) <= -9998 .and. list%vz_zone_col(z) <= -9998) then
      ! 設定のない区画(柱の数は区画の設定から決めるため、ここで先に止める)
      call par_stop("list_vz_zone: zone "//itoa(z)//" of fn_vz_zone has no settings (give vz_out_kind(" &
                    //itoa(z)//"))")
    end if
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
  allocate(grp(1:nzn))
  do z = 1, nzn
    grp(z) = vz%zones(z)%col
  end do
  call zr_set_groups(vz%zr, grp, vz%ncol)    ! 入力群 = 柱(柱を参照するセル数も)

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
      ncell = vz%zr%zones(z)%ncell
      zz%sdmean = zz%sdmean / real(ncell, real64)
      ! M_k = A·Δζ_k·(d が ζ_k 以上のセル数) + 部分層
      jf = 0
      do k = geo%nz, 1, -1
        jf = jf + hist(k, z)           ! d が ζ_k 以上(界面 k 以深)のセル数の累積
        zz%m(k) = a * geo%dzl(k) * real(jf, real64) + part(k, z)
      end do
      ! 整合の検査: Σ W = A_g、Σ M = Σ A d
      wsum = sum(zz%w)
      msum = sum(zz%m)
      adsum = a * zz%sdmean * real(ncell, real64)
      if (abs(wsum - vz%zr%zones(z)%area) > 1.0e-10_real64 * vz%zr%zones(z)%area .or. &
          abs(msum - adsum) > 1.0e-10_real64 * adsum) then
        call par_stop("vz: inconsistent depth weights in zone "//itoa(z)//" (internal check)")
      end if
    end associate
  end do

  ! --- 出口と基底流(共通基盤) ---
  call zr_setup_outlets(vz%zr, g, b, list%vz_out_kind, list%vz_out_cell, list%vz_out_w, zmap)
  call zr_setup_baseflow(vz%zr, p, list%vz_base, list%fn_vz_base)
end subroutine


!----------------------------------------------------------------------
! 同期: 区間の上端流束を確定し(共通基盤)、全柱を進め、区画へ集約し、
! 出口へ渡す(共通基盤)。collective(全ランクが同じ順で呼ぶ)
!----------------------------------------------------------------------
subroutine sync_interval(vz, p, s)
  type(t_vzflow), intent(inout) :: vz
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  integer :: nk, c, z, jf
  real(real64) :: dv, h, thr
  character(len=512) :: msg

  nk = vz%zr%kstep
  if (nk == 0) return

  ! --- 区間の各ステップの上端流束(柱ごと)を確定し、区分一定の区間に圧縮する ---
  call zr_collect_input(vz%zr, p)

  ! --- 全柱を進める(柱ごとに独立 = OpenMP) ---
  h = real(p%dt, real64)
  vz%fsum(:,:) = 0.0_real64
  !$omp parallel do schedule(dynamic)
  do c = 1, vz%ncol
    call vzcol_advance(vz%cols(c), vz%ctl, vz%zr%nseg(c), vz%zr%segl(:,c), vz%zr%segr(:,c), &
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
  do z = 1, vz%zr%nzone
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
      zz%vin = zz%vin + vz%zr%zones(z)%area * vz%fsum(0, c)
      if (dv < 0.0_real64) then
        zz%vcorr = zz%vcorr - dv       ! 丸め規模の負の排水は 0 に切り、補正量として記録
        dv = 0.0_real64
      end if
      zz%vdrain = zz%vdrain + dv
      zz%dvlast = dv
      vz%dvz(z) = dv
      zz%vstore = zone_storage(vz, z)
    end associate
  end do

  ! --- 基底流を加えて出口へ渡し、区間を閉じる(s%vzp も 0 に戻す) ---
  call zr_deliver(vz%zr, p, s, vz%dvz, s%vzp)

  ! --- 台帳 ---
  s%vzstore = total_storage(vz)
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
  do z = 1, vz%zr%nzone
    total_storage = total_storage + vz%zones(z)%vstore
  end do
  total_storage = total_storage / vz%zr%dxdy
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
  integer :: z
  character(len=512) :: line
  call par_info("vz: "//itoa(vz%ncol)//" column(s), "//itoa(vz%zr%nzone)//" zone(s)")
  do z = 1, vz%zr%nzone
    associate (zz => vz%zones(z), zc => vz%zr%zones(z))
      write(line, '(a,i0,a,i0,a,i0,a,es11.4,a,3f9.4)') "  zone ", z, ": column ", zz%col, ", cells ", &
            zc%ncell, ", area ", zc%area, " m2, soil depth min/mean/max", zz%sdmin, zz%sdmean, zz%sdmax
      call par_info(trim(line))
      call zr_report_outlets(vz%zr, z)
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
  write(vz%un_zone, '(a)', advance='no') "time(s),zone,column,area(m2),vin(m3),vstore(m3),vdrain(m3)," // &
                                         "vsurface(m3),vexternal(m3),vcorr(m3),residual(m3)"
  if (vz%zr%have_base) write(vz%un_zone, '(a)', advance='no') ",vbase(m3)"
  write(vz%un_zone, '(a)') ""
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
!   出口の繰越は所有ランクだけが持つので、共通基盤の zr_gather_carry で
!   全ランク同値に集めてから書く(collective)
!----------------------------------------------------------------------
subroutine save_state(vz, p)
  type(t_vzflow), intent(in) :: vz
  type(t_sysparam), intent(in) :: p
  integer :: un, c, z
  real(real64), allocatable :: carry(:)
  call zr_gather_carry(vz%zr, carry)
  if (.not. is_root) return
  call sysdep_mkdir(p%dir_save)
  open(newunit=un, file=trim(p%dir_save)//'/vzflow.dat', form='unformatted', status='replace')
  write(un) save_version, vz%ncol, vz%zr%nzone, vz%zr%nocell
  do c = 1, vz%ncol
    write(un) vz%cols(c)%geo%nz, vz%cols(c)%geo%depth, vz%cols(c)%geo%ks, vz%cols(c)%geo%ths
  end do
  do z = 1, vz%zr%nzone
    write(un) vz%zones(z)%col, vz%zr%zones(z)%ncell, vz%zones(z)%sdmean
  end do
  do c = 1, vz%ncol
    write(un) vz%cols(c)%psi, vz%cols(c)%dtnext, vz%cols(c)%nacc, vz%cols(c)%nrej, vz%cols(c)%nit, &
              vz%cols(c)%dtlast, vz%zr%rlast(c)
    write(un) vz%fcum(0:vz%cols(c)%geo%nz, c)
  end do
  do z = 1, vz%zr%nzone
    write(un) vz%zones(z)%vin, vz%zones(z)%vdrain, vz%zr%zones(z)%vint, vz%zr%zones(z)%vext, &
              vz%zones(z)%vcorr, vz%zones(z)%vstore0, vz%zones(z)%dvlast, vz%zr%zones(z)%vbase
  end do
  if (vz%zr%nocell > 0) then
    write(un) vz%zr%ocell(:, 1:vz%zr%nocell)
    write(un) carry(1:vz%zr%nocell), vz%zr%ovcum(1:vz%zr%nocell)
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
  if (ver /= save_version) then
    close(un)
    call par_stop("vz: state file format version "//itoa(ver)//" does not match the version this " &
                  //"executable reads ("//itoa(save_version)//"): "//fname)
  end if
  if (nc /= vz%ncol .or. nzn /= vz%zr%nzone .or. noc /= vz%zr%nocell) then
    mismatch = .true.
  else
    do c = 1, nc
      read(un) nz, depth, ks, ths
      if (nz /= vz%cols(c)%geo%nz .or. depth /= vz%cols(c)%geo%depth .or. ks /= vz%cols(c)%geo%ks &
          .or. ths /= vz%cols(c)%geo%ths) mismatch = .true.
    end do
    do z = 1, nzn
      read(un) col, ncell, sdmean
      if (col /= vz%zones(z)%col .or. ncell /= vz%zr%zones(z)%ncell .or. sdmean /= vz%zones(z)%sdmean) &
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
      read(un) col_%psi, col_%dtnext, col_%nacc, col_%nrej, col_%nit, col_%dtlast, vz%zr%rlast(c)
      call refresh_theta(col_)
      read(un) vz%fcum(0:col_%geo%nz, c)
    end associate
  end do
  do z = 1, nzn
    read(un) vz%zones(z)%vin, vz%zones(z)%vdrain, vz%zr%zones(z)%vint, vz%zr%zones(z)%vext, &
             vz%zones(z)%vcorr, vz%zones(z)%vstore0, vz%zones(z)%dvlast, vz%zr%zones(z)%vbase
  end do
  if (noc > 0) then
    allocate(oc(1:2, 1:noc), tmp(1:noc))
    read(un) oc
    if (any(oc /= vz%zr%ocell(:, 1:noc))) then
      close(un)
      call par_stop("vz: the outlet cells differ from the saved state "//fname)
    end if
    read(un) tmp, vz%zr%ovcum(1:noc)
    vz%zr%ocarry(1:noc) = tmp
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
