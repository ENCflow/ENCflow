module m_gwflow
  ! ================= 地下水プロセスモジュール(切替器) =================
  ! 鉛直浸透・貯留(vertical)と側方流動(lateral)の2群を持ち、それぞれ
  ! 複数のモデルを排他切替で使う(handoff_gwflow_tani.md §2.2)。
  !   - 有効化は fn_gwflow の指定の有無(未指定なら完全に不活性)
  !   - 鉛直モデルは fn_gwflow 内 &list_gwflow の f_gwvertical で選択
  !     (0 なら fn を書いたまま一時無効化できる)
  !   - 側方モデルは同 f_gwlateral で選択(0:なし, 1:非線形Boussinesq)。
  !     未指定(=0)なら鉛直のみで実行し、側方流動のための資源
  !     (配列・ハロ交換)は一切確保しない
  !   - 加算的な層: f_gwlayer2(風化基岩層)と f_gwconduit(管路連続体層。
  !     下水道網・岩盤亀裂網の等価被圧連続体。m_gwflow_conduit)。
  !     いずれも無効時は資源を一切確保しない
  !   - 加算的なシンク: f_gwpump(井戸揚水・地下水取水。m_gwflow_pump。
  !     無効時は資源を一切確保しない)
  !   - 加算的な修飾: f_gwfrost(凍土による浸透抑制。m_gwflow_frost。
  !     気温(fn_meteo)必須 — 初期化順序の制約により存在検査は m_main が
  !     meteo init 後に m_gwflow_check_meteo で行う。無効時は資源ゼロ)
  !   - 鉛直の束縛は t_gwflow の手続きポインタ成分(abstract interface +
  !     nopass)。側方は当面単一モデルのため直接呼び出し(第2の側方
  !     モデルが実在した時点でポインタ束へ昇格する。等価リファクタとして
  !     逐次ビット一致で検証できる。developer.md §16)
  !   - 各モデルの固有設定・内部状態・リスタート保存はモデル私有
  !     (実装の契約は m_gwflow_bucket のヘッダを参照)
  !   - 土層厚 g%sd を要するモデルを選んだときは、モデル init より前に
  !     m_geoinfo_require_sd で帯配列を要求する(developer.md §16)
  ! 呼び出し順: swflow(流れ)→ gwflow(水収支)→ geomorph(地形)
  ! ====================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo, m_geoinfo_require_sd
  use m_state, only : t_state
  use list_gwflow, only : t_list_gwflow, list_gwflow_read
  use m_gwflow_bucket, only : gwflow_bucket_init, gwflow_bucket_calc, gwflow_bucket_dispose
  use m_gwflow_greenampt, only : gwflow_greenampt_init, gwflow_greenampt_calc, &
                                 gwflow_greenampt_dispose
  use m_gwflow_lateral, only : gwflow_lateral_init, gwflow_lateral_calc, &
                               gwflow_lateral_dispose
  use m_gwflow_layer2, only : gwflow_layer2_init, gwflow_layer2_calc, &
                              gwflow_layer2_dispose
  use m_gwflow_conduit, only : gwflow_conduit_init, gwflow_conduit_calc, &
                               gwflow_conduit_dispose
  use m_gwflow_pump, only : gwflow_pump_init, gwflow_pump_calc, gwflow_pump_dispose
  use m_gwflow_frost, only : gwflow_frost_init, gwflow_frost_calc, gwflow_frost_dispose
  use m_meteo, only : t_meteo
  use m_parallel, only : par_stop, par_allreduce_max, dcp
  use m_util, only : itoa
  implicit none
  private
  public :: t_gwflow
  public :: m_gwflow_init
  public :: m_gwflow_check_meteo
  public :: m_gwflow_calc
  public :: m_gwflow_dispose

  !-------------------------------------------
  ! 地下水モデルのインターフェース
  ! (型成分で参照するため、型定義より前に置くこと)
  !-------------------------------------------
  abstract interface
    subroutine procedure_gwflow_init(p, g, s)
      import :: t_sysparam, t_geoinfo, t_state
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
    end subroutine

    subroutine procedure_gwflow_calc(p, g, s, it, dts)
      import :: t_sysparam, t_geoinfo, t_state
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
      integer, intent(in) :: it
      real, intent(in) :: dts        ! 実効時間刻み(p%dt * idt_gwflow)(s)
    end subroutine

    subroutine procedure_gwflow_dispose(p)
      import :: t_sysparam
      type(t_sysparam), intent(in) :: p
    end subroutine
  end interface
  !-------------------------------------------


  type t_gwflow
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    ! init/calc/dispose は鉛直モデルの束縛(f_gwvertical=0 なら null の
    ! まま)。側方は単一モデル直接呼び出しで lat_enabled が実行判定
    procedure(procedure_gwflow_init),    pointer, nopass :: init    => null()
    procedure(procedure_gwflow_calc),    pointer, nopass :: calc    => null()
    procedure(procedure_gwflow_dispose), pointer, nopass :: dispose => null()
    logical :: enabled = .false.     ! モジュール有効(鉛直・側方・層2・管路層のいずれか)
    logical :: lat_enabled = .false. ! 側方流動の有効化(f_gwlateral=1)
    logical :: l2_enabled = .false.  ! 風化基岩層の有効化(f_gwlayer2=1)
    logical :: c_enabled = .false.   ! 管路連続体層の有効化(f_gwconduit=1)
    logical :: pump_enabled = .false. ! 井戸揚水の有効化(f_gwpump=1)
    logical :: frost_enabled = .false. ! 凍土による浸透抑制の有効化(f_gwfrost=1)
    integer :: idt_gwflow = 1        ! 更新間隔(ステップ数)
    real :: dts = 0.0                ! 実効時間刻み(p%dt * idt_gwflow)(s)
    logical :: initialized = .false.
  end type

