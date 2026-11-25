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
  !   片方向(段 1。f_pd_exchange = 0): 浸水が水田に入る流れ(逆流・外からの越流)は表さない(h_D ≥ hp_c なら流出 0)。
  ! 【双方向(二室化。f_pd_exchange = 1。paddy_plan.md §13、developer.md §119.6)】水田のセルの地表の水を
  !   河道断面形 σ の仕組み(§26.3)で階段形の断面にする: 畦畔の高さ h_lev より下は水田でない面積の割合
  !   s = 1 − a/gv(道路・排水路・畦畔)だけが貯めて流し、上はセル全面。タンクは畦畔より下の水田の水を持ち、
  !   畦畔より上の水は地表が持つので、水田が満ちて水位が畦畔より上ならセルの水 = gv·A·(η − z)(二重計上なし)。
  !   1 ステップ: (1) 雨の回収(矩形換算水深 vh で引く)、(2) 落水口は両向き(水位の高い側を上流として装置則。
  !   湛水が低ければ排水路の水が逆流する。独自の簡略化)、(3) 畦畔: タンクが畦畔高を超えた分は地表へ、地表の
  !   水位が畦畔を越えたら畦畔より上の水で満ちていない水田を瞬時に満たす(足りなければ空きの比で分ける)、
  !   (4) 減水深。地表の水位が畦畔高以上のときは落水口のやり取りをしない(水田は (3) で満ちる)。
  ! 【表現 B: 区画の解像(fn_pd_plot。paddy_plan.md §14、developer.md §119.8)】5〜10 m の格子で
  !   区画をセルの集まりとして解く。区画番号が違うセルの間のエッジ(対角を含む。市松の角
  !   も)に畦畔の仮想壁面を立て、落水口のエッジは装置則(両向き)にする。どちらも浅水流の
  !   本体の上書き(m_swflow_enc_channel の pwall_apply。登録は m_swflow_enc_set_plot_walls)。区画の湛水は
  !   浅水流の h そのもので、本モジュールは事前の湛水深(新しい計算の開始で h を max(h, h0) に)、
  !   減水深(区画のセルの h から perc·dt を系外へ)、台帳(区画の境のエッジの流量を測線と同じ
  !   観測口 m_swflow_enc_edge_flux で読む)だけを受け持つ。タンクはなく、S の台帳は地表の水の
  !   まま(pd_active を立てない)。
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
  ! 【水質(fn_wq。段 4a。paddy_plan.md §16.1、developer.md §119.10)】A のタンクは種類ごとの物質のプール
  !   s%cpn・s%cpd(セル面積基底 g/m2)を持ち、本モジュールが水と同じ割合で物質を動かす(落水・越流はタンクの
  !   濃度で地表の cq へ、双方向の流入は地表の濃度でタンクへ、減水深はタンクの濃度で系外へ = s%fmpd に記録)。
  !   水田の上の雨の物質は m_wq がプールへ直接入れる(s%pdfa。m_wq は本モジュールの後に雨の物質を足すので、
  !   雨の回収は水だけを動かす)。減衰・沈降は m_wq。B は区画の水が地表の水なので、減水深に同伴する物質だけを
  !   動かす(s%fmpd)。事前の湛水の濃度は pd_wq_c0(既定 0)
  ! 【併用】ENC のみ。ネスト(複数インスタンス)・淡塩とは init で停止する。水田のセルは
  !   海・河道(rw)・境界(水位規定・区間流入)・ソース・構造物のセルと、VZ・貯留関数の区画セルに
  !   置けない(雨の回収が boundary_h の式と一致する前提)。面積率は空隙率 gv を超えない。
  !   蒸発散はタンクから引かない(段 4)。B は、A の制限に加えて、蒸発散・地下水・非静水圧・土石流
  !   (f_debris)と併用できず(init で停止)、区画のセルを格子の外周と海の隣にも置けない。B と地形変化の
  !   掃流砂は区画の畦畔・落水口のエッジを越えない(m_geomorph_fluvial が m_swflow_enc_plot_wall で外す。§119.11)。
  !   双方向は、家屋破壊の空隙率の帰還・土石流・非静水圧と併用できず、
  !   水田のセルをため池のセルに置けず、s ≥ 0.05 が要る(init で停止)。地形変化(fn_geomorph)と併用すると、雨滴侵食(f_wash の
  !   雨滴の項・f_splash)は水田の部分を外す(1 − a を掛ける。s%pdfr。§119.5)。流れによる侵食・
  !   浮遊砂・掃流砂はセル全面のまま(タンクは土砂を運ばない)。双方向と浮遊砂(f_suspend)を併用すると、地表から
  !   タンクへ入る水(落水口の逆流・畦畔を越える満水)の浮遊砂を hs から引いて s%pdsd に記録し、m_geomorph の
  !   浮遊砂がそれを田面(z・sd)に積む(独自の簡略化。タンクから出る水は清水。§119.11)。
  ! ==========================================================================
  use, intrinsic :: iso_fortran_env, only : real64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state, sect_vh, sect_h_of, sect_sig
  use m_swflow_enc, only : m_swflow_enc_set_step_sect, m_swflow_enc_nh_active, m_swflow_enc_set_plot_walls, &
                          m_swflow_enc_edge_flux, chn   ! chn は区画の番号・落水口・種類を読むだけ(B。§119.8)
  use m_boundary, only : t_boundary
  use m_zonerunoff, only : t_zonerunoff
  use list_paddy, only : t_list_paddy, list_paddy_read, pd_nclass
  use m_paddy_law, only : t_pddev, t_gtab, dev_q, build_gtab, pi8   ! 落水口の装置則(葉のモジュール。§119.7)
  use m_fileio, only : fileio_read_matrix
  use m_restart, only : restart_write_cell, restart_read_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : param_default, itoa, es_out
  use m_parallel, only : par_info, par_stop, par_abort, dcp, is_root, par_sum_rows, par_scatter_cell, &
                         par_scatter_cell_i, par_allreduce_maxi, par_allreduce_sumi
  implicit none
  private
  public :: t_paddy
  public :: m_paddy_init
  public :: m_paddy_calc
  public :: m_paddy_record
  public :: m_paddy_dispose

  integer, parameter :: save_version = 2026112503 ! paddy.dat の形式の版(2026-11-25 に表現の印、水質の
                                                   !   タンクのプール、浮遊砂の堆積の記録を足した)
  integer, parameter :: nrow = 8                   ! 台帳の行部分和の列数(8 = タンクへ入った浮遊砂の堆積。§119.11)
  real, parameter :: pd_smin = 0.01                ! 双方向の水田のセルの、水田でない面積の割合の下限(落水口の水の
                                                   !   行き場を残す独自の目安。§119.12)
  integer, parameter :: pid_max = 16777215         ! 区画番号の上限(単精度の実数で正確に読める 2^24 − 1)
  integer, parameter :: din8(1:8) = [-1, 0, 1, -1, 1, -1, 0, 1]   ! 8 近傍の向き(浅水流と同じ並び)
  integer, parameter :: djn8(1:8) = [-1, -1, -1, 0, 0, 1, 1, 1]

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
    integer :: exch = 0                        ! 地表と水田のやり取り 0: 片方向、1: 双方向(二室化)
    integer :: rep = 0                         ! 表現 0: A(サブグリッドのタンク)、1: B(区画の解像)
    logical :: wq = .false.                    ! 水質(fn_wq)と併用する(物質のプールと減水深の持ち出し)
    logical :: sed = .false.                   ! 双方向と浮遊砂(f_suspend)の併用: タンクへ入る水の浮遊砂を田面に
                                               !   堆積させる(s%pdsd に記録し m_geomorph が積む。§119.11)
    real :: c0 = 0.0                           ! 事前の湛水の物質の濃度 (mg/L = g/m3)
    real :: aplot = 0.0                        ! 代表区画面積 (m2)
    real :: hlev = 0.0                         ! 畦畔高 (m)
    real :: perc = 0.0                         ! 減水深 (m/s)
    real :: h0(1:pd_nclass) = 0.0              ! 事前の湛水深 (m)
    real, allocatable :: fr1(:,:), fr2(:,:)    ! 種類ごとの面積率(セル面積基底。帯+ハロ)
    real(real64) :: area(1:pd_nclass) = 0.0_real64  ! 種類ごとの水田面積 (m2。全ランク同値)
    real(real64), allocatable :: rows(:,:)     ! (js:je, 1:nrow) 行ごとの量 (m3): 1 雨の回収・2 落水・
                                               !   3 越流・4 減水深(累積)、5 直近のステップの地表への量(正味)、
                                               !   6 落水口からの流入・7 畦畔を越えた流入
                                               !   (累積。双方向と B)。B: 1 区画のセルの雨・
                                               !   2 落水口からの流出・3 畦畔を越えた流出
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
  if (len_trim(list%fn_pd_plot) > 0) pd%rep = 1
  call setup_scalars(pd, list)
  if (pd%rep == 1) then
    call init_plots(pd, p, g, b, s, list, vzr, sfr)
    return
  end if
  call setup_maps(pd, p, g, b, s, list, vzr, sfr)
  call setup_devices(pd, p, list)
  if (pd%exch == 1) call setup_twoway(pd, g, s)
  ! 双方向と浮遊砂(f_suspend)の併用(§119.11): タンクへ入る水の浮遊砂を田面に堆積させる記録
  if (pd%exch == 1 .and. s%sed_active) then
    pd%sed = .true.
    allocate(s%pdsd(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    call par_info("paddy: suspended sediment (f_suspend) carried into the paddy tanks by backflow and over the " &
                  //"levees is deposited on the field surface (the outflow of the tanks is clear)")
  end if

  ! 状態(その種類の水田がある格子だけ確保)と S の台帳の貯留
  allocate(s%pdv(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (pd%have(1)) allocate(s%hpn(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (pd%have(2)) allocate(s%hpd(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  ! 水質と併用するときのタンクの物質のプール(§119.10。水田の上の雨の物質を m_wq がプールへ入れるための
  ! 種類ごとの面積率と、減水深の持ち出しの記録)
  call setup_wq(pd, list, s)
  if (pd%wq) then
    allocate(s%pdfa(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh, 1:2), source = 0.0)
    s%pdfa(:,:,1) = pd%fr1(:,:)
    s%pdfa(:,:,2) = pd%fr2(:,:)
    if (pd%have(1)) allocate(s%cpn(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    if (pd%have(2)) allocate(s%cpd(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  end if
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
    ! 事前の湛水の物質(濃度 pd_wq_c0 × 湛水 × 面積率。セル面積基底)
    if (pd%wq) then
      if (pd%have(1)) s%cpn(:,:) = pd%c0 * s%hpn(:,:) * pd%fr1(:,:)
      if (pd%have(2)) s%cpd(:,:) = pd%c0 * s%hpd(:,:) * pd%fr2(:,:)
    end if
  end if
  do j = dcp%jsh, dcp%jeh
    do i = dcp%ish, dcp%ieh
      s%pdv(i,j) = cell_store(pd, s, i, j)
    end do
  end do
  s%pd_active = .true.
  ! 地形変化と併用するときの雨滴侵食の面積率(§119.5): 水田の上の雨はタンク(田面の湛水)へ
  ! 落ちるので、雨滴侵食(f_wash の雨滴の項・f_splash)に 1 − a を掛ける。地形変化がなければ確保しない
  if (len_trim(p%fn_geomorph) > 0) then
    allocate(s%pdfr(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    s%pdfr(:,:) = pd%fr1(:,:) + pd%fr2(:,:)
    call par_info("paddy: the rain splash erosion of geomorph (the rain term of f_wash and f_splash) " // &
                  "is multiplied by (1 - paddy fraction)")
  end if

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
  real :: dt, a, rain, hd, dsur, f, dv, sp, pc, st, hb, msur
  real(real64) :: rr(1:nrow)

  if (.not. pd%enabled) return
  if (pd%rep == 1) then
    call calc_plots(pd, p, g, s)
    return
  end if
  if (pd%exch == 1) then
    call calc_twoway(pd, p, g, s)
    return
  end if
  dt = p%dt
  !$omp parallel do schedule(dynamic) private(i, j, a, rain, hd, dsur, f, dv, sp, pc, st, rr, hb, msur)
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
      msur = 0.0
      ! (2)〜(4) 種類ごとのタンク
      if (pd%have(1)) then
        f = pd%fr1(i,j)
        if (f > 0.0) then
          hb = s%hpn(i,j)
          call tank_step(pd, pd%dev(1), s%hpn(i,j), a / s%gv(i,j), rain, hd, dt, dv, sp, pc)
          if (pd%wq) call pool_move(s%cpn(i,j), hb + rain, dv, sp, pc, msur, s%fmpd(i,j))
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
          hb = s%hpd(i,j)
          call tank_step(pd, pd%dev(2), s%hpd(i,j), a / s%gv(i,j), rain, hd, dt, dv, sp, pc)
          if (pd%wq) call pool_move(s%cpd(i,j), hb + rain, dv, sp, pc, msur, s%fmpd(i,j))
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
      if (pd%wq) s%cq(i,j) = s%cq(i,j) + msur / s%gv(i,j)   ! タンクから出た物質(cq は h と同じ基底)
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
  real(real64) :: tot(1:nrow), st(1:2), fu(1:2), res, hm(1:2), ff(1:2), cm(1:2), cw(1:2), cc(1:2), vals(1:19)
  real(real64), allocatable :: r1(:), srow(:,:)
  real :: hfull
  integer :: i, j, k, nv
  character(len=32) :: fmt

  if (.not. pd%enabled) return
  allocate(r1(dcp%js:dcp%je))
  do k = 1, nrow
    r1(:) = pd%rows(:,k)
    call par_sum_rows(r1, tot(k))
  end do
  ! 種類ごとの貯留と、畦畔高まで満ちた水田の面積(行部分和)
  hfull = pd%hlev * (1.0 - 1.0e-6)
  allocate(srow(dcp%js:dcp%je, 1:4), source = 0.0_real64)
  if (pd%rep == 1) call plot_rows(pd, g, s, hfull, srow)
  do j = dcp%js, dcp%je
    if (pd%rep == 1) exit
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
  ! 水質と併用するときの種類ごとの水田の水の平均濃度 (mg/L = g/m3。物質の総量 / 水の総量。§119.10)
  if (pd%wq) then
    call wq_rows(pd, g, s, srow)
    do k = 1, 2
      r1(:) = srow(:,k)
      call par_sum_rows(r1, cm(k))
      r1(:) = srow(:,k+2)
      call par_sum_rows(r1, cw(k))
      cc(k) = 0.0_real64
      if (cw(k) > 0.0_real64) cc(k) = cm(k) / cw(k)
    end do
  end if
  if (.not. is_root) return
  res = (st(1) + st(2)) - pd%store0 - (tot(1) - tot(2) - tot(3) - tot(4)) - (tot(6) + tot(7))
  do k = 1, 2
    hm(k) = 0.0_real64
    ff(k) = 0.0_real64
    if (pd%area(k) > 0.0_real64) then
      hm(k) = st(k) / pd%area(k) * 1.0e3_real64
      ff(k) = fu(k) / pd%area(k)
    end if
  end do
  vals(1:16) = [pd%area(1), pd%area(2), tot(1), tot(2), tot(3), tot(4), st(1), st(2), res, &
                tot(5) / real(p%dt, real64), hm(1), hm(2), ff(1), ff(2), tot(6), tot(7)]
  nv = 16
  if (pd%wq) then                ! 種類ごとの平均濃度(§119.10)
    vals(nv+1:nv+2) = cc(1:2)
    nv = nv + 2
  end if
  if (pd%sed) then               ! タンクへ入った水の浮遊砂を田面に積んだ累積(固相の体積。§119.11)
    vals(nv+1) = tot(8)
    nv = nv + 1
  end if
  write(fmt, '(a,i0,a)') '(f0.2,', nv, '(",",es23.15))'
  write(pd%un_csv, fmt) s%t, es_out(vals(1:nv))
  flush(pd%un_csv)
end subroutine


!----------------------------------------------------------------------
! 水質の行部分和(§119.10): 種類ごとの物質(列 1・2)と水(列 3・4)。セル面積基底。A はタンクのプールと
! タンクの水、B は区画のセルの地表の物質(cq × gv)と水(gv × h)
!----------------------------------------------------------------------
subroutine wq_rows(pd, g, s, srow)
  type(t_paddy), intent(in) :: pd
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64), intent(inout) :: srow(dcp%js:, 1:)
  integer :: i, j, c
  srow(:,:) = 0.0_real64
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (pd%rep == 1) then
        c = chn%pcl(i,j)
        if (c <= 0) cycle
        srow(j,c) = srow(j,c) + real(s%cq(i,j) * s%gv(i,j), real64)
        srow(j,c+2) = srow(j,c+2) + real(s%gv(i,j) * s%h(i,j), real64)
      else
        if (pd%have(1)) then
          srow(j,1) = srow(j,1) + real(s%cpn(i,j), real64)
          srow(j,3) = srow(j,3) + real(pd%fr1(i,j) * s%hpn(i,j), real64)
        end if
        if (pd%have(2)) then
          srow(j,2) = srow(j,2) + real(s%cpd(i,j), real64)
          srow(j,4) = srow(j,4) + real(pd%fr2(i,j) * s%hpd(i,j), real64)
        end if
      end if
    end do
  end do
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
! 毎ステップ(双方向。f_pd_exchange = 1。§119.6): 地表の水は σ の階段形の断面(畦畔の高さより下は水田でない
! 面積の割合 1 − a/gv、上はセル全面)で、タンクと落水口(両向き)・畦畔(瞬時)で水をやり取りする。地表の水の
! 足し引きは矩形換算水深 vh で行う(§26.2)。セル単位で帯の中だけ(ハロ交換なし)
!----------------------------------------------------------------------
subroutine calc_twoway(pd, p, g, s)
  type(t_paddy), intent(inout) :: pd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, c
  real :: dt, a, rain, gv, vh, vh0, hd, r, q, sp, pc, fill, wv, dtot, phi, vcrest
  real :: f(1:pd_nclass), tk(1:pd_nclass), qd(1:pd_nclass)
  real :: cqv, pl(1:pd_nclass), w                ! 水質: 地表の物質(cq の基底)、タンクのプール(セル面積基底)
  real :: hsv, dep                               ! 浮遊砂: 地表の hs、タンクへ入って田面に積む分(§119.11)
  real(real64) :: rr(1:nrow)

  dt = p%dt
  !$omp parallel do schedule(dynamic) private(i, j, c, a, rain, gv, vh, vh0, hd, r, q, sp, pc, fill, wv, &
  !$omp                                        dtot, phi, vcrest, f, tk, qd, rr, cqv, pl, w, hsv, dep)
  do j = dcp%js, dcp%je
    rr(:) = 0.0_real64
    do i = g%wx(1,j), g%wx(2,j)
      f(:) = 0.0
      tk(:) = 0.0
      if (pd%have(1)) then
        f(1) = pd%fr1(i,j)
        tk(1) = s%hpn(i,j)
      end if
      if (pd%have(2)) then
        f(2) = pd%fr2(i,j)
        tk(2) = s%hpd(i,j)
      end if
      a = f(1) + f(2)
      if (a <= 0.0) cycle
      gv = s%gv(i,j)
      rain = s%pre(i,j) * dt
      ! (1) 雨の回収(boundary_h が vh に足した雨のうち水田の上の分)と、タンクへの雨
      vh = max(sect_vh(s, i, j, s%h(i,j)) - a * rain / gv, 0.0)
      vh0 = vh
      hd = sect_h_of(s, i, j, vh)
      do c = 1, pd_nclass
        if (f(c) > 0.0) tk(c) = tk(c) + rain
      end do
      ! 水質(§119.10): 地表の物質とタンクのプールを水と同じ順に動かす(水田の上の雨の物質は m_wq がプールへ)
      if (pd%wq) then
        cqv = s%cq(i,j)
        pl(:) = 0.0
        if (pd%have(1)) pl(1) = s%cpn(i,j)
        if (pd%have(2)) pl(2) = s%cpd(i,j)
      end if
      ! 浮遊砂(§119.11): 地表からタンクへ入る水(落水口の逆流・畦畔を越える満水)の浮遊砂を田面に積む
      if (pd%sed) then
        hsv = max(s%hs(i,j), 0.0)
        dep = 0.0
      end if
      ! (2) 落水口(両向き。水位の高い側を上流として装置則を使う)。種類ごとにステップの初めの水位から求め、
      !     陽解法の上限は両側の貯留(タンク、地表 gv·σ(h))で水位差の半分(全水田の面積で数える)
      r = a / (gv * sect_sig(s, i, j, hd))
      do c = 1, pd_nclass
        qd(c) = 0.0
        if (f(c) <= 0.0) cycle
        if (hd >= pd%hlev) cycle     ! 地表の水位が畦畔以上: 水田は畦畔を越える流入(下の (3))で満ちる
        if (tk(c) >= hd) then
          q = dev_q(pd%dev(c), pd%gt, tk(c), hd) * dt / pd%aplot
          q = min(q, max(tk(c) - pd%dev(c)%zlow, 0.0), 0.5 * (tk(c) - hd) / (1.0 + r))
          qd(c) = q
          rr(2) = rr(2) + real(f(c) * q, real64)
        else
          q = dev_q(pd%dev(c), pd%gt, hd, tk(c)) * dt / pd%aplot
          q = min(q, 0.5 * (hd - tk(c)) / (1.0 + r))
          qd(c) = -q
          rr(6) = rr(6) + real(f(c) * q, real64)
        end if
      end do
      do c = 1, pd_nclass
        if (f(c) <= 0.0) cycle
        if (pd%wq) then
          if (qd(c) > 0.0) then                          ! タンク → 地表(タンクの濃度)
            w = pl(c) * min(qd(c) / tk(c), 1.0)
            pl(c) = pl(c) - w
            cqv = cqv + w / gv
          else if (qd(c) < 0.0 .and. vh > 0.0) then       ! 地表 → タンク(地表の濃度)
            w = cqv * min(-f(c) * qd(c) / gv / vh, 1.0)
            cqv = cqv - w
            pl(c) = pl(c) + w * gv
          end if
        end if
        if (pd%sed .and. qd(c) < 0.0 .and. vh > 0.0) then  ! 逆流の水の浮遊砂を田面へ
          w = hsv * min(-f(c) * qd(c) / gv / vh, 1.0)
          hsv = hsv - w
          dep = dep + w
        end if
        tk(c) = tk(c) - qd(c)
        vh = vh + f(c) * qd(c) / gv
      end do
      vh = max(vh, 0.0)
      ! (3) 畦畔: タンクが畦畔高を超えた分は地表へ。地表の水位が畦畔を越えたら、畦畔より上の地表の水で
      !     満ちていない水田を瞬時に満たす(足りなければ空きの比で分ける。越流の長さは持たない)
      do c = 1, pd_nclass
        if (f(c) <= 0.0) cycle
        if (tk(c) > pd%hlev) then
          sp = tk(c) - pd%hlev
          if (pd%wq) then                                ! 越流(タンクの濃度で地表へ)
            w = pl(c) * min(sp / tk(c), 1.0)
            pl(c) = pl(c) - w
            cqv = cqv + w / gv
          end if
          tk(c) = pd%hlev
          vh = vh + f(c) * sp / gv
          rr(3) = rr(3) + real(f(c) * sp, real64)
        end if
      end do
      hd = sect_h_of(s, i, j, vh)
      if (hd > pd%hlev) then
        vcrest = sect_vh(s, i, j, pd%hlev)
        wv = gv * (vh - vcrest)                       ! 畦畔より上の地表の水(セル面積基底)
        dtot = 0.0
        do c = 1, pd_nclass
          if (f(c) > 0.0) dtot = dtot + f(c) * (pd%hlev - tk(c))
        end do
        if (dtot > 0.0 .and. wv > 0.0) then
          phi = min(1.0, wv / dtot)
          do c = 1, pd_nclass
            if (f(c) <= 0.0) cycle
            fill = phi * (pd%hlev - tk(c))
            if (pd%wq .and. vh > 0.0) then               ! 畦畔を越える満水(地表の濃度でタンクへ)
              w = cqv * min(f(c) * fill / gv / vh, 1.0)
              cqv = cqv - w
              pl(c) = pl(c) + w * gv
            end if
            if (pd%sed .and. vh > 0.0) then              ! 満たす水の浮遊砂を田面へ
              w = hsv * min(f(c) * fill / gv / vh, 1.0)
              hsv = hsv - w
              dep = dep + w
            end if
            if (phi >= 1.0) then
              tk(c) = pd%hlev
            else
              tk(c) = tk(c) + fill
            end if
            vh = vh - f(c) * fill / gv
            rr(7) = rr(7) + real(f(c) * fill, real64)
          end do
          vh = max(vh, 0.0)
        end if
      end if
      ! (4) 減水深
      do c = 1, pd_nclass
        if (f(c) <= 0.0) cycle
        pc = min(pd%perc * dt, tk(c))
        if (pd%wq .and. pc > 0.0) then                   ! タンクの濃度で系外へ
          w = pl(c) * min(pc / tk(c), 1.0)
          pl(c) = pl(c) - w
          s%fmpd(i,j) = s%fmpd(i,j) + w
        end if
        tk(c) = tk(c) - pc
        rr(4) = rr(4) + real(f(c) * pc, real64)
      end do
      rr(1) = rr(1) + real(a * rain, real64)
      rr(5) = rr(5) + real(gv * (vh - vh0), real64)
      ! 地表へ(e の回復。契約 2)と状態
      s%h(i,j) = sect_h_of(s, i, j, vh)
      s%e(i,j) = s%z(i,j) + s%h(i,j)
      if (pd%have(1)) s%hpn(i,j) = tk(1)
      if (pd%have(2)) s%hpd(i,j) = tk(2)
      s%pdv(i,j) = f(1) * tk(1) + f(2) * tk(2)
      if (pd%wq) then
        s%cq(i,j) = cqv
        if (pd%have(1)) s%cpn(i,j) = pl(1)
        if (pd%have(2)) s%cpd(i,j) = pl(2)
      end if
      if (pd%sed) then
        if (dep > 0.0) then
          s%hs(i,j) = hsv
          s%pdsd(i,j) = s%pdsd(i,j) + dep
          rr(8) = rr(8) + real(dep, real64)
        end if
      end if
    end do
    pd%rows(j,1:4) = pd%rows(j,1:4) + rr(1:4) * pd%dxdy
    pd%rows(j,5) = rr(5) * pd%dxdy
    pd%rows(j,6:8) = pd%rows(j,6:8) + rr(6:8) * pd%dxdy
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 双方向(二室化。f_pd_exchange = 1。§119.6)の検査と、水田のセルの階段形の断面の登録(collective)
!----------------------------------------------------------------------
subroutine setup_twoway(pd, g, s)
  type(t_paddy), intent(in) :: pd
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, allocatable :: dst(:,:), fst(:,:)
  integer :: i, j, k, nbad, ib, jb, key
  real :: fa
  character(len=256) :: msg
  character(len=32) :: sval

  ! 全ランク同値の判定
  if (s%gv_active) call par_stop("list_paddy: f_pd_exchange=1 cannot be combined with the feedback of building " &
      //"destruction on the void ratio (fn_bldgdebris): the non-paddy fraction 1 - a/gv of a cell would change")
  if (s%debris_active) call par_stop("list_paddy: f_pd_exchange=1 cannot be combined with debris flows " &
      //"(f_debris of fn_geomorph): the mixture entering the paddy tanks is not handled")
  if (m_swflow_enc_nh_active()) call par_stop("list_paddy: f_pd_exchange=1 cannot be combined with the " &
      //"non-hydrostatic correction (f_nonhydrostatic=1): cells with a cross-section shape stay hydrostatic")
  ! 帯で: ため池のセルと、水田でない面積の割合の下限(誤りの種類とセルを 1 つの整数にまとめて全ランクの最大)
  nbad = 0
  ib = 0
  jb = 0
  key = 0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      fa = pd%fr1(i,j) + pd%fr2(i,j)
      if (fa <= 0.0) cycle
      k = 0
      if (1.0 - fa / s%gv(i,j) < pd_smin) k = 1
      if (g%rscap(i,j) > 0.0) k = 2
      if (k > nbad) then
        nbad = k
        ib = i
        jb = j
      end if
    end do
  end do
  if (nbad > 0) key = nbad * (g%nx * g%ny) + (jb - 1) * g%nx + (ib - 1)
  call par_allreduce_maxi(key)
  if (key > 0) then
    nbad = key / (g%nx * g%ny)
    ib = mod(key, g%nx * g%ny)
    jb = ib / g%nx + 1
    ib = mod(ib, g%nx) + 1
    if (nbad == 2) then
      msg = "paddy: f_pd_exchange=1: a paddy cell is a pond cell (rscap > 0; the pond takes the surface water " &
            //"on the void basis)"
    else
      write(sval, '(f4.2)') pd_smin
      msg = "paddy: f_pd_exchange=1: the non-paddy fraction 1 - a/gv of a paddy cell is below "//trim(sval) &
            //" (leave room for levees, farm roads and drains)"
    end if
    call par_stop(trim(msg)//" (e.g. at ("//itoa(ib)//","//itoa(jb)//"))")
  end if
  ! 階段形の断面: 遷移深さ D = 畦畔高、床の割合 = 1 − a/gv(帯 + ハロ)
  allocate(dst(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), fst(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  do j = dcp%jsh, dcp%jeh
    do i = dcp%ish, dcp%ieh
      fa = pd%fr1(i,j) + pd%fr2(i,j)
      if (fa <= 0.0) cycle
      dst(i,j) = pd%hlev
      fst(i,j) = 1.0 - fa / s%gv(i,j)
    end do
  end do
  call m_swflow_enc_set_step_sect(g, s, dst, fst)
  call par_info("paddy: two-way exchange (f_pd_exchange = 1): below the levee crest the surface water of a paddy " &
                //"cell is stored and flows in the non-paddy part (1 - a/gv), above it in the whole cell")
end subroutine


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
! 区画の解像(表現 B。fn_pd_plot。§119.8、paddy_plan.md §14)の初期化: 併用の検査、区画の分布の
! 読み込みと検査、装置、浅水流への畦畔・落水口の登録、事前の湛水深(または復元の照合)、
! 台帳
!----------------------------------------------------------------------
subroutine init_plots(pd, p, g, b, s, list, vzr, sfr)
  type(t_paddy), intent(inout) :: pd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s
  type(t_list_paddy), intent(in) :: list
  type(t_zonerunoff), intent(in) :: vzr, sfr
  integer, allocatable :: pid(:,:), pod(:,:), pcl(:,:)
  integer :: i, j, c

  if (s%debris_active) call par_stop("list_paddy: fn_pd_plot cannot be combined with debris flows " &
      //"(f_debris of fn_geomorph): the levee walls are not checked with the mixture flow")
  call no_combo(p%fn_evap, "fn_evap", "pd_perc_mmd is the daily decrease of the ponding depth and already " &
                //"includes the evapotranspiration")
  call no_combo(p%fn_gwflow, "fn_gwflow", "the infiltration of gwflow and pd_perc_mmd would both drain the " &
                //"plot water")
  if (m_swflow_enc_nh_active()) call par_stop("list_paddy: fn_pd_plot cannot be combined with the " &
      //"non-hydrostatic correction (f_nonhydrostatic=1): the levee walls are not excluded from it")
  call setup_plots(pd, p, g, b, list, vzr, sfr, pid, pod, pcl)
  call setup_devices(pd, p, list)
  call setup_wq(pd, list, s)
  call m_swflow_enc_set_plot_walls(g, pid, pod, pcl, pd%hlev, pd%dev, pd%gt)
  deallocate(pid, pod, pcl)
  if (p%f_state_restore > 0) then
    call restore_state(pd, p, s)
  else
    ! 事前の湛水深: 区画のセルの水深を max(h, h0) にする(帯 + ハロ。全ランクが同じ規則で同じ値)
    do j = dcp%jsh, dcp%jeh
      do i = dcp%ish, dcp%ieh
        c = chn%pcl(i,j)
        if (c <= 0) cycle
        if (s%h(i,j) < pd%h0(c)) then
          ! 足した水の物質(濃度 pd_wq_c0。cq は h と同じ基底の柱状量。§119.10)
          if (pd%wq) s%cq(i,j) = s%cq(i,j) + pd%c0 * (pd%h0(c) - s%h(i,j))
          s%h(i,j) = pd%h0(c)
          s%e(i,j) = s%z(i,j) + s%h(i,j)
        end if
      end do
    end do
    call par_info("paddy: the plot cells start with the water depth max(h, initial ponding depth of the class)")
  end if
  allocate(pd%rows(dcp%js:dcp%je, 1:nrow), source = 0.0_real64)
  pd%store0 = plot_store(pd, g, s)
  call report(pd)
  call open_csv(pd, p)
  pd%enabled = .true.
  pd%initialized = .true.
contains
  subroutine no_combo(fn, name, why)
    character(len=*), intent(in) :: fn, name, why
    if (len_trim(fn) > 0) call par_stop("list_paddy: fn_pd_plot cannot be combined with "//name//" ("//why//")")
  end subroutine
end subroutine


!----------------------------------------------------------------------
! 区画の分布(rank0 が全域で読み、検査して帯 + ハロへ配る)と、帯の検査・種類の有無・面積(B)
!   pid: 区画番号(0 = 水田でない)、pod: 落水口の向き 1〜8(出口セル)、
!   pcl: 装置の種類 1・2(区画のセル)
!----------------------------------------------------------------------
subroutine setup_plots(pd, p, g, b, list, vzr, sfr, pid, pod, pcl)
  type(t_paddy), intent(inout) :: pd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_list_paddy), intent(in) :: list
  type(t_zonerunoff), intent(in) :: vzr, sfr
  integer, allocatable, intent(out) :: pid(:,:), pod(:,:), pcl(:,:)
  real, allocatable :: wp(:,:), wo(:,:), wc(:,:)
  integer, allocatable :: ip(:,:), io(:,:), ic(:,:), mk(:,:)
  integer :: idum(1,1)
  integer :: i, j, k, n, in, jn, ierr, ie, je, nbad, ib, jb, key
  integer :: hv(1:pd_nclass)
  real(real64), allocatable :: r1(:), r2(:)
  character(len=512) :: msg

  ! --- rank0: 全域で読み、検査する ---
  ierr = 0
  ie = 0
  je = 0
  if (is_root) then
    allocate(wp(1:g%nx, 1:g%ny), wo(1:g%nx, 1:g%ny), wc(1:g%nx, 1:g%ny))
    call read_full(p, g, list%fn_pd_plot, wp)
    if (len_trim(list%fn_pd_outlet) > 0) then
      call read_full(p, g, list%fn_pd_outlet, wo)
    else
      wo(:,:) = 0.0
    end if
    if (len_trim(list%fn_pd_class) > 0) then
      call read_full(p, g, list%fn_pd_class, wc)
    else
      wc(:,:) = 1.0
    end if
    ! 境界・ソース・構造物のセルの印(区画のセルに置けない)
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
    ! 値(整数であること)
    allocate(ip(1:g%nx, 1:g%ny), io(1:g%nx, 1:g%ny), ic(1:g%nx, 1:g%ny), source = 0)
    do j = 1, g%ny
      do i = 1, g%nx
        if (ierr > 0) exit
        if (g%x(i,j) <= 0) cycle
        if (.not. is_int(wp(i,j), pid_max)) then
          call fail(11, i, j)
        else if (.not. is_int(wo(i,j), 8)) then
          call fail(12, i, j)
        else if (.not. is_int(wc(i,j), pd_nclass)) then
          call fail(13, i, j)
        else
          ip(i,j) = nint(wp(i,j))
          io(i,j) = nint(wo(i,j))
          ic(i,j) = nint(wc(i,j))
        end if
      end do
    end do
    ! 区画のセルと落水口
    do j = 1, g%ny
      do i = 1, g%nx
        if (ierr > 0) exit
        if (g%x(i,j) <= 0) cycle
        if (ip(i,j) <= 0) then
          if (io(i,j) > 0) call fail(14, i, j)
          ic(i,j) = 0
          cycle
        end if
        if (ic(i,j) < 1) then
          call fail(15, i, j)
        else if (g%sw(i,j) > 0) then
          call fail(3, i, j)
        else if (g%rw(i,j) > 0) then
          call fail(4, i, j)
        else if (mk(i,j) > 0) then
          call fail(5, i, j)
        else if (i == 1 .or. i == g%nx .or. j == 1 .or. j == g%ny) then
          call fail(16, i, j)
        end if
        if (ierr > 0) exit
        do k = 1, 8
          in = i + din8(k)
          jn = j + djn8(k)
          if (g%x(in,jn) <= 0) cycle
          if (g%sw(in,jn) > 0) then
            call fail(17, i, j)
          else if (ip(in,jn) == ip(i,j) .and. nint(wc(in,jn)) /= ic(i,j)) then
            call fail(18, i, j)
          end if
        end do
        if (io(i,j) > 0 .and. ierr == 0) then
          k = io(i,j)
          in = i + din8(k)
          jn = j + djn8(k)
          if (g%x(in,jn) <= 0) then
            call fail(19, i, j)
          else if (ip(in,jn) == ip(i,j)) then
            call fail(20, i, j)
          else if (ip(in,jn) > 0 .and. io(in,jn) == 9 - k) then
            call fail(21, i, j)
          end if
        end if
      end do
    end do
    if (ierr == 0) call plot_stats(ip, io, ic)
  end if
  call par_allreduce_maxi(ierr)
  call par_allreduce_maxi(ie)
  call par_allreduce_maxi(je)
  if (ierr > 0) then
    select case (ierr)
      case (3)
        msg = "paddy: a plot cell is on a sea cell"
      case (4)
        msg = "paddy: a plot cell is on a channel cell (rw)"
      case (5)
        msg = "paddy: a plot cell overlaps a boundary, source or structure cell"
      case (11)
        msg = "paddy: the plot number (fn_pd_plot) must be an integer from 0 to "//itoa(pid_max)
      case (12)
        msg = "paddy: the outlet direction (fn_pd_outlet) must be an integer from 0 to 8"
      case (13)
        msg = "paddy: the outlet class (fn_pd_class) must be 0, 1 or 2"
      case (14)
        msg = "paddy: an outlet direction (fn_pd_outlet) is given on a cell that is not a plot cell"
      case (15)
        msg = "paddy: the outlet class (fn_pd_class) of a plot cell must be 1 or 2"
      case (16)
        msg = "paddy: a plot cell is on the outermost row or column of the grid (it has open boundary faces)"
      case (17)
        msg = "paddy: a plot cell is next to a sea cell"
      case (18)
        msg = "paddy: the cells of a plot have different outlet classes (fn_pd_class must be the same " &
              //"within a plot)"
      case (19)
        msg = "paddy: an outlet points to a cell outside the computational domain"
      case (20)
        msg = "paddy: an outlet points to a cell of the same plot"
      case default
        msg = "paddy: two outlets face each other on the same edge"
    end select
    call par_stop(trim(msg)//" at ("//itoa(ie)//","//itoa(je)//")")
  end if

  ! --- 帯 + ハロへ配る ---
  allocate(pid(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), pod(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), &
           pcl(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0)
  if (is_root) then
    call par_scatter_cell_i(ip, pid)
    call par_scatter_cell_i(io, pod)
    call par_scatter_cell_i(ic, pcl)
  else
    call par_scatter_cell_i(idum, pid)
    call par_scatter_cell_i(idum, pod)
    call par_scatter_cell_i(idum, pcl)
  end if

  ! --- 帯の検査: ため池・VZ・貯留関数の区画のセル、海側のセルの隣(collective に停止) ---
  nbad = 0
  ib = 0
  jb = 0
  key = 0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (pcl(i,j) <= 0) cycle
      k = 0
      if (g%rscap(i,j) > 0.0) k = 1
      if (allocated(vzr%zid)) then
        if (vzr%zid(i,j) > 0) k = 2
      end if
      if (allocated(sfr%zid)) then
        if (sfr%zid(i,j) > 0) k = 3
      end if
      if (g%swall_active) then
        do n = 1, 8
          if (g%ssw(i+din8(n), j+djn8(n)) > 0) k = 4
        end do
      end if
      if (k > nbad) then
        nbad = k
        ib = i
        jb = j
      end if
    end do
  end do
  if (nbad > 0) key = nbad * (g%nx * g%ny) + (jb - 1) * g%nx + (ib - 1)
  call par_allreduce_maxi(key)
  if (key > 0) then
    nbad = key / (g%nx * g%ny)
    ib = mod(key, g%nx * g%ny)
    jb = ib / g%nx + 1
    ib = mod(ib, g%nx) + 1
    select case (nbad)
      case (1)
        msg = "paddy: a plot cell is a pond cell (rscap > 0)"
      case (2)
        msg = "paddy: a plot cell is a VZ zone cell (both would take the rain of the cell)"
      case (3)
        msg = "paddy: a plot cell is a SFM zone cell (both would take the rain of the cell)"
      case default
        msg = "paddy: a plot cell is next to a seaside cell (fn_seaside)"
    end select
    call par_stop(trim(msg)//" (e.g. at ("//itoa(ib)//","//itoa(jb)//"))")
  end if

  ! --- 種類の有無と面積(全ランク同値) ---
  hv(:) = 0
  allocate(r1(dcp%js:dcp%je), r2(dcp%js:dcp%je), source = 0.0_real64)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (pcl(i,j) == 1) then
        hv(1) = 1
        r1(j) = r1(j) + 1.0_real64
      else if (pcl(i,j) == 2) then
        hv(2) = 1
        r2(j) = r2(j) + 1.0_real64
      end if
    end do
  end do
  call par_allreduce_sumi(hv)
  pd%have(:) = hv(:) > 0
  call par_sum_rows(r1, pd%area(1))
  call par_sum_rows(r2, pd%area(2))
  pd%area(:) = pd%area(:) * pd%dxdy
  if (.not. any(pd%have)) call par_stop("paddy: no plot cell in the domain (fn_pd_plot is 0 everywhere)")
contains
  subroutine mark(ii, jj)
    integer, intent(in) :: ii, jj
    if (ii < 1 .or. ii > g%nx .or. jj < 1 .or. jj > g%ny) return
    mk(ii,jj) = 1
  end subroutine
  subroutine fail(code, ii, jj)
    integer, intent(in) :: code, ii, jj
    if (ierr > 0) return
    ierr = code
    ie = ii
    je = jj
  end subroutine
  logical function is_int(v, vmax)
    real, intent(in) :: v
    integer, intent(in) :: vmax
    is_int = .false.
    if (.not. (v >= 0.0 .and. v <= real(vmax))) return
    is_int = abs(v - anint(v)) <= 1.0e-3
  end function
end subroutine


!----------------------------------------------------------------------
! 区画の数・落水口の数・落水口のない区画の数を画面へ(rank0。全域の配列から。区画番号の
! 数で数える)
!----------------------------------------------------------------------
subroutine plot_stats(ip, io, ic)
  integer, intent(in) :: ip(1:, 1:), io(1:, 1:), ic(1:, 1:)
  integer, allocatable :: ids(:), ods(:)
  integer :: n, m, i, j, np, nno, no1, no2, k
  character(len=512) :: line

  n = count(ip > 0)
  m = count(io > 0)
  allocate(ids(1:n), ods(1:max(m, 1)))
  n = 0
  m = 0
  no1 = 0
  no2 = 0
  do j = 1, size(ip, 2)
    do i = 1, size(ip, 1)
      if (ip(i,j) <= 0) cycle
      n = n + 1
      ids(n) = ip(i,j)
      if (io(i,j) > 0) then
        m = m + 1
        ods(m) = ip(i,j)
        if (ic(i,j) == 1) no1 = no1 + 1
        if (ic(i,j) == 2) no2 = no2 + 1
      end if
    end do
  end do
  call isort(ids(1:n))
  if (m > 0) call isort(ods(1:m))
  ! 区画番号の数と、落水口のない区画番号の数(整列した 2 つの列を突き合わせる)
  np = 0
  nno = 0
  k = 1
  do i = 1, n
    if (i > 1) then
      if (ids(i) == ids(i-1)) cycle
    end if
    np = np + 1
    do while (k <= m)
      if (ods(k) >= ids(i)) exit
      k = k + 1
    end do
    if (k > m) then
      nno = nno + 1
    else if (ods(k) /= ids(i)) then
      nno = nno + 1
    end if
  end do
  write(line, '(a,i0,a,i0,a,i0,a,i0,a)') "paddy: resolved plots (fn_pd_plot): ", np, " plot numbers on ", n, &
        " cells; outlets: ", no1, " normal, ", no2, " paddy-dam"
  call par_info(trim(line))
  if (nno > 0) then
    write(line, '(a,i0,a)') "paddy: ", nno, " plot numbers have no outlet (they drain only by percolation and " &
          //"over the levees)"
    call par_info(trim(line))
  end if
end subroutine


!----------------------------------------------------------------------
! 整数の列を昇順に整列する(ヒープソート。初期化の 1 回きり)
!----------------------------------------------------------------------
subroutine isort(a)
  integer, intent(inout) :: a(1:)
  integer :: n, i, t
  n = size(a)
  do i = n / 2, 1, -1
    call sift(i, n)
  end do
  do i = n, 2, -1
    t = a(1)
    a(1) = a(i)
    a(i) = t
    call sift(1, i - 1)
  end do
contains
  subroutine sift(l, r)
    integer, intent(in) :: l, r
    integer :: ii, jj, v
    ii = l
    v = a(ii)
    do
      jj = 2 * ii
      if (jj > r) exit
      if (jj < r) then
        if (a(jj+1) > a(jj)) jj = jj + 1
      end if
      if (a(jj) <= v) exit
      a(ii) = a(jj)
      ii = jj
    end do
    a(ii) = v
  end subroutine
end subroutine


!----------------------------------------------------------------------
! 毎ステップ(B。浅水流の後): 区画の境のエッジの流量の台帳(このステップの確定した流量を
! 測線と同じ観測口で読む)と、区画のセルの減水深(h から perc·dt を系外へ。e の回復)。
! セル単位で帯の中だけ
!----------------------------------------------------------------------
subroutine calc_plots(pd, p, g, s)
  type(t_paddy), intent(inout) :: pd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, k, in, jn, ipl
  real :: dt, q, pc, w
  real(real64) :: rr(1:nrow)

  dt = p%dt
  !$omp parallel do schedule(dynamic) private(i, j, k, in, jn, ipl, q, pc, w, rr)
  do j = dcp%js, dcp%je
    rr(:) = 0.0_real64
    do i = g%wx(1,j), g%wx(2,j)
      if (chn%pcl(i,j) <= 0) cycle
      ipl = chn%pid(i,j)
      ! 区画の境のエッジ(このセルから出る向きが正。落水口と畦畔に分ける)
      do k = 1, 8
        in = i + din8(k)
        jn = j + djn8(k)
        if (chn%pid(in,jn) == ipl) cycle
        if (g%x(in,jn) <= 0) cycle
        q = m_swflow_enc_edge_flux(i, j, in, jn) * dt
        if (chn%pod(i,j) == k .or. chn%pod(in,jn) == 9 - k) then
          if (q > 0.0) then
            rr(2) = rr(2) + real(q, real64)
          else
            rr(6) = rr(6) - real(q, real64)
          end if
        else
          if (q > 0.0) then
            rr(3) = rr(3) + real(q, real64)
          else
            rr(7) = rr(7) - real(q, real64)
          end if
        end if
        rr(5) = rr(5) + real(q, real64)
      end do
      ! 雨(boundary_h が足した区画のセルの雨)と減水深(系外へ)
      rr(1) = rr(1) + real(s%pre(i,j) * dt, real64) * pd%dxdy
      pc = min(pd%perc * dt, max(s%h(i,j), 0.0))
      if (pd%wq .and. pc > 0.0) then
        ! 減水深に同伴する物質(地表の濃度で系外へ。セル面積基底で記録。§119.10)
        if (s%cq(i,j) > 0.0) then
          w = s%cq(i,j) * min(pc / s%h(i,j), 1.0)
          s%cq(i,j) = s%cq(i,j) - w
          s%fmpd(i,j) = s%fmpd(i,j) + w * s%gv(i,j)
        end if
      end if
      s%h(i,j) = s%h(i,j) - pc
      s%e(i,j) = s%z(i,j) + s%h(i,j)
      rr(4) = rr(4) + real(s%gv(i,j) * pc, real64) * pd%dxdy
    end do
    pd%rows(j,1:4) = pd%rows(j,1:4) + rr(1:4)
    pd%rows(j,5) = rr(5)
    pd%rows(j,6:7) = pd%rows(j,6:7) + rr(6:7)
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 台帳の行部分和(B): 種類ごとの区画の水の量 gv·h(列 1・2)と、畦畔高まで満ちたセルの数(列 3・4)
!----------------------------------------------------------------------
subroutine plot_rows(pd, g, s, hfull, srow)
  type(t_paddy), intent(in) :: pd
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, intent(in) :: hfull
  real(real64), intent(inout) :: srow(dcp%js:, 1:)
  integer :: i, j, c
  if (.not. pd%enabled) return
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      c = chn%pcl(i,j)
      if (c <= 0) cycle
      srow(j,c) = srow(j,c) + real(s%gv(i,j) * s%h(i,j), real64)
      if (s%h(i,j) >= hfull) srow(j,c+2) = srow(j,c+2) + 1.0_real64
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 区画の水の量の合計 (m3。gv·h·A の行部分和の決定的総和。collective。B)
!----------------------------------------------------------------------
real(real64) function plot_store(pd, g, s)
  type(t_paddy), intent(in) :: pd
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64), allocatable :: r1(:)
  integer :: i, j
  allocate(r1(dcp%js:dcp%je), source = 0.0_real64)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (chn%pcl(i,j) <= 0) cycle
      r1(j) = r1(j) + real(s%gv(i,j) * s%h(i,j), real64)
    end do
  end do
  call par_sum_rows(r1, plot_store)
  plot_store = plot_store * pd%dxdy
end function


!----------------------------------------------------------------------
! 水質(fn_wq)と併用するかの設定(§119.10): 有効なら事前の湛水の濃度 pd_wq_c0 を読み、減水深で系外へ出る
! 物質の記録 s%fmpd を確保する(A のタンクのプールは呼び出し側が確保する)
!----------------------------------------------------------------------
subroutine setup_wq(pd, list, s)
  type(t_paddy), intent(inout) :: pd
  type(t_list_paddy), intent(in) :: list
  type(t_state), intent(inout) :: s
  if (.not. s%wq_active) then
    if (list%pd_wq_c0 > -9998.0) call par_info("paddy: pd_wq_c0 is not used (fn_wq is not enabled)")
    return
  end if
  pd%wq = .true.
  pd%c0 = param_default("paddy", "pd_wq_c0", list%pd_wq_c0, 0.0, " mg/L", unset = -9999.0)
  if (.not. (pd%c0 >= 0.0)) call par_stop("list_paddy: pd_wq_c0 must be >= 0 (mg/L)")
  allocate(s%fmpd(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (pd%rep == 0) then
    call par_info("paddy: water quality (fn_wq): the paddy tanks carry the substance in well-mixed pools")
  else
    call par_info("paddy: water quality (fn_wq): the percolation of the plot water carries the substance")
  end if
end subroutine


!----------------------------------------------------------------------
! タンクのプールの物質の移動(片方向。§119.10): 雨を足した後の湛水深 h1 から落水 dv・越流 sp が出て、
! 残りから減水深 pc が出る。プール(セル面積基底)からタンクの濃度で、地表へ出る量を msur に、系外へ出る
! 量を fm に足す(水田の上の雨の物質は m_wq が後でプールに入れる)
!----------------------------------------------------------------------
pure subroutine pool_move(pool, h1, dv, sp, pc, msur, fm)
  real, intent(inout) :: pool, msur, fm
  real, intent(in) :: h1, dv, sp, pc
  real :: w, h2
  if (pool <= 0.0 .or. h1 <= 0.0) return
  if (dv + sp > 0.0) then
    w = pool * min((dv + sp) / h1, 1.0)
    pool = pool - w
    msur = msur + w
  end if
  h2 = h1 - dv - sp
  if (pc > 0.0 .and. h2 > 0.0) then
    w = pool * min(pc / h2, 1.0)
    pool = pool - w
    fm = fm + w
  end if
end subroutine


!----------------------------------------------------------------------
! 初版で併用できない機能・実行形態を停止する
!----------------------------------------------------------------------
subroutine check_combinations(p, multi)
  type(t_sysparam), intent(in) :: p
  logical, intent(in) :: multi
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
  if (pd%rep == 1) then
    ! 区画の解像(B)では、サブグリッドのタンク(A)だけの入力を停止する
    if (len_trim(list%fn_pd_frac) > 0 .or. list%pd_frac > -9998.0) call a_only("fn_pd_frac and pd_frac")
    if (len_trim(list%fn_pd_adopt) > 0 .or. list%pd_adopt > -9998.0) then
      call a_only("fn_pd_adopt and pd_adopt (give the outlet classes of the plots with fn_pd_class)")
    end if
    if (list%pd_aplot > -9998.0) call a_only("pd_aplot (the plots are resolved by the grid)")
    if (list%f_pd_exchange > -9998) then
      call a_only("f_pd_exchange (the resolved plots exchange water with their surroundings both ways)")
    end if
  else
    if (len_trim(list%fn_pd_outlet) > 0 .or. len_trim(list%fn_pd_class) > 0) then
      call par_stop("list_paddy: fn_pd_outlet and fn_pd_class require fn_pd_plot (the resolved plots)")
    end if
    pd%aplot = param_default("paddy", "pd_aplot", list%pd_aplot, 3000.0, " m2", unset = -9999.0)
    if (.not. (pd%aplot > 0.0)) call par_stop("list_paddy: pd_aplot must be > 0 (m2)")
  end if
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
  if (pd%rep == 1) return
  if (list%f_pd_exchange <= -9998) then
    pd%exch = 0
    call par_info("paddy: f_pd_exchange = 0 (default)")
  else
    pd%exch = list%f_pd_exchange
    call par_info("paddy: f_pd_exchange = "//itoa(pd%exch))
  end if
  if (pd%exch < 0 .or. pd%exch > 1) then
    call par_stop("list_paddy: f_pd_exchange must be 0(one-way: rain only) or 1(two-way: flood water also " &
                  //"enters the paddy fields): "//itoa(pd%exch))
  end if
contains
  subroutine a_only(name)
    character(len=*), intent(in) :: name
    call par_stop("list_paddy: "//name//" are for the subgrid paddy tanks and cannot be combined with " &
                  //"fn_pd_plot (the resolved plots)")
  end subroutine
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
  if (pd%rep == 1) then
    write(line, '(a,es11.4,a,es11.4,a)') "paddy: resolved plots: plot area with normal outlets ", pd%area(1), &
          " m2, with paddy-dam outlets ", pd%area(2), " m2"
  else
    write(line, '(a,es11.4,a,es11.4,a)') "paddy: paddy area with normal outlets ", pd%area(1), &
          " m2, with paddy-dam outlets ", pd%area(2), " m2"
  end if
  call par_info(trim(line))
  do c = 1, pd_nclass
    if (.not. pd%have(c)) cycle
    associate (dv => pd%dev(c))
      hq = pd%hlev
      q = dev_q(dv, pd%gt, hq, 0.0)
      if (pd%rep == 1) then
        write(line, '(a,i0,a,a,a,g0.4,a,g0.4,a)') "  class ", c, ": ", trim(kname(dv%kind)), &
              ", drains above ", dv%zlow, " m; outflow at the levee crest (free) ", &
              q * 1.0e3, " L/s per outlet"
      else
        write(line, '(a,i0,a,a,a,g0.4,a,g0.4,a)') "  class ", c, ": ", trim(kname(dv%kind)), &
              ", drains above ", dv%zlow, " m; outflow at the levee crest (free) ", &
              q / pd%aplot * 3.6e6, " mm/h of the paddy area"
      end if
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
  character(:), allocatable :: head
  if (.not. is_root) return
  open(newunit=pd%un_csv, file=trim(p%dir_result)//"/paddy.csv", status='replace')
  ! 水質(§119.10)・浮遊砂(§119.11)と併用するときだけ、その列を末尾に足す(既存の列の位置は変えない)
  head = "time(s),area1(m2),area2(m2),rain(m3),outflow(m3),spill(m3),perc(m3),store1(m3)," // &
         "store2(m3),residual(m3),qsurf(m3/s),h1(mm),h2(mm),full1(-),full2(-),inflow(m3),levee_in(m3)"
  if (pd%wq) head = head // ",c1(mg/L),c2(mg/L)"
  if (pd%sed) head = head // ",sed(m3)"
  write(pd%un_csv, '(a)') head
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
    write(un) save_version, dcp%nx_g, dcp%ny_g, merge(1, 0, pd%have(1)), merge(1, 0, pd%have(2)), pd%exch, &
              pd%rep, merge(1, 0, pd%wq), merge(1, 0, pd%sed)
  end if
  ! 湛水深はタンク(A)だけ。B の区画の水は浅水流の h(state.dat)にあり、ここはヘッダ(表現の印)だけ。
  ! 水質と併用する A はタンクのプールの物質も(§119.10。地表の物質は wq.dat)
  if (pd%rep == 0) then
    if (pd%have(1)) call restart_write_cell(un, s%hpn)
    if (pd%have(2)) call restart_write_cell(un, s%hpd)
    if (pd%wq) then
      if (pd%have(1)) call restart_write_cell(un, s%cpn)
      if (pd%have(2)) call restart_write_cell(un, s%cpd)
    end if
    ! 浮遊砂の堆積の記録(地形変化の刻み dt_geomorph の途中で保存したときに残る分。§119.11)
    if (pd%sed) call restart_write_cell(un, s%pdsd)
  end if
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
  integer :: un, hd(1:9), k
  fname = trim(p%dir_save)//'/paddy.dat'
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("paddy: state file not found (was fn_paddy enabled when saving): "//fname)
  un = 0
  hd(:) = 0
  if (is_root) then
    open(newunit=un, file=fname, form='unformatted', status='old', action='read')
    read(un) hd
  end if
  do k = 1, 9
    call par_allreduce_maxi(hd(k))
  end do
  if (hd(1) /= save_version) then
    call par_stop("paddy: state file format version "//itoa(hd(1))//" does not match the version this " &
                  //"executable reads ("//itoa(save_version)//"): "//fname)
  end if
  if (hd(2) /= dcp%nx_g .or. hd(3) /= dcp%ny_g .or. ((hd(4) > 0) .neqv. pd%have(1)) .or. &
      ((hd(5) > 0) .neqv. pd%have(2))) then
    call par_stop("paddy: the grid or the classes of paddy fields differ from the saved state "//fname)
  end if
  if (hd(7) /= pd%rep) then
    call par_stop("paddy: the representation of the paddy fields differs from the saved state (subgrid tanks " &
                  //"with fn_pd_frac / pd_frac, or resolved plots with fn_pd_plot): "//fname)
  end if
  if (hd(6) /= pd%exch) then
    call par_stop("paddy: f_pd_exchange differs from the saved state (the surface water of paddy cells is " &
                  //"stored differently in one-way and two-way runs): "//fname)
  end if
  if ((hd(8) > 0) .neqv. pd%wq) then
    call par_stop("paddy: water quality (fn_wq) differs from the saved state (the paddy tanks carry the " &
                  //"substance only with fn_wq): "//fname)
  end if
  if ((hd(9) > 0) .neqv. pd%sed) then
    call par_stop("paddy: suspended sediment (f_suspend) with f_pd_exchange=1 differs from the saved state: "//fname)
  end if
  if (pd%rep == 0) then
    if (pd%have(1)) call restart_read_cell(un, s%hpn)
    if (pd%have(2)) call restart_read_cell(un, s%hpd)
    if (pd%wq) then
      if (pd%have(1)) call restart_read_cell(un, s%cpn)
      if (pd%have(2)) call restart_read_cell(un, s%cpd)
    end if
    if (pd%sed) call restart_read_cell(un, s%pdsd)
  end if
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
