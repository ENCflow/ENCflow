module m_geomorph
  ! ================= 地形変化プロセスモジュール =================
  ! 河道床の浸食・堆積、badland の浸食、斜面クリープなど、複数の
  ! 地形変化モデルを「重ね合わせ可能なプロセス」として実装する場所。
  !
  ! 設計方針:
  !   - 有効化は list_sysparam の fn_geomorph 指定の有無で決まる
  !     (precip/record と同じ流儀。未指定なら本モジュールは完全に不活性)
  !   - プロセスは排他選択でなく独立フラグの重ね合わせ(演算子分割。
  !     適用順は fluvial → creep)。新モデルの追加 = 「フラグ+パラメータ+
  !     サブルーチン1本」で閉じ、既存プロセスには触れない
  !   - 更新は dt_geomorph 間隔の間欠実行(流れと地形の時定数分離)
  !   - 加速係数 morfac(地形時間の加速。MORFAC 方式): 各プロセスには
  !     実効時間刻み dts = dt * idt_geomorph * morfac を渡す(gwflow の
  !     dts 供給と同じ慣習)。morfac は全プロセス共通の1個
  !     (プロセス別にすると「地形の時間」が分裂するため)。
  !     解釈: 1回の計算 = morfac 回の同一イベントぶんの地形変化
  !   - 土層厚 s%sd との結合(geomorph_plan.md §2.5): 掃流砂(fluvial)は
  !     Δz を s%sd に共動適用する(浸食で土層が薄くなり、gwflow の容量
  !     sd*sy0 が縮む=飽和・流出の早期化。z と sd が同じ Δz で動くため
  !     帯水層底 (z - sd) は不変=岩盤固定が構造的に成立)。浸食は
  !     sd >= 0 の範囲(sd=0 は岩盤露出)。クリープは当面 sd に触れない
  !     (土層のない理想地形のベンチマーク用途を保つ。TODO: 実地形で
  !     クリープを使う段になったら sd 共動と可動層クランプを追加する)
  !
  ! MPI 規約(developer.md §11):
  !   - s%z / s%sd の更新は自帯 js..je のみ(owner-compute)
  !   - calc の末尾で s%z, s%sd のハロ交換を行う(次回の自プロセスの
  !     近傍参照と、流れの重力項・gwflow 側方の近傍参照を賄う。
  !     初回呼び出しのハロは初期化の帯+ハロ切り出し/転記で有効)
  !   - enabled / idt / morfac の実行判定は全ランクで同一(collective 安全)
  !   - s%z を更新したら s%e の整合を必ず回復する(河床が変化しても
  !     水面 e でなく水深 h を保存する、が本モジュールの契約)
  !
  ! 制約(実装済みの明示ガード):
  !   - STG(f_gridsystem=1)は非対応(init 時コピーのため z の時間発展に
  !     追従しない。init で par_stop)
  ! サブグリッド河道幅(fn_width)との併用(2026-08-07 対応):
  !   掃流砂はエッジ流量に frw(水と同じ開口・幅キャップ)、Δz 換算に
  !   1/wfrac(河道底のみ変動)を乗じる。浮遊砂は移流・E-D とも無修正で
  !   整合(calc_suspend ヘッダ参照)。堤防(§17)エッジ=河道—非河道の
  !   境界では掃流砂を運ばない(掃流砂は河道内に閉じる。越流時の土砂は
  !   浮遊砂が壁込みの実フラックス mn1 で運ぶ)
  ! ==============================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo, m_geoinfo_require_sd
  use m_state, only : t_state
  use list_geomorph, only : t_list_geomorph, list_geomorph_read
  use m_parallel, only : par_info, par_warn, par_stop, dcp, par_halo_cell, &
                         par_allreduce_max
  use m_util, only : itoa, rtoa
  implicit none
  private
  public :: t_geomorph
  public :: m_geomorph_init
  public :: m_geomorph_calc
  public :: m_geomorph_dispose

  ! 8近傍の規約(m_swflow_enc と同一。din/djn=近傍、die/dje/ke/sign_e=
  ! エッジ成分の格納位置と向き。k=1..4 が所有成分、k=5..8 は近傍の所有)
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]
  integer, parameter :: die(1:8) = [ -1,  0,  0, -1,  0, -1,  0,  0]
  integer, parameter :: dje(1:8) = [ -1, -1, -1,  0,  0,  0,  0,  0]
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]

  ! 板倉・岸の浮上量式の定数(実践河川水理学(iRIC)第4章 式(3)-(5)。
  ! 原典: 板倉忠興: 河川における乱流拡散現象に関する研究, 土木試験所報告
  ! 第83号, 1984。定数は原式の値であり namelist にしない)
  real, parameter :: ik_k = 0.008        ! K
  real, parameter :: ik_alpha = 0.14     ! α*
  real, parameter :: ik_bstar = 0.143    ! B*
  real, parameter :: ik_eta0 = 0.5       ! η0

  type t_geomorph
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.     ! fn_geomorph 指定の有無で決まる
    integer :: idt_geomorph = 1      ! 更新間隔(ステップ数)
    real :: morfac = 1.0             ! 加速係数(全プロセス共通)
    integer :: f_creep = 0           ! 斜面クリープ(0:無効, 1:有効)
    real :: creep_d = 0.0            ! クリープ拡散係数 (m2/s)
    integer :: f_fluvial = 0         ! 掃流砂 Exner(0:無効, 1:有効)
    integer :: f_qbform = 1          ! 流砂量式(1:芦田・道上, 2:MPM)
    real :: d50 = 0.0                ! 掃流砂の代表粒径 (m)
    real :: tausc = 0.05             ! 掃流の限界無次元掃流力 τ*c
    real :: poroi = 0.0              ! 1 / (1 - λ)(λ: 河床の空隙率。掃流・浮遊共有)
    real :: sgrav = 1.65             ! 土粒子の水中比重 s = (ρs - ρ)/ρ(共有)
    real :: dzmax = 0.0              ! 1エッジ・1更新の河床変動上限 (m)
    integer :: f_bcfeed = 0          ! 開境界の掃流砂給砂(0:流入は無給砂, 1:平衡給砂)
    integer :: f_suspend = 0         ! 浮遊砂(0:無効, 1:有効)
    integer :: f_esform = 1          ! 平衡濃度式(1:超過掃流力線形(簡易))
    real :: sd50 = 0.0               ! 浮遊砂の代表粒径 (m)
    real :: stausc = 0.05            ! 浮遊の限界無次元掃流力 τ*c
    real :: wf = 0.0                 ! 沈降速度 (m/s)(指定 or Rubey 式で導出)
    real :: beta = 1.0               ! 沈降の底面濃度係数(c_b = β・C)
    real :: esa = 0.0                ! 平衡濃度係数(C_eq = esa・(τ*/τ*c - 1))
    integer :: f_wash = 0            ! 斜面浸食(0:無効, 1:有効。f_suspend 必須)
    real :: wkr = 0.0                ! 雨滴侵食係数(無次元)
    real :: wkf = 0.0                ! 面状侵食係数 (m/s)
    real :: wtausc = 0.05            ! 面状侵食の限界無次元掃流力 τ*c
    integer :: f_debris = 0          ! 土石流 E-D(0:無効, 1:有効。f_suspend と排他)
    real :: db_tanphi = 0.0          ! tan(内部摩擦角)
    real :: db_delte = 0.0           ! 侵食速度係数 δe
    real :: db_deltd = 0.0           ! 堆積速度係数 δd
    real :: db_cstar = 0.0           ! 河床の充填濃度 C* = 1 - λ(fluv_porosity から導出)
    integer :: f_dbstop = 0          ! 停止条件の切替(0:なし, 1:低速凝集)
    real :: db_vstop = 0.0           ! 停止判定の速度閾値 (m/s)
    real :: db_wstop = 0.0           ! 低速凝集の河床転換レート (m/s)
    integer :: f_dbres = 0           ! 抵抗則(0:マニング, 1:クーロン+マニング。
                                     !   実体は m_swflow_enc(set_debris で通知))
    logical :: initialized = .false.
  end type

  ! プロセス私有の作業領域(単一インスタンス前提。developer.md §12。
  ! t_geomorph は calc に intent(in) で渡るため、スクラッチは
  ! m_gwflow_lateral の glt と同じモジュール私有に置く)
  type t_creep
    real :: cw(1:4) = 0.0            ! エッジ伝導度重み(= 通過幅/距離)
  end type
  type t_fluvial
    real :: wl(1:8) = 0.0            ! k軸方向フラックスの通過幅 (m)
    real :: ex(1:8) = 0.0            ! k軸方向の単位ベクトル x 成分
    real :: ey(1:8) = 0.0            ! k軸方向の単位ベクトル y 成分
    real :: qbcoef = 0.0             ! 流砂量の次元化係数 sqrt(s g d50^3)
    integer :: nclip = 0             ! dzmax クリップの発生エッジ数(累計)
    real :: vleak = 0.0              ! 岩盤床クリップで失った土砂体積 (m3)(累計)
  end type
  type t_gmwork
    real :: ainv = 0.0               ! 1 / (dx*dy)
    real, allocatable :: q(:,:,:)    ! エッジ流量4成分 (m3/s)。プロセス間で
                                     ! 共有する一時作業領域(各プロセスの
                                     ! ループ1は対象セルの4成分すべてを
                                     ! 0 を含めて必ず上書きする契約)
  end type
  type t_debris
    real :: dist8(1:8) = 0.0         ! 8近傍セル中心までの距離 (m)(最急降下勾配用)
    real, allocatable :: fx(:,:)     ! E-D 交換量の作業領域 (1:nx, js:je)。
                                     !   2パス構造用: パス1が時刻 n の z(近傍参照)
                                     !   から fx を計算し、パス2が適用する。
                                     !   1パスのその場更新は slope8 の近傍読みと
                                     !   競合する(OpenMP データ競合の実バグ)
  end type
  type(t_creep) :: crp
  type(t_fluvial) :: flv
  type(t_debris) :: dbr
  type(t_gmwork) :: wrk

  ! プロセス実装(init/calc)は submodule に分割(m_geomorph_creep /
  ! m_geomorph_fluvial / m_geomorph_suspend。m_swflow_enc の adv/bc/channel と
  ! 同じコード分割用途)。親に残るのは型・定数・共有作業領域・配線
  ! (init/calc の分配)・setup_sd・require_work・dispose。
  ! 注意(§13): submodule 内では contained を使わない(nvfortran の
  ! 二段ホスト結合不具合)。dcp 等の use 経由の名前は submodule 側で
  ! 直接 use する
  interface
    module subroutine init_creep(gm, p, g)
      type(t_geomorph), intent(in) :: gm
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
    end subroutine
    module subroutine calc_creep(gm, g, s, dts)
      type(t_geomorph), intent(in) :: gm
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
      real, intent(in) :: dts
    end subroutine
    module subroutine init_fluvial(gm, p, g, list)
      type(t_geomorph), intent(inout) :: gm
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_list_geomorph), intent(in) :: list
    end subroutine
    module subroutine calc_fluvial(gm, p, g, s, dts)
      type(t_geomorph), intent(in) :: gm
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
      real, intent(in) :: dts
    end subroutine
    module subroutine init_suspend(gm, p, list)
      type(t_geomorph), intent(inout) :: gm
      type(t_sysparam), intent(in) :: p
      type(t_list_geomorph), intent(in) :: list
    end subroutine
    module subroutine calc_suspend(gm, p, g, s, dtw)
      type(t_geomorph), intent(in) :: gm
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
      real, intent(in) :: dtw
    end subroutine
    module subroutine init_wash(gm, list)
      type(t_geomorph), intent(inout) :: gm
      type(t_list_geomorph), intent(in) :: list
    end subroutine
    module subroutine calc_wash(gm, p, g, s, dtw)
      type(t_geomorph), intent(in) :: gm
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
      real, intent(in) :: dtw
    end subroutine
    module subroutine init_debris(gm, g, list)
      type(t_geomorph), intent(inout) :: gm
      type(t_geoinfo), intent(in) :: g
      type(t_list_geomorph), intent(in) :: list
    end subroutine
    module subroutine calc_debris(gm, p, g, s, dtw)
      type(t_geomorph), intent(in) :: gm
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
      real, intent(in) :: dtw
    end subroutine
    ! 共有スクラッチの確保口(実装は m_geomorph_creep 側。gfortran は
    ! private なモジュール手続きをローカルシンボルにするため、submodule
    ! から呼ぶ手続きは分離インターフェース+submodule 実装にする)
    module subroutine require_work(g)
      type(t_geoinfo), intent(in) :: g
    end subroutine
  end interface

