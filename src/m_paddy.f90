module m_paddy
  ! ============ 田んぼダム(水田の落水口の流出抑制。fn_paddy。developer.md §119) ============
  ! 設計の正本は docs/paddy_plan.md。段 1 = 落水口の装置則と、サブグリッドの水田タンク(表現 A)。
  !
  ! 【モデル】セルの水田面積率 a(セル面積に対する割合)を、取組率で「取組なしの通常の落水口」
  !   (種類 1)と「田んぼダムの落水口」(種類 2)に分け(a_1 = a(1 − 取組率)、a_2 = a·取組率)、
  !   種類ごとに湛水深 hp_c(その種類の水田面積の上の水深 m。田面から)のタンクを 1 つ持つ。
  !   セル内の区画はすべて同じ水深とし、落水口は代表区画面積 A_plot ごとに 1 か所: セルの
  !   落水口の数 N_c = a_c·dx·dy/A_plot、セルの流出 N_c·Q_dev(hp_c, h_D)。水田面積あたりの
  !   流出強度 Q_dev/A_plot は格子の大きさによらない(Nihei et al. 2024 の RRI のサブグリッドの
  !   タンクと同じ形。paddy_plan.md §2)。1 ステップ(swflow の直後):
  !     (1) 雨の回収: 水田の上の雨 a·pre·dt/gv を s%h から引き、各タンクに pre·dt を足す
  !         (boundary_h が連続式の後に足した雨と同じ式。m_zonerunoff の zr_recover_rain と同型。
  !         h は負にならない)
  !     (2) 落水: dv = Q_dev(hp_c, h_D)·dt/A_plot。h_D = セルの地表水深(落水口の下流の水位を
  !         田面から測った値)。dv は「流れ始める高さ」までの貯留と、水位差の半分を埋める量で上限
  !         (陽解法の追い越しの防止。§17 の堤防の越流の上限と同じ考え方)
  !     (3) 越流: hp_c が畦畔高を超えた分を地表へ(瞬時。手引きの計算プログラムと同じ扱い)
  !     (4) 減水深: perc·dt を系外へ(台帳に記録)
  !     (5) 地表へ: s%h に Σ a_c·(dv + 越流)/gv を足し、e = z + h を回復する
  !   片方向(段 1): 浸水が水田に入る流れ(逆流・外からの越流)は表さない(h_D ≥ hp_c なら流出 0)。
  !   双方向化には連続式の開いた面積の割合が要る(paddy_plan.md §6)。
  ! 【装置則】(paddy_plan.md §5)落水口 1 か所の流量 Q (m3/s)。H = 湛水深、h_D = 下流の水深。
  !   堰(天端 z、幅 B): 本間公式の形を流量係数 C で一般化(C = 0.525 で本間公式 0.35・0.91。
  !     独自の一般化)。h1 = H − z、h2 = max(h_D − z, 0)。自由 (2/3)C√(2g)B h1^1.5、
  !     h2/h1 ≥ 2/3 で潜り √3 C B h2 √(2g(h1 − h2)) = 自由 × S(r)、S(r) = (3√3/2) r √(1 − r)
  !   三角の切欠き: 自由 (8/15) C tan(θ/2)√(2g) h1^2.5 に同じ S(r) を掛ける(独自の類推)
  !   穴(円・長方形。下端 z_o): 自由流出は開口の弦の幅の積分 C∫b(y)√(2g(H − y))dy(吉川ほか 2010・
  !     宮津ほか 2012)、潜り C A_w √(2g(H − h_D))(A_w = H より下の穴の面積。宮津ほか 2012・2020)。
  !     h_D が穴の下端を超えたら両者の小さい方(カルバートの 3 レジームの min と同じ組み立て。独自)。
  !     円の積分は正規化した G(η) の表(η = (H − z_o)/d ≤ 4。η > 4 は展開)
  !   型 0: 水位調整板の堰、型 1(機能分離型): min(水位調整板の堰, 穴 + 流出量調整板の越流)、
  !   型 2(機能一体型): 穴 + 水位調整板の天端の越流(農林水産省「田んぼダム」の手引き 2026)
  ! 【並列】セル単位で帯の中だけ(owner-compute)。近傍を読まないのでハロ交換なし。台帳の累積は
  !   行ごとの部分和(行は 1 つのランクだけが持つ)を par_sum_rows で集めるので、ランク数・
  !   スレッド数によらない。
  ! 【台帳】タンクのセル面積基底の貯留 s%pdv を calcstat が S(S_surf)に足す。paddy.csv(dt_record
  !   ごと。全ランク同値を rank0 が書く)は雨の回収・落水・越流・減水深の累積(計算開始・再開から)、
  !   種類ごとの貯留・平均湛水深・満水の面積の割合と収支の残差。分布 Hpn・Hpd は m_output が書く。
  !   保存・復元は私有ファイル paddy.dat(契約 5。湛水深の 2 面)。
  ! 【併用】ENC のみ。ネスト(複数インスタンス)・水質・淡塩とは init で停止する。水田のセルは
  !   海・河道(rw)・境界(水位規定・区間流入)・ソース・構造物のセルと、VZ・貯留関数の区画セルに
  !   置けない(雨の回収が boundary_h の式と一致する前提)。面積率は空隙率 gv を超えない。
  !   蒸発散はタンクから引かない(段 4)。
  ! ==========================================================================
  use, intrinsic :: iso_fortran_env, only : real64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_boundary, only : t_boundary
  use m_zonerunoff, only : t_zonerunoff
  use list_paddy, only : t_list_paddy, list_paddy_read, pd_nclass
  use m_fileio, only : fileio_read_matrix
  use m_restart, only : restart_write_cell, restart_read_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : param_default, itoa, es_out
  use m_parallel, only : par_info, par_stop, par_abort, dcp, is_root, par_sum_rows, par_scatter_cell, &
                         par_allreduce_maxi, par_allreduce_sumi
  implicit none
  private
  public :: t_paddy
  public :: m_paddy_init
  public :: m_paddy_calc
  public :: m_paddy_record
  public :: m_paddy_dispose

  integer, parameter :: save_version = 2026112401 ! paddy.dat の形式の版(形式を決めた日 2026-11-24)
  integer, parameter :: nrow = 5                   ! 台帳の行部分和の列数
  real(real64), parameter :: pi8 = 3.14159265358979323846_real64

  !-------------------------------------------
  ! 落水口の装置(種類ごとに 1 つ。高さは田面から m)
  !-------------------------------------------
  type t_pddev
    integer :: kind = 0             ! 0: 水位調整板だけ, 1: 機能分離型, 2: 機能一体型
    real :: zb = 0.0, bb = 0.0      ! 水位調整板の天端の高さ・幅 (m)
    integer :: otype = 1            ! 穴の形 1: 円, 2: 長方形, 3: 三角(型 1・2 のみ)
    real :: od = 0.0                ! 円の径 (m)
    real :: ob = 0.0, oe = 0.0      ! 長方形の幅・高さ (m)
    real :: oang = 0.0              ! 三角の角度 (度)
    real :: oz = 0.0                ! 穴の下端(三角は頂点)の高さ (m)
    real :: zt = -1.0, bt = 0.0     ! 流出量調整板の天端の高さ・越流の幅(型 1。zt < 0 = 越流なし)
    real :: cw = 0.0, co = 0.0      ! 堰・穴の流量係数
    real :: zlow = 0.0              ! 流れ始める高さ (m)
    real :: kwb = 0.0, kwt = 0.0    ! 堰の係数 (2/3)C√(2g)B(水位調整板・流出量調整板)
    real :: ko = 0.0                ! 穴の自由流出の係数(円 C√(2g)d^2.5、長方形 (2/3)C√(2g)b、
                                    !   三角 (8/15)C tan(θ/2)√(2g))
    real :: kos = 0.0               ! 穴の潜りの係数 C√(2g)
  end type

  !-------------------------------------------
  ! 円の穴の正規化した積分 G(η) = ∫_0^min(η,1) 2√(u(1−u)) √(η − u) du の表(0 ≤ η ≤ etamax)
  !-------------------------------------------
  type t_gtab
    integer :: n = 0
    real :: deta = 0.0, etamax = 0.0
    real, allocatable :: v(:)       ! (0:n)
  end type

  !-------------------------------------------
  ! 田んぼダムの状態の容器(t_encflow の成分。init に早期 return 経路があるため全成分
  ! デフォルト初期化。§13)
  !-------------------------------------------
  type t_paddy
    logical :: enabled = .false.
    logical :: initialized = .false.
    logical :: have(1:pd_nclass) = .false.     ! 種類ごとにその水田があるか(全ランク同値)
    type(t_pddev) :: dev(1:pd_nclass)          ! 種類ごとの落水口の装置
    type(t_gtab) :: gt                         ! 円の穴の積分の表(円の穴を使うときだけ)
    real :: aplot = 0.0                        ! 代表区画面積 (m2)
    real :: hlev = 0.0                         ! 畦畔高 (m)
    real :: perc = 0.0                         ! 減水深 (m/s)
    real :: h0(1:pd_nclass) = 0.0              ! 事前の湛水深 (m)
    real, allocatable :: fr1(:,:), fr2(:,:)    ! 種類ごとの面積率(セル面積基底。帯+ハロ)
    real(real64) :: area(1:pd_nclass) = 0.0_real64  ! 種類ごとの水田面積 (m2。全ランク同値)
    real(real64), allocatable :: rows(:,:)     ! (js:je, 1:nrow) 行ごとの量 (m3): 1 雨の回収・2 落水・
                                               !   3 越流・4 減水深(累積)、5 直近のステップの地表への量
    real(real64) :: store0 = 0.0_real64        ! 計算開始(再開)時の貯留 (m3。全ランク同値)
    real(real64) :: dxdy = 0.0_real64          ! セル面積 (m2)
    integer :: un_csv = 0                      ! CSV 装置番号(rank0)
  end type