contains


!----------------------------------------------------------------------
! 地下水モジュールを初期化する
!   fn_gwflow 未指定 or f_gwvertical=0 なら何もしない(enabled = .false.)
!   g は m_geoinfo_require_sd(土層厚の遅延確保)のため inout
!----------------------------------------------------------------------
subroutine m_gwflow_init(gw, p, g, s)
  type(t_gwflow), intent(out) :: gw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  type(t_state), intent(inout) :: s
  type(t_list_gwflow) :: list
  logical :: needs_sd
  real :: sdmax(1)

  if (len_trim(p%fn_gwflow) == 0) return

  call list_gwflow_read(p, list)

  ! --- 側方モデルの選択(当面 Boussinesq のみ。直接呼び出し) ---
  select case (list%f_gwlateral)
    case (0)
      gw%lat_enabled = .false.
    case (1)
      gw%lat_enabled = .true.
    case default
      call par_stop("list_gwflow: f_gwlateral must be 0(none) or 1(boussinesq): " &
                    // itoa(list%f_gwlateral))
  end select

  ! --- 風化基岩層(加算的プロセス。無効時は資源を一切確保しない) ---
  select case (list%f_gwlayer2)
    case (0)
      gw%l2_enabled = .false.
    case (1)
      gw%l2_enabled = .true.
    case default
      call par_stop("list_gwflow: f_gwlayer2 must be 0(none) or 1(weathered bedrock): " &
                    // itoa(list%f_gwlayer2))
  end select

  ! --- 管路連続体層(加算的プロセス。無効時は資源を一切確保しない) ---
  select case (list%f_gwconduit)
    case (0)
      gw%c_enabled = .false.
    case (1)
      gw%c_enabled = .true.
    case default
      call par_stop("list_gwflow: f_gwconduit must be 0(none) or 1(conduit continuum): " &
                    // itoa(list%f_gwconduit))
  end select

  ! --- 井戸揚水(加算的プロセス。無効時は資源を一切確保しない) ---
  select case (list%f_gwpump)
    case (0)
      gw%pump_enabled = .false.
    case (1)
      gw%pump_enabled = .true.
    case default
      call par_stop("list_gwflow: f_gwpump must be 0(none) or 1(wells): " &
                    // itoa(list%f_gwpump))
  end select

  ! --- 凍土による浸透抑制(鉛直浸透能の修飾。無効時は資源ゼロ) ---
  select case (list%f_gwfrost)
    case (0)
      gw%frost_enabled = .false.
    case (1)
      if (list%f_gwvertical == 0) then
        call par_stop("list_gwflow: f_gwfrost=1 requires a vertical model " &
                      // "(f_gwvertical=1 or 2)")
      end if
      gw%frost_enabled = .true.
    case default
      call par_stop("list_gwflow: f_gwfrost must be 0(none) or 1(frozen ground): " &
                    // itoa(list%f_gwfrost))
  end select

  ! すべて 0 なら fn を書いたまま一時無効化する経路
  if (list%f_gwvertical == 0 .and. .not. gw%lat_enabled .and. .not. gw%l2_enabled &
      .and. .not. gw%c_enabled .and. .not. gw%pump_enabled) return

  ! --- 鉛直モデルの束縛(新モデルの追加はここに case を足す) ---
  needs_sd = gw%lat_enabled .or. gw%l2_enabled   ! 側方・層2は土層厚を常に要する
  select case (list%f_gwvertical)
    case (0)
      ! 鉛直なし(側方のみ。初期条件の h_gw を側方流動だけで緩和する用途)
    case (1)
      ! バケツは側方と組めない: 容量が gw_capacity と sd*sy0 で二重定義に
      ! なり、どちらが小さくても意図しない挙動になる(developer.md §16.1)。
      ! 土層厚を容量とする定数浸透能モデルは greenampt + gw_psif=0 で表現できる
      if (gw%lat_enabled) then
        call par_stop("list_gwflow: f_gwvertical=1(bucket) cannot be combined with " &
                      // "f_gwlateral=1 (use f_gwvertical=2 greenampt; gw_psif=0 " &
                      // "gives a constant infiltration rate with capacity sd*sy0)")
      end if
      ! 層2も同じ理由で不可(底面標高 z-sd-d2 に実土層 sd が要る)
      if (gw%l2_enabled) then
        call par_stop("list_gwflow: f_gwvertical=1(bucket) cannot be combined with " &
                      // "f_gwlayer2=1 (use f_gwvertical=2 greenampt)")
      end if
      gw%init    => gwflow_bucket_init
      gw%calc    => gwflow_bucket_calc
      gw%dispose => gwflow_bucket_dispose
    case (2)
      gw%init    => gwflow_greenampt_init
      gw%calc    => gwflow_greenampt_calc
      gw%dispose => gwflow_greenampt_dispose
      needs_sd = .true.
    case default
      call par_stop("list_gwflow: f_gwvertical must be 0(none), 1(bucket) or 2(greenampt): " &
                    // itoa(list%f_gwvertical))
  end select

  ! --- 共通制御の解釈 ---
  if (list%dt_gwflow > 0.0) then
    gw%idt_gwflow = nint(list%dt_gwflow / p%dt)
    if (gw%idt_gwflow <= 0) call par_stop("list_gwflow: dt_gwflow must be >= dt")
  else
    gw%idt_gwflow = 1
  end if
  gw%dts = p%dt * gw%idt_gwflow

  ! 土層厚を要するモデルの遅延確保口(モデル init より前に。§16)。
  ! 確保後、動的共有状態 s%sd へ初期値を転記する(以後のカーネルは
  ! s%sd を読む。g%sd は入力係数として init 検証にのみ残る。
  ! geomorph_plan.md §2.5: 浸食・堆積は s%sd を z と共動更新する)
  if (needs_sd) then
    call m_geoinfo_require_sd(g)
    if (p%f_state_restore > 0) then
      ! restore 時は転記しない(復元値が勝つ。「保存状態を初期条件に
      ! 使う」意味論。sd の入力係数を変えても restore には効かない)。
      ! ただし土層ゼロの save(gwflow 無効時に作成された save)を
      ! sd 必須モデルで使う設定齟齬は停止する(黙って容量ゼロの
      ! 地下水になるのを防ぐ)。判定は全ランク同一(collective 安全)
      sdmax(1) = maxval(s%sd(:, dcp%js:dcp%je))
      call par_allreduce_max(sdmax)
      if (sdmax(1) <= 0.0) then
        call par_stop("gwflow: restored state has zero soil depth (the state file was " &
                      // "created with gwflow disabled), disable restore or recreate the state file")
      end if
    else
      s%sd(:,:) = g%sd(:,:)
    end if
  end if

  gw%enabled = .true.
  s%gw_active = .true.               ! 質量台帳(S_grnd/S_total)と Log 列の拡張を有効化
  if (associated(gw%init)) call gw%init(p, g, s)
  if (gw%lat_enabled) call gwflow_lateral_init(p, g, s, gw%dts)
  if (gw%l2_enabled) call gwflow_layer2_init(p, g, s, gw%dts)
  ! 管路層は層2より後(gwc_leak_layer=2 が層2の有効化・定数を参照する)
  if (gw%c_enabled) call gwflow_conduit_init(p, g, s, gw%dts)
  ! 井戸揚水は層2より後(gwp_layer=2 が層2の有効化を参照する)
  if (gw%pump_enabled) call gwflow_pump_init(p, g, s)
  ! 凍土(s%frofac の確保。気温の存在検査は m_gwflow_check_meteo)
  if (gw%frost_enabled) call gwflow_frost_init(p, g, s)
  gw%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 凍土モデルの気温入力の存在検査(m_main が m_meteo_init の後に呼ぶ。
! m_gwflow_init は初期化順序の制約で meteo より先に走るため)
!----------------------------------------------------------------------
subroutine m_gwflow_check_meteo(gw, mt)
  type(t_gwflow), intent(in) :: gw
  type(t_meteo), intent(in) :: mt
  if (gw%frost_enabled .and. .not. mt%enabled) then
    call par_stop("list_gwflow: f_gwfrost=1 requires air temperature " &
                  // "(specify fn_meteo)")
  end if
end subroutine


!----------------------------------------------------------------------
! 地下水を計算する(run_main から毎ステップ呼ばれる)
!   冒頭の return 判定は全ランクで同一(collective 安全)
!----------------------------------------------------------------------
subroutine m_gwflow_calc(gw, p, g, s, mt, it)
  type(t_gwflow), intent(in) :: gw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_meteo), intent(inout) :: mt   ! 凍土の気温評価(分布気温の読み進みを保持)
  integer, intent(in) :: it

  if (.not. gw%enabled) return
  if (mod(it, gw%idt_gwflow) /= 0) return
  ! 凍土(s%frofac の更新)は鉛直浸透モデルより前(実行順序が結合仕様)
  if (gw%frost_enabled) call gwflow_frost_calc(p, g, s, mt, gw%dts)
  ! 鉛直(セル内)→ 側方(近傍結合)の順。側方 calc の冒頭で
  ! s%hg, s%h のハロを交換する(m_gwflow_lateral ヘッダ参照)
  if (associated(gw%calc)) call gw%calc(p, g, s, it, gw%dts)
  if (gw%lat_enabled) call gwflow_lateral_calc(p, g, s, it, gw%dts)
  ! 風化基岩層(層1→2 の鉛直浸透と層2内の側方流動。加算的)
  if (gw%l2_enabled) call gwflow_layer2_calc(p, g, s, it, gw%dts)
  ! 管路連続体層(地表交換→側方通水→層間交換。加算的。層2より後 =
  ! 上から下の順。この実行順序が結合仕様)
  if (gw%c_enabled) call gwflow_conduit_calc(p, g, s, it, gw%dts)
  ! 井戸揚水(輸送の後に取水 = 水位低下を次ステップの輸送が見る)
  if (gw%pump_enabled) call gwflow_pump_calc(p, g, s, it, gw%dts)
end subroutine


!----------------------------------------------------------------------
! 地下水モジュールを破棄する
!----------------------------------------------------------------------
subroutine m_gwflow_dispose(gw, p, g, s)
  type(t_gwflow), intent(inout) :: gw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (gw%enabled .and. associated(gw%dispose)) call gw%dispose(p)
  if (gw%l2_enabled) call gwflow_layer2_dispose(p, g, s)   ! save は dispose で(契約5)
  if (gw%c_enabled) call gwflow_conduit_dispose(p, g, s)   ! save は dispose で(契約5)
  if (gw%pump_enabled) call gwflow_pump_dispose(p, g)      ! 取水総括の表示(内部状態なし)
  if (gw%frost_enabled) call gwflow_frost_dispose(p, g)    ! save は dispose で(契約5)
  ! 幾何・エッジ作業領域は層間共有のため、どれかが使っていれば破棄する
  if (gw%lat_enabled .or. gw%l2_enabled .or. gw%c_enabled) call gwflow_lateral_dispose(p)
  gw%init    => null()
  gw%calc    => null()
  gw%dispose => null()
  gw%enabled = .false.
  gw%lat_enabled = .false.
  gw%l2_enabled = .false.
  gw%c_enabled = .false.
  gw%pump_enabled = .false.
  gw%frost_enabled = .false.
  gw%initialized = .false.
end subroutine

end module
