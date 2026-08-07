module m_geomorph
  ! ================= 地形変化プロセスモジュール =================
  ! 河道床の浸食・堆積、badland の浸食、斜面クリープなど、複数の
  ! 地形変化モデルを「重ね合わせ可能なプロセス」として実装する場所。
  !
  ! 設計方針:
  !   - 有効化は list_sysparam の fn_geomorph 指定の有無で決まる
  !     (precip/record と同じ流儀。未指定なら本モジュールは完全に不活性)
  !   - プロセスは排他選択でなく独立フラグの重ね合わせ(演算子分割)。
  !     新モデルの追加 = 「フラグ+パラメータ+サブルーチン1本」で閉じ、
  !     既存プロセスには触れない
  !   - 更新は dt_geomorph 間隔の間欠実行(流れと地形の時定数分離)
  !   - 加速係数 morfac(地形時間の加速。MORFAC 方式): 各プロセスには
  !     実効時間刻み dts = dt * idt_geomorph * morfac を渡す(gwflow の
  !     dts 供給と同じ慣習)。morfac は全プロセス共通の1個
  !     (プロセス別にすると「地形の時間」が分裂するため)。
  !     解釈: 1回の計算 = morfac 回の同一イベントぶんの地形変化
  !
  ! MPI 規約(developer.md §11):
  !   - s%z の更新は自帯 js..je のみ(owner-compute)
  !   - calc の末尾で s%z のハロ交換を行う(次回の自プロセスの近傍参照と、
  !     流れの重力項の近傍参照の両方がこれで賄われる。初回呼び出しの
  !     ハロは初期化の帯+ハロ切り出しで有効)
  !   - enabled / idt / morfac の実行判定は全ランクで同一(collective 安全)
  !   - s%z を更新したら s%e の整合を必ず回復する(河床が変化しても
  !     水面 e でなく水深 h を保存する、が本モジュールの契約)
  ! ==============================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use list_geomorph, only : t_list_geomorph, list_geomorph_read
  use m_parallel, only : par_info, par_stop, dcp, par_halo_cell
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

  type t_geomorph
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.     ! fn_geomorph 指定の有無で決まる
    integer :: idt_geomorph = 1      ! 更新間隔(ステップ数)
    real :: morfac = 1.0             ! 加速係数(全プロセス共通)
    integer :: f_creep = 0           ! 斜面クリープ(0:無効, 1:有効)
    real :: creep_d = 0.0            ! クリープ拡散係数 (m2/s)
    logical :: initialized = .false.
  end type

  ! クリープの私有作業領域(単一インスタンス前提。developer.md §12。
  ! t_geomorph は calc に intent(in) で渡るため、スクラッチは
  ! m_gwflow_lateral の glt と同じモジュール私有に置く)
  type t_creep
    real :: ainv = 0.0               ! 1 / (dx*dy)
    real :: cw(1:4) = 0.0            ! エッジ伝導度重み(= 通過幅/距離)
    real, allocatable :: q(:,:,:)    ! エッジ流量4成分 (m3/s)。一時作業領域
  end type
  type(t_creep) :: crp

contains


!----------------------------------------------------------------------
! 地形変化モジュールを初期化する
!   fn_geomorph が未指定なら何もしない(enabled = .false. のまま)
!----------------------------------------------------------------------
subroutine m_geomorph_init(gm, p, g)
  type(t_geomorph), intent(out) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_geomorph) :: list

  ! 設定ファイル未指定 = 地形変化なし(デフォルトの enabled = .false.)
  if (len_trim(p%fn_geomorph) == 0) return

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

  ! (将来のプロセスの検証をここに追加する)

  gm%enabled = .true.
  gm%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 地形変化を計算する(dt_geomorph 間隔で run_main から毎ステップ呼ばれる)
!   有効なプロセスを順に適用して s%z を更新する(演算子分割)。
!   各プロセスは実効時間刻み dts(加速係数込み)ぶんの変化を適用する。
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

  ! --- 有効なプロセスを順に適用(それぞれ自帯 js..je の s%z を更新) ---
  if (gm%f_creep > 0) call calc_creep(gm, g, s, dts)
  ! (将来のプロセスの適用をここに追加する)
  ! TODO(F1a): s%sd 導入後は、各プロセスの Δz を s%sd にも共動適用する
  ! (浸食で土層が薄くなる結合。geomorph_plan.md §2.5)

  ! --- s%e の整合を回復する(本モジュールは水深 h を保存する契約) ---
  !$omp parallel do schedule(static) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      s%e(i,j) = s%z(i,j) + s%h(i,j)
    end do
  end do
  !$omp end parallel do

  ! --- s%z のハロ交換 ---
  ! 自プロセスの次回の近傍参照(クリープの ±1)と、流れの重力項の
  ! 近傍参照の両方が、この1回の交換で賄われる(developer.md §11)
  call par_halo_cell(s%z)