contains


!----------------------------------------------------------------------
! 初期化(fn_paddy 未指定・f_paddy = 0 なら何もしない)
!   multi: 複数インスタンス(ネスト等)で実行中か(初版は非対応)
!   vzr・sfr: VZ・貯留関数の区画の共通部(有効なら水田のセルとの重なりを検査する)
!----------------------------------------------------------------------
subroutine m_paddy_init(pd, p, g, b, s, multi, vzr, sfr)
  type(t_paddy), intent(out) :: pd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s
  logical, intent(in) :: multi
  type(t_zonerunoff), intent(in) :: vzr, sfr
  type(t_list_paddy) :: list
  integer :: i, j

  if (len_trim(p%fn_paddy) == 0) then
    if (p%f_state_restore > 0) call stop_if_orphan(p)
    return
  end if
  call list_paddy_read(p, list)
  select case (list%f_paddy)
    case (0)
      call par_info("list_paddy: f_paddy=0, the paddy fields (fn_paddy) are not enabled")
      if (p%f_state_restore > 0) call stop_if_orphan(p)
      return
    case (1)
    case default
      call par_stop("list_paddy: f_paddy must be 0 or 1: " // itoa(list%f_paddy))
  end select

  call check_combinations(p, multi)
  pd%dxdy = real(g%dx, real64) * real(g%dy, real64)
  call setup_scalars(pd, list)
  call setup_maps(pd, p, g, b, s, list, vzr, sfr)
  call setup_devices(pd, p, list)

  ! 状態(その種類の水田がある格子だけ確保)と S の台帳の貯留
  allocate(s%pdv(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (pd%have(1)) allocate(s%hpn(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (pd%have(2)) allocate(s%hpd(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (p%f_state_restore > 0) then
    call restore_state(pd, p, s)
  else
    do j = dcp%jsh, dcp%jeh
      do i = dcp%ish, dcp%ieh
        if (pd%have(1)) then
          if (pd%fr1(i,j) > 0.0) s%hpn(i,j) = pd%h0(1)
        end if
        if (pd%have(2)) then
          if (pd%fr2(i,j) > 0.0) s%hpd(i,j) = pd%h0(2)
        end if
      end do
    end do
  end if
  do j = dcp%jsh, dcp%jeh
    do i = dcp%ish, dcp%ieh
      s%pdv(i,j) = cell_store(pd, s, i, j)
    end do
  end do
  s%pd_active = .true.

  allocate(pd%rows(dcp%js:dcp%je, 1:nrow), source = 0.0_real64)
  pd%store0 = total_store(pd, s)
  call report(pd)
  call open_csv(pd, p)
  pd%enabled = .true.
  pd%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 毎ステップ(swflow の直後。VZ・貯留関数の後、地下水の前): 雨の回収・落水・越流・減水深と、
! 地表への受け渡し(e の回復まで)。セル単位で帯の中だけ(ハロ交換なし)
!----------------------------------------------------------------------
subroutine m_paddy_calc(pd, p, g, s)
  type(t_paddy), intent(inout) :: pd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: dt, a, rain, hd, dsur, f, dv, sp, pc, st
  real(real64) :: rr(1:nrow)

  if (.not. pd%enabled) return
  dt = p%dt
  !$omp parallel do schedule(dynamic) private(i, j, a, rain, hd, dsur, f, dv, sp, pc, st, rr)
  do j = dcp%js, dcp%je
    rr(:) = 0.0_real64
    do i = g%wx(1,j), g%wx(2,j)
      a = pd%fr1(i,j) + pd%fr2(i,j)
      if (a <= 0.0) cycle
      ! (1) 雨の回収(boundary_h が足した雨のうち水田の上に降った分)
      rain = s%pre(i,j) * dt
      s%h(i,j) = s%h(i,j) - a * rain / s%gv(i,j)
      hd = max(s%h(i,j), 0.0)
      dsur = 0.0
      st = 0.0
      ! (2)〜(4) 種類ごとのタンク
      if (pd%have(1)) then
        f = pd%fr1(i,j)
        if (f > 0.0) then
          call tank_step(pd, pd%dev(1), s%hpn(i,j), a / s%gv(i,j), rain, hd, dt, dv, sp, pc)
          dsur = dsur + f * (dv + sp)
          st = st + f * s%hpn(i,j)
          rr(2) = rr(2) + real(f * dv, real64)
          rr(3) = rr(3) + real(f * sp, real64)
          rr(4) = rr(4) + real(f * pc, real64)
        end if
      end if
      if (pd%have(2)) then
        f = pd%fr2(i,j)
        if (f > 0.0) then
          call tank_step(pd, pd%dev(2), s%hpd(i,j), a / s%gv(i,j), rain, hd, dt, dv, sp, pc)
          dsur = dsur + f * (dv + sp)
          st = st + f * s%hpd(i,j)
          rr(2) = rr(2) + real(f * dv, real64)
          rr(3) = rr(3) + real(f * sp, real64)
          rr(4) = rr(4) + real(f * pc, real64)
        end if
      end if
      rr(1) = rr(1) + real(a * rain, real64)
      rr(5) = rr(5) + real(dsur, real64)
      ! (5) 地表へ(落水と越流)。e の回復(契約 2)
      s%h(i,j) = s%h(i,j) + dsur / s%gv(i,j)
      s%e(i,j) = s%z(i,j) + s%h(i,j)
      s%pdv(i,j) = st
    end do
    pd%rows(j,1:4) = pd%rows(j,1:4) + rr(1:4) * pd%dxdy
    pd%rows(j,5) = rr(5) * pd%dxdy
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 台帳 paddy.csv(dt_record ごと。集計は collective = 全ランクが同じ順で呼ぶ。rank0 が書く)
!   rain・outflow・spill・perc: 計算開始(再開)からの累積 (m3)、store1・store2: 種類ごとの現在の
!   貯留 (m3)、residual: 貯留の変化 − (雨 − 落水 − 越流 − 減水深)、qsurf: 直近のステップに地表へ
!   渡した量の速さ (m3/s)、h1・h2: 種類ごとの平均湛水深 (mm)、full1・full2: 畦畔高まで満ちた
!   水田面積の割合
!----------------------------------------------------------------------
subroutine m_paddy_record(pd, p, g, s)
  type(t_paddy), intent(in) :: pd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64) :: tot(1:nrow), st(1:2), fu(1:2), res, hm(1:2), ff(1:2)
  real(real64), allocatable :: r1(:), srow(:,:)
  real :: hfull
  integer :: i, j, k

  if (.not. pd%enabled) return
  allocate(r1(dcp%js:dcp%je))
  do k = 1, nrow
    r1(:) = pd%rows(:,k)
    call par_sum_rows(r1, tot(k))
  end do
  ! 種類ごとの貯留と、畦畔高まで満ちた水田の面積(行部分和)
  hfull = pd%hlev * (1.0 - 1.0e-6)
  allocate(srow(dcp%js:dcp%je, 1:4), source = 0.0_real64)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (pd%have(1)) then
        if (pd%fr1(i,j) > 0.0) then
          srow(j,1) = srow(j,1) + real(pd%fr1(i,j) * s%hpn(i,j), real64)
          if (s%hpn(i,j) >= hfull) srow(j,3) = srow(j,3) + real(pd%fr1(i,j), real64)
        end if
      end if
      if (pd%have(2)) then
        if (pd%fr2(i,j) > 0.0) then
          srow(j,2) = srow(j,2) + real(pd%fr2(i,j) * s%hpd(i,j), real64)
          if (s%hpd(i,j) >= hfull) srow(j,4) = srow(j,4) + real(pd%fr2(i,j), real64)
        end if
      end if
    end do
  end do
  do k = 1, 2
    r1(:) = srow(:,k)
    call par_sum_rows(r1, st(k))
    st(k) = st(k) * pd%dxdy
    r1(:) = srow(:,k+2)
    call par_sum_rows(r1, fu(k))
    fu(k) = fu(k) * pd%dxdy
  end do
  if (.not. is_root) return
  res = (st(1) + st(2)) - pd%store0 - (tot(1) - tot(2) - tot(3) - tot(4))
  do k = 1, 2
    hm(k) = 0.0_real64
    ff(k) = 0.0_real64
    if (pd%area(k) > 0.0_real64) then
      hm(k) = st(k) / pd%area(k) * 1.0e3_real64
      ff(k) = fu(k) / pd%area(k)
    end if
  end do
  write(pd%un_csv, '(f0.2,14(",",es23.15))') s%t, &
        es_out([pd%area(1), pd%area(2), tot(1), tot(2), tot(3), tot(4), st(1), st(2), res, &
                tot(5) / real(p%dt, real64), hm(1), hm(2), ff(1), ff(2)])
  flush(pd%un_csv)
end subroutine


!----------------------------------------------------------------------
! 破棄(save は dispose で。契約 5)
!----------------------------------------------------------------------
subroutine m_paddy_dispose(pd, p, s)
  type(t_paddy), intent(inout) :: pd
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  if (.not. pd%enabled) return
  if (p%f_state_save > 0) call save_state(pd, p, s)
  if (is_root .and. pd%un_csv /= 0) close(pd%un_csv)
  pd%un_csv = 0
  if (allocated(pd%fr1)) deallocate(pd%fr1)
  if (allocated(pd%fr2)) deallocate(pd%fr2)
  if (allocated(pd%rows)) deallocate(pd%rows)
  if (allocated(pd%gt%v)) deallocate(pd%gt%v)
  s%pd_active = .false.
  pd%enabled = .false.
  pd%initialized = .false.
end subroutine


!======================================================================
!========================= PRIVATE ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 1 つのタンクの 1 ステップ(雨を足した後の落水・越流・減水深)
!   hp: 湛水深 (m。更新して返す)、ag: 水田面積率の合計 / gv(地表の水位の上がり方の換算)、
!   rain: 雨 pre·dt (m)、hd: 下流の水深 (m)、dv・sp・pc: 落水・越流・減水深 (m。水田面積基底)
!----------------------------------------------------------------------
subroutine tank_step(pd, dev, hp, ag, rain, hd, dt, dv, sp, pc)
  type(t_paddy), intent(in) :: pd
  type(t_pddev), intent(in) :: dev
  real, intent(inout) :: hp
  real, intent(in) :: ag, rain, hd, dt
  real, intent(out) :: dv, sp, pc
  hp = hp + rain
  dv = dev_q(dev, pd%gt, hp, hd) * dt / pd%aplot
  ! 上限: 流れ始める高さまでの貯留と、下流との水位差の半分を埋める量(追い越しの防止)
  dv = min(dv, max(hp - dev%zlow, 0.0), 0.5 * max(hp - hd, 0.0) / (1.0 + ag))
  hp = hp - dv
  sp = max(hp - pd%hlev, 0.0)
  hp = hp - sp
  pc = min(pd%perc * dt, hp)
  hp = hp - pc
end subroutine


!----------------------------------------------------------------------
! 落水口 1 か所の流量 (m3/s)。h: 田面からの湛水深、hd: 同じ基準の下流の水深(片方向: hd ≥ h なら 0)
!----------------------------------------------------------------------
pure real function dev_q(dev, gt, h, hd) result(q)
  type(t_pddev), intent(in) :: dev
  type(t_gtab), intent(in) :: gt
  real, intent(in) :: h, hd
  real :: qt
  q = 0.0
  if (h <= dev%zlow .or. hd >= h) return
  select case (dev%kind)
    case (0)
      q = weir_q(dev%kwb, dev%zb, h, hd)
    case (1)
      qt = 0.0
      if (dev%zt >= 0.0) qt = weir_q(dev%kwt, dev%zt, h, hd)
      q = min(weir_q(dev%kwb, dev%zb, h, hd), open_q(dev, gt, h, hd) + qt)
    case (2)
      q = open_q(dev, gt, h, hd) + weir_q(dev%kwb, dev%zb, h, hd)
  end select
end function


!----------------------------------------------------------------------
! 四角セキ(係数 k = (2/3)C√(2g)B、天端 z)。h2/h1 ≥ 2/3 で潜り(本間公式の形)
!----------------------------------------------------------------------
pure real function weir_q(k, z, h, hd) result(q)
  real, intent(in) :: k, z, h, hd
  real :: h1, h2
  q = 0.0
  h1 = h - z
  if (h1 <= 0.0) return
  h2 = max(hd - z, 0.0)
  if (h2 >= h1) return
  q = k * h1 * sqrt(h1)
  if (h2 > h1 * (2.0 / 3.0)) q = q * sub_ratio(h2 / h1)
end function


!----------------------------------------------------------------------
! 潜り越流と自由越流の比 S(r) = (3√3/2) r √(1 − r)(r = h2/h1 ≥ 2/3。r = 2/3 で 1、r = 1 で 0)
!----------------------------------------------------------------------
pure real function sub_ratio(r)
  real, intent(in) :: r
  sub_ratio = 1.5 * sqrt(3.0) * r * sqrt(max(1.0 - r, 0.0))
end function


!----------------------------------------------------------------------
! 穴(円・長方形・三角)の流量。自由流出は開口の積分、潜りは C A_w √(2g(H − h_D)) との小さい方
!----------------------------------------------------------------------
pure real function open_q(dev, gt, h, hd) result(q)
  type(t_pddev), intent(in) :: dev
  type(t_gtab), intent(in) :: gt
  real, intent(in) :: h, hd
  real :: hh, eta, qf, qs, h2
  q = 0.0
  hh = h - dev%oz
  if (hh <= 0.0) return
  select case (dev%otype)
    case (1)      ! 円
      eta = hh / dev%od
      qf = dev%ko * gfun(gt, eta)
      if (hd > dev%oz) then
        qs = dev%kos * dev%od**2 * seg_area(min(eta, 1.0)) * sqrt(h - hd)
        q = min(qf, qs)
      else
        q = qf
      end if
    case (2)      ! 長方形(幅 ob・高さ oe)
      qf = dev%ko * (hh * sqrt(hh) - max(hh - dev%oe, 0.0) * sqrt(max(hh - dev%oe, 0.0)))
      if (hd > dev%oz) then
        qs = dev%kos * dev%ob * min(hh, dev%oe) * sqrt(h - hd)
        q = min(qf, qs)
      else
        q = qf
      end if
    case (3)      ! 三角(V 字の切欠き。頂点 oz)
      q = dev%ko * hh * hh * sqrt(hh)
      h2 = max(hd - dev%oz, 0.0)
      if (h2 > hh * (2.0 / 3.0)) q = q * sub_ratio(h2 / hh)
  end select
end function


!----------------------------------------------------------------------
! 直径 1 の円の、下端から高さ t(0〜1)までの部分の面積 = ∫_0^t 2√(u(1−u)) du
!----------------------------------------------------------------------
pure real function seg_area(t)
  real, intent(in) :: t
  real :: tt
  tt = min(max(t, 0.0), 1.0)
  seg_area = 0.25 * acos(1.0 - 2.0 * tt) - (0.5 - tt) * sqrt(max(tt - tt * tt, 0.0))
end function


!----------------------------------------------------------------------
! G(η)(表の線形補間。η > etamax は (π/4)√s の展開、s = η − 1/2)
!----------------------------------------------------------------------
pure real function gfun(gt, eta)
  type(t_gtab), intent(in) :: gt
  real, intent(in) :: eta
  real :: x, w, sv, is2
  integer :: k
  if (eta >= gt%etamax) then
    sv = eta - 0.5
    is2 = 1.0 / (sv * sv)
    gfun = 0.25 * real(pi8) * sqrt(sv) * (1.0 - is2 * (1.0 / 128.0 + is2 * (20.0 / 65536.0 &
           + is2 * (140.0 / 4194304.0))))
  else
    x = max(eta, 0.0) / gt%deta
    k = min(int(x), gt%n - 1)
    w = x - real(k)
    gfun = (1.0 - w) * gt%v(k) + w * gt%v(k + 1)
  end if
end function


!----------------------------------------------------------------------
! G(η) の表を作る(全ランクが同じ演算で冗長に)。積分は u = (1 − cos θ)/2、θ = θm(1 − v²) で
! 両端の特異性を除いた滑らかな被積分関数を複合 Simpson(256 区間)で
!----------------------------------------------------------------------
subroutine build_gtab(gt)
  type(t_gtab), intent(inout) :: gt
  integer, parameter :: n = 8192
  integer :: k
  gt%n = n
  gt%etamax = 4.0
  gt%deta = gt%etamax / real(n)
  allocate(gt%v(0:n))
  do k = 0, n
    gt%v(k) = real(gquad(real(k, real64) * real(gt%deta, real64)))
  end do
end subroutine


real(real64) function gquad(eta)
  real(real64), intent(in) :: eta
  integer, parameter :: m = 256
  integer :: i
  real(real64) :: um, tm, v, th, u, f, w, sm
  gquad = 0.0_real64
  if (eta <= 0.0_real64) return
  um = min(eta, 1.0_real64)
  tm = acos(1.0_real64 - 2.0_real64 * um)
  sm = 0.0_real64
  do i = 0, m
    v = real(i, real64) / real(m, real64)
    th = tm * (1.0_real64 - v * v)
    u = 0.5_real64 * (1.0_real64 - cos(th))
    f = 0.5_real64 * sin(th)**2 * sqrt(max(eta - u, 0.0_real64)) * 2.0_real64 * tm * v
    if (i == 0 .or. i == m) then
      w = 1.0_real64
    else if (mod(i, 2) == 1) then
      w = 4.0_real64
    else
      w = 2.0_real64
    end if
    sm = sm + w * f
  end do
  gquad = sm / (3.0_real64 * real(m, real64))
end function


!----------------------------------------------------------------------
! 初版で併用できない機能・実行形態を停止する
!----------------------------------------------------------------------
subroutine check_combinations(p, multi)
  type(t_sysparam), intent(in) :: p
  logical, intent(in) :: multi
  call no_combo(p%fn_wq, "fn_wq", "the paddy tanks do not carry solutes yet")
  call no_combo(p%fn_salt, "fn_salt", "the paddy tanks do not interact with the saltwater layers")
  call no_combo(p%fn_nest, "fn_nest", "nesting is not supported by fn_paddy yet")
  if (multi) call par_stop("list_paddy: multiple instances (nesting) are not supported by fn_paddy yet")
  if (p%f_gridsystem /= 0) call par_stop("list_paddy: fn_paddy requires f_gridsystem=0 (ENC)")
contains
  subroutine no_combo(fn, name, why)
    character(len=*), intent(in) :: fn, name, why
    if (len_trim(fn) > 0) call par_stop("list_paddy: fn_paddy cannot be combined with "//name//" ("//why//")")
  end subroutine
end subroutine


!----------------------------------------------------------------------
! スカラーの設定(既定は採用値を "(default)" 付きで表示。§62)。既定値の出典: 区画面積 30 a・
! 畦畔高 0.30 m・減水深 5 mm/d は農林水産省「田んぼダム」の手引き(2026 改訂)の例と計算プログラムの
! 既定(paddy_plan.md §6・§11)
!----------------------------------------------------------------------
subroutine setup_scalars(pd, list)
  type(t_paddy), intent(inout) :: pd
  type(t_list_paddy), intent(in) :: list
  real :: v
  pd%aplot = param_default("paddy", "pd_aplot", list%pd_aplot, 3000.0, " m2", unset = -9999.0)
  if (.not. (pd%aplot > 0.0)) call par_stop("list_paddy: pd_aplot must be > 0 (m2)")
  pd%hlev = param_default("paddy", "pd_hlev", list%pd_hlev, 0.30, " m", unset = -9999.0)
  if (.not. (pd%hlev > 0.0)) call par_stop("list_paddy: pd_hlev must be > 0 (m)")
  v = param_default("paddy", "pd_perc_mmd", list%pd_perc_mmd, 5.0, " mm/d", unset = -9999.0)
  if (.not. (v >= 0.0)) call par_stop("list_paddy: pd_perc_mmd must be >= 0 (mm/d)")
  pd%perc = v / 1000.0 / 86400.0
  if (list%pd_h0 > -9998.0) then
    if (.not. (list%pd_h0 >= 0.0 .and. list%pd_h0 <= pd%hlev)) then
      call par_stop("list_paddy: pd_h0 must satisfy 0 <= pd_h0 <= pd_hlev (m)")
    end if
  end if
end subroutine


!----------------------------------------------------------------------
! 装置の設定(その種類の水田がある格子では、その種類だけ。既定は採用値を "(default)" 付きで
! 表示。§62)。既定値の出典: 堰幅 0.30 m・穴 φ50・V 字 60°・流量係数 0.6 は農林水産省「田んぼダム」の
! 手引き(2026 改訂)の例と計算プログラムの既定、水位調整板の天端 0.03 m は同プログラムの既定
! (皆川・宮津 2022 も同じ)。型の既定は種類 1 = 0(水位調整板だけ)、種類 2 = 1(機能分離型)。
! paddy_plan.md §5・§6・§11
!----------------------------------------------------------------------
subroutine setup_devices(pd, p, list)
  type(t_paddy), intent(inout) :: pd
  type(t_sysparam), intent(in) :: p
  type(t_list_paddy), intent(in) :: list
  integer, parameter :: kind_default(1:2) = [0, 1]
  integer :: c, kk
  real :: h0
  character(len=8) :: tg
  character(len=256) :: line
  logical :: need_circle

  need_circle = .false.
  do c = 1, pd_nclass
    if (.not. pd%have(c)) cycle
    write(tg, '("(",i0,")")') c
    associate (dv => pd%dev(c))
      kk = list%pd_dev_type(c)
      if (kk <= -9998) then
        kk = kind_default(c)
        call par_info("paddy: pd_dev_type"//trim(tg)//" = "//itoa(kk)//" (default)")
      else
        call par_info("paddy: pd_dev_type"//trim(tg)//" = "//itoa(kk))
      end if
      if (kk < 0 .or. kk > 2) then
        call par_stop("list_paddy: pd_dev_type"//trim(tg)//" must be 0(water-level board only), " &
                      //"1(separated type) or 2(integrated type): "//itoa(kk))
      end if
      dv%kind = kk
      dv%zb = param_default("paddy", "pd_board_h"//trim(tg), list%pd_board_h(c), 0.03, " m", unset = -9999.0)
      dv%bb = param_default("paddy", "pd_board_w"//trim(tg), list%pd_board_w(c), 0.30, " m", unset = -9999.0)
      dv%cw = param_default("paddy", "pd_cw"//trim(tg), list%pd_cw(c), 0.6, "", unset = -9999.0)
      if (.not. (dv%zb >= 0.0)) call par_stop("list_paddy: pd_board_h"//trim(tg)//" must be >= 0 (m)")
      if (.not. (dv%bb > 0.0)) call par_stop("list_paddy: pd_board_w"//trim(tg)//" must be > 0 (m)")
      if (.not. (dv%cw > 0.0 .and. dv%cw <= 2.0)) call par_stop("list_paddy: pd_cw"//trim(tg)//" must satisfy 0 < C <= 2")
      dv%kwb = (2.0 / 3.0) * dv%cw * sqrt(2.0 * p%gg) * dv%bb
      if (kk >= 1) then
        if (list%pd_open_type(c) <= -9998) then
          dv%otype = 1
          call par_info("paddy: pd_open_type"//trim(tg)//" = 1 (default)")
        else
          dv%otype = list%pd_open_type(c)
          call par_info("paddy: pd_open_type"//trim(tg)//" = "//itoa(dv%otype))
        end if
        dv%co = param_default("paddy", "pd_co"//trim(tg), list%pd_co(c), 0.6, "", unset = -9999.0)
        if (.not. (dv%co > 0.0 .and. dv%co <= 2.0)) call par_stop("list_paddy: pd_co"//trim(tg)//" must satisfy 0 < C <= 2")
        dv%kos = dv%co * sqrt(2.0 * p%gg)
        dv%oz = param_default("paddy", "pd_open_z"//trim(tg), list%pd_open_z(c), 0.0, " m", unset = -9999.0)
        if (.not. (dv%oz >= 0.0)) call par_stop("list_paddy: pd_open_z"//trim(tg)//" must be >= 0 (m)")
        select case (dv%otype)
          case (1)
            dv%od = param_default("paddy", "pd_open_d"//trim(tg), list%pd_open_d(c), 0.05, " m", unset = -9999.0)
            if (.not. (dv%od > 0.0)) call par_stop("list_paddy: pd_open_d"//trim(tg)//" must be > 0 (m)")
            dv%ko = dv%co * sqrt(2.0 * p%gg) * dv%od**2 * sqrt(dv%od)
            need_circle = .true.
          case (2)
            if (list%pd_open_b(c) <= -9998.0 .or. list%pd_open_e(c) <= -9998.0) then
              call par_stop("list_paddy: pd_open_type"//trim(tg)//"=2 (rectangle) requires pd_open_b"//trim(tg) &
                            //" and pd_open_e"//trim(tg))
            end if
            dv%ob = param_default("paddy", "pd_open_b"//trim(tg), list%pd_open_b(c), 0.0, " m", unset = -9999.0)
            dv%oe = param_default("paddy", "pd_open_e"//trim(tg), list%pd_open_e(c), 0.0, " m", unset = -9999.0)
            if (.not. (dv%ob > 0.0 .and. dv%oe > 0.0)) then
              call par_stop("list_paddy: pd_open_b"//trim(tg)//" and pd_open_e"//trim(tg)//" must be > 0 (m)")
            end if
            dv%ko = (2.0 / 3.0) * dv%co * sqrt(2.0 * p%gg) * dv%ob
          case (3)
            dv%oang = param_default("paddy", "pd_open_ang"//trim(tg), list%pd_open_ang(c), 60.0, " degree", &
                                    unset = -9999.0)
            if (.not. (dv%oang > 0.0 .and. dv%oang < 180.0)) then
              call par_stop("list_paddy: pd_open_ang"//trim(tg)//" must satisfy 0 < angle < 180 (degree)")
            end if
            dv%ko = (8.0 / 15.0) * dv%co * tan(0.5 * dv%oang * real(pi8) / 180.0) * sqrt(2.0 * p%gg)
          case default
            call par_stop("list_paddy: pd_open_type"//trim(tg)//" must be 1(circle), 2(rectangle) or " &
                          //"3(triangle): "//itoa(dv%otype))
        end select
      end if
      if (kk == 1) then
        if (list%pd_plate_h(c) > -9998.0) then
          dv%zt = param_default("paddy", "pd_plate_h"//trim(tg), list%pd_plate_h(c), 0.0, " m", unset = -9999.0)
          if (.not. (dv%zt >= 0.0)) call par_stop("list_paddy: pd_plate_h"//trim(tg)//" must be >= 0 (m)")
          dv%bt = param_default("paddy", "pd_plate_w"//trim(tg), list%pd_plate_w(c), dv%bb, " m", unset = -9999.0)
          if (.not. (dv%bt > 0.0)) call par_stop("list_paddy: pd_plate_w"//trim(tg)//" must be > 0 (m)")
          dv%kwt = (2.0 / 3.0) * dv%cw * sqrt(2.0 * p%gg) * dv%bt
        else if (list%pd_plate_w(c) > -9998.0) then
          call par_stop("list_paddy: pd_plate_w"//trim(tg)//" requires pd_plate_h"//trim(tg))
        end if
      else if (list%pd_plate_h(c) > -9998.0 .or. list%pd_plate_w(c) > -9998.0) then
        call par_stop("list_paddy: pd_plate_h"//trim(tg)//" and pd_plate_w"//trim(tg)//" are for the separated " &
                      //"type (pd_dev_type"//trim(tg)//"=1) only")
      end if
      if (kk == 0 .and. (list%pd_open_type(c) > -9998 .or. list%pd_open_d(c) > -9998.0 .or. &
          list%pd_open_b(c) > -9998.0 .or. list%pd_open_e(c) > -9998.0 .or. list%pd_open_ang(c) > -9998.0 &
          .or. list%pd_open_z(c) > -9998.0 .or. list%pd_co(c) > -9998.0)) then
        call par_info("paddy: the opening parameters of class "//itoa(c)//" are not used (pd_dev_type"//trim(tg) &
                      //"=0 has no opening)")
      end if
      if (kk == 2 .and. .not. (dv%oz < dv%zb)) then
        call par_stop("list_paddy: the opening of the integrated type must be below the board crest " &
                      //"(pd_open_z"//trim(tg)//" < pd_board_h"//trim(tg)//")")
      end if
      ! 流れ始める高さ
      select case (kk)
        case (0)
          dv%zlow = dv%zb
        case (1)
          if (dv%zt >= 0.0) then
            dv%zlow = max(dv%zb, min(dv%oz, dv%zt))
          else
            dv%zlow = max(dv%zb, dv%oz)
          end if
        case (2)
          dv%zlow = min(dv%oz, dv%zb)
      end select
      if (.not. (dv%zlow < pd%hlev)) then
        call par_stop("list_paddy: the outlet of class "//itoa(c)//" starts to drain only above the levee " &
                      //"height pd_hlev (check pd_board_h, pd_open_z and pd_plate_h)")
      end if
      ! 事前の湛水深(既定 = 流れ始める高さ)
      if (list%pd_h0 <= -9998.0) then
        h0 = dv%zlow
        write(line, '(a,g0.6,a)') "paddy: initial ponding depth of class "//itoa(c)//" = ", h0, &
                                  " m (default: the level at which the outlet starts to drain)"
        call par_info(trim(line))
      else
        h0 = list%pd_h0
      end if
      pd%h0(c) = h0
    end associate
  end do
  if (list%pd_h0 > -9998.0) then
    write(line, '(a,g0.6,a)') "paddy: pd_h0 = ", list%pd_h0, " m"
    call par_info(trim(line))
  end if
  if (need_circle) call build_gtab(pd%gt)
end subroutine


!----------------------------------------------------------------------
! 水田面積率・取組率の分布(rank0 が読み、全域で検査して帯へ配る)と、帯の検査・種類の有無・面積
!----------------------------------------------------------------------
subroutine setup_maps(pd, p, g, b, s, list, vzr, sfr)
  type(t_paddy), intent(inout) :: pd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(in) :: s
  type(t_list_paddy), intent(in) :: list
  type(t_zonerunoff), intent(in) :: vzr, sfr
  real, allocatable :: wf(:,:), wa(:,:), w1(:,:), w2(:,:)
  integer, allocatable :: mk(:,:)
  real :: dum(1,1), fa
  integer :: i, j, k, n, ierr, ie, je, nbad, ib, jb, key
  integer :: hv(1:pd_nclass)
  real(real64), allocatable :: r1(:), r2(:)
  character(len=512) :: msg

  ! --- 面積率と取組率の指定(分布と一様値は排他) ---
  if (len_trim(list%fn_pd_frac) > 0 .and. list%pd_frac > -9998.0) then
    call par_stop("list_paddy: specify only one of fn_pd_frac and pd_frac")
  end if
  if (len_trim(list%fn_pd_frac) == 0 .and. list%pd_frac <= -9998.0) then
    call par_stop("list_paddy: the paddy area fraction is required (fn_pd_frac or pd_frac)")
  end if
  if (len_trim(list%fn_pd_adopt) > 0 .and. list%pd_adopt > -9998.0) then
    call par_stop("list_paddy: specify only one of fn_pd_adopt and pd_adopt")
  end if
  if (list%pd_frac > -9998.0) then
    fa = param_default("paddy", "pd_frac", list%pd_frac, 0.0, "", unset = -9999.0)
    if (.not. (fa >= 0.0 .and. fa <= 1.0)) call par_stop("list_paddy: pd_frac must satisfy 0 <= a <= 1")
  end if
  if (len_trim(list%fn_pd_adopt) == 0) then
    fa = param_default("paddy", "pd_adopt", list%pd_adopt, 0.0, "", unset = -9999.0)
    if (.not. (fa >= 0.0 .and. fa <= 1.0)) call par_stop("list_paddy: pd_adopt must satisfy 0 <= r <= 1")
  end if

  ! --- rank0: 全域で読み、検査し、種類ごとの面積率を作る ---
  ierr = 0
  ie = 0
  je = 0
  if (is_root) then
    allocate(wf(1:g%nx, 1:g%ny), wa(1:g%nx, 1:g%ny), w1(1:g%nx, 1:g%ny), w2(1:g%nx, 1:g%ny))
    if (len_trim(list%fn_pd_frac) > 0) then
      call read_full(p, g, list%fn_pd_frac, wf)
    else
      wf(:,:) = list%pd_frac
    end if
    if (len_trim(list%fn_pd_adopt) > 0) then
      call read_full(p, g, list%fn_pd_adopt, wa)
    else
      wa(:,:) = max(list%pd_adopt, 0.0)
    end if
    ! 境界・ソース・構造物のセルの印(水田のセルに置けない)
    allocate(mk(1:g%nx, 1:g%ny), source = 0)
    do k = 1, b%nsrc
      do n = 1, b%src(k)%ncell
        call mark(b%src(k)%cell(1,n), b%src(k)%cell(2,n))
      end do
    end do
    do k = 1, b%nstage
      do n = 1, b%stage(k)%ncell
        call mark(b%stage(k)%cell(1,n), b%stage(k)%cell(2,n))
      end do
    end do
    do k = 1, b%ninflow
      do n = 1, b%inflow(k)%ncell
        call mark(b%inflow(k)%cell(1,n), b%inflow(k)%cell(2,n))
      end do
    end do
    do k = 1, b%nstruct
      do n = 1, b%struct(k)%ncin
        call mark(b%struct(k)%cin(1,n), b%struct(k)%cin(2,n))
      end do
      do n = 1, b%struct(k)%ncout
        call mark(b%struct(k)%cout(1,n), b%struct(k)%cout(2,n))
      end do
    end do
    do j = 1, g%ny
      do i = 1, g%nx
        w1(i,j) = 0.0
        w2(i,j) = 0.0
        if (g%x(i,j) <= 0) cycle
        if (ierr == 0) then
          if (.not. (wf(i,j) >= 0.0 .and. wf(i,j) <= 1.0)) then
            ierr = 1
          else if (.not. (wa(i,j) >= 0.0 .and. wa(i,j) <= 1.0)) then
            ierr = 2
          else if (wf(i,j) > 0.0 .and. g%sw(i,j) > 0) then
            ierr = 3
          else if (wf(i,j) > 0.0 .and. g%rw(i,j) > 0) then
            ierr = 4
          else if (wf(i,j) > 0.0 .and. mk(i,j) > 0) then
            ierr = 5
          end if
          if (ierr > 0) then
            ie = i
            je = j
          end if
        end if
        if (wf(i,j) > 0.0) then
          w1(i,j) = wf(i,j) * (1.0 - wa(i,j))
          w2(i,j) = wf(i,j) * wa(i,j)
        end if
      end do
    end do
  end if
  call par_allreduce_maxi(ierr)
  call par_allreduce_maxi(ie)
  call par_allreduce_maxi(je)
  if (ierr > 0) then
    select case (ierr)
      case (1)
        msg = "paddy: the paddy area fraction must satisfy 0 <= a <= 1"
      case (2)
        msg = "paddy: the adoption ratio must satisfy 0 <= r <= 1"
      case (3)
        msg = "paddy: a paddy cell is on a sea cell"
      case (4)
        msg = "paddy: a paddy cell is on a channel cell (rw); set the fraction to 0 there (the channel cell " &
              //"represents the channel only)"
      case default
        msg = "paddy: a paddy cell overlaps a boundary, source or structure cell"
    end select
    call par_stop(trim(msg)//" at ("//itoa(ie)//","//itoa(je)//")")
  end if

  ! --- 帯へ配る ---
  allocate(pd%fr1(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(pd%fr2(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (is_root) then
    call par_scatter_cell(w1, pd%fr1)
    call par_scatter_cell(w2, pd%fr2)
  else
    call par_scatter_cell(dum, pd%fr1)
    call par_scatter_cell(dum, pd%fr2)
  end if

  ! --- 帯の検査: 面積率 ≤ 空隙率、VZ・貯留関数の区画と重ならない(collective に停止) ---
  nbad = 0
  ib = 0
  jb = 0
  key = 0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      fa = pd%fr1(i,j) + pd%fr2(i,j)
      if (fa <= 0.0) cycle
      k = 0
      if (fa > s%gv(i,j) * (1.0 + 1.0e-6)) k = 1
      if (allocated(vzr%zid)) then
        if (vzr%zid(i,j) > 0) k = 2
      end if
      if (allocated(sfr%zid)) then
        if (sfr%zid(i,j) > 0) k = 3
      end if
      if (k > nbad) then
        nbad = k
        ib = i
        jb = j
      end if
    end do
  end do
  ! 誤りの種類と例のセルを 1 つの整数にまとめて全ランクの最大をとる(種類と場所が同じセルから来る)
  if (nbad > 0) key = nbad * (g%nx * g%ny) + (jb - 1) * g%nx + (ib - 1)
  call par_allreduce_maxi(key)
  if (key > 0) then
    nbad = key / (g%nx * g%ny)
    ib = mod(key, g%nx * g%ny)
    jb = ib / g%nx + 1
    ib = mod(ib, g%nx) + 1
    select case (nbad)
      case (1)
        msg = "paddy: the paddy area fraction exceeds the void ratio gv (buildings) of the cell"
      case (2)
        msg = "paddy: a paddy cell is a VZ zone cell (both would take the rain of the cell)"
      case default
        msg = "paddy: a paddy cell is a SFM zone cell (both would take the rain of the cell)"
    end select
    call par_stop(trim(msg)//" (e.g. at ("//itoa(ib)//","//itoa(jb)//"))")
  end if

  ! --- 種類の有無と面積(全ランク同値) ---
  hv(:) = 0
  allocate(r1(dcp%js:dcp%je), r2(dcp%js:dcp%je), source = 0.0_real64)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (pd%fr1(i,j) > 0.0) then
        hv(1) = 1
        r1(j) = r1(j) + real(pd%fr1(i,j), real64)
      end if
      if (pd%fr2(i,j) > 0.0) then
        hv(2) = 1
        r2(j) = r2(j) + real(pd%fr2(i,j), real64)
      end if
    end do
  end do
  call par_allreduce_sumi(hv)
  pd%have(:) = hv(:) > 0
  call par_sum_rows(r1, pd%area(1))
  call par_sum_rows(r2, pd%area(2))
  pd%area(:) = pd%area(:) * pd%dxdy
  if (.not. any(pd%have)) call par_stop("paddy: no paddy cell in the domain (the fraction is 0 everywhere)")
contains
  subroutine mark(ii, jj)
    integer, intent(in) :: ii, jj
    if (ii < 1 .or. ii > g%nx .or. jj < 1 .or. jj > g%ny) return
    mk(ii,jj) = 1
  end subroutine
end subroutine


!----------------------------------------------------------------------
! 分布ラスタを rank0 で全域形に読む(dir_data 起点)
!----------------------------------------------------------------------
subroutine read_full(p, g, fn, a)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn
  real, intent(inout) :: a(1:, 1:)
  character(:), allocatable :: fname
  logical :: found
  fname = trim(p%dir_data)//"/"//trim(fn)
  inquire(file=fname, exist=found)
  if (.not. found) call par_abort("list_paddy: file not found: "//fname)
  call par_info(" reading "//fname)
  call fileio_read_matrix(fname, g%nx, g%ny, a, p%f_input_mode)
end subroutine


!----------------------------------------------------------------------
! セルの水田の貯留 (m。セル面積基底)
!----------------------------------------------------------------------
real function cell_store(pd, s, i, j)
  type(t_paddy), intent(in) :: pd
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  cell_store = 0.0
  if (pd%have(1)) cell_store = cell_store + pd%fr1(i,j) * s%hpn(i,j)
  if (pd%have(2)) cell_store = cell_store + pd%fr2(i,j) * s%hpd(i,j)
end function


!----------------------------------------------------------------------
! 全水田の貯留 (m3。行部分和の決定的総和。collective)
!----------------------------------------------------------------------
real(real64) function total_store(pd, s)
  type(t_paddy), intent(in) :: pd
  type(t_state), intent(in) :: s
  real(real64), allocatable :: r1(:)
  integer :: j
  allocate(r1(dcp%js:dcp%je), source = 0.0_real64)
  do j = dcp%js, dcp%je
    r1(j) = sum(real(s%pdv(dcp%ish:dcp%ieh, j), real64))
  end do
  call par_sum_rows(r1, total_store)
  total_store = total_store * pd%dxdy
end function


!----------------------------------------------------------------------
! 設定の確認表(初期化時に画面へ)
!----------------------------------------------------------------------
subroutine report(pd)
  type(t_paddy), intent(in) :: pd
  integer :: c
  real :: hq, q
  character(len=512) :: line
  character(len=32), parameter :: kname(0:2) = [character(len=32) :: "water-level board only", &
                                                "separated type", "integrated type"]
  write(line, '(a,es11.4,a,es11.4,a)') "paddy: paddy area with normal outlets ", pd%area(1), &
        " m2, with paddy-dam outlets ", pd%area(2), " m2"
  call par_info(trim(line))
  do c = 1, pd_nclass
    if (.not. pd%have(c)) cycle
    associate (dv => pd%dev(c))
      hq = pd%hlev
      q = dev_q(dv, pd%gt, hq, 0.0)
      write(line, '(a,i0,a,a,a,g0.4,a,g0.4,a)') "  class ", c, ": ", trim(kname(dv%kind)), &
            ", drains above ", dv%zlow, " m; outflow at the levee crest (free) ", &
            q / pd%aplot * 3.6e6, " mm/h of the paddy area"
      call par_info(trim(line))
    end associate
  end do
end subroutine


!----------------------------------------------------------------------
! CSV を開く(rank0)
!----------------------------------------------------------------------
subroutine open_csv(pd, p)
  type(t_paddy), intent(inout) :: pd
  type(t_sysparam), intent(in) :: p
  if (.not. is_root) return
  open(newunit=pd%un_csv, file=trim(p%dir_result)//"/paddy.csv", status='replace')
  write(pd%un_csv, '(a)') "time(s),area1(m2),area2(m2),rain(m3),outflow(m3),spill(m3),perc(m3),store1(m3)," // &
                          "store2(m3),residual(m3),qsurf(m3/s),h1(mm),h2(mm),full1(-),full2(-)"
end subroutine


!----------------------------------------------------------------------
! 保存(私有ファイル paddy.dat。読み並びは restore_state と対。collective)
!----------------------------------------------------------------------
subroutine save_state(pd, p, s)
  type(t_paddy), intent(in) :: pd
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  integer :: un
  un = 0
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/paddy.dat', form='unformatted', status='replace')
    write(un) save_version, dcp%nx_g, dcp%ny_g, merge(1, 0, pd%have(1)), merge(1, 0, pd%have(2))
  end if
  if (pd%have(1)) call restart_write_cell(un, s%hpn)
  if (pd%have(2)) call restart_write_cell(un, s%hpd)
  if (is_root) close(un)
end subroutine


!----------------------------------------------------------------------
! 復元(rank0 が読み、帯へ配る。版・格子・種類の有無が保存時と違えば停止する)
!----------------------------------------------------------------------
subroutine restore_state(pd, p, s)
  type(t_paddy), intent(inout) :: pd
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  character(:), allocatable :: fname
  logical :: found
  integer :: un, hd(1:5)
  fname = trim(p%dir_save)//'/paddy.dat'
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("paddy: state file not found (was fn_paddy enabled when saving): "//fname)
  un = 0
  hd(:) = 0
  if (is_root) then
    open(newunit=un, file=fname, form='unformatted', status='old', action='read')
    read(un) hd
  end if
  call par_allreduce_maxi(hd(1))
  call par_allreduce_maxi(hd(2))
  call par_allreduce_maxi(hd(3))
  call par_allreduce_maxi(hd(4))
  call par_allreduce_maxi(hd(5))
  if (hd(1) /= save_version) then
    call par_stop("paddy: state file format version "//itoa(hd(1))//" does not match the version this " &
                  //"executable reads ("//itoa(save_version)//"): "//fname)
  end if
  if (hd(2) /= dcp%nx_g .or. hd(3) /= dcp%ny_g .or. ((hd(4) > 0) .neqv. pd%have(1)) .or. &
      ((hd(5) > 0) .neqv. pd%have(2))) then
    call par_stop("paddy: the grid or the classes of paddy fields differ from the saved state "//fname)
  end if
  if (pd%have(1)) call restart_read_cell(un, s%hpn)
  if (pd%have(2)) call restart_read_cell(un, s%hpd)
  if (is_root) close(un)
end subroutine


!----------------------------------------------------------------------
! 無効なのに私有ファイルが dir_save にあれば停止する(保存時の水田の水を黙って捨てない)
!----------------------------------------------------------------------
subroutine stop_if_orphan(p)
  type(t_sysparam), intent(in) :: p
  logical :: found
  inquire(file=trim(p%dir_save)//'/paddy.dat', exist=found)
  if (found) then
    call par_stop("paddy: paddy.dat exists in "//trim(p%dir_save)//" but fn_paddy is not enabled at restart" &
                  //" (the stored paddy water would be dropped); enable fn_paddy or remove the file if the" &
                  //" drop is intended")
  end if
end subroutine

end module