contains


!----------------------------------------------------------------------
! 地形変化モジュールを初期化する
!   fn_geomorph が未指定なら何もしない(enabled = .false. のまま)。
!   g は m_geoinfo_require_sd(土層厚の遅延確保)のため inout。
!   s は s%sd への初期値転記のため inout
!----------------------------------------------------------------------
subroutine m_geomorph_init(gm, p, g, s)
  type(t_geomorph), intent(out) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  type(t_state), intent(inout) :: s
  type(t_list_geomorph) :: list

  ! 設定ファイル未指定 = 地形変化なし(デフォルトの enabled = .false.)
  if (len_trim(p%fn_geomorph) == 0) return

  ! STG は非対応(init 時コピーのため z の時間発展に追従しない)
  if (p%f_gridsystem /= 0) then
    call par_stop("m_geomorph: STG(f_gridsystem=1)は地形変化非対応です")
  end if

  call list_geomorph_read(p, list)

  ! --- 解釈と検証(設定ファイル由来の決定的エラーは par_stop で即停止) ---
  if (list%dt_geomorph > 0.0) then
    gm%idt_geomorph = nint(list%dt_geomorph / p%dt)
    if (gm%idt_geomorph <= 0) then
      call par_stop("list_geomorph: dt_geomorph must be >= dt")
    end if
  else
    gm%idt_geomorph = 1                          ! 毎ステップ更新
  end if

  if (list%morfac <= 0.0) then
    call par_stop("list_geomorph: morfac must be > 0")
  end if
  gm%morfac = list%morfac

  gm%f_creep = list%f_creep
  if (gm%f_creep > 0) then
    if (list%creep_d <= 0.0) then
      call par_stop("list_geomorph: f_creep requires creep_d > 0")
    end if
    gm%creep_d = list%creep_d
    call init_creep(gm, p, g)
  end if

  gm%f_fluvial = list%f_fluvial
  gm%f_suspend = list%f_suspend
  gm%f_wash = list%f_wash
  gm%f_debris = list%f_debris

  ! 土石流 E-D と浮遊砂 E-D は同一の s%hs 上で動くため排他
  ! (二重計上防止。debris_plan.md §2.2)
  if (gm%f_debris > 0 .and. gm%f_suspend > 0) then
    call par_stop("list_geomorph: f_debris と f_suspend は併用できません" &
                  // "(同一の hs に対する E-D の二重計上になります)")
  end if
  ! 土石流はイベント計算であり地形時間の加速は適用外
  if (gm%f_debris > 0 .and. gm%morfac /= 1.0) then
    call par_stop("list_geomorph: f_debris は morfac=1 のみ対応です(イベント計算)")
  end if

  ! --- 土砂プロセス(掃流・浮遊・斜面・土石流)の共有設定 ---
  ! (f_wash は f_suspend 必須なので条件には現れない — init_wash が検証)
  if (gm%f_fluvial > 0 .or. gm%f_suspend > 0 .or. gm%f_debris > 0) then
    ! 河床の物性(共有)
    if (list%fluv_porosity < 0.0 .or. list%fluv_porosity >= 1.0) then
      call par_stop("list_geomorph: fluv_porosity must be in [0,1)")
    end if
    if (list%fluv_sgrav <= 0.0) call par_stop("list_geomorph: fluv_sgrav must be > 0")
    gm%poroi = 1.0 / (1.0 - list%fluv_porosity)
    gm%sgrav = list%fluv_sgrav
    ! サブグリッド河道幅(fn_width)併用時の扱い(geomorph_plan.md §2.1):
    !   掃流砂 = frw(水と同じ開口)× Δz の 1/wfrac(河道底のみ変動)。
    !   浮遊砂 = 移流が continuous のミラーで自動整合、E-D は hs・Δz とも
    !   河道断面あたりの量なので wfrac が相殺し無修正(calc_suspend 参照)。
    !   注意: gwflow 併用時の容量 sd*sy0 はセル全面の土層解釈のままで、
    !   幅セルの sd(河道底の土層)とは近似的な整合(既知の妥協)
    ! 土層厚(=可動層厚)の確保と s%sd への転記
    call setup_sd(p, g, s)
  end if

  if (gm%f_fluvial > 0) call init_fluvial(gm, p, g, list)
  if (gm%f_suspend > 0) call init_suspend(gm, p, list)
  if (gm%f_wash > 0) call init_wash(gm, list)
  if (gm%f_debris > 0) call init_debris(gm, g, list)

  ! 浮遊砂輸送の有効化を通知(swflow_enc がステップ内で s%hs を移流する。
  ! 初期化順序: 本 init は m_swflow_init より前)。土石流(f_debris)も
  ! 同じ advect_scalar による hs 輸送を使う
  s%sed_active = (gm%f_suspend > 0 .or. gm%f_debris > 0)
  ! 土石流モデルの有効化を通知(swflow_enc が運動量へ hs を算入し抵抗則を
  ! 切り替える。抵抗則のパラメータは init_debris が set_debris で渡し済み)
  s%debris_active = (gm%f_debris > 0)

  ! (将来のプロセスの検証をここに追加する)

  gm%enabled = .true.
  gm%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 土層厚(=可動層厚)の確保と s%sd への転記(m_gwflow_init と同じ規約の
! 第2の利用者。geomorph init が先に走るため、gwflow 併用時はこちらの
! 転記が先に行われる — 値は同じ g%sd 由来で同一)
!----------------------------------------------------------------------
subroutine setup_sd(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  type(t_state), intent(inout) :: s
  real :: sdmax(1)

  call m_geoinfo_require_sd(g)
  if (p%f_state_restore > 0) then
    ! restore 時は転記しない(復元値が勝つ)。土層ゼロの save を
    ! 浸食計算に使う設定齟齬は停止(判定は全ランク同一 = collective 安全)
    sdmax(1) = maxval(s%sd(:, dcp%js:dcp%je))
    call par_allreduce_max(sdmax)
    if (sdmax(1) <= 0.0) then
      call par_stop("geomorph: 復元した save に土層厚がありません(旧構成で作成された" &
                    // " save)。restore を使わないか、save を作り直してください")
    end if
  else
    s%sd(:,:) = g%sd(:,:)
  end if
end subroutine


!----------------------------------------------------------------------
! 地形変化を計算する(dt_geomorph 間隔で run_main から毎ステップ呼ばれる)
!   有効なプロセスを順に適用して s%z(fluvial は s%sd も)を更新する
!   (演算子分割)。各プロセスは実効時間刻み dts(加速係数込み)ぶんの
!   変化を適用する。
!   注意: 冒頭の return 判定はすべて全ランクで同一(collective 安全)
!----------------------------------------------------------------------
subroutine m_geomorph_calc(gm, p, g, s, it)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  integer :: i, j
  real :: dts

  if (.not. gm%enabled) return
  if (mod(it, gm%idt_geomorph) /= 0) return

  ! 実効時間刻み(間欠実行 × 加速係数)
  dts = p%dt * gm%idt_geomorph * gm%morfac

  ! --- 有効なプロセスを順に適用(それぞれ自帯 js..je を更新) ---
  ! 浮遊砂の E-D は水柱側が水理時間(morfac なし)、河床側が ×morfac の
  ! 台帳分離(MORFAC 方式。geomorph_plan.md §4)のため dtw を別に渡す
  ! 土石流 E-D は最初に適用する: 最急降下勾配が近傍の s%z を読むため、
  ! 他プロセスが帯内の z を先に動かすとハロ行(時刻 n のまま)との
  ! 不整合でランク数依存になる。先頭なら全セル・ハロとも時刻 n の z で
  ! 一貫する(ハロはステップ頭の swflow 交換で最新)
  if (gm%f_debris > 0) call calc_debris(gm, p, g, s, p%dt * gm%idt_geomorph)
  if (gm%f_fluvial > 0) call calc_fluvial(gm, p, g, s, dts)
  if (gm%f_suspend > 0) call calc_suspend(gm, p, g, s, p%dt * gm%idt_geomorph)
  if (gm%f_wash > 0) call calc_wash(gm, p, g, s, p%dt * gm%idt_geomorph)
  if (gm%f_creep > 0) call calc_creep(gm, g, s, dts)
  ! (将来のプロセスの適用をここに追加する)

  ! --- s%e の整合を回復する(本モジュールは水深 h を保存する契約) ---
  !$omp parallel do schedule(static) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      s%e(i,j) = s%z(i,j) + s%h(i,j)
    end do
  end do
  !$omp end parallel do

  ! --- s%z / s%sd のハロ交換 ---
  ! 自プロセスの次回の近傍参照(±1)と、流れの重力項・gwflow 側方の
  ! 近傍参照が、この1回の交換で賄われる(developer.md §11)
  call par_halo_cell(s%z)
  if (gm%f_fluvial > 0 .or. gm%f_suspend > 0 .or. gm%f_debris > 0) then
    call par_halo_cell(s%sd)
  end if
  ! s%hs のハロは swflow_enc のステップ頭交換が担う(移流の直前に最新化)

end subroutine


!----------------------------------------------------------------------
! 斜面クリープの初期化(重み・スクラッチ・安定条件の静的検査)
!   離散化は4近傍の保存形フラックス(5点ラプラシアン)。等方線形拡散
!   D∇²z に厳密に整合し、ガウス丘の解析解ベンチマークと直接比較できる。
!   斜め成分の枠(cw(1), cw(3) = 0)は構造として確保してあり、8近傍化は
!   cw の重み定義の変更で閉じる(その際は実効拡散係数が D と一致する
!   重みの正規化を必ず検証すること)


!----------------------------------------------------------------------
! 掃流砂 Exner の初期化(検証・重み。共有設定(物性・sd・幅ガード)は
! m_geomorph_init の土砂プロセス共有部で設定済み)


!----------------------------------------------------------------------
! 浮遊砂の初期化(検証・沈降速度の導出)
!   移流は m_swflow_enc がステップ内で行う(sed_active。エッジ作業領域は
!   不要)。ここは E-D 交換(calc_suspend)のパラメータのみ


!----------------------------------------------------------------------
! 板倉・岸の浮上量式による平衡濃度 ceq = q_su / w_f
!   実践河川水理学(iRIC)第4章 式(4)(5)。原典: 板倉(1984)。
!     q_su/√(sgd) = K( α*・(ρ/ρs)・Ω/√τ* − w_f/√(sgd) )
!     Ω = (τ*/B*)・[∫_{a'}^∞ ξ(1/√π)e^{−ξ²}dξ / ∫_{a'}^∞ (1/√π)e^{−ξ²}dξ]
!         + τ*/(B*η0) − 1
!       = (τ*/B*)・e^{−a'²}/(√π・erfc(a')) + τ*/(B*η0) − 1
!     a' = B*/τ* − 1/η0、ρ/ρs = 1/(s+1)(s: 水中比重)
!   自己整合性: τ*→0 で a'→∞、比 → a' の漸近から Ω→0(E は必ず負で
!   浸食なし)。a' > 20 は erfc のアンダーフロー域なので 0 で打ち切る
!   (その領域では q_su < 0 が保証される)


!----------------------------------------------------------------------
! Rubey 式の沈降速度
!   w_f = F * sqrt(s g d), F = sqrt(2/3 + 36ν²/(s g d³)) − sqrt(36ν²/(s g d³))
!   (ν = 1.0e-6 m²/s: 清水 20℃ 相当)




!----------------------------------------------------------------------
! 掃流砂 Exner(平衡流砂量による河床の浸食・堆積)
!   保存形の2ループ構造(m_gwflow_lateral と同型):
!     ループ1: エッジの掃流砂フラックス(時刻 n の状態から。
!              書き手はハロ行 je+1 まで=帯界面の冗長計算)
!     ループ2: 発散を取り z と sd を共動更新(自帯 js..je のみ)+
!              gwflow 有効時の容量縮小超過分の地表水への引き渡し
!   エッジ水理量は両セル平均(摩擦項 calc_kth_flux と同じ閉じ方)、
!   流向はセル平均流速のエッジ法線射影。土砂体積は反対称集計により
!   機械精度で保存される(岩盤床クリップ時の損失は vleak に計上)。
!   平衡仮定: 掃流砂の適応距離は局所(格子スケールで平衡が成立)。
!   τ* = n^2 V^2 / (s d50 h^{1/3})(マニング閉じ。有効掃流力の分離は
!   簡略化して省く — 平坦床相当)


!----------------------------------------------------------------------
! 浮遊砂の浸食・沈降(E-D 交換。セル内の鉛直交換のみ=エッジ・ハロ不要)
!   移流は swflow_enc がステップ内で実施済み(sed_active)。ここでは
!   平衡濃度 C_eq への緩和として河床との交換を行う:
!     E = w_f・C_eq(浸食。可動層 sd の範囲でクランプ)
!     D = w_f・β・C (沈降。浮遊量 hs の範囲でクランプ。C = hs/h)
!   C_eq は f_esform で選択(1: 超過掃流力線形 C_eq = esa・(τ*/τ*c − 1)。
!   板倉・岸等の実装は式の case 追加で閉じる)。
!   τ* はセル値(rn, vv, h)からマニング閉じで導出(calc_fluvial と同型)。
!   乾燥セル(h <= dd)は浮遊分を全量河床へ繰り入れる(水のない浮遊砂を
!   残さない。乾湿の激しい氾濫原で必須の閉じ)。
!   サブグリッド河道幅(fn_width)セルでも本ルーチンは無修正で整合する:
!   hs は h と同じ貯留規約(河道断面あたりの柱状量)、Δz も河道底の
!   厚さ変化なので、交換式 dzb = -fx・morfac・poroi から wfrac が相殺する
!   (セル内の実体積は両辺とも ×wfrac・dx・dy)。
!   MORFAC の台帳分離: 水柱側(hs)は水理時間 dtw、河床側(z, sd)は
!   ×morfac(1回の計算 = morfac 回のイベントぶんの河床変化)。
!   morfac=1 では hs と河床の交換が厳密に反対称になり、
!   Σhs + (1−λ)Σ(z−z0) が機械精度で保存される(test/suspend が検定)


!----------------------------------------------------------------------
! 斜面クリープ(線形拡散 dz/dt = D * div(grad z))
!   保存形の2ループ構造(m_gwflow_lateral と同型):
!     ループ1: エッジ流量(時刻 n の z から。書き手はハロ行 je+1 まで)
!     ループ2: 発散を取り z を更新(自帯 js..je のみ)
!   エッジ流量の反対称集計により土砂体積は機械精度で厳密に保存される。
!   帯界面のエッジは両ランクが同一のハロ入力から冗長計算する
!   (ビット厳密な配布。§11「冗長計算=配布機構」)。
!   読み: s%z の自セルと4近傍(ハロは前回 calc 末尾の交換、初回は
!         初期化の帯+ハロ切り出しで有効)
!   書き: 自帯 js..je の s%z のみ(e の回復とハロ交換は呼び出し側)
!   境界: 領域外(x=0)・海(sw>0)とは無フラックス(海域の地形は不変)


!----------------------------------------------------------------------
! 地形変化モジュールを破棄する
!   fluvial のガード発動(dzmax クリップ・岩盤床クリップ)を報告する
!   (ランク局所の診断なので par_warn。stderr のため回帰比較には入らない)
!----------------------------------------------------------------------
subroutine m_geomorph_dispose(gm)
  type(t_geomorph), intent(inout) :: gm
  if (flv%nclip > 0) then
    call par_warn("geomorph fluvial: dzmax クリップが " &
                  // itoa(flv%nclip) // " エッジで発動しました" &
                  // "(dt_geomorph/morfac の見直しを推奨)")
  end if
  if (flv%vleak > 0.0) then
    call par_warn("geomorph fluvial: 岩盤床クリップで " &
                  // rtoa(flv%vleak) // " m3 の土砂収支誤差が生じました")
  end if
  if (allocated(wrk%q)) deallocate(wrk%q)
  if (allocated(dbr%fx)) deallocate(dbr%fx)
  flv%nclip = 0
  flv%vleak = 0.0
  gm%enabled = .false.
  gm%initialized = .false.
end subroutine

end module