end subroutine


!----------------------------------------------------------------------
! 斜面クリープの初期化(重み・スクラッチ・安定条件の静的検査)
!   離散化は4近傍の保存形フラックス(5点ラプラシアン)。等方線形拡散
!   D∇²z に厳密に整合し、ガウス丘の解析解ベンチマークと直接比較できる。
!   斜め成分の枠(cw(1), cw(3) = 0)は構造として確保してあり、8近傍化は
!   cw の重み定義の変更で閉じる(その際は実効拡散係数が D と一致する
!   重みの正規化を必ず検証すること)
!----------------------------------------------------------------------
subroutine init_creep(gm, p, g)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real :: dts, dt_lim
  character(len=256) :: msg

  crp%ainv = 1.0 / (g%dx * g%dy)
  ! エッジ伝導度重み = 通過幅 / セル中心間距離(4近傍のみ)
  crp%cw(1) = 0.0             ! 斜め(未使用)
  crp%cw(2) = g%dx / g%dy     ! 法線 y 方向(通過幅 dx、距離 dy)
  crp%cw(3) = 0.0             ! 斜め(未使用)
  crp%cw(4) = g%dy / g%dx     ! 法線 x 方向(通過幅 dy、距離 dx)

  ! 陽解法(FTCS)の安定条件の静的検査: D*dts*(1/dx^2+1/dy^2) <= 1/2。
  ! D・格子・dts がすべて namelist 由来の静的量なので init で確定できる
  ! (判定は全ランク同一 → par_stop の collective 条件を満たす)
  dts = p%dt * gm%idt_geomorph * gm%morfac
  dt_lim = 0.5 / (gm%creep_d * (1.0 / g%dx**2 + 1.0 / g%dy**2))
  write(msg,'(a,es10.3,a,es10.3,a)') "geomorph creep: dt limit = ", dt_lim, &
                                     " s (dts = ", dts, " s)"
  call par_info(trim(msg))
  if (dts > dt_lim) then
    call par_stop("geomorph creep: dts exceeds the explicit stability limit " &
                  // "(reduce dt_geomorph/morfac/creep_d)")
  end if

  ! エッジ流量4成分(一時作業領域)。j 範囲はセル j を挟むエッジが
  ! j-1 と j にあるため下限 jsh-1(m_swflow_enc の uv/mn と同形)。
  ! 確保時 0: マスク・斜め成分の書かれないエッジは恒久 0(無フラックス)
  allocate(crp%q(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)
end subroutine


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
subroutine calc_creep(gm, g, s, dts)
  type(t_geomorph), intent(in) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt
  real :: gq, dv
  logical :: okc

  ! --- ループ1: エッジ流量(各成分の書き手は一意なので競合しない) ---
  !   帯界面のエッジ成分 k=1..3(行 je)はハロ行 je+1 の書き手が担う
  !   (冗長計算。全域端では行が存在せず対象外)
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) private(i, j, k, in, jn, okc, gq)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        ! z は毎回変わるため、条件を満たさない場合も必ず 0 を代入する
        gq = 0.0
        if (crp%cw(k) > 0.0 .and. okc .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            ! エッジ流量(書き手 c から k 近傍 n に向かい正)
            gq = gm%creep_d * (s%z(i,j) - s%z(in,jn)) * crp%cw(k)
          end if
        end if
        crp%q(k, i+die(k), j+dje(k)) = gq
      end do
    end do
  end do
  !$omp end parallel do

  ! --- ループ2: 発散を取り z を更新 ---
  !   マスク・斜め成分のエッジは 0 が入っているため無条件に8近傍を
  !   集計できる(流出の総和が正)
  !$omp parallel do schedule(static) private(i, j, k, dv)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      dv = 0.0
      do k = 1, 8
        dv = dv + sign_e(k) * crp%q(ke(k), i+die(k), j+dje(k))
      end do
      s%z(i,j) = s%z(i,j) - dv * dts * crp%ainv
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! 地形変化モジュールを破棄する
!----------------------------------------------------------------------
subroutine m_geomorph_dispose(gm)
  type(t_geomorph), intent(inout) :: gm
  if (allocated(crp%q)) deallocate(crp%q)
  gm%enabled = .false.
  gm%initialized = .false.
end subroutine

end module
